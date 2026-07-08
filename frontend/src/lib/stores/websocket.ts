/**
 * Svelte store managing the backend WebSocket connection lifecycle.
 *
 * Exposes a readable connection status plus imperative helpers to connect,
 * disconnect, reconnect, and send the discovery command. Reconnection is
 * manual only: the store never reconnects on its own after a close or error.
 */

import { writable, type Readable } from "svelte/store";

import {
  DEFAULT_WS_URL,
  discoverCommand,
  parseServerMessage,
  type ServerMessage,
} from "$lib/protocol";

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
 * Creates a WebSocket connection store.
 *
 * @param defaultUrl - The endpoint used when `connect` is called without a URL.
 * @returns A readable status store with connection helpers.
 */
export function createWebSocketStore(
  defaultUrl: string = DEFAULT_WS_URL,
): WebSocketStore {
  const { subscribe, set } = writable<ConnectionStatus>("idle");

  let socket: WebSocket | null = null;
  let currentUrl = defaultUrl;
  const handlers = new Set<MessageHandler>();

  function teardownSocket(): void {
    if (socket === null) {
      return;
    }
    socket.onopen = null;
    socket.onclose = null;
    socket.onerror = null;
    socket.onmessage = null;
    socket.close();
    socket = null;
  }

  function connect(url: string = currentUrl): void {
    teardownSocket();
    currentUrl = url;
    set("connecting");

    socket = new WebSocket(url);
    socket.onopen = () => set("open");
    socket.onclose = () => set("closed");
    socket.onerror = () => set("error");
    socket.onmessage = (event: MessageEvent) => {
      const message = parseServerMessage(String(event.data));
      if (message !== null) {
        handlers.forEach((handler) => handler(message));
      }
    };
  }

  function disconnect(): void {
    teardownSocket();
    set("closed");
  }

  function reconnect(url: string = currentUrl): void {
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
