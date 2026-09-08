// Minimal DOM construction helpers (safe: text is always assigned via textContent).

/**
 * Create an element.
 * @param {string} tag
 * @param {Record<string, any>} [props]
 * @param {...(Node|string|number|false|null|undefined|Array)} children
 * @returns {HTMLElement}
 */
export function h(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") {
      node.className = value;
    } else if (key === "text") {
      node.textContent = value;
    } else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (value === true) {
      node.setAttribute(key, "");
    } else if (value !== false && value !== null && value !== undefined) {
      node.setAttribute(key, String(value));
    }
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

/**
 * Remove all child nodes.
 * @param {HTMLElement} node
 */
export function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}
