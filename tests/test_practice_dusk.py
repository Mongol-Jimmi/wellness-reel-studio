import statistics
import unittest

from PIL import ImageChops

from src.practice_dusk import (
    DURATION_SECONDS,
    FPS,
    PHASES,
    VISIBLE_COPY,
    phase_at,
    phase_label,
    render_frame,
    validate_timeline,
)

BANNED = ("cure", "guarantee", "prevents", "eliminates", "instantly", "proven", "you must", "you should")


class PracticeDuskTests(unittest.TestCase):
    def test_timeline_covers_the_minute_without_gaps(self) -> None:
        validate_timeline(PHASES)
        self.assertEqual(PHASES[-1].end, DURATION_SECONDS)

    def test_last_frame_meets_the_first_so_the_loop_is_seamless(self) -> None:
        first = render_frame(0.0, 1)
        last = render_frame(DURATION_SECONDS - 1 / FPS, 1)
        difference = ImageChops.difference(first, last).convert("L")
        self.assertLess(statistics.mean(list(difference.get_flattened_data())), 1.0)

    def test_renders_at_native_vertical_resolution(self) -> None:
        self.assertEqual(render_frame(12.0, 2).size, (1080, 1920))

    def test_breath_words_stay_to_a_single_word(self) -> None:
        for phase in ("inhale", "sip", "exhale"):
            word = phase_label(next(entry for entry in PHASES if entry.name == phase))
            with self.subTest(phase=phase):
                self.assertTrue(word)
                self.assertNotIn(" ", word)

    def test_visible_copy_makes_no_promises(self) -> None:
        for text in VISIBLE_COPY:
            lowered = text.lower()
            with self.subTest(text=text):
                self.assertNotIn("—", text)
                for phrase in BANNED:
                    self.assertNotIn(phrase, lowered)

    def test_rest_phases_hold_the_cloud_still(self) -> None:
        self.assertEqual(phase_at(23.9).name, "rest")
        self.assertEqual(phase_label(phase_at(23.9)), "")


if __name__ == "__main__":
    unittest.main()
