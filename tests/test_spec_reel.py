import copy
import unittest

from src.spec_reel import render_frame, validate_spec

VALID_SPEC = {
    "version": 1,
    "issue_number": 12,
    "slug": "restart-plan",
    "title": "Plan the Restart",
    "render_version": "1.0.0",
    "status": "ready_to_render",
    "publication_status": "human_review_required",
    "format": {"width": 1080, "height": 1920, "fps": 30, "duration_seconds": 30},
    "sources": ["https://doi.org/10.1000/example"],
    "safety": ["General wellness only", "No guaranteed outcome"],
    "beats": [
        {"id": "hook", "start": 0, "end": 6, "headline": "Missed a day?", "body": "The routine is not erased."},
        {"id": "explain", "start": 6, "end": 12, "headline": "Plan the return", "body": "A pre-decided step may reduce decisions later."},
        {"id": "step-one", "start": 12, "end": 18, "headline": "Make it small", "body": "Pick a version that takes two minutes."},
        {"id": "step-two", "start": 18, "end": 24, "headline": "Leave a cue", "body": "Keep what you need where you will restart."},
        {"id": "close", "start": 24, "end": 30, "headline": "Try one return step", "body": "Save if useful."},
    ],
}


class SpecValidationTests(unittest.TestCase):
    def test_valid_spec_renders_at_native_resolution(self) -> None:
        validate_spec(VALID_SPEC)
        self.assertEqual(render_frame(VALID_SPEC, 1.0, scale=2).size, (1080, 1920))

    def test_rejects_unreviewed_status_and_em_dash(self) -> None:
        draft = copy.deepcopy(VALID_SPEC)
        draft["status"] = "draft"
        with self.assertRaisesRegex(ValueError, "ready_to_render"):
            validate_spec(draft)

        unsafe_copy = copy.deepcopy(VALID_SPEC)
        unsafe_copy["beats"][0]["body"] = "A claim — without review."
        with self.assertRaisesRegex(ValueError, "em dash"):
            validate_spec(unsafe_copy)

    def test_final_beat_body_leaves_room_for_the_safety_line(self) -> None:
        crowded = copy.deepcopy(VALID_SPEC)
        crowded["beats"][-1]["body"] = "word " * 30
        with self.assertRaisesRegex(ValueError, "body"):
            validate_spec(crowded)

    def test_source_label_is_optional_and_length_checked(self) -> None:
        labelled = copy.deepcopy(VALID_SPEC)
        labelled["beats"][0]["source_label"] = "Meta-analysis, 2021"
        validate_spec(labelled)
        self.assertEqual(render_frame(labelled, 1.0, scale=1).size, (540, 960))

        too_long = copy.deepcopy(VALID_SPEC)
        too_long["beats"][0]["source_label"] = "x" * 41
        with self.assertRaisesRegex(ValueError, "source_label"):
            validate_spec(too_long)

    def test_rejects_timeline_gaps_and_non_https_sources(self) -> None:
        gap = copy.deepcopy(VALID_SPEC)
        gap["beats"][1]["start"] = 7
        with self.assertRaisesRegex(ValueError, "contiguous"):
            validate_spec(gap)

        source = copy.deepcopy(VALID_SPEC)
        source["sources"] = ["http://example.test/paper"]
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            validate_spec(source)


if __name__ == "__main__":
    unittest.main()
