#!/usr/bin/env python3
"""Generate a quiet deterministic audio bed for a reviewed Reel Spec."""

from __future__ import annotations

import argparse
import math
import struct
import wave
from pathlib import Path

try:
    from .spec_reel import load_spec
except ImportError:
    from spec_reel import load_spec

SAMPLE_RATE = 48_000


def sample_at(time_seconds: float, duration: float, cues: list[float]) -> float:
    bed = 0.008 * math.sin(2 * math.pi * 43.65 * time_seconds)
    bed += 0.005 * math.sin(2 * math.pi * 65.41 * time_seconds)
    chimes = 0.0
    for index, onset in enumerate(cues):
        delta = time_seconds - onset
        if delta < 0:
            continue
        frequency = 174.61 * (2 ** ((index % 7) / 12))
        envelope = math.exp(-delta * 1.4)
        chimes += 0.038 * envelope * math.sin(2 * math.pi * frequency * delta)
    fade = max(0.0, min(1.0, time_seconds / 0.8, (duration - time_seconds) / 1.0))
    return max(-1.0, min(1.0, (bed + chimes) * fade))


def write_audio(spec: dict, output: Path) -> None:
    duration = float(spec["format"]["duration_seconds"])
    cues = [float(beat["start"]) + 0.15 for beat in spec["beats"]]
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        for index in range(round(duration * SAMPLE_RATE)):
            value = sample_at(index / SAMPLE_RATE, duration, cues)
            wav_file.writeframesraw(struct.pack("<h", int(value * 32767)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_audio(load_spec(args.spec), args.output)
    print(args.output)


if __name__ == "__main__":
    main()
