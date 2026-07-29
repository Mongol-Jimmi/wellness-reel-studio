import math
import struct
import wave
from pathlib import Path

DURATION_SECONDS = 35.0
SAMPLE_RATE = 48_000
CUES = (
    (0.2, 174.61),
    (4.5, 196.0),
    (8.5, 220.0),
    (14.0, 246.94),
    (19.5, 261.63),
    (25.0, 293.66),
    (30.5, 329.63),
)


def sample_at(time_seconds: float) -> float:
    bed = 0.009 * math.sin(2 * math.pi * 43.65 * time_seconds)
    bed += 0.006 * math.sin(2 * math.pi * 65.41 * time_seconds)
    chimes = 0.0
    for onset, frequency in CUES:
        delta = time_seconds - onset
        if delta < 0:
            continue
        envelope = math.exp(-delta * 1.35)
        chimes += 0.042 * envelope * math.sin(2 * math.pi * frequency * delta)
        chimes += 0.012 * envelope * math.sin(2 * math.pi * frequency * 1.5 * delta)
    fade = min(1.0, time_seconds / 0.8, (DURATION_SECONDS - time_seconds) / 1.0)
    return max(-1.0, min(1.0, (bed + chimes) * fade))


def main() -> None:
    output = Path(__file__).resolve().parents[1] / "work" / "audio" / "sleep-hygiene.wav"
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
