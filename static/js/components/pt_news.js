// Notícias do Brasil — headlines from PT-BR feeds (no LLM, cached backend).

import { apiGet } from "../lib/api.js";
import { clear, h } from "../lib/dom.js";

/**
 * @param {HTMLElement} slot
 * @param {{bus?: {on: Function}}} [ctx]
 */
export function init(slot, ctx) {
  async function load(fresh = false) {
    try {
      const data = await apiGet(fresh ? "/api/pt/news?refresh=true" : "/api/pt/news");
      clear(slot);
      if (!data.headlines.length) {
        slot.append(h("p", { class: "muted", text: "Sem manchetes agora." }));
        return;
      }
      const list = h("ul", { class: "news-list" });
      for (const headline of data.headlines) {
        list.append(
          h(
            "li",
            { class: "news-item" },
            h(
              "a",
              {
                href: headline.url,
                target: "_blank",
                rel: "noopener",
                class: "news-title",
                text: headline.title,
              },
            ),
            h("span", { class: "news-source", text: headline.source }),
          ),
        );
      }
      slot.append(list);
    } catch (error) {
      renderError(error);
    }
  }

  function renderError(error) {
    clear(slot);
    slot.append(
      h("p", { class: "error", text: `Notícias indisponíveis: ${error.message}` }),
      h("button", { type: "button", class: "chip", text: "Tentar de novo", onclick: () => load(true) }),
    );
  }

  load();
  ctx?.bus?.on("content:refresh", () => load(true));
}
