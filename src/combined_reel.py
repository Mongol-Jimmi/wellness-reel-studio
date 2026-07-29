import argparse
import math
import sys
from dataclasses import dataclass
from functools import lru_cache
from itertools import pairwise
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = 540
HEIGHT = 960
FPS = 30
DURATION_SECONDS = 25.0
FRAME_COUNT = int(DURATION_SECONDS * FPS)
FONT_PATH = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "UbuntuSans.ttf"

OAT = "#F3EBDD"
CHARCOAL = "#303331"
SAGE = "#9FB7A3"
APRICOT = "#EFA982"
SKY = "#9FC7D5"
PLUM = "#806C83"
WHITE = "#FFFFFF"
SHADOW = "#D8D1C5"
MUTED = "#6E716E"
SAFETY_BANNER_TOP = 780
CLOSE_DISCLOSURE_START = 0.0


@dataclass(frozen=True)
class Beat:
    id: str
    start: float
    end: float


BEATS = (
    Beat("intro", 0.0, 3.5),
    Beat("feet", 3.5, 8.5),
    Beat("sound", 8.5, 13.5),
    Beat("air", 13.5, 19.5),
    Beat("now", 19.5, 22.5),
    Beat("close", 22.5, 25.0),
)


@lru_cache(maxsize=64)
def font(size: int) -> ImageFont.FreeTypeFont:
    if not FONT_PATH.exists():
        raise FileNotFoundError(f"required font not found: {FONT_PATH}")
    return ImageFont.truetype(str(FONT_PATH), size=size)


def validate_timeline(beats: tuple[Beat, ...]) -> None:
    if not beats or beats[0].start != 0.0 or beats[-1].end != DURATION_SECONDS:
        raise ValueError("timeline boundaries are invalid")
    for previous, current in pairwise(beats):
        if previous.end != current.start:
            raise ValueError(f"gap or overlap between {previous.id} and {current.id}")
    if any(beat.end <= beat.start for beat in beats):
        raise ValueError("every beat must have positive duration")


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def ease(value: float) -> float:
    value = clamp(value)
    return 1 - (1 - value) ** 3


def smooth(value: float) -> float:
    value = clamp(value)
    return value * value * (3 - 2 * value)


def lerp(start: float, end: float, progress: float) -> float:
    return start + (end - start) * progress


def find_beat(time_seconds: float) -> Beat:
    for beat in BEATS:
        if beat.start <= time_seconds < beat.end:
            return beat
    raise ValueError(f"timestamp outside timeline: {time_seconds}")


def text_width(draw: ImageDraw.ImageDraw, text: str, selected_font: ImageFont.FreeTypeFont) -> int:
    bounds = draw.textbbox((0, 0), text, font=selected_font)
    return bounds[2] - bounds[0]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, size: int, max_width: int) -> str:
    selected_font = font(size)
    lines = []
    current = ""
    for word in text.split():
        candidate = word if not current else f"{current} {word}"
        if current and text_width(draw, candidate, selected_font) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return "\n".join(lines)


def center_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: float,
    size: int,
    fill: str = CHARCOAL,
    max_width: int = 452,
    spacing: int = 8,
) -> None:
    draw.multiline_text(
        (WIDTH / 2, y),
        wrap_text(draw, text, size, max_width),
        font=font(size),
        fill=fill,
        anchor="ma",
        align="center",
        spacing=spacing,
    )


def draw_background(draw: ImageDraw.ImageDraw, time_seconds: float) -> None:
    drift = 18 * math.sin(time_seconds * math.pi / 6)
    draw.ellipse((-170 + drift, 105, 215 + drift, 455), fill="#EEE5D7")
    draw.ellipse((360 - drift, 530, 675 - drift, 850), fill="#EEE5D7")


def draw_header(draw: ImageDraw.ImageDraw) -> None:
    label = "PLAIN-SPOKEN PEBBLE"
    draw.rounded_rectangle((132, 46, 408, 88), radius=21, fill=SAGE)
    draw.text((WIDTH / 2, 67), label, font=font(17), fill=CHARCOAL, anchor="mm")


def active_footer_index(time_seconds: float) -> int:
    beat_id = find_beat(time_seconds).id
    return {"feet": 0, "sound": 1, "air": 2, "now": 3, "close": 3}.get(beat_id, -1)


def draw_footer(draw: ImageDraw.ImageDraw, time_seconds: float) -> None:
    labels = (("FEET", SAGE), ("SOUND", SKY), ("AIR", APRICOT), ("NOW", PLUM))
    active = active_footer_index(time_seconds)
    draw.rounded_rectangle((42, SAFETY_BANNER_TOP, 498, 824), radius=20, fill="#E4DCCE")
    draw.text(
        (WIDTH / 2, 802),
        "GENERAL WELLNESS • STOP IF THIS FEELS WORSE",
        font=font(16),
        fill=CHARCOAL,
        anchor="mm",
    )
    for index, (label, color) in enumerate(labels):
        x = 96 + index * 116
        radius = 13 if index == active else 9
        draw.ellipse((x - radius, 858 - radius, x + radius, 858 + radius), fill=color)
        draw.text((x, 886), label, font=font(13), fill=CHARCOAL, anchor="mm")


def draw_blob(
    draw: ImageDraw.ImageDraw,
    center: tuple[float, float],
    size: tuple[float, float],
    fill: str,
    label: str,
    label_color: str = CHARCOAL,
) -> None:
    center_x, center_y = center
    width, height = size
    box = (
        center_x - width / 2,
        center_y - height / 2,
        center_x + width / 2,
        center_y + height / 2,
    )
    draw.ellipse((box[0] + 18, box[3] - 4, box[2] - 12, box[3] + 17), fill=SHADOW)
    draw.rounded_rectangle(box, radius=min(width, height) / 2.3, fill=fill)
    draw.ellipse((box[0] + 12, box[1] - 8, box[2] - 24, box[3] + 2), fill=fill)
    draw.text((center_x, center_y), label, font=font(31), fill=label_color, anchor="mm")


def draw_intro(draw: ImageDraw.ImageDraw, local: float) -> None:
    center_text(draw, "A GENTLE CHECK-IN", 205, 38)
    words = (("FEET", SAGE, 108), ("SOUND", SKY, 216), ("AIR", APRICOT, 324), ("NOW", PLUM, 432))
    for index, (label, color, x) in enumerate(words):
        onset = 0.35 + index * 0.38
        if local < onset:
            continue
        progress = ease((local - onset) / 0.55)
        y = lerp(690, 420 + (index % 2) * 112, progress)
        draw_blob(draw, (x, y), (112, 82), color, label, WHITE if color == PLUM else CHARCOAL)
    if local >= 2.15:
        center_text(draw, "No need to force a result.", 690, 26, MUTED)


def draw_feet(draw: ImageDraw.ImageDraw, local: float) -> None:
    progress = ease(local / 1.1)
    y = lerp(700, 315, progress)
    breathe = 1 + 0.015 * math.sin(local * math.pi)
    draw_blob(draw, (WIDTH / 2, y), (238 * breathe, 158 / breathe), SAGE, "FEET")
    if local >= 0.8:
        center_text(draw, "If you'd like, notice where your feet or body meet a stable surface.", 520, 29)
    if local >= 3.3:
        center_text(draw, "Just notice the contact.", 705, 24, MUTED)


def draw_sound(draw: ImageDraw.ImageDraw, local: float) -> None:
    progress = ease(local / 1.0)
    x = lerp(-150, WIDTH / 2, progress)
    draw_blob(draw, (x, 320), (210, 136), SKY, "SOUND")
    if local >= 0.7:
        rings = min(3, int((local - 0.7) / 0.55) + 1)
        for index in range(rings):
            radius = 80 + index * 43
            draw.arc(
                (WIDTH / 2 - radius, 320 - radius, WIDTH / 2 + radius, 320 + radius),
                start=-35,
                end=35,
                fill="#6F9DAF",
                width=7,
            )
    if local >= 1.2:
        center_text(draw, "If you'd like, name one sound near you.", 555, 31)
    if local >= 3.25:
        center_text(draw, "No need to change it.", 700, 24, MUTED)


def draw_air(draw: ImageDraw.ImageDraw, local: float) -> None:
    cycle = smooth(clamp(local / 5.3))
    scale = 0.9 + 0.1 * math.sin(cycle * math.pi)
    draw_blob(draw, (WIDTH / 2, 300), (225 * scale, 142 * scale), APRICOT, "AIR")
    ring_radius = 130 + 70 * math.sin(cycle * math.pi)
    draw.ellipse(
        (
            WIDTH / 2 - ring_radius,
            300 - ring_radius,
            WIDTH / 2 + ring_radius,
            300 + ring_radius,
        ),
        outline="#D58962",
        width=5,
    )
    if local >= 0.5:
        center_text(draw, "If you'd like, let one breath move only as deeply as feels comfortable.", 515, 27)
    if local >= 3.65:
        center_text(draw, "Don't force it.", 725, 27, MUTED)


def draw_now(draw: ImageDraw.ImageDraw, local: float) -> None:
    progress = ease(local / 0.65)
    draw_blob(draw, (WIDTH / 2, lerp(700, 330, progress)), (230, 154), PLUM, "NOW", WHITE)
    if local >= 0.7:
        center_text(draw, "If you'd like, notice whether your attention shifted.", 555, 29)
    if local >= 1.8:
        center_text(draw, "No score. No required feeling.", 715, 24, MUTED)


def draw_close(draw: ImageDraw.ImageDraw, local: float) -> None:
    colors = (SAGE, SKY, APRICOT, PLUM)
    labels = ("FEET", "SOUND", "AIR", "NOW")
    for index, (label, color) in enumerate(zip(labels, colors)):
        progress = ease((local - index * 0.16) / 0.55)
        if progress <= 0:
            continue
        x = 96 + index * 116
        y = lerp(620, 290 + (index % 2) * 80, progress)
        draw_blob(draw, (x, y), (108, 78), color, label, WHITE if color == PLUM else CHARCOAL)
    if local >= 0.75:
        center_text(draw, "SAVE IF USEFUL", 585, 39)
    if local >= CLOSE_DISCLOSURE_START:
        center_text(draw, "This was a check-in, not medical treatment.", 700, 22, CHARCOAL)


RENDERERS = {
    "intro": draw_intro,
    "feet": draw_feet,
    "sound": draw_sound,
    "air": draw_air,
    "now": draw_now,
    "close": draw_close,
}


def render_frame(time_seconds: float) -> Image.Image:
    beat = find_beat(time_seconds)
    image = Image.new("RGB", (WIDTH, HEIGHT), OAT)
    draw = ImageDraw.Draw(image)
    draw_background(draw, time_seconds)
    draw_header(draw)
    RENDERERS[beat.id](draw, time_seconds - beat.start)
    draw_footer(draw, time_seconds)
    return image


def stream_frames() -> None:
    validate_timeline(BEATS)
    output = sys.stdout.buffer
    try:
        for frame_index in range(FRAME_COUNT):
            output.write(render_frame(frame_index / FPS).tobytes())
    except BrokenPipeError:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the Plain-Spoken Pebble combined check-in")
    parser.add_argument("--poster", type=Path)
    parser.add_argument("--time", type=float, default=21.5)
    args = parser.parse_args()
    if args.poster:
        if not 0 <= args.time < DURATION_SECONDS:
            raise ValueError("poster timestamp must be inside the timeline")
        args.poster.parent.mkdir(parents=True, exist_ok=True)
        render_frame(args.time).save(args.poster)
        print(args.poster)
        return
    stream_frames()


if __name__ == "__main__":
    main()
