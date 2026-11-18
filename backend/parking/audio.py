"""Render the app's 8-bit alert jingles (frontend/src/sound.ts) to WAV files.

Android plays these as notification-channel sounds, so they must match the
WebAudio previews note for note. tests/test_audio.py checks that both copies of
the note tables agree.
"""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

# Same tables as sound.ts: notes in Hz (0 is a rest) played `step` seconds apart.
# Each note starts at GAIN and decays exponentially to FLOOR over `decay` seconds.
JINGLES: dict[str, dict] = {
    # 8 PM the night before: a gentle falling arpeggio.
    "night": {"notes": [1047, 880, 784, 659, 523, 0, 659, 523], "step": 0.16, "decay": 0.15},
    # 1 hour before the sweepers: a bright reveille that is hard to sleep through.
    "morning": {
        "notes": [784, 1047, 1319, 1047, 1319, 1568, 0, 1568, 1568, 1568, 0, 1319, 1568, 2093, 2093],
        "step": 0.12,
        "decay": 0.11,
    },
}
GAIN = 0.08
FLOOR = 0.001
SAMPLE_RATE = 44100
# WebAudio's 0.08 is quiet next to other notification sounds; scale the whole
# waveform up without changing its shape.
PEAK = {"night": 0.45, "morning": 0.8}


def render(notes: list[int], step: float, decay: float, peak: float = 0.5, rate: int = SAMPLE_RATE) -> list[float]:
    """Samples in [-1, 1] for a square-wave arpeggio."""
    samples = [0.0] * round(len(notes) * step * rate)
    for i, freq in enumerate(notes):
        if not freq:
            continue
        start = round(i * step * rate)
        for n in range(round(step * rate)):
            t = n / rate
            gain = GAIN * (FLOOR / GAIN) ** min(t / decay, 1.0)
            square = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
            samples[start + n] += gain * square
    return [s * peak / GAIN for s in samples]


def write_wav(path: Path, samples: list[float], rate: int = SAMPLE_RATE) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", round(max(-1.0, min(1.0, s)) * 32767)) for s in samples))


def export_jingles(out_dir: Path) -> list[Path]:
    """Write night_alert.wav and morning_alert.wav (Android res/raw names) to out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for kind, spec in JINGLES.items():
        path = out_dir / f"{kind}_alert.wav"
        write_wav(path, render(spec["notes"], spec["step"], spec["decay"], PEAK[kind]))
        paths.append(path)
    return paths
