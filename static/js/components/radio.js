// Live Radio & Teleprompter Feed.

import { apiGet } from "../lib/api.js";
import { floatTo16BitPCM } from "../lib/audio.js";
import { clear, h } from "../lib/dom.js";
import { highlightSegments } from "../lib/highlight.js";
import { createWsClient } from "../ws_client.js";

const MAX_HISTORY_LINES = 100;

/**
 * @param {HTMLElement} slot
 * @param {{bus: {on: Function}}} ctx
 */
export function init(slot, ctx) {
  // Live caption (interim, updates in place) + committed transcript history.
  const viewport = h("div", { class: "transcript-viewport" });
  const historyEl = h("div", { class: "transcript-history" });
  const captionEl = h("p", { class: "transcript-caption", "aria-live": "polite" });
  viewport.append(historyEl, captionEl);

  let audioEl = null;
  let graph = null; // { audioCtx, source, processor, ws, streaming, connected }
  let paused = false;

  const toggleBtn = h("button", {
    type: "button",
    class: "chip",
    text: "Live transcript: off",
    onclick: toggleLive,
  });
  const pauseBtn = h("button", {
    type: "button",
    class: "chip",
    text: "Pause",
    onclick: togglePause,
  });
  const clearBtn = h("button", {
    type: "button",
    class: "chip",
    text: "Clear",
    onclick: clearTranscript,
  });

  (async () => {
    try {
      const stations = await apiGet("/api/radio/stations");
      const select = h("select", { class: "station-select", "aria-label": "Select live station" });
      for (const station of stations) {
        select.append(h("option", { value: station.stream_url, text: station.name }));
      }
      // crossorigin=anonymous is required for the Web Audio API to capture a
      // cross-origin stream (otherwise MediaElementSource yields silence).
      const audio = h("audio", { controls: true, crossorigin: "anonymous" });
      audioEl = audio;
      if (stations.length) audio.src = stations[0].stream_url;
      select.addEventListener("change", () => {
        audio.src = select.value;
        audio.play().catch(() => {});
      });
      clear(slot);
      slot.append(select, audio, h("div", { class: "chips" }, toggleBtn, pauseBtn, clearBtn), viewport);
    } catch (error) {
      clear(slot);
      slot.append(
        h("p", { class: "error", text: `Radio unavailable: ${error.message}` }),
        toggleBtn,
        viewport,
      );
    }
  })();

  async function toggleLive() {
    if (graph?.streaming) {
      stopStreaming();
    } else {
      await startStreaming();
    }
  }

  function togglePause() {
    paused = !paused;
    pauseBtn.textContent = paused ? "Resume" : "Pause";
  }

  function clearTranscript() {
    clear(historyEl);
    clear(captionEl);
  }

  async function startStreaming() {
    if (!audioEl) return;
    audioEl.play().catch(() => {}); // user gesture enables playback
    if (!graph) {
      graph = await buildGraph(audioEl, viewport);
      if (!graph) {
        toggleBtn.textContent = "Live transcript: off";
        return;
      }
    }
    graph.streaming = true;
    const ws = createWsClient({
      url: `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/radio`,
      onOpen: () => {
        graph.connected = true;
        ws.send({ type: "start", sample_rate: graph.audioCtx.sampleRate });
      },
      onClose: () => {
        graph.connected = false;
      },
    });
    graph.ws = ws;
    ws.connect();
    toggleBtn.textContent = "Live transcript: on";
    toggleBtn.classList.add("is-live");
  }

  function stopStreaming() {
    graph.streaming = false;
    graph.connected = false;
    graph.ws?.send({ type: "stop" });
    graph.ws?.close();
    graph.ws = null;
    toggleBtn.textContent = "Live transcript: off";
    toggleBtn.classList.remove("is-live");
  }

  ctx.bus.on("radio:transcript", (message) => {
    if (paused) return;
    const text = typeof message === "string" ? message : message?.text;
    if (!text) return;
    const isFinal = Boolean(message && typeof message === "object" && message.final);

    if (isFinal) {
      // Commit the finalized sentence up into the history and clear the caption.
      historyEl.append(highlightedSegment(text, "transcript-segment"));
      clear(captionEl);
      while (historyEl.childElementCount > MAX_HISTORY_LINES) {
        historyEl.removeChild(historyEl.firstChild);
      }
      historyEl.scrollTop = historyEl.scrollHeight;
    } else {
      // Replace the live caption in place (no flicker of partial results).
      clear(captionEl);
      for (const part of highlightSegments(text)) {
        captionEl.append(part.mark ? h("mark", { text: part.text }) : part.text);
      }
    }
  });
}

function highlightedSegment(text, className) {
  const el = h("p", { class: className });
  for (const part of highlightSegments(text)) {
    el.append(part.mark ? h("mark", { text: part.text }) : part.text);
  }
  return el;
}

async function buildGraph(audioEl, viewport) {
  const AudioContext = window.AudioContext || window.webkitAudioContext;
  if (!AudioContext) {
    viewport.append(h("p", { class: "error", text: "Web Audio API is not supported." }));
    return null;
  }

  let audioCtx;
  let source;
  let workletNode;
  try {
    audioCtx = new AudioContext();
    await audioCtx.audioWorklet.addModule("/static/js/worklets/pcm-processor.js");
    source = audioCtx.createMediaElementSource(audioEl);
    workletNode = new AudioWorkletNode(audioCtx, "pcm-processor");
    source.connect(workletNode);
    workletNode.connect(audioCtx.destination);
  } catch (error) {
    viewport.append(h("p", { class: "error", text: `Audio capture failed: ${error.message}` }));
    return null;
  }
  audioCtx.resume();

  const graph = { audioCtx, source, workletNode, ws: null, streaming: false, connected: false };
  workletNode.port.onmessage = (event) => {
    const chunk = event.data; // Float32Array (4096 samples)
    if (graph.streaming && graph.connected && graph.ws) {
      const pcm = floatTo16BitPCM(chunk);
      graph.ws.send(pcm.buffer); // binary PCM frame (little-endian 16-bit)
    }
  };
  return graph;
}
