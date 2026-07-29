# Combined Check-In Render Brief

- Composition: Plain-Spoken Pebble combined sensory-and-breath check-in
- Output: 540×960 low-resolution preview, 30 fps, H.264/AAC, 25 seconds
- Voice: none; text-led muted-playback design
- Audio: locally synthesized original ambient bed
- Paid media/tools: none
- Incremental external spend: USD $0
- Elicit: no additional request is needed for rendering; existing candidate evidence remains human-review-only
- Style: warm oat canvas, adult humanist typography, asymmetrical tactile pebbles, slow ease-out motion, no flashing or rapid zooms
- Safety: optional general-wellness language; one comfortable breath only; no instant-reset, cure, diagnosis, or treatment claim

## Reproduction

```bash
cd /home/willem/wellness-brand-lab
python3 -m unittest tests/test_combined_reel.py -v
./render_checkin.sh
```

## Draft verification

- H.264/yuv420p, 540×960, 30 fps, exactly 750 frames and 25.000 seconds
- AAC mono, 48 kHz, −19.8 LUFS integrated, −2.6 dBFS true peak
- Automated black-frame scan: no black intervals detected
- Full project suite: 28 tests passing; Ruff passing
- Representative keyframes inspected for all six beats

Human normal-speed playback and creative approval remain required before any final-resolution render or publication.
