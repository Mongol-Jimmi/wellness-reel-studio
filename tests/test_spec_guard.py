import copy
import json
import unittest
from pathlib import Path

from src.spec_guard import check_beats_cite_numbers, check_grounding, check_language, check_safety_verbatim, guard

SPEC = json.loads(Path("reels/specs/self-compassion-friend-line.json").read_text(encoding="utf-8"))
EVIDENCE = (
    "A systematic search identified 20 randomised controlled trials. Nineteen papers, involving 1350 participants, "
    "had sufficient data. Findings indicated a significant, medium reduction in self-criticism (Hedges g = 0.51, "
    "95% CI 0.33 to 0.69). A 2021 review pooled 19 randomised controlled trials with 1350 participants."
)
SAFETY = SPEC["safety"][0]


class SpecGuardTests(unittest.TestCase):
    def test_the_shipped_reel_passes_every_guard(self) -> None:
        guard(SPEC, EVIDENCE, SAFETY)

    def test_invented_numbers_are_rejected(self) -> None:
        spec = copy.deepcopy(SPEC)
        spec["beats"][0]["headline"] = "43 TRIALS, 1350 PEOPLE"
        with self.assertRaisesRegex(ValueError, "43"):
            check_grounding(spec, EVIDENCE)

    def test_thousands_separator_still_matches(self) -> None:
        spec = copy.deepcopy(SPEC)
        spec["beats"][0]["headline"] = "19 trials, 1,350 people"
        check_grounding(spec, EVIDENCE)

    def test_promises_are_rejected(self) -> None:
        for phrase in ("This will cure self-criticism.", "A clinically proven method.", "You must try this tonight."):
            spec = copy.deepcopy(SPEC)
            spec["beats"][2]["body"] = phrase
            with self.subTest(phrase=phrase), self.assertRaises(ValueError):
                check_language(spec)

    def test_softened_safety_boundary_is_rejected(self) -> None:
        spec = copy.deepcopy(SPEC)
        spec["safety"][0] = "General wellness only."
        with self.assertRaisesRegex(ValueError, "word for word"):
            check_safety_verbatim(spec, SAFETY)

    def test_uncited_number_is_rejected(self) -> None:
        spec = copy.deepcopy(SPEC)
        spec["beats"][2]["body"] = "Across 19 trials people got less harsh with themselves."
        with self.assertRaisesRegex(ValueError, "source_label"):
            check_beats_cite_numbers(spec)


if __name__ == "__main__":
    unittest.main()
