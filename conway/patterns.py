"""Pre-configured scenarios. 'O' = live cell, '.' = dead cell."""
from __future__ import annotations

from dataclasses import dataclass

Coords = frozenset  # frozenset[tuple[int, int]] of (row, col)


def parse(text: str) -> Coords:
    rows = [line.strip() for line in text.strip().splitlines()]
    return frozenset((r, c) for r, line in enumerate(rows) for c, ch in enumerate(line) if ch == "O")


def rotate(coords: Coords) -> Coords:
    """Rotate 90 degrees clockwise (and shift back to the origin)."""
    rotated = [(c, -r) for r, c in coords]
    min_r = min(r for r, _ in rotated)
    return frozenset((r - min_r, c) for r, c in rotated)


def place(*parts: tuple[Coords, int, int]) -> Coords:
    """Combine several patterns, each offset by (row, col)."""
    return frozenset((r + dr, c + dc) for pat, dr, dc in parts for r, c in pat)


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    cells: Coords | None  # None => random soup


GLIDER = parse("""
.O.
..O
OOO
""")

BLINKER = parse("OOO")
TOAD = parse("""
.OOO
OOO.
""")
BEACON = parse("""
OO..
OO..
..OO
..OO
""")
PULSAR = parse("""
..OOO...OOO..
.............
O....O.O....O
O....O.O....O
O....O.O....O
..OOO...OOO..
.............
..OOO...OOO..
O....O.O....O
O....O.O....O
O....O.O....O
.............
..OOO...OOO..
""")

SCENARIOS: list[Scenario] = [
    Scenario("Glider",
             "The smallest spaceship. It crawls diagonally forever, repeating its shape every 4 generations.",
             GLIDER),
    Scenario("Gosper Glider Gun",
             "The first known pattern with unbounded growth: it fires a new glider every 30 generations.",
             parse("""
........................O...........
......................O.O...........
............OO......OO............OO
...........O...O....OO............OO
OO........O.....O...OO..............
OO........O...O.OO....O.O...........
..........O.....O.......O...........
...........O...O....................
............OO......................
""")),
    Scenario("Pulsar",
             "A beautiful period-3 oscillator. Nothing moves away; the whole thing just breathes.",
             PULSAR),
    Scenario("Pentadecathlon",
             "Just ten cells in a row, yet it settles into a period-15 oscillator after a burst of activity.",
             parse("OOOOOOOOOO")),
    Scenario("R-pentomino",
             "Only 5 cells, but it churns for over 1,100 generations and spits out gliders before settling.",
             parse("""
.OO
OO.
.O.
""")),
    Scenario("Acorn",
             "Seven tiny cells that take 5,206 generations to stabilise, ending with 633 cells. Be patient!",
             parse("""
.O.....
...O...
OO..OOO
""")),
    Scenario("Diehard",
             "Seems to vanish... but not before 130 generations of drama. Then it dies completely.",
             parse("""
......O.
OO......
.O...OOO
""")),
    Scenario("Lightweight Spaceship",
             "A faster, bigger cousin of the glider that flies horizontally.",
             parse("""
.O..O
O....
O...O
OOOO.
""")),
    Scenario("Glider Collision",
             "Two gliders on a collision course. Turn the speed down and watch what the crash creates.",
             place((GLIDER, 0, 0), (rotate(rotate(GLIDER)), 9, 16))),
    Scenario("Infinite Growth",
             "A tiny 5x5 seed whose population grows without limit (try with wrap-around OFF with W).",
             parse("""
OOO.O
O....
...OO
.OO.O
O.O.O
""")),
    Scenario("Oscillator Garden",
             "A little zoo: blinker (period 2), toad (2), beacon (2) and pulsar (3), all ticking together.",
             place((BLINKER, 2, 0), (TOAD, 8, 0), (BEACON, 14, 0), (PULSAR, 0, 10))),
    Scenario("Random Soup",
             "A random 25% fill. Life from chaos: watch structures emerge, collide, and settle.",
             None),
]
