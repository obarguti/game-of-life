import unittest

from conway.engine import Life
from conway.patterns import GLIDER, SCENARIOS, parse


def board_with(coords, rows=20, cols=20, wrap=True):
    life = Life(rows, cols, wrap)
    life.stamp(coords, 5, 5)
    return life


class EngineTests(unittest.TestCase):
    def test_blinker_oscillates_with_period_2(self):
        life = board_with(parse("OOO"))
        start = life.cells.copy()
        life.step()
        self.assertFalse((life.cells == start).all())
        life.step()
        self.assertTrue((life.cells == start).all())

    def test_block_is_stable(self):
        life = board_with(parse("OO\nOO"))
        life.step()
        self.assertTrue(life.stable)
        self.assertEqual(life.population, 4)

    def test_glider_moves_diagonally_every_4_generations(self):
        life = board_with(GLIDER)
        before = set(zip(*life.cells.nonzero()))
        for _ in range(4):
            life.step()
        after = set(zip(*life.cells.nonzero()))
        self.assertEqual(after, {(r + 1, c + 1) for r, c in before})

    def test_wrap_vs_walls(self):
        # a glider heading off the board survives with wrap but crashes into the wall without
        for wrap in (True, False):
            life = Life(10, 10, wrap)
            life.stamp(GLIDER, 6, 6)
            for _ in range(60):
                life.step()
            if wrap:
                self.assertEqual(life.population, 5)
            else:
                self.assertNotEqual(life.population, 5)

    def test_gosper_gun_grows(self):
        gun = next(s for s in SCENARIOS if "Gun" in s.name).cells
        life = Life(80, 120, wrap=False)
        life.load(gun)
        counts = []
        for _ in range(120):
            life.step()
            counts.append(life.population)
        self.assertGreater(counts[-1], 36)

    def test_scenarios_load(self):
        life = Life(80, 120)
        for s in SCENARIOS:
            if s.cells:
                life.load(s.cells)
                self.assertEqual(life.population, len(s.cells))


if __name__ == "__main__":
    unittest.main()
