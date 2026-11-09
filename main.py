"""
main.py
=======

Entry point for the Minesweeper application.

Run from this folder:

    python main.py

The module only creates the Tk root and hands it to the GUI class.  All game
rules are in ``board.py`` and all drawing is in ``gui.py``.
"""

from __future__ import annotations

import tkinter as tk

from gui import MinesweeperGUI


# Decomposition: the entry point only creates the root and GUI.
def main() -> None:
    """Create the window and start Tkinter's event loop."""
    root = tk.Tk()
    MinesweeperGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
