// AudioWorklet processor for live radio capture.
//
// Passes audio through to the output (so the radio stays audible) and posts
// 16-bit-PCM-ready Float32 chunks (accumulated to 4096 samples) back to the
// main thread via the MessagePort.

const CHUNK_SAMPLES = 4096;

class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer = new Float32Array(CHUNK_SAMPLES);
    this._offset = 0;
  }

  process(inputs, outputs) {
    const input = inputs[0];
    const output = outputs[0];

    if (input && input.length && input[0]) {
      // Passthrough: copy the input channel to the output so the audio is audible.
      for (let channel = 0; channel < output.length; channel += 1) {
        output[channel].set(input[channel] || input[0]);
      }

      const samples = input[0];
      for (let i = 0; i < samples.length; i += 1) {
        this._buffer[this._offset] = samples[i];
        this._offset += 1;
        if (this._offset === CHUNK_SAMPLES) {
          this.port.postMessage(this._buffer);
          this._buffer = new Float32Array(CHUNK_SAMPLES);
          this._offset = 0;
        }
      }
    }

    return true;
  }
}

registerProcessor("pcm-processor", PCMProcessor);
