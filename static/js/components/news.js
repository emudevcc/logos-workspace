// Tech & Business News Pulse (headlines + vocab + comprehension quiz).

import { apiGet, apiPost } from "../lib/api.js";
import { clear, h } from "../lib/dom.js";

/**
 * @param {HTMLElement} slot
 * @param {{bus?: {on: Function}}} [ctx]
 */
export function init(slot, ctx) {
  async function load(fresh = false) {
    try {
      const data = await apiGet(fresh ? "/api/news?refresh=true" : "/api/news");
      clear(slot);
      if (!data.headlines.length) {
        slot.append(h("p", { class: "muted", text: "No headlines available right now." }));
        return;
      }
      const list = h("ul", { class: "news-list" });
      for (const headline of data.headlines) {
        list.append(buildItem(headline));
      }
      slot.append(list);
    } catch (error) {
      renderError(error);
    }
  }

  function renderError(error) {
    clear(slot);
    slot.append(
      h("p", { class: "error", text: `News unavailable: ${error.message}` }),
      h("button", { type: "button", class: "chip", text: "Retry", onclick: () => load(true) }),
    );
  }

  load();
  ctx?.bus?.on("content:refresh", () => load(true));
}

function buildItem(headline) {
  const quizBox = h("div", { class: "quiz" });
  const quizBtn = h("button", {
    type: "button",
    class: "chip",
    text: "Quiz",
    onclick: () => startQuiz(headline, quizBtn, quizBox),
  });

  const item = h(
    "li",
    { class: "news-item" },
    h(
      "a",
      { href: headline.link, target: "_blank", rel: "noopener", class: "news-title", text: headline.title },
    ),
    h("span", { class: "news-source", text: headline.source }),
  );
  if (headline.vocab.length) {
    const terms = h("ul", { class: "vocab-list" });
    for (const term of headline.vocab) {
      terms.append(
        h("li", { class: "vocab-term" }, h("strong", { text: term.term }), ` — ${term.definition}`),
      );
    }
    item.append(terms);
  }
  item.append(h("div", { class: "chips" }, quizBtn), quizBox);
  return item;
}

async function startQuiz(headline, button, quizBox) {
  button.disabled = true;
  button.textContent = "Generating…";
  clear(quizBox);
  try {
    const quiz = await apiPost("/api/quiz", { text: headline.title });
    renderQuiz(quiz, quizBox);
  } catch (error) {
    quizBox.append(h("p", { class: "error", text: error.message }));
  } finally {
    button.disabled = false;
    button.textContent = "Quiz";
  }
}

function renderQuiz(quiz, quizBox) {
  clear(quizBox);
  quizBox.append(h("p", { class: "quiz-question", text: quiz.question }));
  const options = shuffle([quiz.correct_answer, ...quiz.distractors]);
  for (const option of options) {
    quizBox.append(
      h("button", {
        type: "button",
        class: "chip",
        text: option,
        onclick: () => {
          for (const btn of quizBox.querySelectorAll("button")) btn.disabled = true;
          quizBox.append(
            h(
              "p",
              { class: option === quiz.correct_answer ? "quiz-correct" : "quiz-wrong" },
              option === quiz.correct_answer
                ? "✓ Correct"
                : `✗ Correct answer: ${quiz.correct_answer}`,
            ),
          );
        },
      }),
    );
  }
}

function shuffle(items) {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}
