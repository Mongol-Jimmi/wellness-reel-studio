#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
AUDIO="$ROOT/work/audio/sleep-hygiene.wav"
OUTPUT="$ROOT/previews/plain-spoken-pebble-sleep-hygiene-1080p.mp4"
TEMP="$OUTPUT.tmp.mp4"

python3 "$ROOT/src/generate_sleep_audio.py"
python3 "$ROOT/src/sleep_reel.py" --scale 2 | ffmpeg -hide_banner -loglevel warning -y \
  -f rawvideo -pixel_format rgb24 -video_size 1080x1920 -framerate 30 -i pipe:0 \
  -i "$AUDIO" -map 0:v:0 -map 1:a:0 -t 35 \
  -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p \
  -c:a aac -b:a 128k -ar 48000 -af "loudnorm=I=-20:LRA=5:TP=-2" \
  -movflags +faststart "$TEMP"

mv "$TEMP" "$OUTPUT"
printf '%s\n' "$OUTPUT"
