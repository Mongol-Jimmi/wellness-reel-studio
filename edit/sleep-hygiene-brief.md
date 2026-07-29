# Sleep Hygiene High-Resolution Draft

- Composition: Plain-Spoken Pebble sleep hygiene explainer
- Output target: native 1080×1920, 30 fps, H.264/AAC, 35 seconds
- Hook: current CDC/NCHS 2024 statistic with an on-screen source label
- Voice: text-led and readable without sound
- Audio: locally synthesized original ambience
- Copy: humanized pass completed; no em dashes; unfamiliar term explained before advice
- Paid media/tools: none
- Research cost: one explicitly approved Elicit search request using existing plan quota
- Publication status: human review required

## Prerequisites

- Python 3.14 with Pillow from `requirements.txt`
- FFmpeg and ffprobe 8.x on `PATH`
- Optional developer checks: Ruff from `requirements-dev.txt`

```bash
python3 -m pip install -r requirements.txt
```

## Reproduction and verification

Render first, then run the required artifact checks:

```bash
cd /home/willem/wellness-brand-lab
./verify_sleep_reel.sh
```

## Draft verification

- Native render, not an upscale: 1080×1920 drawing surface with 2× typography and geometry
- H.264/yuv420p, 30 fps, exactly 1,050 frames and 35.000 seconds
- AAC mono, 48 kHz, −20.0 LUFS integrated, −2.6 dBFS true peak
- File size: 1,355,964 bytes
- Automated black-frame scan: no black intervals detected
- Full project suite: 35 tests passing; Ruff passing
- Rendered MP4 keyframes inspected across all seven beats

This is general sleep education, not treatment for insomnia or another sleep disorder. Persistent sleep difficulty, major daytime impairment, or concerning symptoms should be discussed with a qualified healthcare professional.
