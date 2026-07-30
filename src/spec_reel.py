#!/usr/bin/env python3
"""Validate and render a reviewed Plain-Spoken Pebble Reel Spec."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image

try:
    from .sleep_reel import INK, MOON, MUTED, PERIWINKLE, Canvas, draw_background, draw_blob
except ImportError:
    from sleep_reel import INK, MOON, MUTED, PERIWINKLE, Canvas, draw_background, draw_blob

SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VERSION = re.compile(r"^\d+\.\d+\.\d+$")
ALLOWED_FORMAT = {"width": 1080, "height": 1920, "fps": 30}
MIN_DURATION = 30
MAX_DURATION = 45
MIN_BEATS = 5
MAX_BEATS = 8
# The final beat shares its space with the safety boundary, so its body stays short.
FINAL_BODY_LIMIT = 120
BEAT_COLORS = ("#9EA9E8", "#F4C96B", "#8CB7C6", "#A7B9A5", "#E79A7E", "#7F718A")


def require_text(value: object, name: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{name} must be non-empty and at most {limit} characters")
    if "—" in value:
        raise ValueError(f"{name} contains an em dash")
    return value.strip()


def validate_spec(spec: dict) -> None:
    if not isinstance(spec, dict) or spec.get("version") != 1:
        raise ValueError("Reel Spec version must be 1")
    if not isinstance(spec.get("issue_number"), int) or spec["issue_number"] < 1:
        raise ValueError("issue_number must be a positive integer")
    if not isinstance(spec.get("slug"), str) or not SLUG.fullmatch(spec["slug"]):
        raise ValueError("slug must use lowercase words separated by hyphens")
    require_text(spec.get("title"), "title", 80)
    if not isinstance(spec.get("render_version"), str) or not VERSION.fullmatch(spec["render_version"]):
        raise ValueError("render_version must use semantic version form")
    if spec.get("status") != "ready_to_render":
        raise ValueError("status must be ready_to_render")
    if spec.get("publication_status") != "human_review_required":
        raise ValueError("publication_status must be human_review_required")

    output_format = spec.get("format")
    if not isinstance(output_format, dict):
        raise TypeError("format is required")
    for key, value in ALLOWED_FORMAT.items():
        if output_format.get(key) != value:
            raise ValueError(f"format {key} must be {value}")
    duration = output_format.get("duration_seconds")
    if not isinstance(duration, (int, float)) or isinstance(duration, bool):
        raise TypeError("duration_seconds must be a number")
    if not MIN_DURATION <= duration <= MAX_DURATION:
        raise ValueError(f"duration_seconds must be between {MIN_DURATION} and {MAX_DURATION}")

    sources = spec.get("sources")
    if not isinstance(sources, list) or not 1 <= len(sources) <= 8:
        raise ValueError("sources must contain 1 to 8 URLs")
    for source in sources:
        if not isinstance(source, str) or urlparse(source).scheme != "https" or not urlparse(source).netloc:
            raise ValueError("every source must be an HTTPS URL")

    safety = spec.get("safety")
    if not isinstance(safety, list) or not safety or len(safety) > 8:
        raise ValueError("safety must contain 1 to 8 boundaries")
    for index, boundary in enumerate(safety):
        require_text(boundary, f"safety[{index}]", 180)

    beats = spec.get("beats")
    if not isinstance(beats, list) or not MIN_BEATS <= len(beats) <= MAX_BEATS:
        raise ValueError(f"beats must contain {MIN_BEATS} to {MAX_BEATS} entries")
    expected_start = 0.0
    ids = set()
    for index, beat in enumerate(beats):
        if not isinstance(beat, dict):
            raise TypeError("every beat must be an object")
        beat_id = require_text(beat.get("id"), f"beats[{index}].id", 40)
        if beat_id in ids:
            raise ValueError("beat IDs must be unique")
        ids.add(beat_id)
        start, end = beat.get("start"), beat.get("end")
        if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in (start, end)):
            raise ValueError("beat times must be numbers")
        if abs(start - expected_start) > 0.001 or end <= start:
            raise ValueError("beat timeline must be positive and contiguous")
        expected_start = float(end)
        require_text(beat.get("headline"), f"beats[{index}].headline", 52)
        body_limit = FINAL_BODY_LIMIT if index == len(beats) - 1 else 180
        require_text(beat.get("body"), f"beats[{index}].body", body_limit)
        if beat.get("source_label") is not None:
            require_text(beat.get("source_label"), f"beats[{index}].source_label", 40)
    if abs(expected_start - duration) > 0.001:
        raise ValueError("beat timeline must end at duration_seconds")


def load_spec(path: Path) -> dict:
    spec = json.loads(path.read_text(encoding="utf-8"))
    validate_spec(spec)
    return spec


def find_beat(spec: dict, time_seconds: float) -> tuple[int, dict]:
    for index, beat in enumerate(spec["beats"]):
        if beat["start"] <= time_seconds < beat["end"]:
            return index, beat
    if math.isclose(time_seconds, spec["format"]["duration_seconds"]):
        return len(spec["beats"]) - 1, spec["beats"][-1]
    raise ValueError("timestamp outside Reel Spec timeline")


def render_frame(spec: dict, time_seconds: float, scale: int = 2) -> Image.Image:
    validate_spec(spec)
    beat_index, beat = find_beat(spec, time_seconds)
    canvas = Canvas(scale)
    draw_background(canvas, time_seconds)

    canvas.rounded_rectangle((62, 24, 478, 64), radius=20, fill=PERIWINKLE)
    canvas.text((270, 44), "PLAIN-SPOKEN PEBBLE", 14, INK)

    marker_width = 340 / len(spec["beats"])
    for index in range(len(spec["beats"])):
        left = 100 + index * marker_width
        fill = INK if index <= beat_index else "#D6D0CA"
        canvas.rounded_rectangle((left, 86, left + marker_width - 8, 94), radius=4, fill=fill)

    progress = (time_seconds - beat["start"]) / (beat["end"] - beat["start"])
    bob = 8 * math.sin(progress * math.pi)
    color = BEAT_COLORS[beat_index % len(BEAT_COLORS)]
    draw_blob(canvas, (270, 300 - bob), (230, 130), color, beat["id"].replace("-", " ").upper(), text_size=20)

    canvas.center_text(beat["headline"], 455, 42, max_width=450, spacing=8)
    body_height = canvas.center_text(beat["body"], 600, 28, fill=MUTED, max_width=430, spacing=8)

    cursor = 600 + body_height + 24
    label = beat.get("source_label")
    if label:
        half_width = 9 + 4.2 * len(label)
        canvas.rounded_rectangle((270 - half_width, cursor, 270 + half_width, cursor + 32), radius=16, fill=MOON)
        canvas.text((270, cursor + 16), label, 14, INK)
        cursor += 56

    if beat_index == len(spec["beats"]) - 1:
        # Fixed band. The final beat's shorter body keeps this clear of both the copy and the counter.
        canvas.center_text(spec["safety"][0], 772, 14, fill=MUTED, max_width=440, spacing=5)

    canvas.text((270, 860), f"{beat_index + 1} OF {len(spec['beats'])}", 15, MUTED)
    canvas.text((270, 908), "SAVE IF USEFUL", 16, INK)
    return canvas.image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--scale", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()

    spec = load_spec(args.spec)
    fps = spec["format"]["fps"]
    frame_count = round(spec["format"]["duration_seconds"] * fps)
    for frame_index in range(frame_count):
        frame = render_frame(spec, frame_index / fps, scale=args.scale)
        sys.stdout.buffer.write(frame.tobytes())


if __name__ == "__main__":
    main()
