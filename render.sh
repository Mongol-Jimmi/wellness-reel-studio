#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SLUGS=(
  soft-punctuation
  plain-spoken-pebble
  permission-slip
  inner-weather
  kind-broadcast
)

mkdir -p "$ROOT/work/audio" "$ROOT/work/posters" "$ROOT/previews"

for slug in "${SLUGS[@]}"; do
  audio="$ROOT/work/audio/$slug.wav"
  output="$ROOT/previews/$slug.mp4"
  temp="$output.tmp.mp4"

  python3 "$ROOT/src/generate_audio.py" --identity "$slug" --output "$audio"
  python3 "$ROOT/src/render.py" --identity "$slug" | ffmpeg -hide_banner -loglevel warning -y \
    -f rawvideo -pixel_format rgb24 -video_size 540x960 -framerate 30 -i pipe:0 \
    -i "$audio" -map 0:v:0 -map 1:a:0 -t 5 \
    -c:v libx264 -preset medium -crf 21 -pix_fmt yuv420p \
    -c:a aac -b:a 128k -ar 48000 -af "loudnorm=I=-20:LRA=5:TP=-2" \
    -movflags +faststart "$temp"
  mv "$temp" "$output"

  python3 "$ROOT/src/render.py" --identity "$slug" --poster "$ROOT/work/posters/$slug.png" --time 4.2
done

ffmpeg -hide_banner -loglevel warning -y \
  -i "$ROOT/previews/soft-punctuation.mp4" \
  -i "$ROOT/previews/plain-spoken-pebble.mp4" \
  -i "$ROOT/previews/permission-slip.mp4" \
  -i "$ROOT/previews/inner-weather.mp4" \
  -i "$ROOT/previews/kind-broadcast.mp4" \
  -filter_complex "[0:v]setpts=PTS-STARTPTS[v0];[0:a]atrim=0:5,asetpts=PTS-STARTPTS[a0];[1:v]setpts=PTS-STARTPTS[v1];[1:a]atrim=0:5,asetpts=PTS-STARTPTS[a1];[2:v]setpts=PTS-STARTPTS[v2];[2:a]atrim=0:5,asetpts=PTS-STARTPTS[a2];[3:v]setpts=PTS-STARTPTS[v3];[3:a]atrim=0:5,asetpts=PTS-STARTPTS[a3];[4:v]setpts=PTS-STARTPTS[v4];[4:a]atrim=0:5,asetpts=PTS-STARTPTS[a4];[v0][a0][v1][a1][v2][a2][v3][a3][v4][a4]concat=n=5:v=1:a=1[v][a]" \
  -map "[v]" -map "[a]" -t 25 \
  -c:v libx264 -preset fast -crf 21 -pix_fmt yuv420p \
  -c:a aac -b:a 128k -ar 48000 -movflags +faststart \
  "$ROOT/previews/all-identities-comparison.mp4"

magick montage \
  "$ROOT/work/posters/soft-punctuation.png" \
  "$ROOT/work/posters/plain-spoken-pebble.png" \
  "$ROOT/work/posters/permission-slip.png" \
  "$ROOT/work/posters/inner-weather.png" \
  "$ROOT/work/posters/kind-broadcast.png" \
  -thumbnail 270x480 -tile 3x2 -geometry +8+8 "$ROOT/previews/identity-contact-sheet.png"

printf '%s\n' "$ROOT/previews/all-identities-comparison.mp4"
