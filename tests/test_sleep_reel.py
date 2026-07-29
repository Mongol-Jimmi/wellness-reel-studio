import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sleep_reel import (
    BEATS,
    DURATION_SECONDS,
    EXPLAIN_TEXT_START,
    FPS,
    HOOK_SOURCE,
    HOOK_SOURCE_START,
    VISIBLE_COPY,
    render_frame,
    validate_timeline,
)

OUTPUT = ROOT / "previews" / "plain-spoken-pebble-sleep-hygiene-1080p.mp4"


class SleepReelTests(unittest.TestCase):
    def test_timeline_is_contiguous_and_35_seconds(self) -> None:
        validate_timeline(BEATS)
        self.assertEqual(BEATS[0].start, 0.0)
        self.assertEqual(BEATS[-1].end, 35.0)
        self.assertEqual(DURATION_SECONDS, 35.0)
        self.assertEqual(FPS, 30)

    def test_renderer_produces_native_low_and_high_resolution_frames(self) -> None:
        self.assertEqual(render_frame(2.0, scale=1).size, (540, 960))
        self.assertEqual(render_frame(2.0, scale=2).size, (1080, 1920))

    def test_every_beat_renders_at_native_1080p(self) -> None:
        for beat in BEATS:
            with self.subTest(beat=beat.id):
                self.assertEqual(render_frame(beat.start + 0.01, scale=2).size, (1080, 1920))

    def test_visible_copy_is_humanized_and_hook_is_sourced(self) -> None:
        self.assertTrue(HOOK_SOURCE.startswith("https://www.cdc.gov/"))
        self.assertTrue(all("—" not in line for line in VISIBLE_COPY))
        self.assertIn("Nearly 1 in 3", " ".join(VISIBLE_COPY))
        self.assertLessEqual(len(VISIBLE_COPY[1].split()), 14)

    def test_source_and_explanation_keep_readable_dwell(self) -> None:
        hook, explain = BEATS[0], BEATS[1]
        self.assertGreaterEqual(hook.end - HOOK_SOURCE_START, 3.5)
        self.assertGreaterEqual(explain.end - (explain.start + EXPLAIN_TEXT_START), 3.5)

    def test_redundant_general_education_footer_is_absent(self) -> None:
        source = (ROOT / "src" / "sleep_reel.py").read_text(encoding="utf-8")
        self.assertNotIn("GENERAL SLEEP EDUCATION", source)

    def test_high_resolution_output_contract(self) -> None:
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
        self.assertEqual((video["width"], video["height"]), (1080, 1920))
        self.assertEqual(video["r_frame_rate"], "30/1")
        self.assertEqual(video["nb_read_frames"], "1050")
        self.assertEqual(audio["sample_rate"], "48000")
        self.assertEqual(float(metadata["format"]["duration"]), 35.0)

    def test_editor_copy_files_do_not_use_em_dashes(self) -> None:
        paths = (
            ROOT / "edit" / "combined-check-in-script.md",
            ROOT / "edit" / "combined-check-in-captions.srt",
            ROOT / "edit" / "sleep-hygiene-script.md",
            ROOT / "edit" / "sleep-hygiene-captions.srt",
            ROOT / "edit" / "derealization-explainer-outline.md",
        )
        for path in paths:
            with self.subTest(path=path.name):
                self.assertNotIn("—", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
