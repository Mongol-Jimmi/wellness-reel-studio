#!/usr/bin/env python3
"""Render and verify a reviewed Reel Spec with fixed local tooling."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.spec_reel import load_spec, render_frame

SPECS_ROOT = ROOT / "reels" / "specs"


def contained_spec(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(SPECS_ROOT.resolve()):
        raise ValueError(f"spec must be inside {SPECS_ROOT}")
    return resolved


def write_captions(spec: dict, output: Path) -> None:
    lines = ["WEBVTT", ""]
    for beat in spec["beats"]:
        start = format_timestamp(beat["start"])
        end = format_timestamp(beat["end"])
        lines.extend([f"{start} --> {end}", f"{beat['headline']}\n{beat['body']}", ""])
    output.write_text("\n".join(lines), encoding="utf-8")


def format_timestamp(seconds: float) -> str:
    milliseconds = round(float(seconds) * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}.{milliseconds:03d}"


def render(spec_path: Path, output_dir: Path) -> dict:
    spec_path = contained_spec(spec_path)
    spec = load_spec(spec_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    video = output_dir / f"{spec['slug']}-v{spec['render_version']}.mp4"
    poster = output_dir / f"{spec['slug']}-v{spec['render_version']}.png"
    captions = output_dir / f"{spec['slug']}-v{spec['render_version']}.vtt"

    with tempfile.TemporaryDirectory() as temporary_directory:
        audio = Path(temporary_directory) / "bed.wav"
        subprocess.run(
            [sys.executable, str(ROOT / "src" / "generate_spec_audio.py"), "--spec", str(spec_path), "--output", str(audio)],
            check=True,
        )
        renderer = subprocess.Popen(
            [sys.executable, str(ROOT / "src" / "spec_reel.py"), "--spec", str(spec_path), "--scale", "2"],
            stdout=subprocess.PIPE,
        )
        if renderer.stdout is None:
            raise RuntimeError("renderer did not provide a video stream")
        ffmpeg = subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "warning", "-y",
                "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", "1080x1920", "-framerate", "30",
                "-i", "pipe:0", "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0",
                "-t", str(spec["format"]["duration_seconds"]), "-c:v", "libx264", "-preset", "medium",
                "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
                "-af", "loudnorm=I=-20:LRA=5:TP=-2", "-movflags", "+faststart", str(video),
            ],
            stdin=renderer.stdout,
            check=False,
        )
        renderer.stdout.close()
        renderer_result = renderer.wait()
        if renderer_result != 0 or ffmpeg.returncode != 0:
            video.unlink(missing_ok=True)
            raise RuntimeError(f"render failed: renderer={renderer_result}, ffmpeg={ffmpeg.returncode}")

    render_frame(spec, 1.0, scale=2).save(poster)
    write_captions(spec, captions)
    verify(video, spec)
    manifest = {
        "slug": spec["slug"],
        "title": spec["title"],
        "status": "human review required",
        "duration": f"{spec['format']['duration_seconds']:g} seconds",
        "resolution": "1080 × 1920",
        "renderVersion": spec["render_version"],
        "issueNumber": spec["issue_number"],
        "videoFile": video.name,
        "posterFile": poster.name,
        "captionsFile": captions.name,
        "specPath": str(spec_path.relative_to(ROOT)),
        "sources": spec["sources"],
    }
    metadata = output_dir / f"{spec['slug']}-v{spec['render_version']}.preview.json"
    metadata.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify(video: Path, spec: dict) -> None:
    completed = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "stream=codec_type,width,height,r_frame_rate,sample_rate:format=duration", "-of", "json", str(video),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    metadata = json.loads(completed.stdout)
    video_stream = next(stream for stream in metadata["streams"] if stream["codec_type"] == "video")
    audio_stream = next(stream for stream in metadata["streams"] if stream["codec_type"] == "audio")
    if (video_stream["width"], video_stream["height"], video_stream["r_frame_rate"]) != (1080, 1920, "30/1"):
        raise ValueError("rendered video format does not match the Reel Spec")
    if audio_stream["sample_rate"] != "48000":
        raise ValueError("rendered audio sample rate must be 48000")
    if abs(float(metadata["format"]["duration"]) - spec["format"]["duration_seconds"]) > 0.05:
        raise ValueError("rendered duration does not match the Reel Spec")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("render-output"))
    args = parser.parse_args()
    print(json.dumps(render(args.spec, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
