"""Colour themes for the maze area. Values are 0xRRGGBB.

The UI panel colours (C_UI_*) are deliberately not part of a theme, so the
side panel stays readable whatever palette is selected.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """One complete palette for the maze drawing."""
    name: str
    bg: int
    floor: int
    wall: int
    path: int
    pattern: int
    entry: int
    exit: int
    player: int


THEMES: list[Theme] = [
    Theme(  # the original colours
        name="Classic",
        bg=0x323232, floor=0x404040, wall=0xDDDDDD,
        path=0x499847, pattern=0xF9A013,
        entry=0x2A4C73, exit=0x2A4C73, player=0xA54900,
    ),
    Theme(
        name="Ocean",
        bg=0x0B1F2E, floor=0x12334A, wall=0x7FD1E8,
        path=0x2EC4B6, pattern=0xFFD166,
        entry=0x4361EE, exit=0x4361EE, player=0xFF6B6B,
    ),
    Theme(
        name="Sunset",
        bg=0x2B1B2E, floor=0x3F2740, wall=0xFFB48A,
        path=0xF4A261, pattern=0xE9C46A,
        entry=0x8338EC, exit=0x8338EC, player=0x06D6A0,
    ),
]
