/** Unit tests for the WebSocket connection store. */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { get } from "svelte/store";

import { DEFAULT_WS_URL } from "$lib/protocol";
import { createWebSocketStore, RETRY_DELAY_MS } from "$lib/stores/websocket";

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
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

/**
 * Returns sockets whose handlers are still attached to the store.
 *
 * @returns Instances the store has not released.
 */
function liveSockets(): MockWebSocket[] {
  return MockWebSocket.instances.filter((socket) => socket.onclose !== null);
}

/**
 * Simulates a production browser page served from the given origin.
 *
 * @param protocol - Page scheme, such as `http:` or `https:`.
 * @param host - Page host including any port.
 */
function stubBrowserPage(protocol: string, host: string): void {
  vi.stubEnv("DEV", false);
  vi.stubGlobal("window", { location: { protocol, host } });
}

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

describe("automatic retry", () => {
  it("retries shortly after the fixed delay following a close", () => {
    const store = createWebSocketStore("ws://example:1");

    store.connect();
    MockWebSocket.instances[0].emitClose();
    vi.advanceTimersByTime(RETRY_DELAY_MS - 1);
    expect(MockWebSocket.instances).toHaveLength(1);
    expect(get(store)).toBe("closed");

    vi.advanceTimersByTime(1);
    expect(MockWebSocket.instances).toHaveLength(2);
    expect(MockWebSocket.instances[1].url).toBe("ws://example:1");
    expect(get(store)).toBe("connecting");
  });

  it("keeps retrying across repeated failures", () => {
    const store = createWebSocketStore();

    store.connect();
    for (let attempt = 0; attempt < 3; attempt++) {
      MockWebSocket.instances[attempt].emitError();
      vi.advanceTimersByTime(RETRY_DELAY_MS);
    }

    expect(MockWebSocket.instances).toHaveLength(4);
    expect(liveSockets()).toHaveLength(1);
  });

  it("schedules one retry when an error is followed by close", () => {
    const store = createWebSocketStore();

    store.connect();
    const socket = MockWebSocket.instances[0];
    socket.emitError();
    socket.emitClose();

    expect(get(store)).toBe("error");
    expect(socket.close).toHaveBeenCalledOnce();
    expect(vi.getTimerCount()).toBe(1);
    vi.advanceTimersByTime(RETRY_DELAY_MS * 3);
    expect(MockWebSocket.instances).toHaveLength(2);
  });

  it("returns to open after a successful retry", () => {
    const store = createWebSocketStore();

    store.connect();
    MockWebSocket.instances[0].emitClose();
    vi.advanceTimersByTime(RETRY_DELAY_MS);
    MockWebSocket.instances[1].open();

    expect(get(store)).toBe("open");
    expect(vi.getTimerCount()).toBe(0);
  });

  it("cancels a pending retry on disconnect", () => {
    const store = createWebSocketStore();

    store.connect();
    MockWebSocket.instances[0].emitClose();
    store.disconnect();
    vi.advanceTimersByTime(RETRY_DELAY_MS * 5);

    expect(MockWebSocket.instances).toHaveLength(1);
    expect(vi.getTimerCount()).toBe(0);
    expect(get(store)).toBe("closed");
  });

  it.each([
    ["error", (socket: MockWebSocket) => socket.emitError()],
    ["closed", (socket: MockWebSocket) => socket.emitClose()],
  ] as const)(
    "does not retry when a subscriber disconnects on %s",
    (status, fail) => {
      const store = createWebSocketStore();
      const unsubscribe = store.subscribe((value) => {
        if (value === status) {
          store.disconnect();
        }
      });

      store.connect();
      fail(MockWebSocket.instances[0]);
      vi.advanceTimersByTime(RETRY_DELAY_MS);
      unsubscribe();

      expect(MockWebSocket.instances).toHaveLength(1);
      expect(vi.getTimerCount()).toBe(0);
      expect(get(store)).toBe("closed");
    },
  );

  it("does not retry when a disconnected socket later fires events", () => {
    const store = createWebSocketStore();

    store.connect();
    const socket = MockWebSocket.instances[0];
    const { onclose, onerror } = socket;
    store.disconnect();
    onerror?.();
    onclose?.();
    vi.advanceTimersByTime(RETRY_DELAY_MS * 5);

    expect(MockWebSocket.instances).toHaveLength(1);
    expect(get(store)).toBe("closed");
  });

  it("reconnects immediately and cancels the pending retry", () => {
    const store = createWebSocketStore();

    store.connect();
    MockWebSocket.instances[0].emitClose();
    store.reconnect();

    expect(MockWebSocket.instances).toHaveLength(2);
    expect(vi.getTimerCount()).toBe(0);
    vi.advanceTimersByTime(RETRY_DELAY_MS * 5);
    expect(MockWebSocket.instances).toHaveLength(2);
  });

  it("ignores stale events from a replaced socket", () => {
    const store = createWebSocketStore();
    const received: unknown[] = [];
    store.onMessage((message) => received.push(message));

    store.connect();
    const stale = MockWebSocket.instances[0];
    const { onopen, onclose, onerror, onmessage } = stale;
    store.reconnect();
    const fresh = MockWebSocket.instances[1];
    fresh.open();
    onerror?.();
    onclose?.();
    onopen?.();
    onmessage?.({
      data: JSON.stringify({ type: "discover_result", streams: [] }),
    } as MessageEvent);
    vi.advanceTimersByTime(RETRY_DELAY_MS * 5);

    expect(get(store)).toBe("open");
    expect(received).toEqual([]);
    expect(MockWebSocket.instances).toHaveLength(2);
    expect(store.sendDiscover()).toBe(true);
    expect(fresh.sent).toHaveLength(1);
  });
});

describe("default URL resolution", () => {
  it("uses the page host over ws for http production pages", () => {
    stubBrowserPage("http:", "example.com:9000");
    const store = createWebSocketStore();

    store.connect();

    expect(MockWebSocket.instances[0].url).toBe("ws://example.com:9000/");
  });

  it("uses wss for https production pages", () => {
    stubBrowserPage("https:", "example.com");
    const store = createWebSocketStore();

    store.connect();

    expect(MockWebSocket.instances[0].url).toBe("wss://example.com/");
  });

  it("resolves at connect time rather than at creation", () => {
    const store = createWebSocketStore();
    stubBrowserPage("https:", "late.example");

    store.connect();

    expect(MockWebSocket.instances[0].url).toBe("wss://late.example/");
  });

  it("falls back to the local endpoint in dev mode", () => {
    vi.stubEnv("DEV", true);
    vi.stubGlobal("window", {
      location: { protocol: "https:", host: "example.com" },
    });
    const store = createWebSocketStore();

    store.connect();

    expect(MockWebSocket.instances[0].url).toBe(DEFAULT_WS_URL);
  });

  it("falls back to the local endpoint outside a browser", () => {
    vi.stubEnv("DEV", false);
    vi.stubGlobal("window", undefined);
    const store = createWebSocketStore();

    store.connect();

    expect(MockWebSocket.instances[0].url).toBe(DEFAULT_WS_URL);
  });

  it("prefers explicit factory and connect URLs", () => {
    stubBrowserPage("https:", "example.com");
    const factoryStore = createWebSocketStore("ws://factory:1");
    factoryStore.connect();
    const connectStore = createWebSocketStore("ws://factory:1");
    connectStore.connect("ws://override:2");

    expect(MockWebSocket.instances.map((socket) => socket.url)).toEqual([
      "ws://factory:1",
      "ws://override:2",
    ]);
  });

  it("reuses the selected URL for automatic and manual retries", () => {
    stubBrowserPage("https:", "example.com");
    const store = createWebSocketStore();

    store.connect("ws://chosen:3");
    MockWebSocket.instances[0].emitClose();
    vi.advanceTimersByTime(RETRY_DELAY_MS);
    store.reconnect();
    store.reconnect("ws://explicit:4");
    MockWebSocket.instances[3].emitError();
    vi.advanceTimersByTime(RETRY_DELAY_MS);

    expect(MockWebSocket.instances.map((socket) => socket.url)).toEqual([
      "ws://chosen:3",
      "ws://chosen:3",
      "ws://chosen:3",
      "ws://explicit:4",
      "ws://explicit:4",
    ]);
  });
});
