import json
import statistics
import unittest
from pathlib import Path

from PIL import ImageChops

from src.generate_practice_voice import load_cues
from src.practice_stepback import (
    DURATION_SECONDS,
    FPS,
    PHASES,
    VISIBLE_COPY,
    distance,
    phase_at,
    phase_word,
    positions,
    render_frame,
    validate_timeline,
)

BANNED = ("cure", "guarantee", "prevents", "eliminates", "instantly", "proven", "you must", "you should")
CUES = Path("reels/practices/step-back-cues.json")


class PracticeStepBackTests(unittest.TestCase):
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

    def test_the_thing_moves_away_and_comes_back_for_the_replay(self) -> None:
        self.assertEqual(distance(4.0), 0.0)
        self.assertGreater(distance(21.9), 0.95)
        self.assertGreater(distance(40.0), 0.95)
        self.assertLess(distance(59.9), 0.05)

    def test_the_pair_stays_centred_however_far_apart(self) -> None:
        for apart in (0.0, 0.5, 1.0):
            you_x, thing_x = positions(apart)
            with self.subTest(apart=apart):
                self.assertAlmostEqual((you_x + thing_x) / 2, 270, delta=6)

    def test_every_spoken_cue_fits_before_the_next_one_starts(self) -> None:
        cues = load_cues(CUES)
        for earlier, later in zip(cues, cues[1:]):
            with self.subTest(cue=earlier.text[:24]):
                self.assertGreaterEqual(later.at - earlier.at, 2.0)
        self.assertLess(cues[-1].at, DURATION_SECONDS)

    def test_pauses_leave_room_to_actually_play_along(self) -> None:
        """The exercise happens in the silences, so the long gaps are load bearing."""
        cues = load_cues(CUES)
        gaps = [later.at - earlier.at for earlier, later in zip(cues, cues[1:])]
        self.assertGreaterEqual(max(gaps), 6.0)

    def test_screen_stays_quiet_and_makes_no_promises(self) -> None:
        self.assertLessEqual(len(VISIBLE_COPY), 8)
        for text in VISIBLE_COPY:
            lowered = text.lower()
            with self.subTest(text=text):
                self.assertNotIn("—", text)
                for phrase in BANNED:
                    self.assertNotIn(phrase, lowered)

    def test_no_word_shows_during_the_thinking_pauses(self) -> None:
        self.assertEqual(phase_word(phase_at(50.0)), "")
        self.assertEqual(phase_word(phase_at(4.0)), "")

    def test_cue_file_is_valid_json_list(self) -> None:
        entries = json.loads(CUES.read_text(encoding="utf-8"))
        self.assertTrue(all({"at", "text"} <= entry.keys() for entry in entries))


if __name__ == "__main__":
    unittest.main()
