#!/usr/bin/env python3
"""One-minute step-back practice in the Plain-Spoken Pebble language.

The viewer plays along: bring one small thing to mind, watch it from a few steps
back, then put what you see into words. The screen carries the distance rather
than instructions. A coral pebble sits pressed against your own periwinkle one at
the start, eases away while you look, and comes back as the minute closes, so the
loop returns to where it began.

Grounded in the 2022 meta-analysis of self-distancing: 48 studies, 102 effect
sizes, a small overall effect, and a moderator worth designing around. Picturing
the event and putting it into words beat either the visual approach or the
pronoun swap on its own, so the practice asks for both.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.motion import (
    apply_texture,
    bezier,
    clamp,
    expo_out,
    hand_stroke,
    power1_in_out,
    power2_in_out,
    smooth,
    stutter,
)
from src.practice_pebble import (
    CORAL,
    HAZE,
    PAPER,
    blend,
    chip_box,
    draw_paper,
    fade_window,
    frosted_chip,
    settle,
    tracked_text,
)
from src.sleep_reel import INK, MOON, MUTED, PERIWINKLE, SHADOW, Canvas

WIDTH = 540
HEIGHT = 960
FPS = 30
DURATION_SECONDS = 60.0
SOURCE_URL = "https://doi.org/10.1080/02699931.2022.2134094"
VISIBLE_COPY = ("step back", "keep it small", "look", "say it", "what next", "again?", "Cognition & Emotion, 2022")

CENTRE_Y = 430.0
CENTRE_X = 270.0
# Both pebbles move, so the pair stays centred however far apart they are.
NEAR_OFFSET = 44.0
STEP_OFFSET = 74.0


@dataclass(frozen=True)
class Phase:
    name: str
    start: float
    end: float


PHASES = (
    Phase("settle", 0.0, 9.0),
    Phase("picture", 9.0, 22.0),
    Phase("say", 22.0, 36.0),
    Phase("watch", 36.0, 48.0),
    Phase("hold", 48.0, 54.0),
    Phase("close", 54.0, 60.0),
)
STEP_STARTS = (9.0, 22.0, 36.0)


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


def distance(time_seconds: float) -> float:
    """How far the thing has moved from you, 0 pressed against you and 1 an arm's length off."""
    phase = phase_at(time_seconds)
    progress = (time_seconds - phase.start) / (phase.end - phase.start)
    if phase.name == "settle":
        return 0.0
    if phase.name == "picture":
        # Stepping back is the slow move of the minute, so it eases at both ends.
        return power2_in_out(progress)
    if phase.name == "close":
        return 1.0 - power2_in_out(progress)
    return 1.0


def draw_pebble(canvas: Canvas, centre: tuple[float, float], size: tuple[float, float], fill: str) -> None:
    """The same soft pebble the explainer Reels use."""
    centre_x, centre_y = centre
    width, height = size
    box = (centre_x - width / 2, centre_y - height / 2, centre_x + width / 2, centre_y + height / 2)
    canvas.ellipse((box[0] + 16, box[3] + 10, box[2] - 12, box[3] + 28), fill=SHADOW)
    canvas.rounded_rectangle(box, radius=min(width, height) / 2.3, fill=fill)
    canvas.ellipse((box[0] + 10, box[1] - 7, box[2] - 20, box[3] + 2), fill=fill)


def positions(apart: float) -> tuple[float, float]:
    """Where you sit and where the thing sits, measured out from the centre."""
    offset = NEAR_OFFSET + STEP_OFFSET * apart
    return CENTRE_X - offset, CENTRE_X + offset * 0.95


def draw_account(canvas: Canvas, time_seconds: float, apart: float) -> None:
    """A line drawn from you to the thing while you put what you see into words.

    The meta-analysis found the visual and verbal approach beat either half on
    its own, so the describing gets its own mark on screen rather than living
    only in the narration. It draws on across the phase and holds afterwards,
    the way a said thing stays said, then lets go as the pebbles come back.
    """
    phase = phase_at(time_seconds)
    if phase.name in ("settle", "picture"):
        return
    you_x, thing_x = positions(apart)
    if phase.name == "say":
        drawn = power1_in_out((time_seconds - phase.start) / 8.0)
        alpha = 1.0
    else:
        drawn = 1.0
        alpha = 1.0 if phase.name in ("watch", "hold") else 1.0 - expo_out((time_seconds - phase.start) / 2.4)
    hand_stroke(
        canvas,
        bezier((you_x + 46, CENTRE_Y + 34), ((you_x + thing_x) / 2, CENTRE_Y + 96), (thing_x - 30, CENTRE_Y + 46)),
        drawn,
        MOON,
        width=3.0,
        seed=3,
        wobble=2.2,
        alpha=alpha * 0.92,
    )


def draw_words(canvas: Canvas, time_seconds: float, apart: float) -> None:
    """Small mustard marks crossing the gap while you describe what you can see.

    Stepped to 12fps like every decorative mark in the house style.
    """
    phase = phase_at(time_seconds)
    if phase.name != "say":
        return
    you_x, thing_x = positions(apart)
    progress = (stutter(time_seconds) - phase.start) / (phase.end - phase.start)
    for index in range(4):
        local = clamp(progress * 1.6 - index * 0.18)
        if local <= 0 or local >= 1:
            continue
        travel = smooth(local)
        x = you_x + 52 + (thing_x - you_x - 96) * travel
        y = CENTRE_Y - 10 - 30 * math.sin(math.pi * travel) + index * 7
        radius = 5.6 - index * 0.6
        canvas.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=blend(PAPER, MOON, 0.9 * math.sin(math.pi * local)),
        )


def phase_word(phase: Phase) -> str:
    return {"picture": "look", "say": "say it", "watch": "what next"}.get(phase.name, "")


def draw_step_dots(canvas: Canvas, time_seconds: float) -> None:
    for index, start in enumerate(STEP_STARTS):
        x = 270 - 26 + index * 26
        radius = 4.0
        canvas.ellipse(
            (x - radius, 790 - radius, x + radius, 790 + radius),
            fill=PERIWINKLE if time_seconds >= start else SHADOW,
        )


def render_frame(time_seconds: float, scale: int = 2) -> Image.Image:
    if scale not in (1, 2):
        raise ValueError("scale must be 1 or 2")
    validate_timeline(PHASES)
    time_seconds %= DURATION_SECONDS
    phase = phase_at(time_seconds)
    apart = distance(time_seconds)

    canvas = Canvas(scale)
    draw_paper(canvas, time_seconds)

    you_x, thing_x = positions(apart)
    # The thing shrinks a little as it moves off, the way anything does with distance.
    thing_scale = 1.0 - 0.18 * apart
    draw_pebble(
        canvas,
        (thing_x, CENTRE_Y + 18 * apart),
        (150 * thing_scale, 104 * thing_scale),
        blend(CORAL, HAZE, 0.25 * apart),
    )
    draw_account(canvas, time_seconds, apart)
    draw_words(canvas, time_seconds, apart)
    draw_pebble(canvas, (you_x, CENTRE_Y), (176, 122), PERIWINKLE)

    canvas.rounded_rectangle((132, 44, 408, 86), radius=21, fill=PERIWINKLE)
    canvas.text((270, 65), "PLAIN-SPOKEN PEBBLE", 17, INK)

    intro = fade_window(time_seconds, 0.6, 8.2, 1.0)
    close = fade_window(time_seconds, 54.6, 59.4, 0.9)
    word = phase_word(phase)
    label = word or ("step back" if intro > 0.01 else "again?" if close > 0.01 else "")
    alpha = fade_window(time_seconds, phase.start, phase.end, 0.6) if word else max(intro, close)
    if label:
        size, tracking = (30, 8) if word else (28, 4)
        frosted_chip(canvas, chip_box(label, size, tracking, 656, canvas, settle(alpha)), alpha)
        tracked_text(canvas, label, 656, size, alpha, INK, tracking)

    tracked_text(canvas, "keep it small", 716, 16, intro * 0.85, MUTED, 2)
    if close > 0.01:
        canvas.rounded_rectangle((146, 700, 394, 742), radius=20, fill=MOON)
        canvas.text((270, 721), "Cognition & Emotion, 2022", 15, INK)
    draw_step_dots(canvas, time_seconds)
    apply_texture(canvas.image, time_seconds, DURATION_SECONDS, scale)
    return canvas.image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    for frame_index in range(round(DURATION_SECONDS * FPS)):
        sys.stdout.buffer.write(render_frame(frame_index / FPS, args.scale).tobytes())


if __name__ == "__main__":
    main()
