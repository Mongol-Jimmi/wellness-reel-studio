import math
import struct
import wave
from pathlib import Path

DURATION_SECONDS = 25.0
SAMPLE_RATE = 48_000
CUES = (
    (0.2, 196.0),
    (3.5, 220.0),
    (8.5, 246.94),
    (13.5, 261.63),
    (19.5, 293.66),
    (22.5, 329.63),
)


def sample_at(time_seconds: float) -> float:
    bed = 0.010 * math.sin(2 * math.pi * 49.0 * time_seconds)
    bed += 0.006 * math.sin(2 * math.pi * 73.5 * time_seconds)
    chimes = 0.0
    for onset, frequency in CUES:
        delta = time_seconds - onset
        if delta < 0:
            continue
        envelope = math.exp(-delta * 1.5)
        chimes += 0.045 * envelope * math.sin(2 * math.pi * frequency * delta)
        chimes += 0.014 * envelope * math.sin(2 * math.pi * frequency * 1.5 * delta)
    fade = min(1.0, time_seconds / 0.7, (DURATION_SECONDS - time_seconds) / 0.8)
    return max(-1.0, min(1.0, (bed + chimes) * fade))


def main() -> None:
    output = Path(__file__).resolve().parents[1] / "work" / "audio" / "combined-check-in.wav"
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        for index in range(int(DURATION_SECONDS * SAMPLE_RATE)):
            wav_file.writeframesraw(struct.pack("<h", int(sample_at(index / SAMPLE_RATE) * 32767)))
    print(output)


if __name__ == "__main__":
    main()
