# ADR 0003: A shared motion vocabulary, ported from the news studio's animation bank

## Status

Accepted, 2026-07-31.

## Context

The one-minute practice Reels were animated ad hoc. Every move in both renderers ran
through a single smoothstep, decorative marks moved at the same rate as the thing the
viewer was following, and the frames were flat fills with no material to them. They read
as competent vector animation rather than as a made object.

The news studio in `openmontage-news-studio` had already solved this for a different
house style. Its `lib/vox_motion_presets/vox-presets.js` locks an easing per gesture and
refuses to expose them as options, and its `lib/animation_bank/` holds 36 catalogued
entries with lint, dependency resolution and a browsable preview page.

That studio composes in HTML and CSS, animates with GSAP, and renders by capturing frames
from a headless browser. The practice Reels compose in Pillow, and their tests assert on
rendered frames — including the loop seam, which is checked as a mean pixel delta between
the first and last frame of the minute.

## Decision

Port the ideas, not the stack. `src/motion.py` holds:

- **Named easings per gesture**, matching the preset table's curves. The long breath moves
  sit on `power2_in_out` so they stall at the turn; the second sip takes `expo_out`; the
  captions arrive on `back_out`.
- **A deterministic grain and vignette pass**, following the bank's `paper-grain` and
  `edge-vignette` entries. Fixed offsets on a fixed cadence rather than noise, for the same
  reason that entry gives: a render has to reproduce frame for frame.
- **Strokes that draw themselves on with a wobble**, following `hand-drawn-marks`. The bank
  gets its wobble from an SVG turbulence filter; the same read comes here from two low
  harmonics with seeded phases, which is cheap, smooth and repeatable.
- **12fps stutter on decorative motion only**, which is the bank's hard rule.

Two deliberate divergences from the source, both because this is a calm practice and not a
news reel:

- `scalePop` overshoots at `back.out(1.7)`. Captions here settle at `1.1`, which still
  arrives rather than fades, without the bounce.
- The grain steps on `floor(t / step + 0.5)` rather than `floor(t / step)`, so the last
  frame of the minute lands back on the opening offset. Without that the loop seam test
  fails on the texture alone: a stepped sequence's last step is never its first. This only
  works because the cadence divides the runtime a whole number of times and that count
  divides evenly by the number of offsets, so `grain_index` refuses any runtime where it
  would not.

The bank's catalogue machinery — the entry format, lint, dependency resolution, preview
page — is **not** ported. It earns its keep across 36 entries and many compositions; at two
renderers sharing one module, a module with docstrings is the catalogue.

## Consequences

- Both practice renderers share their motion, so a change to the house feel is one edit.
- Frames cost roughly 40ms more each for the texture pass, about 70 seconds on a full
  render. The grain and vignette are baked into one cached multiply layer per offset
  rather than two passes, because the eye reads them as one material.
- The loop seam test keeps working unchanged, which was the constraint that shaped the
  grain cadence.
- Strokes are supersampled inside their own bounding box rather than frame-wide. Pillow
  draws hard-edged lines, and the smoothing is what makes a stroke read as ink; doing it
  frame-wide would cost more than the rest of the composition.
