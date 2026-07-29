import argparse
import math
import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from identities import IDENTITIES, Identity, accessible_foreground, validate_identities

WIDTH = 540
HEIGHT = 960
FPS = 30
FRAME_COUNT = 150
FONT_PATH = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "UbuntuSans.ttf"


@lru_cache(maxsize=64)
def font(size: int) -> ImageFont.FreeTypeFont:
    if not FONT_PATH.exists():
        raise FileNotFoundError(f"required font not found: {FONT_PATH}")
    return ImageFont.truetype(str(FONT_PATH), size=size)


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


def width_of(draw: ImageDraw.ImageDraw, text: str, selected_font: ImageFont.FreeTypeFont) -> int:
    bounds = draw.textbbox((0, 0), text, font=selected_font)
    return bounds[2] - bounds[0]


def center_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: float,
    size: int,
    fill: str,
    spacing: int = 8,
) -> None:
    draw.multiline_text(
        (WIDTH / 2, y),
        text,
        font=font(size),
        fill=fill,
        anchor="ma",
        align="center",
        spacing=spacing,
        stroke_width=0,
    )


def header(draw: ImageDraw.ImageDraw, identity: Identity, number: int) -> None:
    text = f"0{number}  {identity.name.upper()}"
    selected_font = font(17)
    tag_width = width_of(draw, text, selected_font) + 30
    accent = identity.accents[0]
    draw.rounded_rectangle(((WIDTH - tag_width) / 2, 55, (WIDTH + tag_width) / 2, 94), radius=20, fill=accent)
    draw.text((WIDTH / 2, 74), text, font=selected_font, fill=accessible_foreground(accent, identity.text_color), anchor="mm")


def footer(draw: ImageDraw.ImageDraw, identity: Identity) -> None:
    draw.text((36, 916), f"SOURCE {identity.source_id} · BRAND STUDY", font=font(13), fill=identity.text_color)
    draw.text((504, 916), "05 SEC", font=font(13), fill=identity.text_color, anchor="ra")


def soft_punctuation(image: Image.Image, identity: Identity, time_seconds: float) -> None:
    draw = ImageDraw.Draw(image)
    coral, sage, blue = identity.accents
    breath = 1 + 0.018 * math.sin(time_seconds * math.pi / 2.5)
    radius = 240 * breath
    draw.ellipse((WIDTH / 2 - radius, 250 - radius, WIDTH / 2 + radius, 250 + radius), fill="#FAF5EC")
    comma_y = lerp(105, 235, ease(time_seconds / 0.8))
    draw.text((118, comma_y), ",", font=font(230), fill=coral, anchor="ma")
    if time_seconds >= 0.65:
        center_text(draw, "YOU CAN PAUSE", 370, 43, identity.text_color)
    if time_seconds >= 1.45:
        expansion = ease((time_seconds - 1.45) / 0.9)
        left_x = lerp(240, 74, expansion)
        right_x = lerp(300, 466, expansion)
        draw.text((left_x, 540), "(", font=font(145), fill=sage, anchor="mm")
        draw.text((right_x, 540), ")", font=font(145), fill=sage, anchor="mm")
        center_text(draw, "without falling behind", 525, 27, identity.text_color)
    if time_seconds >= 3.35:
        fall = ease((time_seconds - 3.35) / 0.65)
        y = lerp(350, 710, fall)
        squash = 1 - 0.25 * math.sin(clamp((time_seconds - 3.9) / 0.5) * math.pi)
        draw.ellipse((248, y - 24 * squash, 292, y + 24 * squash), fill=blue)
    if time_seconds >= 4.15:
        center_text(draw, "A thought can land gently.", 780, 23, identity.text_color)


def pebble(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float], fill: str, text: str, text_color: str) -> None:
    left, top, right, bottom = box
    draw.rounded_rectangle(box, radius=min((right - left), (bottom - top)) / 2.4, fill=fill)
    draw.ellipse((left + 12, top - 8, right - 20, bottom + 4), fill=fill)
    foreground = accessible_foreground(fill, text_color)
    draw.text(((left + right) / 2, (top + bottom) / 2), text, font=font(25), fill=foreground, anchor="mm")


def plain_spoken_pebble(image: Image.Image, identity: Identity, time_seconds: float) -> None:
    draw = ImageDraw.Draw(image)
    sage, apricot, sky, plum = identity.accents
    arrivals = [
        (0.2, (-170, 270), (52, 270), (185, 125), sage, "FEET"),
        (0.85, (540, 430), (292, 430), (190, 110), apricot, "ROOM"),
        (1.5, (-160, 570), (90, 570), (165, 105), sky, "SOUND"),
        (2.35, (540, 680), (250, 665), (215, 132), plum, "NOW"),
    ]
    for onset, start, end, size, color, text in arrivals:
        if time_seconds < onset:
            continue
        progress = ease((time_seconds - onset) / 0.75)
        x = lerp(start[0], end[0], progress)
        y = lerp(start[1], end[1], progress)
        breathe = 1 + 0.012 * math.sin((time_seconds - onset) * math.pi)
        width, height = size[0] * breathe, size[1] / breathe
        draw.ellipse((x + 12, y + height - 2, x + width - 6, y + height + 15), fill="#D8D1C5")
        pebble(draw, (x, y, x + width, y + height), color, text, identity.text_color)
    if time_seconds >= 3.55:
        center_text(draw, "FEET HERE.  SOUND AROUND.  NOW.", 825, 22, identity.text_color)


def permission_slip(image: Image.Image, identity: Identity, time_seconds: float) -> None:
    draw = ImageDraw.Draw(image)
    coral, lilac, mint = identity.accents
    tab_progress = ease(time_seconds / 0.85)
    tab_y = lerp(960, 245, tab_progress)
    draw.rounded_rectangle((58, tab_y, 482, tab_y + 165), radius=38, fill=coral)
    draw.ellipse((88, tab_y + 55, 126, tab_y + 93), fill=identity.background_color)
    draw.text((285, tab_y + 82), "PAUSE", font=font(54), fill=identity.text_color, anchor="mm")
    if time_seconds >= 1.8:
        loop_progress = ease((time_seconds - 1.8) / 1.0)
        draw.arc((84, 430, 456, 760), start=195, end=195 + 310 * loop_progress, fill=lilac, width=28)
        draw.rounded_rectangle((454, 550, 560, 675), radius=28, fill=lilac)
    if time_seconds >= 2.8:
        draw.rounded_rectangle((-58, 690, 118, 785), radius=26, fill=mint)
        draw.text((74, 738), "CHOOSE", font=font(17), fill=identity.text_color, anchor="mm")
    if time_seconds >= 1.0:
        center_text(draw, "IF YOU WANT.", 485, 45, identity.text_color)
    if time_seconds >= 3.55:
        center_text(draw, "THE CHOICE STAYS YOURS", 810, 23, identity.text_color)


def inner_weather(image: Image.Image, identity: Identity, time_seconds: float) -> None:
    draw = ImageDraw.Draw(image)
    sky, sun, lilac, green = identity.accents
    drift = 20 * math.sin(time_seconds * math.pi / 2.5)
    draw.ellipse((-100 + drift, 155, 310 + drift, 505), fill="#C8E0E5")
    draw.ellipse((255 - drift, 110, 650 - drift, 470), fill="#E9DFF0")
    draw.ellipse((90, 565, 500, 875), fill="#CDE3D5")
    center_x, center_y = WIDTH / 2, 455
    draw.ellipse((105, 290, 435, 620), fill=identity.background_color, outline=sky, width=18)
    angle = lerp(-125, 125, smooth(time_seconds / 4.2))
    radians = math.radians(angle)
    endpoint = (center_x + math.cos(radians) * 118, center_y + math.sin(radians) * 118)
    draw.line((center_x, center_y, endpoint[0], endpoint[1]), fill=identity.text_color, width=10)
    draw.ellipse((center_x - 18, center_y - 18, center_x + 18, center_y + 18), fill=sun)
    center_text(draw, "NOTICE", 390, 38, identity.text_color)
    labels = (("HEAVY", 122, 675, lilac), ("LIGHT", 270, 710, sun), ("MIXED", 418, 675, green))
    for text, x, y, color in labels:
        draw.rounded_rectangle((x - 60, y - 24, x + 60, y + 24), radius=18, fill=color)
        draw.text((x, y), text, font=font(16), fill=identity.text_color, anchor="mm")
    if time_seconds >= 3.45:
        center_text(draw, "What's here—without grading it?", 805, 23, identity.text_color)


def kind_broadcast(image: Image.Image, identity: Identity, time_seconds: float) -> None:
    draw = ImageDraw.Draw(image)
    yellow, coral, mint, blue = identity.accents
    pulse = 8 + 5 * (0.5 + 0.5 * math.sin(time_seconds * math.pi * 2))
    draw.ellipse((56 - pulse, 150 - pulse, 56 + pulse, 150 + pulse), fill=coral)
    draw.text((86, 150), "LIVE CHECK-IN", font=font(22), fill=identity.text_color, anchor="lm")
    bars = [
        (0.2, -500, 44, 280, 496, 390, yellow, "NOTICE"),
        (0.9, 540, 72, 410, 468, 520, mint, "YOUR"),
        (1.6, -500, 44, 540, 496, 675, blue, "SHOULDERS"),
    ]
    for onset, start_x, end_x, top, right, bottom, color, text in bars:
        if time_seconds < onset:
            continue
        x = lerp(start_x, end_x, ease((time_seconds - onset) / 0.65))
        if x >= right:
            continue
        draw.rounded_rectangle((x, top, right, bottom), radius=34, fill=color)
        draw.text(((x + right) / 2, (top + bottom) / 2), text, font=font(42), fill="#18212B", anchor="mm")
    if time_seconds >= 2.8:
        draw.rounded_rectangle((68, 735, 472, 810), radius=26, outline=identity.text_color, width=3)
        draw.text((WIDTH / 2, 772), "NO SCORE. JUST NOTICE.", font=font(22), fill=identity.text_color, anchor="mm")
    if time_seconds >= 4.0:
        draw.ellipse((478, 143, 494, 159), fill=yellow)


RENDERERS = {
    "soft-punctuation": soft_punctuation,
    "plain-spoken-pebble": plain_spoken_pebble,
    "permission-slip": permission_slip,
    "inner-weather": inner_weather,
    "kind-broadcast": kind_broadcast,
}


def get_identity(slug: str) -> tuple[int, Identity]:
    for index, identity in enumerate(IDENTITIES, start=1):
        if identity.slug == slug:
            return index, identity
    raise ValueError(f"unknown identity: {slug}")


def render_frame(identity: Identity, number: int, time_seconds: float) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), identity.background_color)
    draw = ImageDraw.Draw(image)
    header(draw, identity, number)
    RENDERERS[identity.slug](image, identity, time_seconds)
    footer(draw, identity)
    return image


def stream(identity: Identity, number: int) -> None:
    output = sys.stdout.buffer
    try:
        for frame_index in range(FRAME_COUNT):
            output.write(render_frame(identity, number, frame_index / FPS).tobytes())
    except BrokenPipeError:
        pass


def main() -> None:
    validate_identities(IDENTITIES)
    parser = argparse.ArgumentParser(description="Render one wellness brand identity study")
    parser.add_argument("--identity", required=True, choices=[item.slug for item in IDENTITIES])
    parser.add_argument("--poster", type=Path)
    parser.add_argument("--time", type=float, default=3.8)
    args = parser.parse_args()
    number, identity = get_identity(args.identity)
    if args.poster:
        if not 0 <= args.time < identity.duration_seconds:
            raise ValueError("poster timestamp must be inside the clip")
        args.poster.parent.mkdir(parents=True, exist_ok=True)
        render_frame(identity, number, args.time).save(args.poster)
        print(args.poster)
        return
    stream(identity, number)


if __name__ == "__main__":
    main()
