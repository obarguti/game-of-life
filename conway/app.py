"""Pygame front-end for Conway's Game of Life."""
from __future__ import annotations

import collections
import sys
import time

import numpy as np
import pygame

from .engine import Life
from . import __version__
from .patterns import SCENARIOS, rotate

# ---- layout -----------------------------------------------------------------
COLS, ROWS, CELL = 120, 80, 8
GRID_W, GRID_H = COLS * CELL, ROWS * CELL
SIDEBAR_W, BAR_H = 280, 52
WIN_W, WIN_H = GRID_W + SIDEBAR_W, GRID_H + BAR_H

SPEEDS = [0.5, 1, 2, 5, 10, 20, 30, 60, 120, 240]  # generations per second
DEFAULT_SPEED = 4
ZOOMS = [8, 10, 12, 16, 20, 24, 32, 40]  # pixels per cell; 8 = whole board visible

# ---- palette ----------------------------------------------------------------
BG = np.array((11, 15, 26))
PANEL = (19, 25, 43)
PANEL_HI = (32, 42, 70)
TEXT = (222, 230, 247)
MUTED = (125, 138, 168)
ACCENT = (94, 234, 212)
TRAIL = np.array((105, 70, 190))

# Cell colour by age: newborn = bright white, mature = cyan -> violet -> magenta.
_AGE_STOPS = [1, 3, 12, 30, 63]
_AGE_COLOURS = np.array([(255, 255, 255), (120, 255, 220), (70, 195, 255), (140, 120, 255), (225, 100, 200)])
AGE_LUT = np.stack(
    [np.interp(np.arange(64), _AGE_STOPS, _AGE_COLOURS[:, ch]) for ch in range(3)], axis=1
).astype(np.uint8)

HELP_LINES = [
    ("CONWAY'S GAME OF LIFE", None),
    ("", None),
    ("The rules (applied to every cell, every generation):", "h"),
    ("  1. A live cell with 2 or 3 live neighbours survives.", None),
    ("  2. A live cell with fewer than 2 or more than 3 neighbours dies.", None),
    ("  3. A dead cell with exactly 3 live neighbours becomes alive.", None),
    ("Neighbours = the 8 cells touching it. That's all - the rest is emergent!", "m"),
    ("", None),
    ("Getting started:", "h"),
    ("  1. Pick a scenario on the right, or draw your own with the mouse.", None),
    ("  2. Press SPACE to run. Press N to advance one generation at a time.", None),
    ("  3. Change the speed with the slider or the UP / DOWN arrow keys.", None),
    ("", None),
    ("Controls:", "h"),
    ("  Left mouse   draw / stamp         Right mouse   erase", None),
    ("  SPACE        play / pause         N or RIGHT    step (hold to repeat)", None),
    ("  UP / DOWN    speed                1-9, 0        load scenario", None),
    ("  Wheel        zoom in / out        H-scroll      speed (or Shift+wheel)", None),
    ("  Middle-drag  pan (or Shift+drag)  Home / F      reset zoom", None),
    ("  T            draw <-> stamp tool  R             rotate stamp", None),
    ("  X            random soup          C             clear board", None),
    ("  W            wrap edges on/off    G             grid lines", None),
    ("  H            this help            ESC           quit", None),
    ("", None),
    ("Colours: new cells flash white and age to blue and violet.", "m"),
    ("The faint purple glow is where cells recently died.", "m"),
    ("", None),
    ("Press H or click anywhere to start.", "a"),
]


def wrap_text(font: pygame.font.Font, text: str, width: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if font.size(trial)[0] <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + [cur] if cur else lines


class App:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Conway's Game of Life")
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("segoeui,arial,helvetica", 16)
        self.small = pygame.font.SysFont("segoeui,arial,helvetica", 14)
        self.big = pygame.font.SysFont("segoeui,arial,helvetica", 24, bold=True)

        self.life = Life(ROWS, COLS, wrap=True)
        self.rng = np.random.default_rng()
        self.running = False
        self.speed_idx = DEFAULT_SPEED
        self.acc = 0.0
        self.show_grid = True
        self.show_help = True
        self.tool = "draw"  # or "stamp"
        self.selected = 0
        self.stamp_cells = SCENARIOS[0].cells
        self.paint_value: bool | None = None
        self.last_cell: tuple[int, int] | None = None
        self.dragging_slider = False
        self.history: collections.deque[int] = collections.deque(maxlen=240)
        self.hold_start = 0.0
        self.hold_last = 0.0

        self.board_surf = pygame.Surface((COLS, ROWS))
        # view: cs = pixels per cell, (ox, oy) = pixel offset of the viewport into the board
        self.cs = ZOOMS[0]
        self.ox = self.oy = 0
        self.panning = False
        self.wheel_x = self.wheel_y = 0.0
        self._grid_key = None
        self._grid_surf = pygame.Surface((GRID_W, GRID_H), pygame.SRCALPHA)

        # clickable rectangles
        self.btn_play = pygame.Rect(12, GRID_H + 8, 104, 36)
        self.btn_step = pygame.Rect(124, GRID_H + 8, 80, 36)
        self.btn_clear = pygame.Rect(212, GRID_H + 8, 80, 36)
        self.btn_random = pygame.Rect(300, GRID_H + 8, 90, 36)
        self.slider = pygame.Rect(470, GRID_H + 22, 250, 8)
        self.btn_help = pygame.Rect(WIN_W - 48, GRID_H + 8, 36, 36)
        self.item_h = 24
        self.list_top = 196
        self.items = [
            pygame.Rect(GRID_W + 10, self.list_top + i * self.item_h, SIDEBAR_W - 20, self.item_h)
            for i in range(len(SCENARIOS))
        ]

        self.load_scenario(0)

    # ---- actions ------------------------------------------------------------
    def load_scenario(self, idx: int) -> None:
        self.selected = idx
        sc = SCENARIOS[idx]
        if sc.cells is None:
            self.life.randomize(0.25, self.rng)
            self.stamp_cells = None
        else:
            self.life.load(sc.cells)
            self.stamp_cells = sc.cells
        self.history.clear()
        self.running = False
        self.acc = 0.0

    def clear(self) -> None:
        self.life.clear()
        self.history.clear()
        self.running = False

    def step(self) -> None:
        self.life.step()
        self.history.append(self.life.population)

    def speed(self) -> float:
        return SPEEDS[self.speed_idx]

    def change_speed(self, delta: int) -> None:
        self.speed_idx = max(0, min(len(SPEEDS) - 1, self.speed_idx + delta))

    def toggle_tool(self) -> None:
        if self.stamp_cells is None:  # random soup has nothing to stamp
            self.tool = "draw"
        else:
            self.tool = "stamp" if self.tool == "draw" else "draw"

    def set_slider(self, x: int) -> None:
        frac = (x - self.slider.left) / self.slider.width
        self.speed_idx = max(0, min(len(SPEEDS) - 1, round(frac * (len(SPEEDS) - 1))))

    # ---- view (zoom / pan) --------------------------------------------------
    def clamp_view(self) -> None:
        self.ox = max(0, min(COLS * self.cs - GRID_W, self.ox))
        self.oy = max(0, min(ROWS * self.cs - GRID_H, self.oy))

    def zoom_by(self, steps: int, anchor: tuple[int, int]) -> None:
        """Zoom in (+) or out (-), keeping the board point under `anchor` fixed."""
        idx = max(0, min(len(ZOOMS) - 1, ZOOMS.index(self.cs) + steps))
        new = ZOOMS[idx]
        if new == self.cs:
            return
        ax, ay = anchor if self.cell_at(anchor) else (GRID_W // 2, GRID_H // 2)
        wx, wy = (ax + self.ox) / self.cs, (ay + self.oy) / self.cs  # in cell units
        self.cs = new
        self.ox, self.oy = round(wx * new - ax), round(wy * new - ay)
        self.clamp_view()

    def reset_view(self) -> None:
        self.cs, self.ox, self.oy = ZOOMS[0], 0, 0

    def cell_to_screen(self, r: int, c: int) -> tuple[int, int]:
        return c * self.cs - self.ox, r * self.cs - self.oy

    # ---- input --------------------------------------------------------------
    def cell_at(self, pos) -> tuple[int, int] | None:
        x, y = pos
        if 0 <= x < GRID_W and 0 <= y < GRID_H:
            return (y + self.oy) // self.cs, (x + self.ox) // self.cs
        return None

    def stamp_origin(self, cell: tuple[int, int]) -> tuple[int, int]:
        h = max(r for r, _ in self.stamp_cells) + 1
        w = max(c for _, c in self.stamp_cells) + 1
        return cell[0] - h // 2, cell[1] - w // 2

    def paint_line(self, a: tuple[int, int], b: tuple[int, int], value: bool) -> None:
        n = max(abs(a[0] - b[0]), abs(a[1] - b[1]), 1)
        for i in range(n + 1):
            r = round(a[0] + (b[0] - a[0]) * i / n)
            c = round(a[1] + (b[1] - a[1]) * i / n)
            self.life.set_cell(r, c, value)

    def handle_event(self, e: pygame.event.Event) -> bool:
        if e.type == pygame.QUIT:
            return False
        if e.type == pygame.KEYDOWN:
            k = e.key
            if self.show_help and k not in (pygame.K_ESCAPE,):
                self.show_help = False
                return True
            if k == pygame.K_ESCAPE:
                return False
            elif k == pygame.K_SPACE:
                self.running = not self.running
            elif k in (pygame.K_n, pygame.K_RIGHT):
                self.running = False
                self.step()
                self.hold_start = self.hold_last = time.monotonic()
            elif k in (pygame.K_UP, pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                self.change_speed(+1)
            elif k in (pygame.K_DOWN, pygame.K_MINUS, pygame.K_KP_MINUS):
                self.change_speed(-1)
            elif k == pygame.K_c:
                self.clear()
            elif k == pygame.K_x:
                self.load_scenario(len(SCENARIOS) - 1)
            elif k == pygame.K_g:
                self.show_grid = not self.show_grid
            elif k == pygame.K_w:
                self.life.wrap = not self.life.wrap
            elif k == pygame.K_h:
                self.show_help = True
            elif k in (pygame.K_HOME, pygame.K_f):
                self.reset_view()
            elif k == pygame.K_t:
                self.toggle_tool()
            elif k == pygame.K_r and self.stamp_cells is not None:
                self.stamp_cells = rotate(self.stamp_cells)
            elif pygame.K_0 <= k <= pygame.K_9:
                idx = 9 if k == pygame.K_0 else k - pygame.K_1
                if idx < len(SCENARIOS):
                    self.load_scenario(idx)
        elif e.type == pygame.MOUSEWHEEL:
            if self.show_help:
                return True
            # Vertical wheel = zoom. Horizontal wheel (or Shift + wheel) = speed.
            shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
            dx, dy = e.precise_x, e.precise_y
            if shift and not dx:
                dx, dy = dy, 0.0
            self.wheel_x += dx
            self.wheel_y += dy
            while abs(self.wheel_y) >= 1:
                step = 1 if self.wheel_y > 0 else -1
                self.zoom_by(step, pygame.mouse.get_pos())
                self.wheel_y -= step
            while abs(self.wheel_x) >= 1:
                step = 1 if self.wheel_x > 0 else -1
                self.change_speed(step)
                self.wheel_x -= step
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button in (1, 2, 3):
            self.on_mouse_down(e)
        elif e.type == pygame.MOUSEBUTTONUP:
            self.paint_value = None
            self.last_cell = None
            self.dragging_slider = False
            self.panning = False
        elif e.type == pygame.MOUSEMOTION:
            if self.panning:
                self.ox -= e.rel[0]
                self.oy -= e.rel[1]
                self.clamp_view()
            elif self.dragging_slider:
                self.set_slider(e.pos[0])
            elif self.paint_value is not None:
                cell = self.cell_at(e.pos)
                if cell:
                    self.paint_line(self.last_cell or cell, cell, self.paint_value)
                    self.last_cell = cell
        return True

    def on_mouse_down(self, e: pygame.event.Event) -> None:
        if self.show_help:
            self.show_help = False
            return
        pos = e.pos
        shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
        if e.button == 2 or (e.button == 1 and shift and self.cell_at(pos)):
            self.panning = True
            return
        if e.button == 1:
            if self.btn_play.collidepoint(pos):
                self.running = not self.running
            elif self.btn_step.collidepoint(pos):
                self.running = False
                self.step()
            elif self.btn_clear.collidepoint(pos):
                self.clear()
            elif self.btn_random.collidepoint(pos):
                self.load_scenario(len(SCENARIOS) - 1)
            elif self.btn_help.collidepoint(pos):
                self.show_help = True
            elif self.slider.inflate(24, 28).collidepoint(pos):
                self.dragging_slider = True
                self.set_slider(pos[0])
            else:
                for i, rect in enumerate(self.items):
                    if rect.collidepoint(pos):
                        self.load_scenario(i)
                        return
        cell = self.cell_at(pos)
        if not cell:
            return
        if e.button == 3:
            self.paint_value, self.last_cell = False, cell
            self.life.set_cell(*cell, False)
        elif self.tool == "stamp" and self.stamp_cells is not None:
            self.life.stamp(self.stamp_cells, *self.stamp_origin(cell))
        else:
            self.paint_value = not bool(self.life.cells[cell])
            self.last_cell = cell
            self.life.set_cell(*cell, self.paint_value)

    # ---- drawing ------------------------------------------------------------
    def grid_overlay(self) -> pygame.Surface:
        key = (self.cs, self.ox % self.cs, self.oy % self.cs)
        if key != self._grid_key:
            self._grid_key = key
            self._grid_surf.fill((0, 0, 0, 0))
            colour = (255, 255, 255, 9 if self.cs <= 8 else 22)
            for x in range(-(self.ox % self.cs), GRID_W, self.cs):
                pygame.draw.line(self._grid_surf, colour, (x, 0), (x, GRID_H))
            for y in range(-(self.oy % self.cs), GRID_H, self.cs):
                pygame.draw.line(self._grid_surf, colour, (0, y), (GRID_W, y))
        return self._grid_surf

    def render_board(self) -> None:
        life, cs = self.life, self.cs
        glow = (life.ghost[..., None] * 0.55).astype(np.float32)
        rgb = BG + (TRAIL - BG) * glow
        alive = life.cells
        rgb[alive] = AGE_LUT[np.minimum(life.age[alive], 63)]
        pygame.surfarray.blit_array(self.board_surf, np.ascontiguousarray(rgb.astype(np.uint8).swapaxes(0, 1)))

        # Only scale the part of the board that is visible.
        c0, r0 = self.ox // cs, self.oy // cs
        c1 = min(COLS, -(-(self.ox + GRID_W) // cs))
        r1 = min(ROWS, -(-(self.oy + GRID_H) // cs))
        part = self.board_surf.subsurface((c0, r0, c1 - c0, r1 - r0))
        self.screen.set_clip((0, 0, GRID_W, GRID_H))
        self.screen.blit(pygame.transform.scale(part, ((c1 - c0) * cs, (r1 - r0) * cs)), self.cell_to_screen(r0, c0))
        if self.show_grid:
            self.screen.blit(self.grid_overlay(), (0, 0))

        cell = self.cell_at(pygame.mouse.get_pos())
        if cell and not self.show_help and not self.panning:
            if self.tool == "stamp" and self.stamp_cells is not None:
                sr, sc = self.stamp_origin(cell)
                ghost = pygame.Surface((cs, cs), pygame.SRCALPHA)
                ghost.fill((*ACCENT, 120))
                for r, c in self.stamp_cells:
                    self.screen.blit(ghost, self.cell_to_screen((sr + r) % ROWS, (sc + c) % COLS))
            else:
                x, y = self.cell_to_screen(*cell)
                pygame.draw.rect(self.screen, ACCENT, (x, y, cs, cs), 1)
        self.screen.set_clip(None)

        if cs > ZOOMS[0]:
            label = f"Zoom {cs / ZOOMS[0]:.2g}x   |   middle-drag or Shift+drag to pan   |   Home to reset"
            surf = self.small.render(label, True, TEXT)
            pill = pygame.Rect(10, GRID_H - 34, surf.get_width() + 20, 24)
            pygame.draw.rect(self.screen, PANEL, pill, border_radius=12)
            self.screen.blit(surf, (pill.x + 10, pill.y + 3))

    def text(self, s, pos, font=None, colour=TEXT, centre=False) -> None:
        surf = (font or self.font).render(s, True, colour)
        rect = surf.get_rect(center=pos) if centre else surf.get_rect(topleft=pos)
        self.screen.blit(surf, rect)

    def button(self, rect, label, active=False) -> None:
        hover = rect.collidepoint(pygame.mouse.get_pos())
        col = ACCENT if active else (PANEL_HI if hover else (28, 36, 60))
        pygame.draw.rect(self.screen, col, rect, border_radius=8)
        self.text(label, rect.center, colour=(10, 20, 30) if active else TEXT, centre=True)

    def render_sidebar(self) -> None:
        x0 = GRID_W
        pygame.draw.rect(self.screen, PANEL, (x0, 0, SIDEBAR_W, GRID_H))
        self.text("Game of Life", (x0 + 16, 12), self.big, ACCENT)

        life = self.life
        if life.population == 0 and life.generation > 0:
            status, scol = "Extinct", (255, 120, 120)
        elif life.stable:
            status, scol = "Stable", (255, 200, 110)
        else:
            status, scol = ("Running" if self.running else "Paused"), (140, 230, 150)
        rows = [
            ("Generation", f"{life.generation:,}"),
            ("Population", f"{life.population:,}"),
            ("Speed", f"{self.speed():g} gen/s"),
            ("Edges", "wrap (W)" if life.wrap else "walls (W)"),
            ("Tool", "stamp (T)" if self.tool == "stamp" else "draw (T)"),
        ]
        y = 50
        for label, value in rows:
            self.text(label, (x0 + 16, y), self.small, MUTED)
            self.text(value, (x0 + SIDEBAR_W - 16 - self.small.size(value)[0], y), self.small)
            y += 21
        self.text(status, (x0 + SIDEBAR_W - 16 - self.font.size(status)[0], 12 + 6), self.font, scol)

        self.text("SCENARIOS  (keys 1-9, 0)", (x0 + 16, self.list_top - 24), self.small, MUTED)
        mouse = pygame.mouse.get_pos()
        for i, (sc, rect) in enumerate(zip(SCENARIOS, self.items)):
            if i == self.selected:
                pygame.draw.rect(self.screen, PANEL_HI, rect, border_radius=6)
                pygame.draw.rect(self.screen, ACCENT, (rect.x, rect.y + 3, 3, rect.h - 6), border_radius=2)
            elif rect.collidepoint(mouse):
                pygame.draw.rect(self.screen, (26, 34, 58), rect, border_radius=6)
            key = str((i + 1) % 10) if i < 10 else ("X" if i == len(SCENARIOS) - 1 else "")
            self.text(key, (rect.x + 10, rect.y + 3), self.small, MUTED)
            self.text(sc.name, (rect.x + 30, rect.y + 2), self.small, TEXT if i == self.selected else (190, 200, 225))

        desc_y = self.list_top + len(SCENARIOS) * self.item_h + 8
        for line in wrap_text(self.small, SCENARIOS[self.selected].description, SIDEBAR_W - 32)[:5]:
            self.text(line, (x0 + 16, desc_y), self.small, MUTED)
            desc_y += 17

        self.render_sparkline(pygame.Rect(x0 + 16, GRID_H - 52, SIDEBAR_W - 32, 38))

    def render_sparkline(self, rect: pygame.Rect) -> None:
        pygame.draw.rect(self.screen, (14, 19, 34), rect, border_radius=6)
        self.text("population", (rect.x + 6, rect.y + 2), pygame.font.Font(None, 15), MUTED)
        if len(self.history) < 2:
            return
        hi = max(max(self.history), 1)
        n = len(self.history)
        pts = [
            (rect.x + 4 + i * (rect.w - 8) / (self.history.maxlen - 1),
             rect.bottom - 4 - v / hi * (rect.h - 14))
            for i, v in enumerate(self.history)
        ]
        # right-align so the newest sample sits at the right edge
        shift = (self.history.maxlen - n) * (rect.w - 8) / (self.history.maxlen - 1)
        pygame.draw.lines(self.screen, ACCENT, False, [(x + shift, y) for x, y in pts], 2)

    def render_bar(self) -> None:
        pygame.draw.rect(self.screen, PANEL, (0, GRID_H, WIN_W, BAR_H))
        pygame.draw.line(self.screen, (40, 50, 80), (0, GRID_H), (WIN_W, GRID_H))
        self.button(self.btn_play, "Pause (Space)" if self.running else "Play (Space)", self.running)
        self.button(self.btn_step, "Step (N)")
        self.button(self.btn_clear, "Clear (C)")
        self.button(self.btn_random, "Random (X)")
        self.button(self.btn_help, "?")

        self.text("Speed", (self.slider.left - 56, self.slider.centery - 10), self.small, MUTED)
        pygame.draw.rect(self.screen, (40, 50, 80), self.slider, border_radius=4)
        frac = self.speed_idx / (len(SPEEDS) - 1)
        filled = self.slider.copy()
        filled.width = int(self.slider.width * frac)
        pygame.draw.rect(self.screen, ACCENT, filled, border_radius=4)
        pygame.draw.circle(self.screen, TEXT, (self.slider.left + int(self.slider.width * frac), self.slider.centery), 9)
        self.text(f"{self.speed():g} gen/s", (self.slider.right + 20, self.slider.centery - 10), self.small)

    def render_help(self) -> None:
        veil = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        veil.fill((6, 9, 18, 225))
        self.screen.blit(veil, (0, 0))
        mono = pygame.font.SysFont("consolas,couriernew,monospace", 16)
        y = 40
        for line, style in HELP_LINES:
            if style is None and line.startswith("CONWAY"):
                self.text(line, (WIN_W // 2, y + 12), self.big, ACCENT, centre=True)
                y += 36
                continue
            colour = {"h": ACCENT, "m": MUTED, "a": (255, 214, 120)}.get(style, TEXT)
            self.text(line, (110, y), mono, colour)
            y += 22
        label = f"v{__version__}"
        self.text(label, (WIN_W - 16 - self.small.size(label)[0], 16), self.small, MUTED)

    def render(self) -> None:
        self.screen.fill(BG)
        self.render_board()
        self.render_sidebar()
        self.render_bar()
        if self.show_help:
            self.render_help()
        pygame.display.flip()

    # ---- main loop ----------------------------------------------------------
    def run(self) -> None:
        alive = True
        while alive:
            dt = self.clock.tick(60) / 1000.0
            for e in pygame.event.get():
                alive = self.handle_event(e) and alive

            if self.running:
                self.acc += dt * self.speed()
                steps = min(int(self.acc), 8)
                self.acc = 0.0 if steps == 8 else self.acc - steps
                for _ in range(steps):
                    self.step()
            else:
                keys = pygame.key.get_pressed()
                now = time.monotonic()
                if (keys[pygame.K_n] or keys[pygame.K_RIGHT]) and not self.show_help \
                        and now - self.hold_start > 0.35 and now - self.hold_last > 0.05:
                    self.step()
                    self.hold_last = now

            self.render()
        pygame.quit()


def main() -> None:
    App().run()
    sys.exit(0)


if __name__ == "__main__":
    main()
