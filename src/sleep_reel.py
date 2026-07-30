import argparse
import math
import sys
from dataclasses import dataclass
from functools import lru_cache
from itertools import pairwise
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

LOGICAL_WIDTH = 540
LOGICAL_HEIGHT = 960
FPS = 30
DURATION_SECONDS = 35.0
FRAME_COUNT = int(DURATION_SECONDS * FPS)
FONT_PATH = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "UbuntuSans.ttf"
HOOK_SOURCE = "https://www.cdc.gov/nchs/products/databriefs/db559.htm"
HOOK_SOURCE_START = 0.4
EXPLAIN_TEXT_START = 0.4

CREAM = "#F2EEE8"
INK = "#2D3142"
PERIWINKLE = "#9EA9E8"
MOON = "#F4C96B"
SKY = "#8CB7C6"
SAGE = "#A7B9A5"
CORAL = "#E79A7E"
PLUM = "#7F718A"
WHITE = "#FFFFFF"
MUTED = "#626779"
SHADOW = "#D6D0CA"

VISIBLE_COPY = (
    "Nearly 1 in 3 U.S. adults got under seven hours of sleep a day in 2024.",
    "Sleep hygiene means habits that help your body know bedtime is coming.",
    "Start with your wake-up time. Keep it close to the same time most days.",
    "Give yourself a dimmer, quieter hour before bed when you can.",
    "If caffeine keeps you up, move your last cup earlier.",
    "A cool, quiet, dark room is a good place to start.",
    "Pick one to try tonight. Save if useful.",
    "If sleep problems stick around, talk with a healthcare professional.",
)


@dataclass(frozen=True)
class Beat:
    id: str
    start: float
    end: float


BEATS = (
    Beat("hook", 0.0, 4.5),
    Beat("explain", 4.5, 8.5),
    Beat("time", 8.5, 14.0),
    Beat("light", 14.0, 19.5),
    Beat("caffeine", 19.5, 25.0),
    Beat("room", 25.0, 30.5),
    Beat("close", 30.5, 35.0),
)


@lru_cache(maxsize=128)
def load_font(size: int) -> ImageFont.FreeTypeFont:
    if not FONT_PATH.exists():
        raise FileNotFoundError(f"required font not found: {FONT_PATH}")
    return ImageFont.truetype(str(FONT_PATH), size=size)


class Canvas:
    def __init__(self, scale: int) -> None:
        if scale not in (1, 2):
            raise ValueError("scale must be 1 or 2")
        self.scale = scale
        self.image = Image.new("RGB", (LOGICAL_WIDTH * scale, LOGICAL_HEIGHT * scale), CREAM)
        self.draw = ImageDraw.Draw(self.image)

    def n(self, value: float) -> int:
        return round(value * self.scale)

    def point(self, point: tuple[float, float]) -> tuple[int, int]:
        return self.n(point[0]), self.n(point[1])

    def box(self, box: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
        return tuple(self.n(value) for value in box)

    def ellipse(self, box: tuple[float, float, float, float], **kwargs) -> None:
        if "width" in kwargs:
            kwargs["width"] = self.n(kwargs["width"])
        self.draw.ellipse(self.box(box), **kwargs)

    def rounded_rectangle(self, box: tuple[float, float, float, float], radius: float, **kwargs) -> None:
        if "width" in kwargs:
            kwargs["width"] = self.n(kwargs["width"])
        self.draw.rounded_rectangle(self.box(box), radius=self.n(radius), **kwargs)

    def line(self, points: tuple[float, ...], **kwargs) -> None:
        if "width" in kwargs:
            kwargs["width"] = self.n(kwargs["width"])
        self.draw.line(tuple(self.n(value) for value in points), **kwargs)

    def arc(self, box: tuple[float, float, float, float], **kwargs) -> None:
        if "width" in kwargs:
            kwargs["width"] = self.n(kwargs["width"])
        self.draw.arc(self.box(box), **kwargs)

    def text(
        self,
        point: tuple[float, float],
        text: str,
        size: int,
        fill: str,
        anchor: str = "mm",
    ) -> None:
        self.draw.text(
            self.point(point),
            text,
            font=load_font(size * self.scale),
            fill=fill,
            anchor=anchor,
        )

    def center_text(
        self,
        text: str,
        y: float,
        size: int,
        fill: str = INK,
        max_width: int = 452,
        spacing: int = 8,
    ) -> float:
        """Draw centered text growing downward from y and return its logical height."""
        wrapped = self._wrap(text, size, max_width)
        font = load_font(size * self.scale)
        origin = self.point((LOGICAL_WIDTH / 2, y))
        self.draw.multiline_text(
            origin,
            wrapped,
            font=font,
            fill=fill,
            anchor="ma",
            align="center",
            spacing=self.n(spacing),
        )
        bounds = self.draw.multiline_textbbox(
            origin, wrapped, font=font, anchor="ma", align="center", spacing=self.n(spacing)
        )
        return (bounds[3] - bounds[1]) / self.scale

    def _wrap(self, text: str, size: int, max_width: int) -> str:
        selected_font = load_font(size * self.scale)
        lines = []
        current = ""
        for word in text.split():
            candidate = word if not current else f"{current} {word}"
            bounds = self.draw.textbbox((0, 0), candidate, font=selected_font)
            if current and bounds[2] - bounds[0] > self.n(max_width):
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return "\n".join(lines)


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


def draw_blob(
    canvas: Canvas,
    center: tuple[float, float],
    size: tuple[float, float],
    fill: str,
    label: str,
    label_color: str = INK,
    text_size: int = 30,
) -> None:
    center_x, center_y = center
    width, height = size
    box = (
        center_x - width / 2,
        center_y - height / 2,
        center_x + width / 2,
        center_y + height / 2,
    )
    canvas.ellipse((box[0] + 18, box[3] - 4, box[2] - 12, box[3] + 16), fill=SHADOW)
    canvas.rounded_rectangle(box, radius=min(width, height) / 2.3, fill=fill)
    canvas.ellipse((box[0] + 12, box[1] - 8, box[2] - 24, box[3] + 2), fill=fill)
    canvas.text(center, label, text_size, label_color)


def draw_background(canvas: Canvas, time_seconds: float) -> None:
    drift = 14 * math.sin(time_seconds * math.pi / 8)
    canvas.ellipse((-175 + drift, 105, 205 + drift, 460), fill="#E8E4EC")
    canvas.ellipse((370 - drift, 555, 700 - drift, 900), fill="#E8E4EC")
    for index, point in enumerate(((420, 145), (458, 185), (390, 205))):
        pulse = 3 * math.sin(time_seconds + index)
        canvas.ellipse(
            (point[0] - 5 - pulse, point[1] - 5 - pulse, point[0] + 5 + pulse, point[1] + 5 + pulse),
            fill=MOON,
        )


def draw_header(canvas: Canvas) -> None:
    canvas.rounded_rectangle((132, 44, 408, 86), radius=21, fill=PERIWINKLE)
    canvas.text((LOGICAL_WIDTH / 2, 65), "PLAIN-SPOKEN PEBBLE", 17, INK)


def draw_hook(canvas: Canvas, local: float) -> None:
    if local >= 0.15:
        canvas.center_text("NEARLY", 155, 28, MUTED)
    scale = ease((local - 0.25) / 0.7)
    if scale > 0:
        size = max(18, round(88 * scale))
        canvas.center_text("1 IN 3", 205, size, INK)
    if local >= 1.3:
        canvas.center_text("U.S. adults got under seven hours of sleep a day in 2024.", 470, 30, INK)
    if local >= HOOK_SOURCE_START:
        canvas.rounded_rectangle((150, 650, 390, 696), radius=20, fill=MOON)
        canvas.text((LOGICAL_WIDTH / 2, 673), "CDC / NCHS, 2024", 18, INK)


def draw_explain(canvas: Canvas, local: float) -> None:
    progress = ease(local / 0.85)
    y = lerp(700, 280, progress)
    draw_blob(canvas, (LOGICAL_WIDTH / 2, y), (300, 145), PERIWINKLE, "SLEEP HYGIENE", INK, 28)
    if local >= EXPLAIN_TEXT_START:
        canvas.center_text(
            "Sleep hygiene means habits that help your body know bedtime is coming.",
            525,
            29,
        )
    if local >= 3.0:
        canvas.center_text("Start small.", 700, 24, MUTED)


def draw_time(canvas: Canvas, local: float) -> None:
    draw_blob(canvas, (LOGICAL_WIDTH / 2, 285), (220, 135), PERIWINKLE, "TIME")
    canvas.ellipse((160, 385, 380, 605), outline=INK, width=6)
    angle = -90 + 65 * smooth(local / 4.8)
    radians = math.radians(angle)
    canvas.line(
        (
            LOGICAL_WIDTH / 2,
            495,
            LOGICAL_WIDTH / 2 + math.cos(radians) * 78,
            495 + math.sin(radians) * 78,
        ),
        fill=INK,
        width=7,
    )
    canvas.ellipse((258, 483, 282, 507), fill=MOON)
    if local >= 0.7:
        canvas.center_text("Start with your wake-up time.", 650, 30)
    if local >= 3.0:
        canvas.center_text("Keep it close to the same time most days.", 715, 22, MUTED)


def draw_light(canvas: Canvas, local: float) -> None:
    dim = smooth(local / 4.7)
    canvas.ellipse((115, 190, 425, 500), fill=MOON)
    cover_x = lerp(480, 150, dim)
    canvas.ellipse((cover_x, 155, cover_x + 330, 500), fill="#E8E4EC")
    draw_blob(canvas, (LOGICAL_WIDTH / 2, 520), (190, 118), SKY, "LIGHT")
    if local >= 0.8:
        canvas.center_text("Give yourself a dimmer, quieter hour before bed when you can.", 660, 27)


def draw_caffeine(canvas: Canvas, local: float) -> None:
    progress = ease(local / 0.9)
    x = lerp(-180, LOGICAL_WIDTH / 2, progress)
    draw_blob(canvas, (x, 285), (245, 135), CORAL, "CAFFEINE", INK, 26)
    canvas.rounded_rectangle((185, 395, 355, 555), radius=22, fill="#F7F1E9", outline=INK, width=5)
    canvas.arc((330, 430, 410, 520), start=-80, end=80, fill=INK, width=6)
    for index in range(3):
        wave = 8 * math.sin(local + index)
        canvas.arc((205 + index * 38, 345 - wave, 250 + index * 38, 420 - wave), start=180, end=360, fill=MUTED, width=4)
    if local >= 1.0:
        canvas.center_text("If caffeine keeps you up, move your last cup earlier.", 650, 29)


def draw_room(canvas: Canvas, local: float) -> None:
    draw_blob(canvas, (LOGICAL_WIDTH / 2, 250), (205, 126), PLUM, "ROOM", WHITE)
    canvas.rounded_rectangle((105, 355, 435, 610), radius=28, fill="#3D435B")
    canvas.ellipse((160, 415, 250, 505), fill=MOON)
    canvas.ellipse((195, 390, 285, 500), fill="#3D435B")
    for x, y in ((320, 410), (365, 470), (305, 535)):
        canvas.ellipse((x - 5, y - 5, x + 5, y + 5), fill=WHITE)
    if local >= 0.8:
        canvas.center_text("A cool, quiet, dark room is a good place to start.", 660, 29)


def draw_close(canvas: Canvas, local: float) -> None:
    items = (("TIME", PERIWINKLE), ("LIGHT", MOON), ("CAFFEINE", CORAL), ("ROOM", PLUM))
    for index, (label, color) in enumerate(items):
        progress = ease((local - index * 0.15) / 0.55)
        if progress <= 0:
            continue
        x = 88 + index * 122
        y = lerp(620, 260 + (index % 2) * 90, progress)
        draw_blob(canvas, (x, y), (112, 78), color, label, WHITE if color == PLUM else INK, 16)
    if local >= 0.75:
        canvas.center_text("PICK ONE TO TRY TONIGHT", 520, 34)
    if local >= 1.55:
        canvas.center_text("Save if useful.", 620, 26, MUTED)
    if local >= 0.0:
        canvas.center_text(
            "If sleep problems stick around, talk with a healthcare professional.",
            700,
            19,
            INK,
        )


RENDERERS = {
    "hook": draw_hook,
    "explain": draw_explain,
    "time": draw_time,
    "light": draw_light,
    "caffeine": draw_caffeine,
    "room": draw_room,
    "close": draw_close,
}


def render_frame(time_seconds: float, scale: int = 2) -> Image.Image:
    beat = find_beat(time_seconds)
    canvas = Canvas(scale)
    draw_background(canvas, time_seconds)
    draw_header(canvas)
    RENDERERS[beat.id](canvas, time_seconds - beat.start)
    return canvas.image


def stream_frames(scale: int) -> None:
    validate_timeline(BEATS)
    output = sys.stdout.buffer
    try:
        for frame_index in range(FRAME_COUNT):
            output.write(render_frame(frame_index / FPS, scale=scale).tobytes())
    except BrokenPipeError:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the Plain-Spoken Pebble sleep hygiene Reel")
    parser.add_argument("--scale", type=int, choices=(1, 2), default=2)
    parser.add_argument("--poster", type=Path)
    parser.add_argument("--time", type=float, default=32.5)
    args = parser.parse_args()
    if args.poster:
        if not 0 <= args.time < DURATION_SECONDS:
            raise ValueError("poster timestamp must be inside the timeline")
        args.poster.parent.mkdir(parents=True, exist_ok=True)
        render_frame(args.time, scale=args.scale).save(args.poster)
        print(args.poster)
        return
    stream_frames(args.scale)


if __name__ == "__main__":
    main()
