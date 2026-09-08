// Livros — browse the 66-book registry with conservative profile facts.

import { apiGet } from "../lib/api.js";
import { clear, h } from "../lib/dom.js";

/**
 * @param {HTMLElement} slot
 */
export function init(slot) {
  async function load() {
    clear(slot);
    try {
      const books = await apiGet("/api/bible/books");
      renderGroups(slot, books);
    } catch (error) {
      slot.append(h("p", { class: "error", text: error.message }));
    }
  }

  function renderGroups(container, books) {
    const byTestament = {
      AT: books.filter((book) => book.testament === "AT"),
      NT: books.filter((book) => book.testament === "NT"),
    };
    for (const [testament, label] of [
      ["AT", "Antigo Testamento (39)"],
      ["NT", "Novo Testamento (27)"],
    ]) {
      const group = h("div", { class: "bible-book-group" });
      group.append(h("h5", { class: "bible-subtitle", text: label }));
      const list = h("ul", { class: "bible-book-list" });
      for (const book of byTestament[testament] || []) {
        list.append(
          h(
            "li",
            { class: "bible-book-row" },
            h("span", { class: "bible-book-name", text: `${book.name_pt} (${book.code})` }),
            h("span", { class: "muted", text: book.genre }),
            h("p", {
              class: "bible-note",
              text: `${book.author} · ${book.date} · ${book.occasion}`,
            }),
          ),
        );
      }
      group.append(list);
      container.append(group);
    }
  }

  load();
}
