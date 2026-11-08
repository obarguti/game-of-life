"""The Game of Life simulation itself (no graphics, easy to test)."""
from __future__ import annotations

import numpy as np


class Life:
    """A rectangular board of cells.

    cells : bool array, True = alive
    age   : how many generations each living cell has survived (drives colour)
    ghost : fading "afterglow" left where a cell recently died (drives trails)
    """

    def __init__(self, rows: int, cols: int, wrap: bool = True):
        self.rows, self.cols, self.wrap = rows, cols, wrap
        self.cells = np.zeros((rows, cols), dtype=bool)
        self.age = np.zeros((rows, cols), dtype=np.int32)
        self.ghost = np.zeros((rows, cols), dtype=np.float32)
        self.generation = 0
        self.stable = False  # True when the last step changed nothing

    # -- simulation ---------------------------------------------------------
    def _neighbour_counts(self) -> np.ndarray:
        a = self.cells.astype(np.uint8)
        offsets = [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)]
        if self.wrap:  # toroidal: edges connect to the opposite side
            return sum(np.roll(a, (dr, dc), axis=(0, 1)) for dr, dc in offsets)
        p = np.pad(a, 1)
        r, c = self.rows, self.cols
        return sum(p[1 + dr:1 + dr + r, 1 + dc:1 + dc + c] for dr, dc in offsets)

    def step(self) -> None:
        alive = self.cells
        n = self._neighbour_counts()
        # Birth: dead cell with exactly 3 neighbours. Survival: live cell with 2 or 3.
        new = (n == 3) | (alive & (n == 2))
        died = alive & ~new
        self.age = np.where(new, np.where(alive, self.age + 1, 1), 0)
        self.ghost *= 0.82
        self.ghost[died] = 1.0
        self.stable = bool(np.array_equal(new, alive))
        self.cells = new
        self.generation += 1

    # -- editing ------------------------------------------------------------
    @property
    def population(self) -> int:
        return int(self.cells.sum())

    def set_cell(self, r: int, c: int, alive: bool) -> None:
        if 0 <= r < self.rows and 0 <= c < self.cols:
            self.cells[r, c] = alive
            self.age[r, c] = 1 if alive else 0
            self.ghost[r, c] = 0.0
            self.stable = False

    def stamp(self, coords, r0: int, c0: int) -> None:
        for r, c in coords:
            rr, cc = r0 + r, c0 + c
            if self.wrap:
                rr, cc = rr % self.rows, cc % self.cols
            self.set_cell(rr, cc, True)

    def clear(self) -> None:
        self.cells[:] = False
        self.age[:] = 0
        self.ghost[:] = 0
        self.generation = 0
        self.stable = False

    def randomize(self, density: float = 0.25, rng=None) -> None:
        rng = rng or np.random.default_rng()
        self.clear()
        self.cells = rng.random((self.rows, self.cols)) < density
        self.age = self.cells.astype(np.int32)

    def load(self, coords) -> None:
        """Clear the board and place a pattern in the middle."""
        self.clear()
        h = max(r for r, _ in coords) + 1
        w = max(c for _, c in coords) + 1
        self.stamp(coords, (self.rows - h) // 2, (self.cols - w) // 2)
