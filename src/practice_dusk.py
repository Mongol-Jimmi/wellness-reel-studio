#!/usr/bin/env python3
"""Dusk variant of the cloud practice: darker sky, fewer words, warmth instead of alarm."""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from functools import lru_cache
from itertools import pairwise
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH = 540
HEIGHT = 960
FPS = 30
DURATION_SECONDS = 60.0
FONT_PATH = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "UbuntuSans.ttf"
SOURCE_URL = "https://doi.org/10.1016/j.xcrm.2022.100895"
ANCHOR_MOTIF = "breathing cloud"
SHOT_VARIANTS = ("open sky", "diagonal drift", "cloud close-up")
CHANGE_EVENTS = (
    0.0, 1.0, 3.5, 6.5, 9.0, 11.5, 13.5, 15.5, 19.0, 23.5,
    24.5, 27.0, 29.0, 31.0, 35.0, 39.0, 40.0, 42.5, 44.5, 46.5,
    50.5, 54.5, 55.5, 58.5, 60.0,
)
VISIBLE_COPY = ("cyclic sigh", "never forced", "in", "more", "out", "again?", "Cell Reports Medicine, 2023")

INK = (243, 241, 250)
INK_SOFT = (206, 202, 226)
FOG = (240, 246, 245)
CLOUD = (203, 209, 243)
CLOUD_WARM = (238, 205, 183)
SAGE = (244, 201, 107)
LAVENDER = (158, 169, 232)
ROSE = (176, 178, 236)
GOLD = (244, 201, 107)
COOL_TOP = (44, 49, 86)
COOL_BOTTOM = (116, 100, 132)
WARM_TOP = (56, 58, 98)
WARM_BOTTOM = (196, 136, 112)


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
    raise ValueError(f"timestamp outside timeline: {time_seconds}")


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def smooth(value: float) -> float:
    value = clamp(value)
    return value * value * (3 - 2 * value)


def fade_window(time_seconds: float, start: float, end: float, fade: float = 0.6) -> float:
    return min(smooth((time_seconds - start) / fade), smooth((end - time_seconds) / fade))


@lru_cache(maxsize=32)
def font(size: int) -> ImageFont.FreeTypeFont:
    if not FONT_PATH.exists():
        raise FileNotFoundError(f"required font not found: {FONT_PATH}")
    return ImageFont.truetype(str(FONT_PATH), size=size)


@lru_cache(maxsize=4)
def gradient(scale: int, is_warm: bool) -> Image.Image:
    width, height = WIDTH * scale, HEIGHT * scale
    top, bottom = (WARM_TOP, WARM_BOTTOM) if is_warm else (COOL_TOP, COOL_BOTTOM)
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    for y in range(height):
        progress = y / max(1, height - 1)
        color = tuple(round(top[i] + (bottom[i] - top[i]) * progress) for i in range(3))
        draw.line((0, y, width, y), fill=color)
    return image.convert("RGBA")


@lru_cache(maxsize=2)
def grain(scale: int) -> Image.Image:
    image = Image.new("RGBA", (WIDTH * scale, HEIGHT * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for index in range(420):
        x = ((index * 149) % WIDTH) * scale
        y = ((index * 83 + index * index * 7) % HEIGHT) * scale
        alpha = 8 + index % 10
        draw.point((x, y), fill=(232, 232, 248, alpha))
    return image


@lru_cache(maxsize=16)
def cloud_sprite(scale: int, tone: str = "cool") -> Image.Image:
    width, height = 330 * scale, 210 * scale
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    puffs = (
        (20, 92, 130, 177),
        (74, 51, 195, 174),
        (142, 25, 264, 174),
        (215, 73, 317, 177),
        (58, 113, 280, 190),
    )
    for box in puffs:
        draw.ellipse(tuple(value * scale for value in box), fill=220)
    mask = mask.filter(ImageFilter.GaussianBlur(5 * scale))

    color = CLOUD_WARM if tone == "warm" else CLOUD
    sprite = Image.new("RGBA", (width, height), (*color, 0))
    sprite.putalpha(mask)

    highlight = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    highlight_draw = ImageDraw.Draw(highlight)
    highlight_draw.ellipse(
        (89 * scale, 57 * scale, 239 * scale, 147 * scale),
        fill=(255, 255, 255, 35),
    )
    return Image.alpha_composite(sprite, highlight.filter(ImageFilter.GaussianBlur(16 * scale)))


def paste_cloud(
    image: Image.Image,
    center: tuple[float, float],
    size: float,
    opacity: float,
    scale: int,
    tone: str = "cool",
    shadow: bool = False,
) -> None:
    base = cloud_sprite(scale, tone)
    width = max(1, round(base.width * size))
    height = max(1, round(base.height * size))
    sprite = base.resize((width, height), Image.Resampling.LANCZOS)
    if opacity < 1:
        alpha = sprite.getchannel("A").point(lambda value: round(value * clamp(opacity)))
        sprite.putalpha(alpha)
    left = round(center[0] * scale - width / 2)
    top = round(center[1] * scale - height / 2)
    if shadow:
        shadow_sprite = Image.new("RGBA", sprite.size, (26, 28, 52, 0))
        shadow_sprite.putalpha(sprite.getchannel("A").point(lambda value: round(value * 0.30)))
        image.alpha_composite(
            shadow_sprite.filter(ImageFilter.GaussianBlur(10 * scale)),
            (left + 5 * scale, top + 12 * scale),
        )
    image.alpha_composite(sprite, (left, top))


def add_sky_layers(image: Image.Image, time_seconds: float, scale: int) -> None:
    cycle = 2 * math.pi * time_seconds / DURATION_SECONDS
    sun = Image.new("RGBA", image.size, (0, 0, 0, 0))
    sun_draw = ImageDraw.Draw(sun)
    sun_x = (420 + 26 * math.sin(cycle)) * scale
    sun_y = (188 - 18 * math.cos(cycle)) * scale
    radius = 58 * scale
    sun_draw.ellipse((sun_x - radius, sun_y - radius, sun_x + radius, sun_y + radius), fill=(*GOLD, 82))
    image.alpha_composite(sun.filter(ImageFilter.GaussianBlur(28 * scale)))

    paste_cloud(
        image,
        (76 + 28 * math.sin(cycle), 205 + 8 * math.cos(cycle)),
        0.76,
        0.42,
        scale,
    )
    paste_cloud(
        image,
        (466 + 34 * math.sin(cycle + 2.1), 338 + 11 * math.cos(cycle + 2.1)),
        0.63,
        0.36,
        scale,
        "warm",
    )
    paste_cloud(
        image,
        (118 + 25 * math.sin(cycle + 4.0), 728 + 9 * math.cos(cycle + 4.0)),
        0.55,
        0.28,
        scale,
    )


def shot_index(time_seconds: float) -> int:
    if 24.5 <= time_seconds < 40.0:
        return 1
    if 40.0 <= time_seconds < 54.5:
        return 2
    return 0


def shot_center(time_seconds: float, phase: Phase) -> tuple[float, float]:
    positions = ((270.0, 470.0), (215.0, 505.0), (300.0, 442.0))
    index = shot_index(time_seconds)
    if phase.name == "rest":
        progress = smooth((time_seconds - phase.start) / (phase.end - phase.start))
        next_index = min(2, index + 1)
        return tuple(
            positions[index][axis] + (positions[next_index][axis] - positions[index][axis]) * progress
            for axis in (0, 1)
        )
    return positions[index]


def breath_scale(phase: Phase, time_seconds: float) -> float:
    progress = (time_seconds - phase.start) / (phase.end - phase.start)
    shot_boost = (1.0, 0.92, 1.14)[shot_index(time_seconds)]
    if phase.name == "inhale":
        value = 0.70 + 0.25 * smooth(progress)
    elif phase.name == "sip":
        value = 0.95 + 0.10 * smooth(progress)
    elif phase.name == "exhale":
        value = 1.05 - 0.35 * smooth(progress)
    else:
        value = 0.70 + 0.012 * math.sin(2 * math.pi * time_seconds / DURATION_SECONDS)
    return value * shot_boost


def phase_color(phase: Phase) -> tuple[int, int, int]:
    return {"inhale": LAVENDER, "sip": ROSE, "exhale": GOLD}.get(phase.name, LAVENDER)


def add_breath_halo(
    image: Image.Image,
    center: tuple[float, float],
    phase: Phase,
    time_seconds: float,
    cloud_size: float,
    scale: int,
) -> None:
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    radius = 124 * cloud_size * scale
    color = phase_color(phase)
    alpha = 34 if phase.name in {"intro", "rest", "close"} else 58
    draw.ellipse(
        (
            center[0] * scale - radius,
            center[1] * scale - radius * 0.72,
            center[0] * scale + radius,
            center[1] * scale + radius * 0.72,
        ),
        fill=(*color, alpha),
    )
    image.alpha_composite(layer.filter(ImageFilter.GaussianBlur(30 * scale)))


def add_sip_puff(
    image: Image.Image,
    center: tuple[float, float],
    phase: Phase,
    time_seconds: float,
    scale: int,
) -> None:
    if phase.name != "sip":
        return
    progress = smooth((time_seconds - phase.start) / (phase.end - phase.start))
    direction = -1 if shot_index(time_seconds) == 1 else 1
    x = center[0] + direction * (135 - 82 * progress)
    y = center[1] - 82 + 40 * progress
    paste_cloud(image, (x, y), 0.25 + 0.08 * progress, fade_window(time_seconds, phase.start, phase.end, 0.25), scale, "warm")


def add_exhale_stream(
    image: Image.Image,
    center: tuple[float, float],
    phase: Phase,
    time_seconds: float,
    scale: int,
) -> None:
    if phase.name != "exhale":
        return
    progress = (time_seconds - phase.start) / (phase.end - phase.start)
    direction = -1 if shot_index(time_seconds) == 1 else 1
    for index in range(5):
        local = clamp(progress * 1.35 - index * 0.16)
        if local <= 0 or local >= 1:
            continue
        x = center[0] + direction * (92 + 245 * local)
        y = center[1] - 38 - 60 * math.sin(math.pi * local) + index * 9
        paste_cloud(
            image,
            (x, y),
            0.18 + 0.18 * local,
            math.sin(math.pi * local) * 0.62,
            scale,
            "warm" if index % 2 else "cool",
        )


def add_foreground_bank(image: Image.Image, time_seconds: float, scale: int) -> None:
    cycle = 2 * math.pi * time_seconds / DURATION_SECONDS
    paste_cloud(image, (80 + 18 * math.sin(cycle), 916), 1.08, 0.58, scale, shadow=True)
    paste_cloud(image, (402 + 20 * math.sin(cycle + 1.7), 930), 1.22, 0.55, scale, "warm", True)


def add_glass_pill(
    image: Image.Image,
    text: str,
    y: float,
    alpha: float,
    scale: int,
    accent: tuple[int, int, int] = INK,
) -> None:
    if not text or alpha <= 0:
        return
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    selected_font = font(19 * scale)
    bounds = draw.textbbox((0, 0), text, font=selected_font)
    width = (bounds[2] - bounds[0]) / scale + 54
    box = (
        round((270 - width / 2) * scale),
        round((y - 24) * scale),
        round((270 + width / 2) * scale),
        round((y + 24) * scale),
    )
    draw.rounded_rectangle(
        box,
        radius=24 * scale,
        fill=(236, 238, 255, round(46 * clamp(alpha))),
        outline=(255, 255, 255, round(90 * clamp(alpha))),
        width=max(1, scale),
    )
    draw.ellipse(
        (
            (270 - width / 2 + 15) * scale,
            (y - 3) * scale,
            (270 - width / 2 + 21) * scale,
            (y + 3) * scale,
        ),
        fill=(*accent, round(220 * clamp(alpha))),
    )
    draw.text(
        (276 * scale, y * scale),
        text,
        font=selected_font,
        fill=(*INK, round(245 * clamp(alpha))),
        anchor="mm",
    )
    image.alpha_composite(layer)


def add_centered_text(
    image: Image.Image,
    text: str,
    y: float,
    size: int,
    alpha: float,
    scale: int,
    fill: tuple[int, int, int] = INK,
) -> None:
    if not text or alpha <= 0:
        return
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.text(
        (270 * scale, y * scale),
        text,
        font=font(size * scale),
        fill=(*fill, round(255 * clamp(alpha))),
        anchor="mm",
    )
    image.alpha_composite(layer)


def phase_label(phase: Phase) -> str:
    return {"inhale": "in", "sip": "more", "exhale": "out"}.get(phase.name, "")


def render_frame(time_seconds: float, scale: int = 2) -> Image.Image:
    if scale not in (1, 2):
        raise ValueError("scale must be 1 or 2")
    validate_timeline(PHASES)
    time_seconds %= DURATION_SECONDS
    phase = phase_at(time_seconds)

    warmth = 0.72 * (1 - math.cos(2 * math.pi * time_seconds / DURATION_SECONDS)) / 2
    image = Image.blend(gradient(scale, False), gradient(scale, True), warmth)
    add_sky_layers(image, time_seconds, scale)

    center = shot_center(time_seconds, phase)
    cloud_size = breath_scale(phase, time_seconds)
    add_breath_halo(image, center, phase, time_seconds, cloud_size, scale)
    add_exhale_stream(image, center, phase, time_seconds, scale)
    paste_cloud(
        image,
        center,
        cloud_size,
        0.98,
        scale,
        "warm" if phase.name == "exhale" else "cool",
        shadow=True,
    )
    add_sip_puff(image, center, phase, time_seconds, scale)
    add_foreground_bank(image, time_seconds, scale)
    image.alpha_composite(grain(scale))

    intro_alpha = fade_window(time_seconds, 0.15, 7.2, 0.8)
    add_centered_text(image, "cyclic sigh", 98, 30, intro_alpha, scale)
    add_centered_text(image, "never forced", 148, 15, fade_window(time_seconds, 2.9, 8.3, 0.65), scale, INK_SOFT)

    label = phase_label(phase)
    if label:
        add_glass_pill(
            image,
            label,
            757,
            fade_window(time_seconds, phase.start, phase.end, 0.4),
            scale,
            phase_color(phase),
        )

    close_alpha = fade_window(time_seconds, 55.0, 59.35, 0.75)
    add_centered_text(image, "again?", 105, 30, close_alpha, scale)
    add_centered_text(image, "Cell Reports Medicine, 2023", 148, 13, close_alpha * 0.8, scale, INK_SOFT)
    return image.convert("RGB")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    for frame_index in range(round(DURATION_SECONDS * FPS)):
        frame = render_frame(frame_index / FPS, args.scale)
        sys.stdout.buffer.write(frame.tobytes())


if __name__ == "__main__":
    main()
