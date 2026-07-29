#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
OUTPUT="$ROOT/previews/plain-spoken-pebble-sleep-hygiene-1080p.mp4"

"$ROOT/render_sleep_reel.sh"
cd "$ROOT"
python3 -m unittest tests/test_sleep_reel.py -v
ffprobe -v error -count_frames \
  -show_entries stream=codec_type,width,height,r_frame_rate,nb_read_frames,sample_rate,duration:format=duration,size \
  -of json "$OUTPUT"

if ffmpeg -hide_banner -i "$OUTPUT" -vf "blackdetect=d=0.10:pix_th=0.01" -an -f null - 2>&1 | grep -q "black_start"; then
  printf '%s\n' "Black interval detected" >&2
  exit 1
fi

printf '%s\n' "Sleep Reel render and verification passed"
