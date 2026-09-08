import { test } from "node:test";
import assert from "node:assert/strict";

import { createWsClient } from "../../static/js/ws_client.js";

class FakeWebSocket {
  static OPEN = 1;
  static instances = [];

  constructor(url) {
    this.url = url;
    this.readyState = 0;
    this.listeners = {};
    this.sent = [];
    FakeWebSocket.instances.push(this);
  }

  addEventListener(type, fn) {
    (this.listeners[type] ||= []).push(fn);
  }

  send(data) {
    this.sent.push(data);
  }

  close() {
    this._emit("close");
  }

  _open() {
    this.readyState = FakeWebSocket.OPEN;
    this._emit("open");
  }

  _message(data) {
    this._emit("message", { data });
  }

  _emit(type, event = {}) {
    for (const fn of this.listeners[type] || []) fn(event);
  }
}

function makeClient(overrides = {}) {
  const timers = [];
  const client = createWsClient({
    url: "ws://x",
    WebSocketImpl: FakeWebSocket,
    setTimeoutFn: (fn, ms) => {
      timers.push({ fn, ms });
      return timers.length;
    },
    clearTimeoutFn: () => {},
    ...overrides,
  });
  return { client, timers };
}

test("reconnects with backoff after close", () => {
  FakeWebSocket.instances = [];
  const { client, timers } = makeClient();
  client.connect();

  const first = FakeWebSocket.instances[0];
  first._open();
  first._emit("close");
  assert.equal(timers.length, 1);
  assert.equal(timers[0].ms, 1000);

  timers[0].fn();
  const second = FakeWebSocket.instances[1];
  assert.ok(second);
  second._emit("close");
  assert.equal(timers.length, 2);
  assert.equal(timers[1].ms, 2000);
});

test("open resets the backoff attempt counter", () => {
  FakeWebSocket.instances = [];
  const { client, timers } = makeClient();
  client.connect();

  const first = FakeWebSocket.instances[0];
  first._open();
  first._emit("close");
  assert.equal(timers[0].ms, 1000);

  timers[0].fn();
  const second = FakeWebSocket.instances[1];
  second._open(); // resets attempt to 0
  second._emit("close");
  assert.equal(timers.length, 2);
  assert.equal(timers[1].ms, 1000);
});

test("close prevents reconnection", () => {
  FakeWebSocket.instances = [];
  const { client, timers } = makeClient();
  client.connect();
  const socket = FakeWebSocket.instances[0];
  client.close();
  socket._emit("close");
  assert.equal(timers.length, 0);
});

test("answers server ping with pong", () => {
  FakeWebSocket.instances = [];
  const { client } = makeClient();
  client.connect();
  const socket = FakeWebSocket.instances[0];
  socket._open();
  socket._message('{"type":"ping"}');
  assert.deepEqual(socket.sent, ['{"type":"pong"}']);
});

test("send with binary payload sends raw bytes", () => {
  FakeWebSocket.instances = [];
  const { client } = makeClient();
  client.connect();
  const socket = FakeWebSocket.instances[0];
  socket._open();
  const buffer = new ArrayBuffer(4);
  client.send(buffer);
  assert.equal(socket.sent.length, 1);
  assert.equal(socket.sent[0], buffer);
});

test("parses JSON messages before dispatching", () => {
  FakeWebSocket.instances = [];
  let received;
  const { client } = makeClient({ onMessage: (message) => (received = message) });
  client.connect();
  const socket = FakeWebSocket.instances[0];
  socket._message('{"type":"ping"}');
  assert.deepEqual(received, { type: "ping" });
});
