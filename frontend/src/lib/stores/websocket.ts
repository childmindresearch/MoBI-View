/**
 * Svelte store managing the backend WebSocket connection lifecycle.
 *
 * Exposes a readable connection status plus imperative helpers to connect,
 * disconnect, reconnect, and send the discovery command. After an unexpected
 * close or error the store retries the same URL every `RETRY_DELAY_MS` until
 * `disconnect` is called; `reconnect` skips the wait and connects immediately.
 */

import { writable, type Readable } from "svelte/store";

import {
  DEFAULT_WS_URL,
  discoverCommand,
  parseServerMessage,
  type ServerMessage,
} from "$lib/protocol";

/** Fixed delay before automatically retrying a dropped connection. */
export const RETRY_DELAY_MS = 1500;

/** Lifecycle states for the backend WebSocket connection. */
export type ConnectionStatus =
  | "idle"
  | "connecting"
  | "open"
  | "closed"
  | "error";

/** Callback invoked for every decoded server message. */
export type MessageHandler = (message: ServerMessage) => void;

/** Public surface of the WebSocket connection store. */
export interface WebSocketStore extends Readable<ConnectionStatus> {
  connect: (url?: string) => void;
  disconnect: () => void;
  reconnect: (url?: string) => void;
  sendDiscover: () => boolean;
  onMessage: (handler: MessageHandler) => () => void;
}

/**
 * Resolves the endpoint used when no explicit URL is supplied.
 *
 * Production browser builds connect to the serving host's root path, matching
 * the page scheme (`https:` -> `wss:`). Dev mode and non-browser (SSR/test)
 * contexts fall back to `DEFAULT_WS_URL`.
 *
 * @returns The WebSocket URL for the current runtime context.
 */
function resolveDefaultUrl(): string {
  if (import.meta.env.DEV || typeof window === "undefined") {
    return DEFAULT_WS_URL;
  }
  const { protocol, host } = window.location;
  const scheme = protocol === "https:" ? "wss:" : "ws:";
  return `${scheme}//${host}/`;
}

/**
 * Creates a WebSocket connection store.
 *
 * @param defaultUrl - Endpoint used when `connect` is called without a URL;
 *   when omitted, it is resolved from the runtime context at connect time.
 * @returns A readable status store with connection helpers.
 */
export function createWebSocketStore(defaultUrl?: string): WebSocketStore {
  const { subscribe, set } = writable<ConnectionStatus>("idle");

  let socket: WebSocket | null = null;
  let currentUrl: string | null = defaultUrl ?? null;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  const handlers = new Set<MessageHandler>();

  /** Cancels any pending automatic retry. */
  function cancelRetry(): void {
    if (retryTimer !== null) {
      clearTimeout(retryTimer);
      retryTimer = null;
    }
  }

  /**
   * Detaches all handlers from a socket and closes it.
   *
   * @param target - The socket to release.
   */
  function releaseSocket(target: WebSocket): void {
    target.onopen = null;
    target.onclose = null;
    target.onerror = null;
    target.onmessage = null;
    target.close();
  }

  /** Releases the active socket, if any, and clears the shared reference. */
  function teardownSocket(): void {
    if (socket === null) {
      return;
    }
    releaseSocket(socket);
    socket = null;
  }

  /**
   * Handles an unexpected close or error of the active socket by releasing it
   * and scheduling a single retry against the same URL.
   *
   * @param target - The socket that reported the failure.
   * @param status - The status to publish while waiting to retry.
   */
  function handleFailure(target: WebSocket, status: ConnectionStatus): void {
    if (socket !== target) {
      return;
    }
    teardownSocket();
    cancelRetry();
    // Schedule before notifying so a subscriber calling disconnect() cancels it.
    retryTimer = setTimeout(() => {
      retryTimer = null;
      connect();
    }, RETRY_DELAY_MS);
    set(status);
  }

  /**
   * Opens a socket unless one is already active, cancelling any pending retry.
   *
   * @param url - Endpoint override; defaults to the last selected URL, then
   *   the factory URL, then the runtime-resolved default.
   */
  function connect(url?: string): void {
    if (socket !== null) {
      return;
    }
    cancelRetry();

    const target = url ?? currentUrl ?? resolveDefaultUrl();
    currentUrl = target;
    set("connecting");

    const ws = new WebSocket(target);
    socket = ws;
    ws.onopen = () => {
      if (socket === ws) {
        set("open");
      }
    };
    ws.onclose = () => handleFailure(ws, "closed");
    // Browsers follow an error with close; releasing here keeps the error state.
    ws.onerror = () => handleFailure(ws, "error");
    ws.onmessage = (event: MessageEvent) => {
      if (socket !== ws) {
        return;
      }
      const message = parseServerMessage(String(event.data));
      if (message !== null) {
        handlers.forEach((handler) => handler(message));
      }
    };
  }

  /** Closes the active socket and suppresses automatic retries. */
  function disconnect(): void {
    cancelRetry();
    teardownSocket();
    set("closed");
  }

  /**
   * Replaces any socket or pending retry with an immediate new connection.
   *
   * @param url - Endpoint override; defaults to the last selected URL.
   */
  function reconnect(url?: string): void {
    cancelRetry();
    teardownSocket();
    connect(url);
  }

  function sendDiscover(): boolean {
    if (socket === null || socket.readyState !== WebSocket.OPEN) {
      return false;
    }
    socket.send(JSON.stringify(discoverCommand()));
    return true;
  }

  function onMessage(handler: MessageHandler): () => void {
    handlers.add(handler);
    return () => {
      handlers.delete(handler);
    };
  }

  return { subscribe, connect, disconnect, reconnect, sendDiscover, onMessage };
}

/** Shared application-wide WebSocket connection store. */
export const websocketStore = createWebSocketStore();
