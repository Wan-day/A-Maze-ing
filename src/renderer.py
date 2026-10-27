#!/usr/bin/env python3
"""MLX viewer for a generated maze.

Reads the maze from the output file (via MazeFileParser), lays the window out
from RenderConfig, and can ask the generator for a new maze through the
``regenerate`` callback it is given.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

import mlx

from config import (
    EVENT_KEY_PRESS, EVENT_KEY_RELEASE, EVENT_WINDOW_CLOSE,
    EVENT_MOUSE_PRESS,
    MASK_KEY_PRESS, MASK_KEY_RELEASE, MASK_NONE, MASK_MOUSE_PRESS,
    KEY_ESC, KEY_LEFT, KEY_RIGHT, KEY_UP, KEY_DOWN,
    KEY_SPACE, KEY_C,
    C_WHITE, C_UI_BG, C_UI_ACTIVE, C_UI_INACTIVE,
    MARGIN, UI_W, UI_BTN_H, UI_BTN_W, UI_BTN_GAP, FLASH_DURATION,
    MLX_CHAR_W, MLX_CHAR_H,
)
from errors import ConfigError
from maze_parser import MazeData, MazeFileParser
from render_config import RenderConfig
from themes import THEMES, Theme

if TYPE_CHECKING:
    from a_maze_ing import Config


@dataclass
class Button:
    """A clickable rectangle in the UI panel, optionally bound to a key.

    Attributes:
        label: Text drawn inside the button.
        action: Method called when the button is pressed.
        key: Keycode that triggers the same action (optional).
        deferred: Run the action on the next frame instead of immediately
            (use for slow actions, so the highlight shows first).
        x, y, w, h: Rectangle in window pixels (set by make_buttons).
        flash_until: Highlight deadline; 0.0 means not highlighted.
    """
    label: str
    action: Callable[[], None]
    key: int | None = None
    deferred: bool = False
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    flash_until: float = 0.0

    def contains(self, px: int, py: int) -> bool:
        """Return True if the pixel (px, py) is inside the button."""
        return (self.x <= px < self.x + self.w
                and self.y <= py < self.y + self.h)


class MazeRenderer():
    """Draw a maze in an MLX window and let the user walk through it.

    Args:
        config: Validated base configuration (from a_maze_ing.py).
        regenerate: Optional callback that generates a new maze and rewrites
            OUTPUT_FILE. Called when SPACE is pressed. Without it, SPACE
            just reloads the maze file.
    """

    def __init__(self, config: Config,
                 regenerate: Callable[[], None] | None = None):
        self.config: Config = config
        self.layout: RenderConfig = RenderConfig.from_config(config)
        self.regenerate = regenerate
        self.parser = MazeFileParser()
        self.pending_action: Callable[[], None] | None = None
        self.theme_index: int = 0
        self.theme: Theme = THEMES[self.theme_index]
        self.buttons: list[Button] = self.make_buttons()
        self.maze: MazeData = self.load_maze()
        self.player_col: int = self.maze.entry[0]
        self.player_row: int = self.maze.entry[1]
        self.m = mlx.Mlx()
        self.mlx_ptr = self.m.mlx_init()
        self.win_ptr = self.m.mlx_new_window(self.mlx_ptr,
                                             self.layout.win_w,
                                             self.layout.win_h,
                                             "maze")
        self.img_ptr = self.m.mlx_new_image(self.mlx_ptr,
                                            self.layout.win_w,
                                            self.layout.win_h)
        self.img_addr, _, self.img_size_line, _ = \
            self.m.mlx_get_data_addr(self.img_ptr)

    def load_maze(self) -> MazeData:
        """Parse OUTPUT_FILE and check it matches the base configuration.

        Raises:
            ConfigError: If the file is malformed or disagrees with the
                configured size / entry / exit.
        """
        maze = self.parser.parse(self.config["OUTPUT_FILE"])
        if (maze.cols, maze.rows) != (self.config["WIDTH"],
                                      self.config["HEIGHT"]):
            raise ConfigError("Maze file size does not match WIDTH/HEIGHT")
        if (maze.entry, maze.exit) != (self.config["ENTRY"],
                                       self.config["EXIT"]):
            raise ConfigError("Maze file entry/exit does not match config")
        return maze

    def draw_maze(self) -> None:
        self.m.mlx_hook(self.win_ptr, EVENT_KEY_PRESS, MASK_KEY_PRESS,
                        self.key_press_handler, None)
        self.m.mlx_hook(self.win_ptr, EVENT_KEY_RELEASE, MASK_KEY_RELEASE,
                        self.key_release_handler, None)
        self.m.mlx_hook(self.win_ptr, EVENT_WINDOW_CLOSE, MASK_NONE,
                        self.close_handler, None)
        self.m.mlx_hook(self.win_ptr, EVENT_MOUSE_PRESS, MASK_MOUSE_PRESS,
                        self.mouse_press_handler, None)
        self.m.mlx_expose_hook(self.win_ptr, self.expose_handler, None)
        self.m.mlx_loop_hook(self.mlx_ptr, self.game_loop, None)
        self.m.mlx_loop(self.mlx_ptr)
        self.m.mlx_destroy_image(self.mlx_ptr, self.img_ptr)
        self.m.mlx_destroy_window(self.mlx_ptr, self.win_ptr)
        self.m.mlx_release(self.mlx_ptr)

    def game_loop(self, param: Any) -> int:
        """Fires every frame for the lifetime of the loop.
        Signature: mlx_loop_hook(mlx_ptr, func, param) -> None
        This is where deferred work actually runs. Flags set in key handlers
        are consumed here, one per frame, keeping handlers fast.
        Sequence for SPACE:
          Frame N:   button pressed - pending_action set, highlight shown
          Frame N+1: game_loop sees pending_action - action runs - redraw
          Frame N+2: flash timer expires - highlight removed - redraw
        """
        if self.pending_action is not None:
            action, self.pending_action = self.pending_action, None
            action()
            self.render_scene()

        now = time.time()
        expired = [b for b in self.buttons
                   if b.flash_until and now > b.flash_until]
        if expired:
            for button in expired:
                button.flash_until = 0.0
            self.render_scene()

        return 0

    def expose_handler(self, param: Any) -> None:
        """Redraw the scene when MLX maps or exposes the window."""
        self.render_scene()

    def str_color(self, color: int) -> int:
        """Convert 0xRRGGBB to 0xBBGGRR for mlx_string_put."""
        r = (color >> 16) & 0xFF
        g = (color >> 8) & 0xFF
        b = color & 0xFF
        return (b << 16) | (g << 8) | r

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
        if not (0 <= x < self.layout.win_w and 0 <= y < self.layout.win_h):
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
        x1 = min(self.layout.win_w, x + w)
        y1 = min(self.layout.win_h, y + h)
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
        inset = self.layout.wall_size
        interior_size = self.layout.cell_size - 2 * inset
        self.write_rect(self.tile_px(tile_col) + inset,
                        self.tile_py(tile_row) + inset,
                        interior_size, interior_size, color)

    def draw_wall_north(self, tile_col: int, tile_row: int) -> None:
        """North wall: top edge strip, trimmed at both corners."""
        self.write_rect(self.tile_px(tile_col) + self.layout.wall_size,
                        self.tile_py(tile_row),
                        self.layout.cell_size - 2 * self.layout.wall_size,
                        self.layout.wall_size, self.theme.wall)

    def draw_wall_south(self, tile_col: int, tile_row: int) -> None:
        """South wall: bottom edge strip, trimmed at both corners."""
        self.write_rect(self.tile_px(tile_col) + self.layout.wall_size,
                        self.tile_py(tile_row) + self.layout.cell_size -
                        self.layout.wall_size,
                        self.layout.cell_size - 2 * self.layout.wall_size,
                        self.layout.wall_size, self.theme.wall)

    def draw_wall_west(self, tile_col: int, tile_row: int) -> None:
        """West wall: left edge strip, trimmed at both corners."""
        self.write_rect(self.tile_px(tile_col),
                        self.tile_py(tile_row) + self.layout.wall_size,
                        self.layout.wall_size, self.layout.cell_size -
                        2 * self.layout.wall_size,
                        self.theme.wall)

    def draw_wall_east(self, tile_col: int, tile_row: int) -> None:
        """East wall: right edge strip, trimmed at both corners."""
        self.write_rect(self.tile_px(tile_col) + self.layout.cell_size -
                        self.layout.wall_size,
                        self.tile_py(tile_row) + self.layout.wall_size,
                        self.layout.wall_size, self.layout.cell_size -
                        2 * self.layout.wall_size,
                        self.theme.wall)

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
        return (tile_col * self.layout.cell_size) + MARGIN

    def tile_py(self, tile_row: int) -> int:
        """Convert tile row index to pixel y (top-left corner of tile)."""
        return (tile_row * self.layout.cell_size) + MARGIN

# ==============
# WALL COLLISION
# ==============

    def in_bounds(self, col: int, row: int) -> bool:
        """Return True if (col, row) is a valid tile position inside the grid.
        Called before draw_tile - an out-of-range index computes a pixel
        coordinate outside the image buffer and raises ValueError.
        """
        return 0 <= col < self.maze.cols and 0 <= row < self.maze.rows

    def can_move(self, col: int, row: int, direction: str) -> bool:
        """Return True if player can step in direction from (col, row).
        Only checks wall bitmask - bounds are guaranteed by caller.
        Bitmask format from M03: bit 3 = West, bit 2 = South,
                                 bit 1 = East, bit 0 = North
        """
        bitmask = self.maze.grid[row][col]  # MAZE_GRID - maze data
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
        self.write_rect(0, 0, self.layout.win_w, self.layout.win_h,
                        self.theme.bg)
        for row in range(self.maze.rows):
            for col in range(self.maze.cols):
                self.draw_tile(col, row, self.theme.floor)

    def draw_layer_pattern(self) -> None:
        """Layer 2: Pattern tiles - decorative cells, drawn after floor."""
        for tile_col, tile_row in self.maze.pattern:
            self.draw_tile(tile_col, tile_row, self.theme.pattern)

    def draw_layer_path(self) -> None:
        """Layer 3: Solution path, drawn after pattern tiles."""
        for tile_col, tile_row in self.maze.path:
            self.draw_tile(tile_col, tile_row, self.theme.path)

    def draw_layer_overlay(self) -> None:
        """Layer 4 + 5: Entry, exit, and all walls."""
        self.draw_tile(*self.maze.entry, self.theme.entry)
        self.draw_tile(*self.maze.exit,  self.theme.exit)
        for row in range(self.maze.rows):
            for col in range(self.maze.cols):
                self.draw_tile_walls(col, row, self.maze.grid[row][col])

    def draw_layer_player(self) -> None:
        """Layer 6: Player tile - drawn last in maze area, always on top."""
        self.draw_tile(self.player_col, self.player_row, self.theme.player)

    def make_buttons(self) -> list[Button]:
        """Create the UI buttons and stack them in the side panel.

        Positions are computed once here; drawing and click detection both
        read them, so what you see is what you can click.
        """
        buttons = [
            Button("Regenerate", self.do_regen, key=KEY_SPACE, deferred=True),
            Button("Colors", self.next_theme, key=KEY_C),
        ]
        x = self.layout.maze_w + (UI_W - UI_BTN_W) // 2
        y = self.layout.win_h // 2 + 10
        for button in buttons:
            button.x, button.y = x, y
            button.w, button.h = UI_BTN_W, UI_BTN_H
            y += UI_BTN_H + UI_BTN_GAP
        return buttons

    def draw_layer_ui(self) -> None:
        """Layer 7: UI panel background and buttons."""
        self.write_rect(self.layout.maze_w, 0, UI_W,
                        self.layout.win_h, C_UI_BG)
        for button in self.buttons:
            color = C_UI_ACTIVE if button.flash_until else C_UI_INACTIVE
            self.write_rect(button.x, button.y, button.w, button.h, color)

    def put_text(self, x: int, y: int, color: int, text: str) -> None:
        """Draw text directly on the window (y is the top of the text)."""
        self.m.mlx_string_put(self.mlx_ptr, self.win_ptr, x, y,
                              self.str_color(color), text)

    def draw_ui_labels(self) -> None:
        """Draw UI text labels on top of the image buffer.
        Must be called AFTER render() - mlx_string_put draws directly
        to the window and is overwritten if render() is called again.
        """
        label_x = self.layout.maze_w + (UI_W - UI_BTN_W) // 2
        base_y = self.layout.win_h // 2

        legend = (("ARROWS", "Move"), ("SPACE", "Regenerate"),
                  ("C", "Colors"), ("ESC", "Quit"))
        for i, (key_name, description) in enumerate(legend):
            y = base_y - 110 + i * 30
            self.put_text(label_x, y, C_UI_INACTIVE, key_name)
            self.put_text(label_x + 100, y, C_WHITE, description)

        for button in self.buttons:
            text_w = len(button.label) * MLX_CHAR_W
            text_x = button.x + (button.w - text_w) // 2
            text_y = button.y + (button.h - MLX_CHAR_H) // 2
            self.put_text(text_x, text_y, C_WHITE, button.label)

        last = self.buttons[-1]
        self.put_text(label_x, last.y + last.h + 25, C_UI_INACTIVE,
                      f"Theme: {self.theme.name}")

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

    def key_press_handler(self, keycode: int, param: Any) -> int:
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

        for button in self.buttons:
            if keycode == button.key:
                self.press(button)

        return 0

    def mouse_press_handler(self, button_id: int, x: int, y: int,
                            param: Any) -> int:
        """Handle mouse presses: a left click on a button presses it."""
        if button_id != 1:
            return 0
        for button in self.buttons:
            if button.contains(x, y):
                self.press(button)
                break
        return 0

    def press(self, button: Button) -> None:
        """Single entry point for a button, whether clicked or keyed."""
        button.flash_until = time.time() + FLASH_DURATION
        if button.deferred:
            self.pending_action = button.action
        else:
            button.action()
        self.render_scene()

    def close_handler(self, param: Any) -> int:
        """Handle the X button (window close event).
        Event 33 (DestroyNotify) is the correct hook for this.
        Do NOT use event 17 (ClientMessage) - it is unreliable
        across display configurations with this MLX build.
        """
        self.m.mlx_loop_exit(self.mlx_ptr)
        return 0

    def key_release_handler(self, keycode: int,
                            param: Any) -> int:
        """Handle key release events (event 3).
        Fires when a key is released - use it for continuous movement,
        held-key animations, or UI button release.
        Registered but does nothing here - see WHAT TO TRY NEXT.
        """
        return 0

# =============================================================================
# ACTIONS
# =============================================================================

    def next_theme(self) -> None:
        """Switch to the next colour theme (wraps around)."""
        self.theme_index = (self.theme_index + 1) % len(THEMES)
        self.theme = THEMES[self.theme_index]

    def do_regen(self) -> None:
        """Generate a new maze (if a callback was given) and reload it.

        The callback rewrites OUTPUT_FILE; the maze is then parsed again, so
        the window always shows what is in the file. On failure the current
        maze stays on screen.
        """
        try:
            if self.regenerate is not None:
                self.regenerate()
            self.maze = self.load_maze()
        except Exception as e:
            print(f"Regeneration failed: {e}")
            return
        self.player_col, self.player_row = self.maze.entry


def main() -> None:
    """View an existing maze file: python3 renderer.py config.txt"""
    from a_maze_ing import load_config, validate_config

    if len(sys.argv) != 2:
        print("Usage: python3 renderer.py config.txt")
        return
    try:
        config = validate_config(load_config(sys.argv[1]))
        MazeRenderer(config).draw_maze()
    except (ConfigError, OSError) as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
