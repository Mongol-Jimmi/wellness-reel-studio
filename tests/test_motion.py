import unittest

from PIL import Image

from src.motion import (
    GRAIN_STEP,
    apply_texture,
    back_out,
    bezier,
    expo_out,
    grain_index,
    hand_stroke,
    linear,
    power1_in_out,
    power2_in_out,
    power2_out,
    smooth,
    stutter,
)
from src.sleep_reel import Canvas

EASINGS = (linear, smooth, expo_out, power1_in_out, power2_in_out, power2_out, back_out)


class EasingTests(unittest.TestCase):
    def test_every_curve_starts_at_zero_and_ends_at_one(self) -> None:
        for ease in EASINGS:
            with self.subTest(ease=ease.__name__):
                self.assertAlmostEqual(ease(0.0), 0.0, places=6)
                self.assertAlmostEqual(ease(1.0), 1.0, places=6)

    def test_every_curve_clamps_outside_its_window(self) -> None:
        for ease in EASINGS:
            with self.subTest(ease=ease.__name__):
                self.assertAlmostEqual(ease(-3.0), 0.0, places=6)
                self.assertAlmostEqual(ease(9.0), 1.0, places=6)

    def test_every_curve_moves_forwards_the_whole_way(self) -> None:
        """back_out overshoots, so it is checked against its own peak, not 1."""
        for ease in EASINGS:
            samples = [ease(step / 40) for step in range(41)]
            with self.subTest(ease=ease.__name__):
                self.assertTrue(all(b >= a - 1e-9 for a, b in zip(samples, samples[1:])) or ease is back_out)
                self.assertGreater(samples[20], 0.0)

    def test_back_out_overshoots_then_settles(self) -> None:
        self.assertGreater(max(back_out(step / 40) for step in range(41)), 1.0)
        self.assertAlmostEqual(back_out(1.0), 1.0, places=6)

    def test_the_slow_curve_lingers_at_both_ends(self) -> None:
        """A breath spends its time at the turn, which is what power2 buys."""
        self.assertLess(power2_in_out(0.15), smooth(0.15))
        self.assertGreater(power2_in_out(0.85), smooth(0.85))

    def test_expo_out_arrives_early(self) -> None:
        self.assertGreater(expo_out(0.3), 0.85)


class StutterTests(unittest.TestCase):
    def test_holds_a_value_for_the_whole_step(self) -> None:
        self.assertEqual(stutter(1.0, 12), stutter(1.08, 12))
        self.assertNotEqual(stutter(1.0, 12), stutter(1.09, 12))

    def test_rejects_a_meaningless_rate(self) -> None:
        with self.assertRaises(ValueError):
            stutter(1.0, 0)


class GrainTests(unittest.TestCase):
    def test_the_last_frame_of_the_minute_lands_back_on_the_opening_offset(self) -> None:
        self.assertEqual(grain_index(0.0, 60.0), grain_index(60.0 - 1 / 30, 60.0))

    def test_every_offset_is_held_for_one_step_once_the_loop_is_closed(self) -> None:
        """The opening and closing runs are half steps that join into one at the wrap.

        That split is exactly what lets the last frame land back on the first
        offset, so it is the design rather than a rounding accident.
        """
        held = [grain_index(frame / 30, 60.0) for frame in range(60 * 30)]
        runs = [[held[0], 0]]
        for index in held:
            runs[-1][1] += 1 if index == runs[-1][0] else 0
            if index != runs[-1][0]:
                runs.append([index, 1])
        frames_per_step = round(GRAIN_STEP * 30)
        self.assertEqual(runs[0][1] + runs[-1][1], frames_per_step)
        self.assertEqual({run[1] for run in runs[1:-1]}, {frames_per_step})
        self.assertEqual([run[0] for run in runs[:6]], [0, 1, 2, 3, 4, 0])

    def test_refuses_a_runtime_the_cadence_cannot_close(self) -> None:
        with self.assertRaises(ValueError):
            grain_index(0.0, 35.0)

    def test_texture_darkens_the_frame_without_tinting_it(self) -> None:
        plain = Image.new("RGB", (540, 960), "#EFE8DC")
        textured = plain.copy()
        apply_texture(textured, 0.0, 60.0, 1)
        self.assertLess(sum(textured.getpixel((270, 480))), sum(plain.getpixel((270, 480))))
        # Corners take the vignette, the middle only the grain.
        self.assertLess(sum(textured.getpixel((6, 6))), sum(textured.getpixel((270, 480))))

    def test_texture_is_identical_on_a_second_render(self) -> None:
        first, second = Image.new("RGB", (540, 960), "#EFE8DC"), Image.new("RGB", (540, 960), "#EFE8DC")
        apply_texture(first, 12.4, 60.0, 1)
        apply_texture(second, 12.4, 60.0, 1)
        self.assertEqual(first.tobytes(), second.tobytes())


class HandStrokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.path = bezier((120.0, 400.0), (270.0, 460.0), (420.0, 400.0))

    def _ink(self, progress: float) -> int:
        canvas = Canvas(1)
        blank = canvas.image.tobytes()
        hand_stroke(canvas, self.path, progress, "#F4C96B")
        return sum(a != b for a, b in zip(blank, canvas.image.tobytes()))

    def test_a_longer_reveal_puts_down_more_ink(self) -> None:
        self.assertGreater(self._ink(1.0), self._ink(0.4))
        self.assertGreater(self._ink(0.4), 0)

    def test_nothing_is_drawn_before_the_reveal_starts_or_while_invisible(self) -> None:
        self.assertEqual(self._ink(0.0), 0)
        canvas = Canvas(1)
        blank = canvas.image.tobytes()
        hand_stroke(canvas, self.path, 1.0, "#F4C96B", alpha=0.0)
        self.assertEqual(canvas.image.tobytes(), blank)

    def test_the_wobble_repeats_exactly_between_renders(self) -> None:
        first, second = Canvas(1), Canvas(1)
        hand_stroke(first, self.path, 0.8, "#F4C96B", seed=3)
        hand_stroke(second, self.path, 0.8, "#F4C96B", seed=3)
        self.assertEqual(first.image.tobytes(), second.image.tobytes())

    def test_a_different_seed_gives_a_different_line(self) -> None:
        first, second = Canvas(1), Canvas(1)
        hand_stroke(first, self.path, 0.8, "#F4C96B", seed=3)
        hand_stroke(second, self.path, 0.8, "#F4C96B", seed=11)
        self.assertNotEqual(first.image.tobytes(), second.image.tobytes())

    def test_the_line_wanders_off_the_mathematical_curve(self) -> None:
        """Without this the stroke is a plotted bezier, which is the thing it must not look like."""
        straight, wobbled = Canvas(1), Canvas(1)
        hand_stroke(straight, self.path, 1.0, "#F4C96B", wobble=0.0)
        hand_stroke(wobbled, self.path, 1.0, "#F4C96B", wobble=4.0)
        self.assertNotEqual(straight.image.tobytes(), wobbled.image.tobytes())


if __name__ == "__main__":
    unittest.main()
