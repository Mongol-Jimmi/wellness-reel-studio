#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
AUDIO="$ROOT/work/audio/cyclic-sigh-practice.wav"
CUES="$ROOT/work/audio/cyclic-sigh-cues"
OUTPUT="$ROOT/previews/cyclic-sigh-pebble-60s.mp4"
TEMP="$OUTPUT.tmp.mp4"

if [[ ! -f "$AUDIO" ]]; then
  if [[ -f "$HOME/.config/wellness-brand-lab/secrets.env" ]]; then
    set -a
    # Local secret file is outside the repository and never copied into render artifacts.
    . "$HOME/.config/wellness-brand-lab/secrets.env"
    set +a
  fi
  python3 "$ROOT/src/generate_practice_voice.py" --output "$AUDIO" --cache-dir "$CUES"
fi

python3 "$ROOT/src/practice_pebble.py" --scale 2 | ffmpeg -hide_banner -loglevel warning -y \
  -f rawvideo -pixel_format rgb24 -video_size 1080x1920 -framerate 30 -i pipe:0 \
  -i "$AUDIO" -map 0:v:0 -map 1:a:0 -t 60 \
  -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p \
  -c:a aac -b:a 160k -ar 48000 -af "loudnorm=I=-20:LRA=5:TP=-2" \
  -movflags +faststart "$TEMP"

mv "$TEMP" "$OUTPUT"
printf '%s\n' "$OUTPUT"
