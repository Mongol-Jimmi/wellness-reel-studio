#!/usr/bin/env python3
"""Generate and time a Coral-voice cyclic sigh guide through OpenRouter."""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
import re
import struct
import urllib.error
import urllib.request
import wave
from dataclasses import dataclass
from pathlib import Path

MODEL = "openai/gpt-audio-mini"
VOICE = "coral"
SAMPLE_RATE = 24_000
DURATION_SECONDS = 60
MAX_TOKENS = 900  # a cue is a single short line; anything longer is the model answering back
API_URL = "https://openrouter.ai/api/v1/chat/completions"


@dataclass(frozen=True)
class Cue:
    at: float
    text: str


CUES = (
    Cue(0.8, "Let's practice a cyclic sigh. Keep every breath easy, never forced."),
    Cue(9.6, "Breathe in gently through your nose."),
    Cue(13.7, "A second, smaller sip."),
    Cue(16.0, "And a long, unhurried sigh out."),
    Cue(24.9, "Again. Breathe in."),
    Cue(29.2, "A smaller sip."),
    Cue(31.4, "And a long, unhurried sigh out."),
    Cue(40.3, "One more. Breathe in."),
    Cue(44.7, "Small sip."),
    Cue(47.0, "Breathe all the way out, slowly."),
    Cue(55.0, "Replay when you're ready. Let the rhythm grow familiar."),
)


def request_pcm(api_key: str, text: str) -> tuple[bytes, str]:
    # Practice cues are instructions aimed at the viewer, so "say this" invites the model to
    # answer them instead of voicing them. Asking it to repeat the line back is the frame that
    # holds. MAX_TOKENS caps the damage when it answers anyway: one refusal once billed for
    # thirteen minutes of generated audio.
    prompt = f'Repeat this line back to me word for word and say nothing else: "{text}"' 
    body = {
        "model": MODEL,
        "modalities": ["text", "audio"],
        "audio": {"voice": VOICE, "format": "pcm16"},
        "stream": True,
        "temperature": 0,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    chunks: list[bytes] = []
    transcript: list[str] = []
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload == "[DONE]":
                    break
                event = json.loads(payload)
                audio = event["choices"][0].get("delta", {}).get("audio") or {}
                if audio.get("data"):
                    chunks.append(base64.b64decode(audio["data"]))
                if audio.get("transcript") is not None:
                    transcript.append(audio["transcript"])
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"OpenRouter TTS failed with HTTP {error.code}: {detail}") from error
    pcm = b"".join(chunks)
    if not pcm:
        raise RuntimeError("OpenRouter returned no audio")
    spoken_text = "".join(transcript).strip()
    if not spoken_text:
        raise RuntimeError("OpenRouter returned audio without a transcript")
    return pcm, spoken_text


def normalized_words(text: str) -> list[str]:
    return re.findall(r"[a-z]+(?:'[a-z]+)?", text.lower())


def write_wav(path: Path, pcm: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(pcm)


def read_samples(path: Path) -> list[int]:
    with wave.open(str(path), "rb") as source:
        if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (1, 2, SAMPLE_RATE):
            raise ValueError(f"unexpected audio format in {path}")
        frames = source.readframes(source.getnframes())
    return list(struct.unpack(f"<{len(frames) // 2}h", frames))


def load_cues(path: Path) -> tuple[Cue, ...]:
    """Read a practice's spoken cues. Each entry is a start time and the words to say."""
    entries = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"{path} must hold a non-empty list of cues")
    cues = tuple(Cue(float(entry["at"]), str(entry["text"])) for entry in entries)
    if any(later.at <= earlier.at for earlier, later in zip(cues, cues[1:])):
        raise ValueError("cue times must increase")
    if cues[-1].at >= DURATION_SECONDS:
        raise ValueError("the last cue must start inside the minute")
    return cues


def mix_cues(cues: tuple[Cue, ...], paths: list[Path], output: Path) -> None:
    frame_count = DURATION_SECONDS * SAMPLE_RATE
    mixed = [0.0] * frame_count
    for index, (cue, path) in enumerate(zip(cues, paths, strict=True)):
        samples = read_samples(path)
        start = round(cue.at * SAMPLE_RATE)
        next_at = cues[index + 1].at if index + 1 < len(cues) else DURATION_SECONDS
        available = round((next_at - cue.at - 0.15) * SAMPLE_RATE)
        if len(samples) > available:
            raise ValueError(
                f"cue {index + 1} is {len(samples) / SAMPLE_RATE:.2f}s but only "
                f"{available / SAMPLE_RATE:.2f}s fits; shorten its script"
            )
        fade_frames = round(0.025 * SAMPLE_RATE)
        for offset, sample in enumerate(samples):
            fade = min(1.0, offset / fade_frames, (len(samples) - 1 - offset) / fade_frames)
            mixed[start + offset] += sample * max(0.0, fade) * 0.86

    for frame in range(frame_count):
        time_seconds = frame / SAMPLE_RATE
        bed = 280 * math.sin(2 * math.pi * 48 * time_seconds)
        bed += 175 * math.sin(2 * math.pi * 72 * time_seconds)
        bed *= 0.82 + 0.18 * math.sin(2 * math.pi * time_seconds / DURATION_SECONDS)
        mixed[frame] += bed

    pcm = b"".join(struct.pack("<h", round(max(-32768, min(32767, sample)))) for sample in mixed)
    write_wav(output, pcm)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--cues", type=Path, help="JSON list of {at, text}. Defaults to the cyclic sigh script.")
    args = parser.parse_args()
    cues = load_cues(args.cues) if args.cues else CUES

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required")
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    cue_paths = []
    for index, cue in enumerate(cues, start=1):
        path = args.cache_dir / f"{index:02d}.wav"
        transcript_path = path.with_suffix(".txt")
        cue_paths.append(path)
        has_matching_cache = (
            path.exists()
            and transcript_path.exists()
            and normalized_words(transcript_path.read_text(encoding="utf-8")) == normalized_words(cue.text)
        )
        if has_matching_cache and not args.force:
            continue
        print(f"Generating voice cue {index}/{len(cues)}")
        next_at = cues[index].at if index < len(cues) else DURATION_SECONDS
        max_bytes = round((next_at - cue.at - 0.15) * SAMPLE_RATE * 2)
        for attempt in range(1, 4):
            pcm, transcript = request_pcm(api_key, cue.text)
            is_exact = normalized_words(transcript) == normalized_words(cue.text)
            if is_exact and len(pcm) <= max_bytes:
                break
            reason = "model added or changed words" if not is_exact else "audio exceeded its cue window"
            print(f"Retrying cue {index}: {reason} (attempt {attempt}/3)")
        else:
            raise RuntimeError(f"OpenRouter did not read cue {index} exactly: {transcript!r}")
        write_wav(path, pcm)
        transcript_path.write_text(transcript + "\n", encoding="utf-8")
    mix_cues(cues, cue_paths, args.output)
    print(args.output)


if __name__ == "__main__":
    main()
