#!/usr/bin/env python3

import time
import mlx
from dataclasses import dataclass
from config import (  # type: ignore
    EVENT_KEY_PRESS, EVENT_KEY_RELEASE, EVENT_WINDOW_CLOSE,
    MASK_KEY_PRESS, MASK_KEY_RELEASE, MASK_NONE,
    KEY_ESC, KEY_LEFT, KEY_RIGHT, KEY_UP, KEY_DOWN,
    KEY_SPACE,
    C_WHITE, C_BG, C_FLOOR, C_WALL, C_ENTRY, C_EXIT,
    C_PATH, C_PATTERN, C_PLAYER, C_UI_BG, C_UI_ACTIVE, C_UI_INACTIVE,
)


@dataclass
class MazeConfig:
    cols: int
    rows: int
    entry: tuple[int, int]
    exit: tuple[int, int]
    output_file: str
    perfect: bool
    cell_size: int
    win_w: int
    win_h: int
    wall_size: int
    maze_w: int


class ConfigError(Exception):
    """Raised when the configuration file is invalid."""


class MazeRenderer():
    MAX_WIN_W, MAX_WIN_H = 1600, 900
    MARGIN = 20
    MIN_CELL, MAX_CELL = 8, 100
    MIN_WIN_W = 600          # keeps the text panel readable for tiny mazes
    TEXT_ROWS = 12
    TEXT_ROW_H = 18          # px per row (monospace ~12-14pt font)
    TEXT_PADDING = 10
    WALL_RATIO = 12
    WALL_MIN = 1
    WALL_MAX = 2
    TEXT_PANEL_H = TEXT_ROWS * TEXT_ROW_H + 2 * TEXT_PADDING   # 236
    BORDER = 2
    UI_W = 300
    UI_BTN_H = 40
    UI_BTN_W = 200
    FLASH_DURATION = 0.15  # seconds a button stays highlighted after keypress
    DIRECTIONS = {            # letter: (dx, dy, wall bit that blocks the move)
        "N": (0, -1, 0b0001),
        "E": (1, 0, 0b0010),
        "S": (0, 1, 0b0100),
        "W": (-1, 0, 0b1000),
    }

    def __init__(self, path: str):
        self.flash_regen: float | None = None
        self.pending_regen: bool = False
        try:
            self.cfg: MazeConfig = self.set_config(path)
        except ConfigError as e:
            print(f"Error: {e}")
            raise SystemExit(1)
        temp: tuple[list[list[int]],
                    list[tuple[int, int]],
                    list[tuple[int, int]]] = self.set_maze()
        self.maze_grid: list[list[int]] = temp[0]
        self.path: list[tuple[int, int]] = temp[1]
        self.pattern: list[tuple[int, int]] = temp[2]
        self.player_col: int = self.cfg.entry[0]
        self.player_row: int = self.cfg.entry[1]
        self.m = mlx.Mlx()
        self.mlx_ptr = self.m.mlx_init()
        self.win_ptr = self.m.mlx_new_window(self.mlx_ptr,
                                             self.cfg.win_w,
                                             self.cfg.win_h,
                                             "maze")
        self.img_ptr = self.m.mlx_new_image(self.mlx_ptr,
                                            self.cfg.win_w,
                                            self.cfg.win_h)
        self.img_addr, _, self.img_size_line, _ = \
            self.m.mlx_get_data_addr(self.img_ptr)

    def draw_maze(self) -> None:
        self.m.mlx_hook(self.win_ptr, EVENT_KEY_PRESS, MASK_KEY_PRESS,
                        self.key_press_handler, None)
        self.m.mlx_hook(self.win_ptr, EVENT_KEY_RELEASE, MASK_KEY_RELEASE,
                        self.key_release_handler, None)
        self.m.mlx_hook(self.win_ptr, EVENT_WINDOW_CLOSE, MASK_NONE,
                        self.close_handler, None)
        self.render_scene()
        self.m.mlx_loop_hook(self.mlx_ptr, self.game_loop, None)
        self.m.mlx_loop(self.mlx_ptr)
        self.m.mlx_destroy_image(self.mlx_ptr, self.img_ptr)
        self.m.mlx_destroy_window(self.mlx_ptr, self.win_ptr)
        self.m.mlx_release(self.mlx_ptr)

    def game_loop(self, param) -> int:
        """Fires every frame for the lifetime of the loop.
        Signature: mlx_loop_hook(mlx_ptr, func, param) -> None
        This is where deferred work actually runs. Flags set in key handlers
        are consumed here, one per frame, keeping handlers fast.
        Sequence for SPACE:
          Frame N:   key pressed - pending_regen set, highlight shown, returns
          Frame N+1: game_loop sees pending_regen - do_regen() runs - redraw
          Frame N+2: flash timer expires - highlight removed - redraw
        """
        if self.pending_regen:
            self.pending_regen = False
            self.do_regen()
            self.render_scene()

        if self.flash_regen is not None and \
                time.time() - self.flash_regen > self.FLASH_DURATION:
            self.flash_regen = None
            self.render_scene()

        return 0

    def str_color(self, color: int) -> int:
        """Convert 0xRRGGBB to 0xBBGGRR for mlx_string_put."""
        r = (color >> 16) & 0xFF
        g = (color >> 8) & 0xFF
        b = color & 0xFF
        return (b << 16) | (g << 8) | r

# ===============
# MAZE PARSING
# ===============

    def set_maze(self) -> tuple[list[list[int]],
                                list[tuple[int, int]],
                                list[tuple[int, int]]]:
        grid, entry, exit_, path = self.parse_maze(self.cfg.output_file)
        if (len(grid), len(grid[0])) != (self.cfg.rows, self.cfg.cols):
            raise ConfigError("Maze file size does not match WIDTH/HEIGHT")
        if (entry, exit_) != (self.cfg.entry, self.cfg.exit):
            raise ConfigError("Maze file entry/exit does not match config")
        pattern = [(3, 3), (4, 3), (3, 4), (4, 4)]   # not stored in the file
        return grid, path, pattern

    def parse_maze(self, filename: str) -> tuple[list[list[int]],
                                                 tuple[int, int],
                                                 tuple[int, int],
                                                 list[tuple[int, int]]]:
        """Parse an output file into (grid, entry, exit, path_cells).

        Layout: hex grid rows, blank line, entry, exit, N/E/S/W path string.
        Bit layout: 0 = North, 1 = East, 2 = South, 3 = West (1 = closed).
        path_cells is the list of (col, row) cells from entry to exit.
        """
        try:
            with open(filename, "r", encoding="utf-8") as f:
                lines = f.read().split("\n")
        except OSError as e:
            raise ConfigError(f"Cannot read maze file '{filename}': "
                              f"{e.strerror}")

        if "" not in lines:
            raise ConfigError("Missing blank line after the grid")
        split_at = lines.index("")
        grid_lines, tail = lines[:split_at], lines[split_at + 1:]

        # --- grid ---
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
        rows, cols = len(grid), len(grid[0])

        # --- entry, exit, path ---
        if len(tail) < 3 or not tail[2]:
            raise ConfigError("Expected entry, exit and path lines "
                              "after the grid")
        entry = self._parse_coords("entry", tail[0])
        exit_ = self._parse_coords("exit", tail[1])
        moves = tail[2]

        for name, (x, y) in (("entry", entry), ("exit", exit_)):
            if not (0 <= x < cols and 0 <= y < rows):
                raise ConfigError(f"{name} {x},{y} is outside the "
                                  f"{cols}x{rows} maze")

        # --- walk the path, checking every step against the walls ---
        x, y = entry
        path_cells = [(x, y)]
        for i, letter in enumerate(moves, start=1):
            if letter not in self.DIRECTIONS:
                raise ConfigError(f"Path step {i}: invalid letter '{letter}'")
            dx, dy, wall_bit = self.DIRECTIONS[letter]
            if grid[y][x] & wall_bit:
                raise ConfigError(f"Path step {i}: wall blocks {letter} "
                                  f"at {x},{y}")
            x, y = x + dx, y + dy
            if not (0 <= x < cols and 0 <= y < rows):
                raise ConfigError(f"Path step {i}: leaves the maze")
            path_cells.append((x, y))

        if path_cells[-1] != exit_:
            raise ConfigError(f"Path ends at {path_cells[-1]}, "
                              f"not at exit {exit_}")

        return grid, entry, exit_, path_cells

# ===============
# CONFIG PARSING
# ===============

    def _parse_int(self, key: str, value: str) -> int:
        try:
            return int(value)
        except ValueError:
            raise ConfigError(f"{key} must be an integer, got '{value}'")

    def _parse_coords(self, key: str, value: str) -> tuple[int, int]:
        parts = value.split(",")
        if len(parts) != 2:
            raise ConfigError(f"{key} must be in the form x,y, got '{value}'")
        return (self._parse_int(key, parts[0].strip()),
                self._parse_int(key, parts[1].strip()))

    def compute_window_size(self, width: int,
                            height: int) -> tuple[int, int, int]:
        """Return (cell_size, window_w, window_h)."""
        avail_w = self.MAX_WIN_W - 2 * self.MARGIN - self.UI_W
        avail_h = self.MAX_WIN_H - 2 * self.MARGIN

        cell = min(avail_w // width, avail_h // height)
        cell = max(self.MIN_CELL, min(self.MAX_CELL, cell))

        window_w = cell * width + 2 * self.MARGIN + self.UI_W
        window_h = max(cell * height + 2 * self.MARGIN, 300)
        # 300 keeps the labels visible on tiny mazes
        return cell, window_w, window_h

    def set_config(self, path: str) -> MazeConfig:
        raw: dict[str, str] = {}
        MANDATORY_KEYS = ("WIDTH",
                          "HEIGHT",
                          "ENTRY",
                          "EXIT",
                          "OUTPUT_FILE",
                          "PERFECT")
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError as e:
            raise ConfigError("Cannot read config file"
                              f"'{path}': {e.strerror}")

        for lineno, line in enumerate(lines, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise ConfigError(f"Line {lineno}: "
                                  f"expected KEY=VALUE, got '{line}'")
            key, value = (part.strip() for part in line.split("=", 1))
            if not key or not value:
                raise ConfigError(f"Line {lineno}: empty key or value")
            if key in raw:
                raise ConfigError(f"Line {lineno}: duplicate key '{key}'")
            raw[key] = value

        missing = [k for k in MANDATORY_KEYS if k not in raw]
        if missing:
            raise ConfigError(f"Missing mandatory keys: {', '.join(missing)}")
        width = self._parse_int("WIDTH", raw["WIDTH"])
        height = self._parse_int("HEIGHT", raw["HEIGHT"])
        if width <= 0 or height <= 0:
            raise ConfigError("WIDTH and HEIGHT must be greater than 0")

        entry = self._parse_coords("ENTRY", raw["ENTRY"])
        exit_ = self._parse_coords("EXIT", raw["EXIT"])
        for name, (x, y) in (("ENTRY", entry), ("EXIT", exit_)):
            if not (0 <= x < width and 0 <= y < height):
                raise ConfigError(f"{name} {x},{y} "
                                  f"is outside the {width}x{height} maze")
        if entry == exit_:
            raise ConfigError("ENTRY and EXIT must be different cells")
        output_file = raw["OUTPUT_FILE"]

        if raw["PERFECT"] not in ("True", "False"):
            raise ConfigError("PERFECT must be True or False, got"
                              f" '{raw['PERFECT']}'")
        perfect = raw["PERFECT"] == "True"
        cell, win_w, win_h, = self.compute_window_size(width, height)

        wall_size: int = cell // self.WALL_RATIO
        if (wall_size > self.WALL_MAX):
            wall_size = self.WALL_MAX
        elif wall_size < self.WALL_MIN:
            wall_size = self.WALL_MIN

        maze_w = width * cell + 2 * self.MARGIN

        return MazeConfig(width, height, entry, exit_, output_file,
                          perfect, cell, win_w, win_h, wall_size,
                          maze_w)

# ===============
# DRAWING METHODS
# ===============

    def write_pixel(self, x: int, y: int, color: int) -> None:
        """Write single pixel at (x, y) into the image buffer.
        MLX stores pixels in BGR order, 4 bytes per pixel:
            [Blue, Green, Red, Alpha].
        Color constants use 0xRRGGBB (RGB) - the universal convention used by
        Photoshop, Aseprite, and every browser color picker.
        The conversion to BGR
        happens silently inside write_pixel and write_rect. Callers always pass
        0xRRGGBB unchanged.
        Uses img_size_line for the row stride - never recompute as width x 4.
        Out-of-bounds coords are skipped silently.
        """
        if not (0 <= x < self.cfg.win_w and 0 <= y < self.cfg.win_h):
            return
        byte_index = y * self.img_size_line + x * 4
        self.img_addr[byte_index] = color & 0xFF              # blue
        self.img_addr[byte_index + 1] = (color >> 8) & 0xFF   # green
        self.img_addr[byte_index + 2] = (color >> 16) & 0xFF  # red
        self.img_addr[byte_index + 3] = 0xFF                  # alpha

    def write_rect(self, x: int, y: int, w: int, h: int, color: int) -> None:
        """Fill a rectangle with a solid color using fast row slice assignment.
        Builds one complete BGR row as a bytearray (w x 4 bytes), then copies
        it into each row via slice assignment - bulk memory copy, orders of
        magnitude faster than a per-pixel loop for large fills like backgrounds
        """
        x0, y0 = max(0, x), max(0, y)
        x1 = min(self.cfg.win_w, x + w)
        y1 = min(self.cfg.win_h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        blue, green, red = color & 0xFF, (color >> 8) & 0xFF, \
            (color >> 16) & 0xFF
        row = bytearray([blue, green, red, 0xFF]) * (x1 - x0)
        for yy in range(y0, y1):
            start = yy * self.img_size_line + x0 * 4
            self.img_addr[start:start + len(row)] = row

    def render(self) -> None:
        """Push image buffer to window.
        Nothing drawn with write_pixel / write_rect is visible until this call.
        Draw everything first, then call render() once per frame.
        """
        self.m.mlx_put_image_to_window(self.mlx_ptr,
                                       self.win_ptr, self.img_ptr, 0, 0)

    def draw_tile(self, tile_col: int, tile_row: int, color: int) -> None:
        """Fill interior of a tile, inset by WALL_SIZE on all sides."""
        inset = self.cfg.wall_size
        interior_size = self.cfg.cell_size - 2 * inset
        self.write_rect(self.tile_px(tile_col) + inset,
                        self.tile_py(tile_row) + inset,
                        interior_size, interior_size, color)

    def draw_wall_north(self, tile_col: int, tile_row: int) -> None:
        """North wall: top edge strip, trimmed at both corners."""
        self.write_rect(self.tile_px(tile_col) + self.cfg.wall_size,
                        self.tile_py(tile_row),
                        self.cfg.cell_size - 2 * self.cfg.wall_size,
                        self.cfg.wall_size, C_WALL)

    def draw_wall_south(self, tile_col: int, tile_row: int) -> None:
        """South wall: bottom edge strip, trimmed at both corners."""
        self.write_rect(self.tile_px(tile_col) + self.cfg.wall_size,
                        self.tile_py(tile_row) + self.cfg.cell_size -
                        self.cfg.wall_size,
                        self.cfg.cell_size - 2 * self.cfg.wall_size,
                        self.cfg.wall_size, C_WALL)

    def draw_wall_west(self, tile_col: int, tile_row: int) -> None:
        """West wall: left edge strip, trimmed at both corners."""
        self.write_rect(self.tile_px(tile_col),
                        self.tile_py(tile_row) + self.cfg.wall_size,
                        self.cfg.wall_size, self.cfg.cell_size -
                        2 * self.cfg.wall_size,
                        C_WALL)

    def draw_wall_east(self, tile_col: int, tile_row: int) -> None:
        """East wall: right edge strip, trimmed at both corners."""
        self.write_rect(self.tile_px(tile_col) + self.cfg.cell_size -
                        self.cfg.wall_size,
                        self.tile_py(tile_row) + self.cfg.wall_size,
                        self.cfg.wall_size, self.cfg.cell_size -
                        2 * self.cfg.wall_size,
                        C_WALL)

    def draw_tile_walls(self,
                        tile_col: int, tile_row: int, bitmask: int) -> None:
        """Draw walls encoded in a 4-bit bitmask.
        Bit layout:
          bit 3 (0b1000) = West
          bit 2 (0b0100) = South
          bit 1 (0b0010) = East
          bit 0 (0b0001) = North
        Extracting each bit: (bitmask >> bit_position) & 1
        If 1, that wall is present and gets drawn.
        """
        if (bitmask >> 3) & 1:
            self.draw_wall_west(tile_col, tile_row)
        if (bitmask >> 2) & 1:
            self.draw_wall_south(tile_col, tile_row)
        if (bitmask >> 1) & 1:
            self.draw_wall_east(tile_col, tile_row)
        if (bitmask >> 0) & 1:
            self.draw_wall_north(tile_col, tile_row)

# ================
# TILE COORDINATES
# ================

    def tile_px(self, tile_col: int) -> int:
        """Convert tile column index to pixel x (top-left corner of tile)."""
        return (tile_col * self.cfg.cell_size) + self.MARGIN

    def tile_py(self, tile_row: int) -> int:
        """Convert tile row index to pixel y (top-left corner of tile)."""
        return (tile_row * self.cfg.cell_size) + self.MARGIN

# ==============
# WALL COLLISION
# ==============

    def in_bounds(self, col: int, row: int) -> bool:
        """Return True if (col, row) is a valid tile position inside the grid.
        Called before draw_tile - an out-of-range index computes a pixel
        coordinate outside the image buffer and raises ValueError.
        """
        return 0 <= col < self.cfg.cols and 0 <= row < self.cfg.rows

    def can_move(self, col: int, row: int, direction: str) -> bool:
        """Return True if player can step in direction from (col, row).
        Only checks wall bitmask - bounds are guaranteed by caller.
        Bitmask format from M03: bit 3 = West, bit 2 = South,
                                 bit 1 = East, bit 0 = North
        """
        bitmask = self.maze_grid[row][col]  # MAZE_GRID - maze data
        if direction == "north":
            return not ((bitmask >> 0) & 1)
        if direction == "south":
            return not ((bitmask >> 2) & 1)
        if direction == "east":
            return not ((bitmask >> 1) & 1)
        if direction == "west":
            return not ((bitmask >> 3) & 1)
        return False

# =================
# COMPOSITOR LAYERS
# =================

    def draw_layer_floor(self) -> None:
        """Layer 1: Fill window background, then all maze tile interiors."""
        self.write_rect(0, 0, self.cfg.win_w, self.cfg.win_h, C_BG)
        for row in range(self.cfg.rows):
            for col in range(self.cfg.cols):
                self.draw_tile(col, row, C_FLOOR)

    def draw_layer_pattern(self) -> None:
        """Layer 2: Pattern tiles - decorative cells, drawn after floor."""
        for tile_col, tile_row in self.pattern:
            self.draw_tile(tile_col, tile_row, C_PATTERN)

    def draw_layer_path(self) -> None:
        """Layer 3: Solution path, drawn after pattern tiles."""
        for tile_col, tile_row in self.path:
            self.draw_tile(tile_col, tile_row, C_PATH)

    def draw_layer_overlay(self) -> None:
        """Layer 4 + 5: Entry, exit, and all walls."""
        self.draw_tile(*self.cfg.entry, C_ENTRY)
        self.draw_tile(*self.cfg.exit,  C_EXIT)
        for row in range(self.cfg.rows):
            for col in range(self.cfg.cols):
                self.draw_tile_walls(col, row, self.maze_grid[row][col])

    def draw_layer_player(self) -> None:
        """Layer 6: Player tile - drawn last in maze area, always on top."""
        self.draw_tile(self.player_col, self.player_row, C_PLAYER)

    def draw_layer_ui(self) -> None:
        """Layer 7: UI panel background and regen button."""
        ui_center_x = self.cfg.maze_w + self.UI_W // 2
        btn_y = self.cfg.win_h // 2
        btn_color = C_UI_ACTIVE if self.flash_regen is not None \
            else C_UI_INACTIVE
        self.write_rect(self.cfg.maze_w, 0, self.UI_W, self.cfg.win_h, C_UI_BG)
        self.write_rect(ui_center_x - self.UI_BTN_W // 2, btn_y,
                        self.UI_BTN_W, self.UI_BTN_H, btn_color)

    def draw_ui_labels(self) -> None:
        """Draw UI text labels on top of the image buffer.
        Must be called AFTER render() - mlx_string_put draws directly
        to the window and is overwritten if render() is called again.
        """
        ui_center_x = self.cfg.maze_w + self.UI_W // 2
        btn_y = self.cfg.win_h // 2
        label_x = ui_center_x - self.UI_BTN_W // 2

        self.m.mlx_string_put(self.mlx_ptr,
                              self.win_ptr, label_x, btn_y - 110,
                              self.str_color(C_UI_INACTIVE), "ARROWS")
        self.m.mlx_string_put(self.mlx_ptr,
                              self.win_ptr,
                              label_x, btn_y - 110,
                              self.str_color(C_WHITE), "                Move")
        self.m.mlx_string_put(self.mlx_ptr,
                              self.win_ptr,
                              label_x, btn_y - 80,
                              self.str_color(C_UI_INACTIVE), "SPACE")
        self.m.mlx_string_put(self.mlx_ptr, self.win_ptr,
                              label_x, btn_y - 80,
                              self.str_color(C_WHITE), "          Regenerate")
        self.m.mlx_string_put(self.mlx_ptr, self.win_ptr,
                              label_x, btn_y - 50,
                              self.str_color(C_UI_INACTIVE), "ESC")
        self.m.mlx_string_put(self.mlx_ptr, self.win_ptr,
                              label_x, btn_y - 50,
                              self.str_color(C_WHITE), "                Quit")

# ============
# SCENE RENDER
# ============

    def render_scene(self) -> None:
        """Draw entire scene in layer order, render, then draw text labels."""
        self.draw_layer_floor()
        self.draw_layer_pattern()
        self.draw_layer_path()
        self.draw_layer_overlay()
        self.draw_layer_player()
        self.draw_layer_ui()
        self.render()
        self.draw_ui_labels()

# =================
# HANDLER METHODS
# =================

    def key_press_handler(self, keycode: int, param) -> int:
        """Handle key press events.
        keycode is the X11/XQuartz keycode of the pressed key.
        ESC exits the loop cleanly via mlx_loop_exit().
        """
        if keycode == KEY_ESC:
            self.m.mlx_loop_exit(self.mlx_ptr)
            return 0
        if (keycode == KEY_UP and self.in_bounds(self.player_col,
                                                 self.player_row - 1)
           and self.can_move(self.player_col, self.player_row, "north")):
            self.player_row -= 1
            self.render_scene()
        if (keycode == KEY_DOWN and self.in_bounds(self.player_col,
                                                   self.player_row + 1)
           and self.can_move(self.player_col,
                             self.player_row, "south")):
            self.player_row += 1
            self.render_scene()
        if (keycode == KEY_RIGHT and self.in_bounds(self.player_col + 1,
                                                    self.player_row)
           and self.can_move(self.player_col, self.player_row, "east")):
            self.player_col += 1
            self.render_scene()
        if (keycode == KEY_LEFT and self.in_bounds(self.player_col - 1,
                                                   self.player_row)
           and self.can_move(self.player_col, self.player_row, "west")):
            self.player_col -= 1
            self.render_scene()

        if keycode == KEY_SPACE:
            self.pending_regen = True
            self.flash_regen = time.time()
            self.render_scene()

        return 0

    def close_handler(self, param) -> int:
        """Handle the X button (window close event).
        Event 33 (DestroyNotify) is the correct hook for this.
        Do NOT use event 17 (ClientMessage) - it is unreliable
        across display configurations with this MLX build.
        """
        self.m.mlx_loop_exit(self.mlx_ptr)
        return 0

    def key_release_handler(self, keycode: int, param) -> int:
        """Handle key release events (event 3).
        Fires when a key is released - use it for continuous movement,
        held-key animations, or UI button release.
        Registered but does nothing here - see WHAT TO TRY NEXT.
        """
        return 0

# =============================================================================
# ACTIONS
# =============================================================================

    def do_regen(self) -> None:
        """Simulate maze regeneration - 300ms of blocking work.
        Here it just sleeps to demonstrate timing without complexity.
        Because this runs in game_loop, the UI highlight from flash_regen
        is already visible on screen before this blocks.
        """
        time.sleep(0.3)
        self.player_col, self.player_row = self.cfg.entry


def main():
    maze = MazeRenderer("maze_config")
    maze.draw_maze()


if __name__ == "__main__":
    main()
