# Conway's Game of Life

A small, good-looking Game of Life built with Python, pygame and numpy.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m conway
```

Run the tests with `python -m unittest discover -s tests`.

## The rules

Life is a grid of cells, each alive or dead. Every generation, all cells update at once:

1. A live cell with **2 or 3** live neighbours survives.
2. A live cell with fewer than 2 (loneliness) or more than 3 (overcrowding) neighbours dies.
3. A dead cell with **exactly 3** live neighbours becomes alive.

Neighbours are the 8 surrounding cells. From these rules come still lifes, oscillators,
"spaceships" (like the glider) and even guns that fire endless gliders.

## Suggested workflow

1. Start on the **Glider** scenario, paused. Press **N** a few times and watch it walk diagonally.
2. Try other scenarios (click them or press 1-9, 0). Read the description under the list.
3. Draw your own shapes with the mouse, then press **Space**.
4. Press **T** for the stamp tool: click to drop the selected pattern anywhere, **R** rotates it.
   Dropping a glider into the Pulsar is a fun experiment.
5. Slow down (or step) at interesting moments; speed up to see the long-term fate.

## Controls

| Input | Action |
|---|---|
| Left mouse | Draw cells (drag) / stamp pattern |
| Right mouse | Erase |
| Space | Play / pause |
| N or Right arrow | Step one generation (hold to repeat) |
| Up / Down, `+` / `-`, slider | Speed (0.5 - 240 gen/s) |
| Scroll wheel (vertical) | Zoom in/out around the cursor (1x - 5x) |
| Horizontal scroll, or Shift + wheel | Speed |
| Middle-drag, or Shift + left-drag | Pan when zoomed in |
| Home or F | Reset zoom to the full board |
| 1-9, 0 | Load scenario |
| X | Random soup |
| T / R | Toggle draw/stamp tool / rotate stamp |
| C | Clear |
| W | Toggle wrap-around edges (torus) vs. solid walls |
| G | Toggle grid lines |
| H | Help overlay |
| Esc | Quit |

## Things that make it more interesting

- **Age colouring**: newborn cells flash white and shift to blue, then violet, so you can see what is stable.
- **Fading trails**: a purple glow marks where cells recently died, making motion visible.
- **Wrap-around vs. walls**: gliders either loop forever or crash at the edge.
- **Population graph** and a status badge (Running / Paused / Stable / Extinct).
- **Methuselahs**: R-pentomino, Acorn and Diehard are tiny starts with very long, chaotic lives.

## Layout

- `conway/engine.py` - simulation (numpy, no graphics)
- `conway/patterns.py` - scenarios
- `conway/app.py` - pygame UI
