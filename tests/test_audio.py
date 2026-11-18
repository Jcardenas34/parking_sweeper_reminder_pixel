import json
import re
import wave
from pathlib import Path

from parking.audio import JINGLES, SAMPLE_RATE, export_jingles, render

SOUND_TS = Path(__file__).resolve().parents[1] / "frontend" / "src" / "sound.ts"


def test_wavs_are_valid(tmp_path):
    paths = export_jingles(tmp_path)
    assert sorted(p.name for p in paths) == ["morning_alert.wav", "night_alert.wav"]
    for p in paths:
        with wave.open(str(p)) as w:
            assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, SAMPLE_RATE)
            kind = p.name.split("_")[0]
            spec = JINGLES[kind]
            assert w.getnframes() == round(len(spec["notes"]) * spec["step"] * SAMPLE_RATE)


def test_morning_is_louder_and_longer_than_night():
    m, n = JINGLES["morning"], JINGLES["night"]
    morning = render(m["notes"], m["step"], m["decay"], 0.8)
    night = render(n["notes"], n["step"], n["decay"], 0.45)
    assert max(map(abs, morning)) > max(map(abs, night))
    assert len(morning) > len(night)


def test_rests_are_silent():
    spec = JINGLES["night"]
    rest = spec["notes"].index(0)
    samples = render(spec["notes"], spec["step"], spec["decay"])
    start = round(rest * spec["step"] * SAMPLE_RATE)
    assert all(s == 0 for s in samples[start : start + round(spec["step"] * SAMPLE_RATE)])


def test_tables_match_sound_ts():
    """audio.py and sound.ts must play the same jingles."""
    src = SOUND_TS.read_text()
    for kind, spec in JINGLES.items():
        m = re.search(kind + r":\s*\{\s*notes:\s*(\[[^\]]*\]),\s*step:\s*([\d.]+),\s*decay:\s*([\d.]+)", src)
        assert m, f"{kind} not found in sound.ts"
        assert json.loads(m.group(1)) == spec["notes"]
        assert float(m.group(2)) == spec["step"]
        assert float(m.group(3)) == spec["decay"]
