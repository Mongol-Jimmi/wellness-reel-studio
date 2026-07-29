#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
AUDIO="$ROOT/work/audio/combined-check-in.wav"
OUTPUT="$ROOT/previews/plain-spoken-pebble-combined-check-in-lowres.mp4"
TEMP="$OUTPUT.tmp.mp4"

python3 "$ROOT/src/generate_checkin_audio.py"
python3 "$ROOT/src/combined_reel.py" | ffmpeg -hide_banner -loglevel warning -y \
  -f rawvideo -pixel_format rgb24 -video_size 540x960 -framerate 30 -i pipe:0 \
  -i "$AUDIO" -map 0:v:0 -map 1:a:0 -t 25 \
  -c:v libx264 -preset medium -crf 21 -pix_fmt yuv420p \
  -c:a aac -b:a 128k -ar 48000 -af "loudnorm=I=-20:LRA=5:TP=-2" \
  -movflags +faststart "$TEMP"

mv "$TEMP" "$OUTPUT"
printf '%s\n' "$OUTPUT"
