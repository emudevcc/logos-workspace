// Gramática PT — regra do dia (with 'outra regra') + coach de gramática (LLM).

import { apiGet, apiPost } from "../lib/api.js";
import { clear, h } from "../lib/dom.js";

/**
 * @param {HTMLElement} slot
 */
export function init(slot) {
  const ruleBox = h("div", { class: "pt-rule" });
  const otherBtn = h("button", {
    type: "button",
    class: "chip",
    text: "Outra regra",
    onclick: nextRule,
  });
  const answerBox = h("div", { class: "pt-coach-answer" });
  const input = h("textarea", {
    class: "pt-coach-input",
    rows: 2,
    placeholder: "Pergunte algo de gramática (ex.: 'por que às vezes uso subjuntivo?')",
  });
  const askBtn = h("button", { type: "button", class: "chip", text: "Perguntar", onclick: ask });
  const coachStatus = h("p", { class: "srs-status", "aria-live": "polite" });

  let currentTitle = null;
  let busy = false;

  function renderRule(rule) {
    clear(ruleBox);
    currentTitle = rule.title;
    ruleBox.append(
      h("h4", { class: "pt-rule-title", text: rule.title }),
      h("p", { text: rule.regra_pt }),
    );
    if (rule.nota_es) ruleBox.append(h("p", { class: "es-note", text: `🇪🇸 ${rule.nota_es}` }));
    ruleBox.append(
      h("p", { class: "pt-rule-ok", text: `✓ ${rule.exemplo_ok}` }),
      rule.exemplo_err ? h("p", { class: "pt-rule-err", text: `✗ ${rule.exemplo_err}` }) : null,
    );
  }

  async function loadRuleOfDay() {
    try {
      const rule = await apiGet("/api/pt/grammar/rule-of-day");
      renderRule(rule);
    } catch (error) {
      clear(ruleBox);
      ruleBox.append(h("p", { class: "error", text: error.message }));
    }
  }

  async function nextRule() {
    try {
      const query = currentTitle
        ? `?exclude=${encodeURIComponent(currentTitle)}`
        : "";
      const rule = await apiGet(`/api/pt/grammar/rule-random${query}`);
      renderRule(rule);
    } catch (error) {
      coachStatus.textContent = error.message;
    }
  }

  async function ask() {
    const question = input.value.trim();
    if (!question || busy) return;
    busy = true;
    askBtn.disabled = true;
    askBtn.textContent = "Pensando…";
    clear(answerBox);
    try {
      const result = await apiPost("/api/pt/grammar/coach", { pergunta: question });
      answerBox.append(h("p", { text: result.resposta_pt }));
      if (result.nota_es) {
        answerBox.append(h("p", { class: "es-note", text: `🇪🇸 ${result.nota_es}` }));
      }
      if (result.exemplos && result.exemplos.length) {
        answerBox.append(
          h(
            "ul",
            { class: "wod-examples" },
            result.exemplos.map((example) => h("li", { text: example })),
          ),
        );
      }
    } catch (error) {
      coachStatus.textContent = `Não consegui responder: ${error.message}`;
    } finally {
      busy = false;
      askBtn.disabled = false;
      askBtn.textContent = "Perguntar";
    }
  }

  slot.append(
    h("h4", { class: "pt-section-title", text: "Regra do dia" }),
    ruleBox,
    h("div", { class: "chips" }, otherBtn),
    h("h4", { class: "pt-section-title", text: "Coach de gramática" }),
    input,
    h("div", { class: "chips" }, askBtn),
    answerBox,
    coachStatus,
  );

  loadRuleOfDay();
}
