import json
import tempfile
import unittest
from pathlib import Path

from scripts.assemble_site import assemble, source_for


class SiteTests(unittest.TestCase):
    def test_static_manifest_has_review_traceability(self) -> None:
        reels = json.loads(Path("site/reels.json").read_text(encoding="utf-8"))
        for reel in reels:
            with self.subTest(slug=reel.get("slug")):
                self.assertTrue(reel["renderVersion"])
                self.assertTrue(reel["sourceIssue"])
                self.assertIn("Reel Spec", reel["links"])
                self.assertIn("Evidence", reel["links"])

    def test_site_assembly_copies_every_manifest_asset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "site"
            assemble(output)
            reels = json.loads((output / "reels.json").read_text(encoding="utf-8"))
            for reel in reels:
                self.assertTrue((output / reel["video"]).is_file())
                self.assertTrue((output / reel["poster"]).is_file())
                self.assertTrue((output / reel["links"]["Captions"]).is_file())

    def test_site_assembly_rejects_path_traversal(self) -> None:
        with self.assertRaises(ValueError):
            source_for("media/../secret.env")
        with self.assertRaises(ValueError):
            source_for("https://example.test/video.mp4")


if __name__ == "__main__":
    unittest.main()
