"""
cell.py
=======

The smallest unit of the Minesweeper model.

CT pillar shown here: **Abstraction**.
A real Minesweeper square has a lot of information attached to it (a picture,
a number, whether it is covered, whether it has a flag, ...).  For the game
logic we only need four pieces of state, so this class hides everything else.

The class deliberately has *exactly* the four properties requested by the
project brief:

    is_mine          -> bool
    is_revealed      -> bool
    is_flagged       -> bool
    adjacent_mines   -> int (0..8)

`slots=True` keeps the object small and prevents accidental extra attributes,
which is a nice way to make the abstraction strict.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Cell:
    """One square on the Minesweeper board.

    Parameters
    ----------
    is_mine:
        True when this cell contains a mine.
    is_revealed:
        True after the player has opened this cell.  On a loss the board also
        marks mine cells as revealed so the UI can show them.
    is_flagged:
        True while the player has placed a flag on this cell.
    adjacent_mines:
        Number of mines in the (at most eight) neighbouring cells.
        A mine cell itself always has 0 here because it is not a safe cell.
    """

    is_mine: bool = False
    is_revealed: bool = False
    is_flagged: bool = False
    adjacent_mines: int = 0
