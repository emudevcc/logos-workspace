// Pronúncia PT — minimal pairs and pronunciation pitfalls for Spanish speakers.

import { apiGet } from "../lib/api.js";
import { clear, h } from "../lib/dom.js";
import { pronounceButton } from "../lib/pronounce.js";

/**
 * @param {HTMLElement} slot
 */
export function init(slot) {
  const tabs = h("div", { class: "segmented pt-tabs" });
  const pairsTab = h("button", { type: "button", class: "chip", text: "Pares mínimos" });
  const pitfallsTab = h("button", { type: "button", class: "chip", text: "Pegadinhas" });
  const body = h("div");
  tabs.append(pairsTab, pitfallsTab);

  async function showPairs() {
    pairsTab.classList.add("is-active");
    pitfallsTab.classList.remove("is-active");
    clear(body);
    try {
      const pairs = await apiGet("/api/pt/pronunciation/minimal-pairs");
      const list = h("ul", { class: "pt-list" });
      for (const pair of pairs) {
        list.append(
          h(
            "li",
            { class: "pt-pair-row" },
            h("span", { class: "pt-keys", text: `${pair.a} / ${pair.b}` }),
            pronounceButton(pair.a, "🔊", "pt-BR"),
            pronounceButton(pair.b, "🔊", "pt-BR"),
            h("p", { class: "es-note", text: `🇪🇸 ${pair.nota_es}` }),
          ),
        );
      }
      body.append(list);
    } catch (error) {
      body.append(h("p", { class: "error", text: error.message }));
    }
  }

  async function showPitfalls() {
    pitfallsTab.classList.add("is-active");
    pairsTab.classList.remove("is-active");
    clear(body);
    try {
      const pitfalls = await apiGet("/api/pt/pronunciation/pitfalls");
      const list = h("ul", { class: "pt-list" });
      for (const pitfall of pitfalls) {
        list.append(
          h(
            "li",
            { class: "pt-pitfall" },
            h("strong", { text: pitfall.issue }),
            h("p", { text: pitfall.tip_pt }),
            pitfall.nota_es ? h("p", { class: "es-note", text: `🇪🇸 ${pitfall.nota_es}` }) : null,
          ),
        );
      }
      body.append(list);
    } catch (error) {
      body.append(h("p", { class: "error", text: error.message }));
    }
  }

  pairsTab.addEventListener("click", showPairs);
  pitfallsTab.addEventListener("click", showPitfalls);
  slot.append(tabs, body);
  showPairs();
}
