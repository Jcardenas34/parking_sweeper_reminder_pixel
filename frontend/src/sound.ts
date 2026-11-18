/**
 * 8-bit alert jingles: square-wave arpeggios through WebAudio, no audio files.
 * backend/parking/audio.py renders the same tables to res/raw/*.wav for Android
 * notification channels; tests/test_audio.py checks the two copies match.
 */

export type Jingle = "night" | "morning";

// Notes in Hz (0 = rest) played `step` seconds apart, each decaying over `decay` seconds.
export const JINGLES: Record<Jingle, { notes: number[]; step: number; decay: number }> = {
  night: { notes: [1047, 880, 784, 659, 523, 0, 659, 523], step: 0.16, decay: 0.15 },
  morning: {
    notes: [784, 1047, 1319, 1047, 1319, 1568, 0, 1568, 1568, 1568, 0, 1319, 1568, 2093, 2093],
    step: 0.12,
    decay: 0.11,
  },
};

let ctx: AudioContext | null = null;

export function play(kind: Jingle): void {
  try {
    ctx ??= new AudioContext();
    const { notes, step, decay } = JINGLES[kind];
    notes.forEach((freq, i) => {
      if (!freq) return;
      const osc = ctx!.createOscillator();
      const gain = ctx!.createGain();
      const start = ctx!.currentTime + i * step;
      osc.type = "square";
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0.08, start);
      gain.gain.exponentialRampToValueAtTime(0.001, start + decay);
      osc.connect(gain).connect(ctx!.destination);
      osc.start(start);
      osc.stop(start + step);
    });
  } catch {
    /* audio unavailable */
  }
}

/** A single short blip for button presses. */
export function blip(): void {
  try {
    ctx ??= new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    const start = ctx.currentTime;
    osc.type = "square";
    osc.frequency.value = 1319;
    gain.gain.setValueAtTime(0.04, start);
    gain.gain.exponentialRampToValueAtTime(0.001, start + 0.05);
    osc.connect(gain).connect(ctx.destination);
    osc.start(start);
    osc.stop(start + 0.06);
  } catch {
    /* audio unavailable */
  }
}
