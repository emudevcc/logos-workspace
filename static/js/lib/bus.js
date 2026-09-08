// Minimal typed pub/sub bus for wiring WebSocket messages to components.

/**
 * @returns {{on: (type: string, fn: Function) => () => void, emit: (type: string, payload: any) => void}}
 */
export function createBus() {
  const listeners = new Map();

  function on(type, fn) {
    if (!listeners.has(type)) listeners.set(type, new Set());
    listeners.get(type).add(fn);
    return () => listeners.get(type)?.delete(fn);
  }

  function emit(type, payload) {
    const set = listeners.get(type);
    if (!set) return;
    for (const fn of [...set]) fn(payload);
  }

  return { on, emit };
}
