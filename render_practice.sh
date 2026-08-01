#!/usr/bin/env bash
# Render a one-minute practice Reel: frames from the renderer, narration from
# the cached voice cues, muxed to a looping 1080x1920 mp4.
#
#   ./render_practice.sh cyclic-sigh
#   ./render_practice.sh step-back
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PRACTICE="${1:-cyclic-sigh}"

case "$PRACTICE" in
  cyclic-sigh)
    RENDERER="src/practice_pebble.py"
    AUDIO="$ROOT/work/audio/cyclic-sigh-practice.wav"
    CUES=""  # the sigh cues are the voice script's built-in default
    OUTPUT="$ROOT/previews/cyclic-sigh-pebble-60s.mp4"
    ;;
  step-back)
    RENDERER="src/practice_stepback.py"
    AUDIO="$ROOT/work/audio/step-back.wav"
    CUES="$ROOT/reels/practices/step-back-cues.json"
    OUTPUT="$ROOT/previews/step-back-60s.mp4"
    ;;
  *)
    echo "unknown practice: $PRACTICE (known: cyclic-sigh, step-back)" >&2
    exit 2
    ;;
esac

TEMP="$OUTPUT.tmp.mp4"

if [[ ! -f "$AUDIO" ]]; then
  if [[ -f "$HOME/.config/wellness-brand-lab/secrets.env" ]]; then
    set -a
    # Local secret file is outside the repository and never copied into render artifacts.
    . "$HOME/.config/wellness-brand-lab/secrets.env"
    set +a
  fi
  # Generating voice spends paid quota, so it only runs when the cached
  # narration is genuinely missing.
  python3 "$ROOT/src/generate_practice_voice.py" --output "$AUDIO" \
    --cache-dir "${AUDIO%.wav}-cues" ${CUES:+--cues "$CUES"}
fi

python3 "$ROOT/$RENDERER" --scale 2 | ffmpeg -hide_banner -loglevel warning -y \
  -f rawvideo -pixel_format rgb24 -video_size 1080x1920 -framerate 30 -i pipe:0 \
  -i "$AUDIO" -map 0:v:0 -map 1:a:0 -t 60 \
  -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p \
  -c:a aac -b:a 160k -ar 48000 -af "loudnorm=I=-20:LRA=5:TP=-2" \
  -movflags +faststart "$TEMP"

mv "$TEMP" "$OUTPUT"
printf '%s\n' "$OUTPUT"
