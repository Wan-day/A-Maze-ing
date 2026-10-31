"""Parser for the maze output file written by 'MazeGenerator.write_output()'.

File layout::

    <hex grid, one row per line>
    <blank line>
    <entry x,y>
    <exit x,y>
    <path as a string of N/E/S/W>

Bit layout of a hex digit: 0 = North, 1 = East, 2 = South, 3 = West
(a set bit means the wall is closed).
"""

from dataclasses import dataclass

from mlx_config import DIRECTIONS
from errors import ConfigError

CLOSED_CELL = 0xF


@dataclass(frozen=True)
class MazeData:
    """Everything the renderer needs to draw a maze.

    Attributes:
        grid: Wall bitmasks, indexed ``grid[row][col]``.
        entry: Entry cell as (x, y).
        exit: Exit cell as (x, y).
        path: Cells of the solution from entry to exit, as (x, y).
        pattern: Cells of the "42" pattern, as (x, y).
    """
    grid: list[list[int]]
    entry: tuple[int, int]
    exit: tuple[int, int]
    path: list[tuple[int, int]]
    pattern: list[tuple[int, int]]

    @property
    def cols(self) -> int:
        """Number of cells in a row."""
        return len(self.grid[0])

    @property
    def rows(self) -> int:
        """Number of rows."""
        return len(self.grid)


class MazeFileParser:
    """Read and validate a maze output file."""

    def parse(self, filename: str) -> MazeData:
        """Parse a maze file.

        Args:
            filename: Path of the maze file.

        Returns:
            The parsed and validated maze.

        Raises:
            ConfigError: If the file cannot be read or its content is
                malformed (bad hex, ragged rows, path walking through a
                wall, path not ending at the exit, ...).
        """
        grid_lines, tail = self._split_sections(self._read_lines(filename))
        grid = self._parse_grid(grid_lines)
        rows, cols = len(grid), len(grid[0])

        if len(tail) < 3 or not tail[2]:
            raise ConfigError("Expected entry, exit and path lines "
                              "after the grid")
        entry = self._parse_coords("entry", tail[0])
        exit_ = self._parse_coords("exit", tail[1])
        for name, (x, y) in (("entry", entry), ("exit", exit_)):
            if not (0 <= x < cols and 0 <= y < rows):
                raise ConfigError(f"{name} {x},{y} is outside the "
                                  f"{cols}x{rows} maze")

        path = self._walk_path(grid, entry, exit_, tail[2])
        return MazeData(grid, entry, exit_, path, self._find_pattern(grid))

    # ---- file structure ----

    def _read_lines(self, filename: str) -> list[str]:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return f.read().splitlines()
        except OSError as e:
            raise ConfigError(f"Cannot read maze file '{filename}': "
                              f"{e.strerror}")

    def _split_sections(self,
                        lines: list[str]) -> tuple[list[str], list[str]]:
        if "" not in lines:
            raise ConfigError("Missing blank line after the grid")
        split_at = lines.index("")
        return lines[:split_at], lines[split_at + 1:]

    # ---- grid ----

    def _parse_grid(self, grid_lines: list[str]) -> list[list[int]]:
        if not grid_lines:
            raise ConfigError("Maze file contains no grid")
        grid: list[list[int]] = []
        for lineno, line in enumerate(grid_lines, start=1):
            try:
                row = [int(ch, 16) for ch in line]
            except ValueError:
                raise ConfigError(f"Line {lineno}: "
                                  f"invalid hex digit in '{line}'")
            if grid and len(row) != len(grid[0]):
                raise ConfigError(f"Line {lineno}: row has {len(row)} cells, "
                                  f"expected {len(grid[0])}")
            grid.append(row)
        return grid

    def _find_pattern(self, grid: list[list[int]]) -> list[tuple[int, int]]:
        """Return the "42" pattern cells.

        The generator never opens a wall of a pattern cell, and every other
        cell is carved into the maze, so the fully closed cells (0xF) are
        exactly the pattern. This keeps the file format unchanged.
        """
        return [(x, y)
                for y, row in enumerate(grid)
                for x, value in enumerate(row)
                if value == CLOSED_CELL]

    # ---- entry / exit / path ----

    def _parse_coords(self, key: str, value: str) -> tuple[int, int]:
        parts = value.split(",")
        if len(parts) != 2:
            raise ConfigError(f"{key} must be in the form x,y, got '{value}'")
        try:
            return int(parts[0].strip()), int(parts[1].strip())
        except ValueError:
            raise ConfigError(f"{key} coordinates must be integers, "
                              f"got '{value}'")

    def _walk_path(self, grid: list[list[int]], entry: tuple[int, int],
                   exit_: tuple[int, int],
                   moves: str) -> list[tuple[int, int]]:
        """Follow the N/E/S/W string, checking each step against the walls."""
        rows, cols = len(grid), len(grid[0])
        x, y = entry
        cells = [(x, y)]
        for i, letter in enumerate(moves, start=1):
            if letter not in DIRECTIONS:
                raise ConfigError(f"Path step {i}: invalid letter '{letter}'")
            dx, dy, wall_bit = DIRECTIONS[letter]
            if grid[y][x] & wall_bit:
                raise ConfigError(f"Path step {i}: wall blocks {letter} "
                                  f"at {x},{y}")
            x, y = x + dx, y + dy
            if not (0 <= x < cols and 0 <= y < rows):
                raise ConfigError(f"Path step {i}: leaves the maze")
            cells.append((x, y))
        if cells[-1] != exit_:
            raise ConfigError(f"Path ends at {cells[-1]}, not at exit {exit_}")
        return cells
