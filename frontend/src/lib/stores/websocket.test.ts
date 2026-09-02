/** Unit tests for the WebSocket connection store. */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { get } from "svelte/store";

import { createWebSocketStore } from "$lib/stores/websocket";

/** Minimal controllable WebSocket double for exercising the store. */
class MockWebSocket {
  static readonly OPEN = 1;
  static instances: MockWebSocket[] = [];

  readyState = 0;
  sent: string[] = [];
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;

  constructor(public url: string) {
    MockWebSocket.instances.push(this);
  }

  send(payload: string): void {
    this.sent.push(payload);
  }

  close = vi.fn(() => {
    this.readyState = 3;
  });

  open(): void {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.();
  }

  emitClose(): void {
    this.onclose?.();
  }

  emitError(): void {
    this.onerror?.();
  }

  emitMessage(data: string): void {
    this.onmessage?.({ data } as MessageEvent);
  }
}

beforeEach(() => {
  MockWebSocket.instances = [];
  vi.stubGlobal("WebSocket", MockWebSocket);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("connect", () => {
  it("starts in the idle state", () => {
    const store = createWebSocketStore();

    expect(get(store)).toBe("idle");
  });

  it("uses the default endpoint when no URL is given", () => {
    const store = createWebSocketStore("ws://localhost:8765");

    store.connect();

    expect(MockWebSocket.instances[0].url).toBe("ws://localhost:8765");
  });

  it("transitions to connecting then open", () => {
    const store = createWebSocketStore();

    store.connect();
    expect(get(store)).toBe("connecting");

    MockWebSocket.instances[0].open();
    expect(get(store)).toBe("open");
  });

  it("transitions to error when the socket errors", () => {
    const store = createWebSocketStore();

    store.connect();
    const socket = MockWebSocket.instances[0];
    socket.emitError();
    socket.emitClose();

    expect(get(store)).toBe("error");
  });

  it("transitions to closed when the server closes the socket", () => {
    const store = createWebSocketStore();

    store.connect();
    MockWebSocket.instances[0].emitClose();

    expect(get(store)).toBe("closed");
  });
});

describe("disconnect", () => {
  it("closes the socket and reports the closed state", () => {
    const store = createWebSocketStore();

    store.connect();
    const socket = MockWebSocket.instances[0];
    store.disconnect();

    expect(socket.close).toHaveBeenCalledOnce();
    expect(get(store)).toBe("closed");
  });
});

describe("reconnect", () => {
  it("opens a fresh socket on the same endpoint", () => {
    const store = createWebSocketStore("ws://localhost:8765");

    store.connect();
    store.reconnect();

    expect(MockWebSocket.instances).toHaveLength(2);
    expect(MockWebSocket.instances[1].url).toBe("ws://localhost:8765");
    expect(get(store)).toBe("connecting");
  });

  it("does not replace an existing socket when connect is called again", () => {
    const store = createWebSocketStore();

    store.connect();
    store.connect();

    expect(MockWebSocket.instances).toHaveLength(1);
  });
});

describe("sendDiscover", () => {
  it("sends the discover command when the socket is open", () => {
    const store = createWebSocketStore();

    store.connect();
    MockWebSocket.instances[0].open();
    const ok = store.sendDiscover();

    expect(ok).toBe(true);
    expect(MockWebSocket.instances[0].sent).toEqual([
      JSON.stringify({ command: "discover" }),
    ]);
  });

  it("does nothing when the socket is not open", () => {
    const store = createWebSocketStore();

    store.connect();
    const ok = store.sendDiscover();

    expect(ok).toBe(false);
    expect(MockWebSocket.instances[0].sent).toEqual([]);
  });
});

describe("onMessage", () => {
  it("forwards decoded server messages to subscribers", () => {
    const store = createWebSocketStore();
    const received: unknown[] = [];

    store.connect();
    store.onMessage((message) => received.push(message));
    MockWebSocket.instances[0].emitMessage(
      JSON.stringify({ type: "discover_result", streams: ["EEG"] }),
    );

    expect(received).toEqual([{ type: "discover_result", streams: ["EEG"] }]);
  });

  it("stops forwarding after the handler is removed", () => {
    const store = createWebSocketStore();
    const received: unknown[] = [];

    store.connect();
    const unsubscribe = store.onMessage((message) => received.push(message));
    unsubscribe();
    MockWebSocket.instances[0].emitMessage(
      JSON.stringify({ type: "discover_result", streams: ["EEG"] }),
    );

    expect(received).toEqual([]);
  });
});
