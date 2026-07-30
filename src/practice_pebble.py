#!/usr/bin/env python3
"""One-minute cyclic sigh practice in the Plain-Spoken Pebble language.

Same warm paper, same soft lavender shapes, same mustard source chip as the
explainer Reels. The tweak is that the pebble is no longer a label holder. It
breathes: filling on the inhale, catching the second sip, settling and warming
through the sigh out. Every motion has a whole number of cycles per minute, so
the last frame meets the first and the Reel loops without a seam.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.sleep_reel import INK, MOON, MUTED, PERIWINKLE, SHADOW, Canvas, load_font

WIDTH = 540
HEIGHT = 960
FPS = 30
DURATION_SECONDS = 60.0
SOURCE_URL = "https://doi.org/10.1016/j.xcrm.2022.100895"
VISIBLE_COPY = ("cyclic sigh", "never forced", "in", "more", "out", "again?", "Cell Reports Medicine, 2023")

# Warm oat instead of the explainer's brighter cream, so an unlit room stays comfortable.
PAPER = "#EFE8DC"
HAZE = "#E4DFEA"
CORAL = "#E79A7E"
REST_WIDTH, REST_HEIGHT = 196.0, 132.0
FULL_WIDTH, FULL_HEIGHT = 344.0, 226.0
CENTRE_Y = 432.0


@dataclass(frozen=True)
class Phase:
    name: str
    start: float
    end: float


PHASES = (
    Phase("intro", 0.0, 9.0),
    Phase("inhale", 9.0, 13.5),
    Phase("sip", 13.5, 15.5),
    Phase("exhale", 15.5, 23.5),
    Phase("rest", 23.5, 24.5),
    Phase("inhale", 24.5, 29.0),
    Phase("sip", 29.0, 31.0),
    Phase("exhale", 31.0, 39.0),
    Phase("rest", 39.0, 40.0),
    Phase("inhale", 40.0, 44.5),
    Phase("sip", 44.5, 46.5),
    Phase("exhale", 46.5, 54.5),
    Phase("close", 54.5, 60.0),
)
CYCLE_STARTS = (9.0, 24.5, 40.0)


def validate_timeline(phases: tuple[Phase, ...]) -> None:
    if not phases or phases[0].start != 0.0 or phases[-1].end != DURATION_SECONDS:
        raise ValueError("timeline must span exactly sixty seconds")
    if any(phase.end <= phase.start for phase in phases):
        raise ValueError("every phase must have positive duration")
    for previous, current in pairwise(phases):
        if previous.end != current.start:
            raise ValueError(f"gap or overlap between {previous.name} and {current.name}")


def phase_at(time_seconds: float) -> Phase:
    time_seconds %= DURATION_SECONDS
    for phase in PHASES:
        if phase.start <= time_seconds < phase.end:
            return phase
    return PHASES[-1]


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def smooth(value: float) -> float:
    value = clamp(value)
    return value * value * (3 - 2 * value)


def fade_window(time_seconds: float, start: float, end: float, fade: float = 0.6) -> float:
    return min(smooth((time_seconds - start) / fade), smooth((end - time_seconds) / fade))


def breath(time_seconds: float) -> tuple[float, float]:
    """How full the pebble is from 0 to 1, and how much warmth the release carries."""
    phase = phase_at(time_seconds)
    progress = (time_seconds - phase.start) / (phase.end - phase.start)
    if phase.name == "inhale":
        return 0.88 * smooth(progress), 0.0
    if phase.name == "sip":
        return 0.88 + 0.12 * smooth(progress), 0.0
    if phase.name == "exhale":
        return 1.0 - smooth(progress), smooth(1 - abs(progress - 0.5) * 2)
    return 0.0, 0.0


def blend(first: str, second: str, amount: float) -> str:
    left = tuple(int(first[index : index + 2], 16) for index in (1, 3, 5))
    right = tuple(int(second[index : index + 2], 16) for index in (1, 3, 5))
    mixed = tuple(round(left[i] + (right[i] - left[i]) * clamp(amount)) for i in range(3))
    return "#%02X%02X%02X" % mixed


def draw_paper(canvas: Canvas, time_seconds: float) -> None:
    """Warm ground plus the two pale lavender shapes, drifting four times a minute."""
    canvas.draw.rectangle((0, 0, canvas.image.width, canvas.image.height), fill=PAPER)
    drift = 16 * math.sin(2 * math.pi * time_seconds / 15)
    canvas.ellipse((-175 + drift, 105, 205 + drift, 460), fill=HAZE)
    canvas.ellipse((370 - drift, 555, 700 - drift, 900), fill=HAZE)
    for index, point in enumerate(((424, 150), (462, 190), (392, 210))):
        pulse = 3 * math.sin(2 * math.pi * (time_seconds / DURATION_SECONDS) * 8 + index)
        canvas.ellipse(
            (point[0] - 5 - pulse, point[1] - 5 - pulse, point[0] + 5 + pulse, point[1] + 5 + pulse),
            fill=MOON,
        )


def draw_pebble(canvas: Canvas, time_seconds: float) -> None:
    """The pebble from the explainer Reels, given a breath."""
    fullness, warmth = breath(time_seconds)
    width = REST_WIDTH + (FULL_WIDTH - REST_WIDTH) * fullness
    height = REST_HEIGHT + (FULL_HEIGHT - REST_HEIGHT) * fullness
    centre_y = CENTRE_Y - 20 * fullness
    fill = blend(PERIWINKLE, PAPER, warmth * 0.30)

    box = (270 - width / 2, centre_y - height / 2, 270 + width / 2, centre_y + height / 2)
    canvas.ellipse((box[0] + 18 + 6 * fullness, box[3] + 14, box[2] - 12 - 6 * fullness, box[3] + 34), fill=SHADOW)
    canvas.rounded_rectangle(box, radius=min(width, height) / 2.3, fill=fill)
    canvas.ellipse((box[0] + 12, box[1] - 8, box[2] - 24, box[3] + 2), fill=fill)

    phase = phase_at(time_seconds)
    if phase.name == "sip":
        progress = smooth((time_seconds - phase.start) / (phase.end - phase.start))
        radius = 20 + 6 * progress
        sip_x = 270 + width / 2 - 26
        sip_y = box[1] - 34 - 22 * progress
        canvas.ellipse((sip_x - radius, sip_y - radius * 0.78, sip_x + radius, sip_y + radius * 0.78), fill=PERIWINKLE)


def draw_release(canvas: Canvas, time_seconds: float) -> None:
    """Three mustard motes drifting off as the breath leaves. The dots are already brand furniture."""
    phase = phase_at(time_seconds)
    if phase.name != "exhale":
        return
    progress = (time_seconds - phase.start) / (phase.end - phase.start)
    for index in range(3):
        local = clamp(progress * 1.5 - index * 0.22)
        if local <= 0 or local >= 1:
            continue
        drift = smooth(local)
        x = 270 + (58 + index * 26) + 96 * drift
        y = CENTRE_Y - 30 - 74 * drift + 10 * index
        radius = (5.5 - index * 0.8) * (1 - 0.35 * drift)
        fade = math.sin(math.pi * local)
        canvas.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=blend(PAPER, MOON, 0.85 * fade),
        )


def frosted_chip(canvas: Canvas, box: tuple[float, float, float, float], strength: float) -> None:
    """Frost on warm paper: soften what is behind it, lift it, keep a hairline edge."""
    if strength <= 0.01:
        return
    scaled = tuple(canvas.n(value) for value in box)
    region = canvas.image.crop(scaled).filter(ImageFilter.GaussianBlur(canvas.n(7)))
    veil = Image.new("RGBA", region.size, (255, 252, 246, round(150 * strength)))
    frosted = Image.alpha_composite(region.convert("RGBA"), veil)
    radius = round((scaled[3] - scaled[1]) / 2)
    mask = Image.new("L", region.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, region.width - 1, region.height - 1), radius=radius, fill=round(255 * strength))
    canvas.image.paste(frosted.convert("RGB"), scaled[:2], mask)

    edge = Image.new("RGBA", canvas.image.size, (0, 0, 0, 0))
    ImageDraw.Draw(edge).rounded_rectangle(scaled, radius=radius, outline=(255, 255, 255, round(190 * strength)), width=max(1, canvas.n(1)))
    canvas.image.paste(Image.alpha_composite(canvas.image.convert("RGBA"), edge).convert("RGB"), (0, 0))


def tracked_text(canvas: Canvas, text: str, centre_y: float, size: int, alpha: float, fill: str, tracking: float) -> None:
    if alpha <= 0.01:
        return
    font = load_font(canvas.n(size))
    spacing = canvas.n(tracking)
    widths = [font.getlength(character) for character in text]
    total = sum(widths) + spacing * max(0, len(text) - 1)
    layer = Image.new("RGBA", canvas.image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    colour = tuple(int(fill[index : index + 2], 16) for index in (1, 3, 5))
    x = canvas.n(270) - total / 2
    for character, width in zip(text, widths):
        draw.text((x, canvas.n(centre_y)), character, font=font, fill=(*colour, round(255 * clamp(alpha))), anchor="lm")
        x += width + spacing
    canvas.image.paste(Image.alpha_composite(canvas.image.convert("RGBA"), layer).convert("RGB"), (0, 0))


def chip_box(text: str, size: int, tracking: float, centre_y: float, canvas: Canvas) -> tuple[float, float, float, float]:
    font = load_font(canvas.n(size))
    width = (sum(font.getlength(character) for character in text) + canvas.n(tracking) * max(0, len(text) - 1)) / canvas.scale
    half = width / 2 + 30
    return (270 - half, centre_y - 30, 270 + half, centre_y + 30)


def phase_word(phase: Phase) -> str:
    return {"inhale": "in", "sip": "more", "exhale": "out"}.get(phase.name, "")


def draw_cycle_dots(canvas: Canvas, time_seconds: float) -> None:
    for index, start in enumerate(CYCLE_STARTS):
        x = 270 - 26 + index * 26
        radius = 4.0
        done = time_seconds >= start
        canvas.ellipse((x - radius, 790 - radius, x + radius, 790 + radius), fill=PERIWINKLE if done else SHADOW)


def render_frame(time_seconds: float, scale: int = 2) -> Image.Image:
    if scale not in (1, 2):
        raise ValueError("scale must be 1 or 2")
    validate_timeline(PHASES)
    time_seconds %= DURATION_SECONDS
    phase = phase_at(time_seconds)

    canvas = Canvas(scale)
    draw_paper(canvas, time_seconds)
    draw_release(canvas, time_seconds)
    draw_pebble(canvas, time_seconds)

    canvas.rounded_rectangle((132, 44, 408, 86), radius=21, fill=PERIWINKLE)
    canvas.text((270, 65), "PLAIN-SPOKEN PEBBLE", 17, INK)

    intro = fade_window(time_seconds, 0.6, 8.2, 1.0)
    close = fade_window(time_seconds, 55.0, 59.4, 0.9)
    word = phase_word(phase)
    if word:
        alpha = fade_window(time_seconds, phase.start, phase.end, 0.5)
        frosted_chip(canvas, chip_box(word, 30, 8, 656, canvas), alpha)
        tracked_text(canvas, word, 656, 30, alpha, INK, 8)
    else:
        label = "cyclic sigh" if intro > 0.01 else "again?" if close > 0.01 else ""
        alpha = max(intro, close)
        if label:
            frosted_chip(canvas, chip_box(label, 28, 4, 656, canvas), alpha)
            tracked_text(canvas, label, 656, 28, alpha, INK, 4)

    tracked_text(canvas, "never forced", 716, 16, intro * 0.85, MUTED, 2)
    if close > 0.01:
        canvas.rounded_rectangle((150, 700, 390, 742), radius=20, fill=MOON)
        canvas.text((270, 721), "Cell Reports Medicine, 2023", 15, INK)
    draw_cycle_dots(canvas, time_seconds)
    return canvas.image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    for frame_index in range(round(DURATION_SECONDS * FPS)):
        sys.stdout.buffer.write(render_frame(frame_index / FPS, args.scale).tobytes())


if __name__ == "__main__":
    main()
