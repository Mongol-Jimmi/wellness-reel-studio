import statistics
import unittest

from PIL import ImageChops

from src.practice_pebble import (
    DURATION_SECONDS,
    FPS,
    PHASES,
    VISIBLE_COPY,
    breath,
    phase_at,
    phase_word,
    render_frame,
    validate_timeline,
)

BANNED = ("cure", "guarantee", "prevents", "eliminates", "instantly", "proven", "you must", "you should")


class PracticePebbleTests(unittest.TestCase):
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

    def test_pebble_fills_on_the_way_in_and_empties_on_the_way_out(self) -> None:
        self.assertLess(breath(9.2)[0], breath(13.4)[0])
        self.assertAlmostEqual(breath(15.5)[0], 1.0, places=2)
        self.assertLess(breath(23.4)[0], 0.05)
        self.assertEqual(breath(24.0)[0], 0.0)

    def test_only_the_release_carries_warmth(self) -> None:
        self.assertEqual(breath(11.0)[1], 0.0)
        self.assertGreater(breath(19.5)[1], 0.5)

    def test_one_word_at_a_time_and_silence_at_rest(self) -> None:
        for phase, expected in (("inhale", "in"), ("sip", "more"), ("exhale", "out")):
            word = phase_word(next(entry for entry in PHASES if entry.name == phase))
            with self.subTest(phase=phase):
                self.assertEqual(word, expected)
                self.assertNotIn(" ", word)
        self.assertEqual(phase_word(phase_at(23.9)), "")

    def test_visible_copy_makes_no_promises(self) -> None:
        for text in VISIBLE_COPY:
            lowered = text.lower()
            with self.subTest(text=text):
                self.assertNotIn("—", text)
                for phrase in BANNED:
                    self.assertNotIn(phrase, lowered)


if __name__ == "__main__":
    unittest.main()
