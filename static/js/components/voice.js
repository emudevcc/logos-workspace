// Voice Conversational Partner & Scenario Roleplay (push-to-talk).

import { apiPost } from "../lib/api.js";
import { h } from "../lib/dom.js";

const MAX_HISTORY_TURNS = 20;
const MAX_LOG_LINES = 20;

/**
 * @param {HTMLElement} slot
 */
export function init(slot) {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    slot.append(h("p", { class: "error", text: "Speech recognition is not supported in this browser." }));
    return;
  }

  const scenarioInput = h("input", {
    class: "voice-scenario",
    value: "Client Q&A: explain a project delay",
    "aria-label": "Roleplay scenario",
  });
  const talkBtn = h("button", { class: "primary", type: "button", text: "Hold to talk" });
  const logEl = h("div", { class: "voice-log", "aria-live": "polite" });
  const history = [];

  slot.append(
    h("p", { class: "muted", text: "Hold the button (or hold Space/Enter) to speak." }),
    scenarioInput,
    talkBtn,
    logEl,
  );

  const recognition = new Recognition();
  recognition.lang = "en-US";
  recognition.interimResults = false;
  recognition.continuous = false;

  let finalTranscript = "";

  recognition.onresult = (event) => {
    finalTranscript = Array.from(event.results)
      .map((result) => result[0].transcript)
      .join(" ");
  };

  recognition.onend = async () => {
    talkBtn.disabled = false;
    const userSays = finalTranscript.trim();
    finalTranscript = "";
    if (!userSays) return;

    appendLine(h("p", { class: "voice-user" }, h("strong", { text: "You: " }), userSays));
    try {
      const data = await apiPost("/api/voice/turn", {
        scenario: scenarioInput.value,
        user_says: userSays,
        history,
      });
      history.push({ role: "user", text: userSays }, { role: "partner", text: data.partner_says });
      if (history.length > MAX_HISTORY_TURNS) history.splice(0, history.length - MAX_HISTORY_TURNS);
      appendLine(h("p", { class: "voice-partner" }, h("strong", { text: "Partner: " }), data.partner_says));
      speak(data.partner_says);
    } catch (error) {
      appendLine(h("p", { class: "error", text: error.message }));
    }
  };

  recognition.onerror = () => {
    talkBtn.disabled = false;
  };

  function appendLine(node) {
    logEl.append(node);
    while (logEl.childElementCount > MAX_LOG_LINES) logEl.removeChild(logEl.firstChild);
  }

  function speak(text) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-US";
    window.speechSynthesis.speak(utterance);
  }

  function startHold(event) {
    event.preventDefault();
    try {
      recognition.start();
      talkBtn.disabled = true;
    } catch {
      talkBtn.disabled = false;
    }
  }

  function endHold(event) {
    event.preventDefault();
    recognition.stop();
  }

  talkBtn.addEventListener("mousedown", startHold);
  talkBtn.addEventListener("mouseup", endHold);
  talkBtn.addEventListener("touchstart", startHold);
  talkBtn.addEventListener("touchend", endHold);
  talkBtn.addEventListener("keydown", (event) => {
    if (event.key === " " || event.key === "Enter") startHold(event);
  });
  talkBtn.addEventListener("keyup", (event) => {
    if (event.key === " " || event.key === "Enter") endHold(event);
  });
}
