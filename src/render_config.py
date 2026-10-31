"""Layout settings for the MLX renderer.

The renderer's configuration is split in two:

* the base ``Config`` (WIDTH, HEIGHT, ENTRY, EXIT, OUTPUT_FILE, PERFECT,
  SEED), which is parsed and validated in ``a_maze_ing.py``;
* ``RenderConfig`` (this module), which only holds pixel-level layout values
  and is *derived* from the base config, so nothing is parsed twice.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mlx_config import (
    MAX_WIN_W, MAX_WIN_H, MARGIN, MIN_CELL, MAX_CELL, UI_W,
    WALL_RATIO, WALL_MIN, WALL_MAX,
)

if TYPE_CHECKING:
    from a_maze_ing import Config


@dataclass(frozen=True)
class RenderConfig:
    """Pixel layout of the window.

    Attributes:
        cell_size: Side of one maze cell in pixels.
        wall_size: Thickness of a wall in pixels.
        maze_w: Width in pixels of the maze area (the UI panel starts here).
        win_w: Total window width in pixels.
        win_h: Total window height in pixels.
    """
    cell_size: int
    wall_size: int
    maze_w: int
    win_w: int
    win_h: int

    @classmethod
    def from_config(cls, config: Config) -> RenderConfig:
        """Compute the layout that fits a maze of the configured size.

        Args:
            config: Validated base configuration.

        Returns:
            The render layout for a WIDTH x HEIGHT maze.
        """
        width = config["WIDTH"]
        height = config["HEIGHT"]

        avail_w = MAX_WIN_W - 2 * MARGIN - UI_W
        avail_h = MAX_WIN_H - 2 * MARGIN
        cell = min(avail_w // width, avail_h // height)
        cell = max(MIN_CELL, min(MAX_CELL, cell))

        wall = max(WALL_MIN, min(WALL_MAX, cell // WALL_RATIO))
        maze_w = width * cell + 2 * MARGIN
        win_w = maze_w + UI_W
        # 300 keeps the labels visible on tiny mazes
        win_h = max(cell * height + 2 * MARGIN, 300)
        return cls(cell_size=cell, wall_size=wall, maze_w=maze_w,
                   win_w=win_w, win_h=win_h)
