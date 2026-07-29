import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from identities import (
    IDENTITIES,
    accessible_foreground,
    contrast_ratio,
    validate_identities,
)
from render import render_frame


class IdentityTests(unittest.TestCase):
    def test_comparison_set_contains_five_unique_five_second_identities(self) -> None:
        validate_identities(IDENTITIES)
        self.assertEqual(len(IDENTITIES), 5)
        self.assertEqual(len({identity.slug for identity in IDENTITIES}), 5)
        self.assertTrue(all(identity.duration_seconds == 5.0 for identity in IDENTITIES))

    def test_selected_adhd_candidates_are_preserved(self) -> None:
        self.assertEqual(
            {identity.source_id for identity in IDENTITIES},
            {"A4", "R4", "R1", "G3", "A6"},
        )

    def test_primary_copy_meets_wcag_aa_contrast(self) -> None:
        for identity in IDENTITIES:
            with self.subTest(identity=identity.slug):
                self.assertGreaterEqual(
                    contrast_ratio(identity.text_color, identity.background_color),
                    4.5,
                )

    def test_accent_copy_gets_an_accessible_foreground(self) -> None:
        for identity in IDENTITIES:
            for accent in identity.accents:
                with self.subTest(identity=identity.slug, accent=accent):
                    foreground = accessible_foreground(accent, identity.text_color)
                    self.assertGreaterEqual(contrast_ratio(foreground, accent), 4.5)

    def test_every_identity_renders_across_its_timeline(self) -> None:
        for number, identity in enumerate(IDENTITIES, start=1):
            for time_seconds in (0.0, 0.91, 1.0, 1.61, 2.0, 3.0, 4.9):
                with self.subTest(identity=identity.slug, time=time_seconds):
                    self.assertEqual(render_frame(identity, number, time_seconds).size, (540, 960))


if __name__ == "__main__":
    unittest.main()
