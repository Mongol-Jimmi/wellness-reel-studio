from dataclasses import dataclass


@dataclass(frozen=True)
class Identity:
    source_id: str
    slug: str
    name: str
    duration_seconds: float
    background_color: str
    text_color: str
    accents: tuple[str, ...]
    sample_prompt: str


IDENTITIES = (
    Identity(
        "A4",
        "soft-punctuation",
        "Soft Punctuation",
        5.0,
        "#F5EBDD",
        "#24343A",
        ("#E87762", "#78A88C", "#6C8FB3"),
        "You can pause, without falling behind.",
    ),
    Identity(
        "R4",
        "plain-spoken-pebble",
        "Plain-Spoken Pebble",
        5.0,
        "#F3EBDD",
        "#303331",
        ("#9FB7A3", "#EFA982", "#9FC7D5", "#806C83"),
        "FEET here. SOUND around. NOW.",
    ),
    Identity(
        "R1",
        "permission-slip",
        "Permission Slip",
        5.0,
        "#FFF7ED",
        "#243039",
        ("#F47C6B", "#B9A7E8", "#8FCDB7"),
        "Pause, if you want. The choice stays yours.",
    ),
    Identity(
        "G3",
        "inner-weather",
        "Inner Weather",
        5.0,
        "#DCEFF2",
        "#21343B",
        ("#7AA6B8", "#F2C66D", "#B796C8", "#73A989"),
        "Notice what's here—without grading it.",
    ),
    Identity(
        "A6",
        "kind-broadcast",
        "Kind Broadcast",
        5.0,
        "#18212B",
        "#FFF8E8",
        ("#FFCF66", "#EF7F72", "#76C9B1", "#86A8E7"),
        "A five-second check-in: notice your shoulders.",
    ),
)


def _rgb(hex_color: str) -> tuple[float, float, float]:
    value = hex_color.removeprefix("#")
    if len(value) != 6:
        raise ValueError(f"invalid color: {hex_color}")
    return tuple(int(value[index : index + 2], 16) / 255 for index in (0, 2, 4))


def _luminance(hex_color: str) -> float:
    channels = tuple(
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in _rgb(hex_color)
    )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(first: str, second: str) -> float:
    bright, dark = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (bright + 0.05) / (dark + 0.05)


def accessible_foreground(background: str, preferred: str) -> str:
    if contrast_ratio(preferred, background) >= 4.5:
        return preferred
    candidates = ("#121212", "#FFFFFF")
    return max(candidates, key=lambda color: contrast_ratio(color, background))


def validate_identities(identities: tuple[Identity, ...]) -> None:
    if not identities:
        raise ValueError("at least one identity is required")
    slugs = [identity.slug for identity in identities]
    if len(slugs) != len(set(slugs)):
        raise ValueError("identity slugs must be unique")
    for identity in identities:
        if identity.duration_seconds <= 0:
            raise ValueError(f"invalid duration for {identity.slug}")
        if contrast_ratio(identity.text_color, identity.background_color) < 4.5:
            raise ValueError(f"primary copy contrast is too low for {identity.slug}")
