// Daily Audio & Podcast Digest (Morning Brief) with an episode list.

import { apiGet, apiPost } from "../lib/api.js";
import { clear, h } from "../lib/dom.js";
import { highlightSegments } from "../lib/highlight.js";

/**
 * @param {HTMLElement} slot
 * @param {{bus?: {on: Function}}} [ctx]
 */
export function init(slot, ctx) {
  async function load(fresh = false) {
    try {
      const data = await apiGet(fresh ? "/api/podcast-digest?refresh=true" : "/api/podcast-digest");
      clear(slot);
      render(data);
    } catch (error) {
      renderError(error);
    }
  }

  function render(data) {
    slot.append(h("h3", { class: "subtitle", text: data.title }));

    const brief = h("div", { class: "brief" });
    for (const paragraph of data.brief) brief.append(h("p", { text: paragraph }));
    slot.append(brief);

    if (data.key_terms.length) {
      const terms = h("ul", { class: "vocab-list" });
      for (const term of data.key_terms) {
        terms.append(
          h("li", { class: "vocab-term" }, h("strong", { text: term.term }), ` — ${term.definition}`),
        );
      }
      slot.append(terms);
    }

    if (data.episodes.length) slot.append(buildEpisodes(data.episodes));
  }

  function renderError(error) {
    clear(slot);
    slot.append(
      h("p", { class: "error", text: `Digest unavailable: ${error.message}` }),
      h("button", { type: "button", class: "chip", text: "Retry", onclick: () => load(true) }),
    );
  }

  load();
  ctx?.bus?.on("content:refresh", () => load(true));
}

function buildEpisodes(episodes) {
  const audio = h("audio", { controls: true, preload: "none" });
  const nowPlaying = h("p", { class: "muted", text: "Select an episode to play" });

  const setRate = (rate) => () => {
    audio.playbackRate = rate;
  };
  const player = h(
    "div",
    { class: "audio-player" },
    nowPlaying,
    audio,
    h(
      "div",
      { class: "chips" },
      h("button", { class: "chip", type: "button", onclick: setRate(1), text: "1×" }),
      h("button", { class: "chip", type: "button", onclick: setRate(1.25), text: "1.25×" }),
    ),
  );

  const transcriptBox = h("div", { class: "podcast-transcript" });
  const list = h("ul", { class: "episode-list" });
  for (const episode of episodes) {
    const playBtn = h("button", {
      class: "chip",
      type: "button",
      text: "▶",
      title: "Play",
      onclick: () => play(episode),
    });
    const transcriptBtn = h("button", {
      class: "chip",
      type: "button",
      text: "Transcript",
      onclick: () => transcribe(episode, transcriptBox, transcriptBtn),
    });
    list.append(
      h(
        "li",
        { class: "episode-item" },
        h("span", { class: "episode-title", text: episode.title }),
        h("div", { class: "chips" }, playBtn, transcriptBtn),
      ),
    );
  }

  function play(episode) {
    if (!episode.audio_url) return;
    nowPlaying.textContent = episode.title;
    audio.src = episode.audio_url;
    audio.play().catch(() => {});
  }

  return h("div", { class: "podcast-episodes" }, player, list, transcriptBox);
}

async function transcribe(episode, container, button) {
  if (!episode.audio_url) {
    container.append(h("p", { class: "error", text: "No audio available for this episode." }));
    return;
  }
  button.disabled = true;
  button.textContent = "Transcribing…";
  clear(container);
  container.append(h("p", { class: "muted", text: "Transcribing…" }));
  try {
    const data = await apiPost("/api/radio/transcribe", { audio_url: episode.audio_url });
    clear(container);
    const paragraph = h("p", { class: "transcript-segment" });
    for (const part of highlightSegments(data.text)) {
      paragraph.append(part.mark ? h("mark", { text: part.text }) : part.text);
    }
    container.append(paragraph);
  } catch (error) {
    clear(container);
    container.append(h("p", { class: "error", text: error.message }));
  } finally {
    button.disabled = false;
    button.textContent = "Transcript";
  }
}
