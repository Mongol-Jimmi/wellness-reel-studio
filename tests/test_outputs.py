import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREVIEWS = ROOT / "previews"
SLUGS = (
    "soft-punctuation",
    "plain-spoken-pebble",
    "permission-slip",
    "inner-weather",
    "kind-broadcast",
)


def probe(path: Path) -> dict:
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
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


@unittest.skipUnless(all((PREVIEWS / f"{slug}.mp4").exists() for slug in SLUGS), "render previews first")
class OutputTests(unittest.TestCase):
    def test_each_identity_has_exact_video_contract(self) -> None:
        for slug in SLUGS:
            with self.subTest(slug=slug):
                metadata = probe(PREVIEWS / f"{slug}.mp4")
                video = next(stream for stream in metadata["streams"] if stream["codec_type"] == "video")
                audio = next(stream for stream in metadata["streams"] if stream["codec_type"] == "audio")
                self.assertEqual((video["width"], video["height"]), (540, 960))
                self.assertEqual(video["r_frame_rate"], "30/1")
                self.assertEqual(video["nb_read_frames"], "150")
                self.assertEqual(float(metadata["format"]["duration"]), 5.0)
                self.assertEqual(audio["sample_rate"], "48000")

    def test_comparison_has_five_complete_video_segments(self) -> None:
        metadata = probe(PREVIEWS / "all-identities-comparison.mp4")
        video = next(stream for stream in metadata["streams"] if stream["codec_type"] == "video")
        audio = next(stream for stream in metadata["streams"] if stream["codec_type"] == "audio")
        self.assertEqual(video["nb_read_frames"], "750")
        self.assertEqual(float(video["duration"]), 25.0)
        self.assertEqual(float(audio["duration"]), 25.0)


if __name__ == "__main__":
    unittest.main()
