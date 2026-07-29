import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from combined_reel import (
    BEATS,
    CHARCOAL,
    CLOSE_DISCLOSURE_START,
    DURATION_SECONDS,
    FPS,
    OAT,
    SAFETY_BANNER_TOP,
    active_footer_index,
    render_frame,
    validate_timeline,
)
from identities import contrast_ratio

OUTPUT = ROOT / "previews" / "plain-spoken-pebble-combined-check-in-lowres.mp4"


class CombinedReelTests(unittest.TestCase):
    def test_timeline_is_contiguous_and_25_seconds(self) -> None:
        validate_timeline(BEATS)
        self.assertEqual(BEATS[0].start, 0.0)
        self.assertEqual(BEATS[-1].end, 25.0)
        self.assertEqual(DURATION_SECONDS, 25.0)
        self.assertEqual(FPS, 30)

    def test_representative_frames_render_at_every_beat(self) -> None:
        for beat in BEATS:
            with self.subTest(beat=beat.id):
                frame = render_frame(beat.start + 0.01)
                self.assertEqual(frame.size, (540, 960))

    def test_footer_tracks_actual_beat_boundaries(self) -> None:
        self.assertEqual(active_footer_index(18.75), 2)
        self.assertEqual(active_footer_index(19.5), 3)

    def test_safety_disclosure_is_readable_and_starts_with_close(self) -> None:
        self.assertGreaterEqual(contrast_ratio(CHARCOAL, OAT), 4.5)
        self.assertLessEqual(SAFETY_BANNER_TOP, 800)
        self.assertEqual(CLOSE_DISCLOSURE_START, 0.0)

    @unittest.skipUnless(OUTPUT.exists(), "render the combined Reel first")
    def test_rendered_reel_has_exact_delivery_contract(self) -> None:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-count_frames",
                "-show_entries",
                "stream=codec_type,width,height,r_frame_rate,nb_read_frames,sample_rate,duration:format=duration",
                "-of",
                "json",
                str(OUTPUT),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        metadata = json.loads(result.stdout)
        video = next(stream for stream in metadata["streams"] if stream["codec_type"] == "video")
        audio = next(stream for stream in metadata["streams"] if stream["codec_type"] == "audio")
        self.assertEqual((video["width"], video["height"]), (540, 960))
        self.assertEqual(video["r_frame_rate"], "30/1")
        self.assertEqual(video["nb_read_frames"], "750")
        self.assertEqual(audio["sample_rate"], "48000")
        self.assertEqual(float(metadata["format"]["duration"]), 25.0)


if __name__ == "__main__":
    unittest.main()
