#!/usr/bin/env python3
"""Shared motion and material vocabulary for the Plain-Spoken Pebble Reels.

Ported from the news studio's animation bank and its locked-easing preset
table, kept to the four ideas that survive the trip into a calm, one-minute,
looping practice:

* **Named easings instead of one smoothstep.** Every move picks a curve on
  purpose. A pebble filling with breath and a caption arriving on screen are
  not the same gesture and should not share a curve.
* **A deterministic grain pass.** Fine dot texture, multiplied over the whole
  frame, jumping between five fixed offsets on a 0.4s cadence. It stops the
  flat fills reading as vector art. Fixed offsets rather than noise, because a
  render has to reproduce frame for frame.
* **Strokes that draw themselves on, with a wobble.** The bank gets its
  hand-drawn feel from a turbulence filter; here the same read comes from two
  low harmonics with seeded phases, which is smooth, cheap, and repeatable.
* **12fps stutter, decorative motion only.** The house rule from the bank.
  Small drifting marks step; the thing the viewer is following does not.

The one deliberate divergence: the bank's `scalePop` overshoots at
`back.out(1.7)`, which is a news-reel gesture. Captions here settle at 1.1,
which still arrives rather than fading, without the bounce.
"""

from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw

# --- easings ---------------------------------------------------------------
# Matching the preset table's curves: power1 is quadratic, power2 cubic.


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def linear(progress: float) -> float:
    return clamp(progress)


def smooth(progress: float) -> float:
    """Smoothstep. The old house default, kept for moves that want no accent."""
    progress = clamp(progress)
    return progress * progress * (3 - 2 * progress)


def expo_out(progress: float) -> float:
    """Arrives fast and settles. For anything that should feel already-there."""
    progress = clamp(progress)
    return 1.0 if progress >= 1.0 else 1 - 2 ** (-10 * progress)


def power1_in_out(progress: float) -> float:
    progress = clamp(progress)
    if progress < 0.5:
        return 2 * progress * progress
    return 1 - (-2 * progress + 2) ** 2 / 2


def power2_in_out(progress: float) -> float:
    """The slowest ease in and out of the set. Breath belongs on this curve."""
    progress = clamp(progress)
    if progress < 0.5:
        return 4 * progress * progress * progress
    return 1 - (-2 * progress + 2) ** 3 / 2


def power2_out(progress: float) -> float:
    progress = clamp(progress)
    return 1 - (1 - progress) ** 3


def back_out(progress: float, overshoot: float = 1.1) -> float:
    """Overshoots and settles back. Low overshoot keeps it a settle, not a pop."""
    progress = clamp(progress)
    shifted = progress - 1
    return 1 + (overshoot + 1) * shifted**3 + overshoot * shifted**2


def stutter(time_seconds: float, fps: int = 12) -> float:
    """Quantise a time to a coarser grid, for decorative motion only."""
    if fps <= 0:
        raise ValueError("fps must be positive")
    return math.floor(time_seconds * fps) / fps


# --- material --------------------------------------------------------------

GRAIN_STEP = 0.4  # seconds a single grain offset is held
GRAIN_OFFSETS = ((0, 0), (-13, 5), (20, -15), (-5, -23), (15, 13))
GRAIN_PITCH = 3.0  # logical px between dot centres
GRAIN_DEPTH = 15  # how far a dot pixel darkens, out of 255
VIGNETTE_DEPTH = 0.13  # darkening at the very corners


def grain_index(time_seconds: float, duration_seconds: float) -> int:
    """Which offset is held at this moment.

    Rounds rather than floors so the final frame of the minute lands back on
    the opening offset: the grain then loops as cleanly as everything else on
    screen. It only works because the cadence divides the runtime a whole
    number of times and that count divides evenly by the number of offsets.
    """
    steps = duration_seconds / GRAIN_STEP
    if abs(steps - round(steps)) > 1e-9 or round(steps) % len(GRAIN_OFFSETS):
        raise ValueError(
            f"grain would not loop: {duration_seconds}s must divide by {GRAIN_STEP}s "
            f"into a whole multiple of {len(GRAIN_OFFSETS)} offsets"
        )
    # floor(x + 0.5) rather than round(), which rounds halves to even and would
    # hold every other offset for an extra half step. The epsilon covers frame
    # times that land a hair under a boundary (59.8 / 0.4 is 149.49999...),
    # which would otherwise make one step of the minute a frame short.
    return math.floor(time_seconds / GRAIN_STEP + 0.5 + 1e-9) % len(GRAIN_OFFSETS)


@lru_cache(maxsize=16)
def _texture_layer(width: int, height: int, scale: int, index: int) -> Image.Image:
    """One grain offset and the vignette, baked together into a single multiply.

    Two passes would cost two full-frame operations per frame for a result the
    eye reads as one material, so they are combined once and cached.
    """
    pitch = max(2, round(GRAIN_PITCH * scale))
    dot = max(1, round(pitch * 0.45))
    tile = Image.new("L", (pitch, pitch), 255)
    ImageDraw.Draw(tile).ellipse((0, 0, dot, dot), fill=255 - GRAIN_DEPTH)

    offset_x, offset_y = GRAIN_OFFSETS[index]
    layer = Image.new("L", (width + 2 * pitch, height + 2 * pitch))
    for x in range(0, layer.width, pitch):
        for y in range(0, layer.height, pitch):
            layer.paste(tile, (x, y))
    left = pitch + (round(offset_x * scale) % pitch)
    top = pitch + (round(offset_y * scale) % pitch)
    grain = layer.crop((left, top, left + width, top + height))

    # Kept as RGB, not L: this is multiplied into every frame, and converting
    # on each call costs more than the multiply itself.
    return ImageChops.multiply(grain, _vignette_layer(width, height)).convert("RGB")


@lru_cache(maxsize=4)
def _vignette_layer(width: int, height: int) -> Image.Image:
    """Gentle radial darkening toward the edges, built small and scaled up.

    Computed at a fraction of the frame because a vignette has no detail to
    lose, and a full-resolution pass in Python would cost seconds per render.
    """
    small_width, small_height = 48, 84
    layer = Image.new("L", (small_width, small_height))
    pixels = layer.load()
    for x in range(small_width):
        for y in range(small_height):
            # Wider than tall and sitting slightly high, so the darkening
            # gathers under the frame rather than ringing the subject.
            dx = (x / small_width - 0.5) / 1.12
            dy = (y / small_height - 0.46) / 0.76
            radius = math.hypot(dx, dy) * 2
            fall = clamp((radius - 0.46) / 0.54)
            pixels[x, y] = round(255 * (1 - VIGNETTE_DEPTH * fall * fall))
    return layer.resize((width, height), Image.Resampling.BICUBIC)


def apply_texture(image: Image.Image, time_seconds: float, duration_seconds: float, scale: int) -> None:
    """Lay the grain and vignette over a finished frame, in place."""
    layer = _texture_layer(image.width, image.height, scale, grain_index(time_seconds, duration_seconds))
    image.paste(ImageChops.multiply(image, layer), (0, 0))


# --- hand-drawn strokes ----------------------------------------------------


@lru_cache(maxsize=64)
def _phases(seed: int) -> tuple[float, float, float, float]:
    generator = random.Random(seed)
    return tuple(generator.uniform(0, math.tau) for _ in range(4))


def _wobble(position: float, seed: int, amount: float) -> tuple[float, float]:
    """Two low harmonics, seeded. Smooth along the stroke, identical every render."""
    a, b, c, d = _phases(seed)
    return (
        amount * (math.sin(position * 5.1 + a) * 0.6 + math.sin(position * 11.3 + b) * 0.4),
        amount * (math.sin(position * 4.7 + c) * 0.6 + math.sin(position * 12.9 + d) * 0.4),
    )


def bezier(start: tuple[float, float], control: tuple[float, float], end: tuple[float, float], samples: int = 48) -> list[tuple[float, float]]:
    points = []
    for step in range(samples + 1):
        t = step / samples
        inverse = 1 - t
        points.append(
            (
                inverse * inverse * start[0] + 2 * inverse * t * control[0] + t * t * end[0],
                inverse * inverse * start[1] + 2 * inverse * t * control[1] + t * t * end[1],
            )
        )
    return points


SUPERSAMPLE = 3  # Pillow draws hard-edged lines; a stroke needs softer than that


def hand_stroke(
    canvas,
    points: list[tuple[float, float]],
    progress: float,
    fill: str,
    width: float = 3.0,
    seed: int = 7,
    wobble: float = 2.4,
    alpha: float = 1.0,
) -> None:
    """Draw a wobbled stroke on, revealing the first `progress` of its length.

    Rendered supersampled inside its own bounding box rather than across the
    whole frame: the smoothing is what makes it read as ink instead of a
    plotted line, and doing it frame-wide would cost more than the whole
    remaining composition.
    """
    if progress <= 0 or alpha <= 0.01 or len(points) < 2:
        return
    drawn = points[: max(2, round(len(points) * clamp(progress)))]
    wobbled = [
        (x + dx, y + dy)
        for index, (x, y) in enumerate(drawn)
        for dx, dy in [_wobble(index / max(1, len(points) - 1), seed, wobble)]
    ]

    pad = width + wobble + 2
    left = min(x for x, _ in wobbled) - pad
    top = min(y for _, y in wobbled) - pad
    right = max(x for x, _ in wobbled) + pad
    bottom = max(y for _, y in wobbled) + pad
    origin = (canvas.n(left), canvas.n(top))
    size = (max(1, canvas.n(right) - origin[0]), max(1, canvas.n(bottom) - origin[1]))

    mask = Image.new("L", (size[0] * SUPERSAMPLE, size[1] * SUPERSAMPLE))
    ImageDraw.Draw(mask).line(
        [((canvas.n(x) - origin[0]) * SUPERSAMPLE, (canvas.n(y) - origin[1]) * SUPERSAMPLE) for x, y in wobbled],
        fill=round(255 * clamp(alpha)),
        width=max(1, round(canvas.n(width) * SUPERSAMPLE)),
        joint="curve",
    )
    canvas.image.paste(Image.new("RGB", size, fill), origin, mask.resize(size, Image.Resampling.LANCZOS))
