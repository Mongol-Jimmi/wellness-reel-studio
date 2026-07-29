import argparse
import math
import struct
import wave
from pathlib import Path

from identities import IDENTITIES

SAMPLE_RATE = 48_000
DURATION_SECONDS = 5.0
FREQUENCIES = {
    "soft-punctuation": (220.0, 277.18, 329.63),
    "plain-spoken-pebble": (196.0, 246.94, 293.66),
    "permission-slip": (261.63, 329.63, 392.0),
    "inner-weather": (174.61, 220.0, 261.63),
    "kind-broadcast": (233.08, 293.66, 349.23),
}
CUES = (0.18, 1.25, 2.55, 4.05)


def sample_at(time_seconds: float, notes: tuple[float, ...]) -> float:
    bed = 0.012 * math.sin(2 * math.pi * notes[0] / 4 * time_seconds)
    chimes = 0.0
    for index, onset in enumerate(CUES):
        delta = time_seconds - onset
        if delta < 0:
            continue
        frequency = notes[index % len(notes)]
        chimes += 0.055 * math.exp(-delta * 2.2) * math.sin(2 * math.pi * frequency * delta)
        chimes += 0.018 * math.exp(-delta * 3.0) * math.sin(2 * math.pi * frequency * 2 * delta)
    fade = min(1.0, time_seconds / 0.35, (DURATION_SECONDS - time_seconds) / 0.45)
    return max(-1.0, min(1.0, (bed + chimes) * fade))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an original five-second identity sting")
    parser.add_argument("--identity", required=True, choices=[item.slug for item in IDENTITIES])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    notes = FREQUENCIES[args.identity]
    with wave.open(str(args.output), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        for index in range(int(DURATION_SECONDS * SAMPLE_RATE)):
            value = int(sample_at(index / SAMPLE_RATE, notes) * 32767)
            wav_file.writeframesraw(struct.pack("<h", value))
    print(args.output)


if __name__ == "__main__":
    main()
