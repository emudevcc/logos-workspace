// Auto-reconnecting WebSocket client with exponential backoff (1s -> 15s cap).

import { backoffDelay } from "./lib/backoff.js";

/**
 * @param {object} options
 * @param {string} options.url
 * @param {() => void} [options.onOpen]
 * @param {(message: any) => void} [options.onMessage]
 * @param {() => void} [options.onClose]
 * @param {(state: "online" | "offline") => void} [options.onStatus]
 * @param {typeof WebSocket} [options.WebSocketImpl]
 * @param {typeof setTimeout} [options.setTimeoutFn]
 * @param {typeof clearTimeout} [options.clearTimeoutFn]
 * @returns {{connect: () => void, send: (payload: any) => void, close: () => void}}
 */
export function createWsClient({
  url,
  onOpen,
  onMessage,
  onClose,
  onStatus,
  WebSocketImpl = globalThis.WebSocket,
  setTimeoutFn = setTimeout,
  clearTimeoutFn = clearTimeout,
} = {}) {
  let socket = null;
  let attempt = 0;
  let reconnectTimer = null;
  let closedByUser = false;

  function connect() {
    socket = new WebSocketImpl(url);
    socket.addEventListener("open", () => {
      attempt = 0;
      onStatus?.("online");
      onOpen?.();
    });
    socket.addEventListener("message", (event) => {
      let data = event.data;
      try {
        data = JSON.parse(event.data);
      } catch {
        // Keep the raw string when the payload is not JSON.
      }
      // Answer the server heartbeat so the backend does not evict this peer.
      if (data && typeof data === "object" && data.type === "ping") {
        send({ type: "pong" });
      }
      onMessage?.(data);
    });
    socket.addEventListener("close", () => {
      onStatus?.("offline");
      onClose?.();
      if (!closedByUser) {
        attempt += 1;
        reconnectTimer = setTimeoutFn(connect, backoffDelay(attempt));
      }
    });
  }

  function send(payload) {
    if (!socket || socket.readyState !== WebSocketImpl.OPEN) return;
    if (payload instanceof ArrayBuffer || ArrayBuffer.isView(payload)) {
      socket.send(payload); // raw binary frame (e.g. audio PCM)
    } else {
      socket.send(JSON.stringify(payload));
    }
  }

  function close() {
    closedByUser = true;
    if (reconnectTimer != null) clearTimeoutFn(reconnectTimer);
    socket?.close();
  }

  return { connect, send, close };
}
