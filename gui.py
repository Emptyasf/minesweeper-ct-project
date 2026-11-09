"""
gui.py
======

The Tkinter view for Minesweeper.

Design rule
-----------
This file **only draws and handles events**.  It never calculates neighbour
counts, decides whether a move wins, or opens a zero region itself.  Those
rules live in :mod:`board`.  Keeping the UI and model separate is an example
of **Decomposition** and **Abstraction**.

Dark theme
----------
Every colour, font, spacing value, animation delay and limit is kept in the
single ``THEME`` dictionary below.  Change a value there and the whole game
updates consistently.

The GUI uses a single ``tk.Canvas`` for the grid instead of dozens of default
Tk buttons.  That gives complete control over the flat, modern look, hover
states, flashes and animations.

Animations use ``root.after`` only.  ``time.sleep`` is never used, so the
event loop always remains responsive.
"""

from __future__ import annotations

import time
import tkinter as tk
from typing import Callable

from board import Board, GameState

# ====================================================================== #
#  ONE PLACE FOR THE ENTIRE THEME
# ====================================================================== #
THEME: dict[str, dict] = {
    "colours": {
        # Window and panels
        "window_bg": "#0f1419",
        "panel_bg": "#151b23",
        # Cells
        "hidden": "#1e2733",
        "hidden_border": "#2b3645",
        "hidden_highlight": "#344254",
        "hover": "#2a3646",
        "hover_outline": "#22d3ee",
        "revealed": "#0b0f14",
        # Accent and text
        "accent": "#22d3ee",
        "accent_dark": "#0e7490",
        "text": "#e5e7eb",
        "muted": "#94a3b8",
        "white": "#ffffff",
        # LED display
        "led_bg": "#000000",
        "led_red": "#ef4444",
        # Game symbols
        "flag": "#fb923c",
        "mine": "#ef4444",
        "mine_glow": "#7f1d1d",
        "mine_bg": "#2a1114",
        "exploded_bg": "#dc2626",
        "wrong_flag": "#fbbf24",
        "win_green": "#4ade80",
        "win_bg": "#0f2a1a",
        # Buttons
        "button_bg": "#1e2733",
        "button_hover": "#2a3646",
        "button_pressed": "#164e63",
        # Status colours
        "status_playing": "#22d3ee",
        "status_won": "#4ade80",
        "status_lost": "#f87171",
        # Overlay
        "overlay_bg": "#151b23",
        "overlay_border": "#22d3ee",
        "overlay_shadow": "#020617",
        # Classic bright number colours on a dark background
        "number_1": "#38bdf8",
        "number_2": "#4ade80",
        "number_3": "#f87171",
        "number_4": "#a78bfa",
        "number_5": "#fb923c",
        "number_6": "#2dd4bf",
        "number_7": "#f472b6",
        "number_8": "#e5e7eb",
    },
    "fonts": {
        "number": ("Consolas", 16, "bold"),
        "mine": ("Consolas", 20, "bold"),
        "flag": ("Segoe UI Symbol", 16, "bold"),
        "face": ("Segoe UI Emoji", 20),
        "ui": ("Segoe UI", 10),
        "ui_bold": ("Segoe UI", 10, "bold"),
        "button": ("Segoe UI", 9, "bold"),
        "status": ("Segoe UI", 12, "bold"),
        "led": ("Consolas", 20, "bold"),
        "title": ("Segoe UI", 18, "bold"),
        "overlay": ("Segoe UI", 11),
    },
    "sizes": {
        "cell": 36,
        "min_cell": 22,
        "grid_pad": 10,
        "border_width": 1,
        "hover_width": 2,
        "topbar_pad_x": 14,
        "topbar_pad_y": 8,
        "difficulty_pad_x": 10,
        "difficulty_pad_y": 4,
        "difficulty_gap": 6,
        "face_pad_x": 8,
        "face_pad_y": 2,
        "led_width": 4,
        "led_digits": 3,
        "led_pad_x": 8,
        "led_pad_y": 2,
        "led_label_gap": 2,
        "raised_inset": 1,
        "raised_line_width": 1,
        "flash_inset": 2,
        "overlay_border_width": 2,
        "entry_border_width": 1,
        "dialog_field_gap": 6,
        "screen_margin_x": 40,
        "screen_margin_y": 80,
        "status_pad_y": 7,
        "footer_pad_y": 5,
        "overlay_width": 300,
        "overlay_height": 200,
        "overlay_pad": 20,
        "overlay_gap": 8,
        "dialog_pad": 20,
        "dialog_gap": 10,
        "dialog_wrap": 300,
        "entry_width": 8,
        "wrong_flag_inset": 8,
        "wrong_flag_width": 2,
        "mine_glow_radius": 12,
        "min_window_width": 430,
        "custom_min": 3,
        "custom_max": 20,
        "max_led_seconds": 999,
    },
    "timing": {
        "flood_wave_ms": 25,
        "flash_ms": 120,
        "mine_reveal_ms": 42,
        "shake_step_ms": 35,
        "shake_offsets": (6, -6, 4, -4, 2, -2, 0),
        "timer_tick_ms": 200,
        "pulse_ms": 180,
        "pulse_cycles": 8,
        "win_overlay_delay_ms": 450,
        "face_reset_ms": 130,
    },
}


class MinesweeperGUI:
    """The Tkinter controller and view for the game."""

    # Decomposition: wire the model, view state and theme together.
    def __init__(
        self,
        root: tk.Tk,
        rows: int = 8,
        cols: int = 8,
        num_mines: int = 10,
    ) -> None:
        """Create the window state, build the UI and start a beginner game."""
        self.root = root
        self.root.title("Minesweeper  ·  Computational Thinking & Mathematics")
        self.root.configure(bg=THEME["colours"]["window_bg"])
        self.root.resizable(False, False)

        # Current game settings and session records.
        self.rows = rows
        self.cols = cols
        self.num_mines = num_mines
        self.cell_size = THEME["sizes"]["cell"]
        self.difficulty_key = "beginner"
        self.best_times: dict[tuple[int, int, int], int] = {}
        self.board: Board | None = None

        # Tk variables used by the labels.
        self.mines_var = tk.StringVar(
            master=root,
            value=self._format_led(num_mines),
        )
        self.timer_var = tk.StringVar(master=root, value=self._format_led(0))
        self.status_var = tk.StringVar(master=root, value="Playing")
        self.best_var = tk.StringVar(master=root, value="Best: --")
        self.score_var = tk.StringVar(master=root, value="Score: 0")

        # Runtime state that is not part of the game model.
        self._generation = 0
        self._hover: tuple[int, int] | None = None
        self._pressed_cell: tuple[int, int] | None = None
        self._animating = False
        self._timer_started = False
        self._start_time: float | None = None
        self._end_time: float | None = None
        self._timer_job: str | None = None
        self._pulse_job: str | None = None
        self._win_overlay: tk.Frame | None = None
        self._custom_dialog: CustomGameDialog | None = None
        self.difficulty_buttons: dict[str, tk.Button] = {}

        self._build_ui()
        self._bind_keys()
        self._new_game(rows, cols, num_mines, "beginner")

    # ================================================================== #
    #  UI construction
    # ================================================================== #
    # Decomposition: top bar, difficulty bar, grid, status and footer.
    def _build_ui(self) -> None:
        """Create the top bar, difficulty bar, canvas, status and footer."""
        colours = THEME["colours"]
        sizes = THEME["sizes"]
        fonts = THEME["fonts"]

        self.main = tk.Frame(self.root, bg=colours["window_bg"])
        self.main.pack(fill="both", expand=True)

        # ---------------- Top bar: mines | face | timer ---------------- #
        topbar = tk.Frame(self.main, bg=colours["panel_bg"])
        topbar.pack(fill="x")
        for column in range(3):
            topbar.grid_columnconfigure(column, weight=1)

        left_section = tk.Frame(topbar, bg=colours["panel_bg"])
        left_section.grid(
            row=0,
            column=0,
            sticky="w",
            padx=(sizes["topbar_pad_x"], 0),
            pady=sizes["topbar_pad_y"],
        )
        tk.Label(
            left_section,
            text="MINES",
            bg=colours["panel_bg"],
            fg=colours["muted"],
            font=fonts["ui_bold"],
        ).pack(anchor="w")
        self.mines_label = tk.Label(
            left_section,
            textvariable=self.mines_var,
            bg=colours["led_bg"],
            fg=colours["led_red"],
            font=fonts["led"],
            width=sizes["led_width"],
            padx=sizes["led_pad_x"],
            pady=sizes["led_pad_y"],
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        self.mines_label.pack(anchor="w", pady=(sizes["led_label_gap"], 0))

        centre_section = tk.Frame(topbar, bg=colours["panel_bg"])
        centre_section.grid(row=0, column=1)
        self.face_button = tk.Button(
            centre_section,
            text="🙂",
            command=self._restart,
            bg=colours["button_bg"],
            fg=colours["text"],
            activebackground=colours["button_hover"],
            activeforeground=colours["text"],
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=fonts["face"],
            padx=sizes["face_pad_x"],
            pady=sizes["face_pad_y"],
            cursor="hand2",
        )
        self.face_button.pack()

        right_section = tk.Frame(topbar, bg=colours["panel_bg"])
        right_section.grid(
            row=0,
            column=2,
            sticky="e",
            padx=(0, sizes["topbar_pad_x"]),
            pady=sizes["topbar_pad_y"],
        )
        tk.Label(
            right_section,
            text="TIME",
            bg=colours["panel_bg"],
            fg=colours["muted"],
            font=fonts["ui_bold"],
        ).pack(anchor="e")
        self.timer_label = tk.Label(
            right_section,
            textvariable=self.timer_var,
            bg=colours["led_bg"],
            fg=colours["led_red"],
            font=fonts["led"],
            width=sizes["led_width"],
            padx=sizes["led_pad_x"],
            pady=sizes["led_pad_y"],
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        self.timer_label.pack(anchor="e", pady=(sizes["led_label_gap"], 0))

        # ---------------- Difficulty segmented buttons ---------------- #
        difficulty_bar = tk.Frame(self.main, bg=colours["panel_bg"])
        difficulty_bar.pack(fill="x")

        difficulty_buttons = tk.Frame(difficulty_bar, bg=colours["panel_bg"])
        difficulty_buttons.pack(
            side="left",
            padx=(sizes["difficulty_pad_x"], 0),
            pady=(0, sizes["difficulty_pad_y"]),
        )

        for key, label, command in (
            ("beginner", "Beginner 8×8 · 10", self._choose_beginner),
            ("intermediate", "Intermediate 16×16 · 40", self._choose_intermediate),
            ("custom", "Custom…", self._open_custom_dialog),
        ):
            button = self._flat_button(
                difficulty_buttons,
                text=label,
                command=command,
                font=fonts["button"],
                padx=sizes["difficulty_pad_x"],
                pady=sizes["difficulty_pad_y"],
            )
            button.pack(side="left", padx=(0, sizes["difficulty_gap"]))
            self.difficulty_buttons[key] = button

        self.best_label = tk.Label(
            difficulty_bar,
            textvariable=self.best_var,
            bg=colours["panel_bg"],
            fg=colours["muted"],
            font=fonts["ui_bold"],
        )
        self.best_label.pack(
            side="right",
            padx=(0, sizes["difficulty_pad_x"]),
            pady=(0, sizes["difficulty_pad_y"]),
        )

        # ---------------- Grid canvas ---------------- #
        self.grid_holder = tk.Frame(self.main, bg=colours["window_bg"])
        self.grid_holder.pack()

        self.canvas = tk.Canvas(
            self.grid_holder,
            width=self._canvas_width(),
            height=self._canvas_height(),
            bg=colours["window_bg"],
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()
        self._bind_canvas()

        # ---------------- Status line below the grid ---------------- #
        status_frame = tk.Frame(self.main, bg=colours["window_bg"])
        status_frame.pack(fill="x", pady=(sizes["status_pad_y"], 0))
        self.status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            bg=colours["window_bg"],
            fg=colours["status_playing"],
            font=fonts["status"],
        )
        self.status_label.pack()

        # ---------------- Footer: shortcut hint + score ---------------- #
        footer = tk.Frame(self.main, bg=colours["window_bg"])
        footer.pack(
            fill="x",
            padx=sizes["topbar_pad_x"],
            pady=(0, sizes["footer_pad_y"]),
        )
        tk.Label(
            footer,
            text=(
                "L reveal  ·  R flag  ·  M / double-click chord  ·  "
                "R restart  ·  1/2/3 level  ·  Esc quit"
            ),
            bg=colours["window_bg"],
            fg=colours["muted"],
            font=fonts["ui"],
        ).pack(side="left")
        tk.Label(
            footer,
            textvariable=self.score_var,
            bg=colours["window_bg"],
            fg=colours["muted"],
            font=fonts["ui_bold"],
        ).pack(side="right")

    # Abstraction: one reusable flat dark button style.
    def _flat_button(
        self,
        parent: tk.Misc,
        text: str,
        command: Callable[[], None],
        font: tuple,
        padx: int,
        pady: int,
    ) -> tk.Button:
        """Create a flat, dark Tk button (no default grey relief)."""
        colours = THEME["colours"]
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=colours["button_bg"],
            fg=colours["text"],
            activebackground=colours["button_hover"],
            activeforeground=colours["text"],
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=font,
            padx=padx,
            pady=pady,
            cursor="hand2",
        )

    # Decomposition: mouse events stay separate from game rules.
    def _bind_canvas(self) -> None:
        """Bind mouse events.  All game rules are still delegated to Board."""
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<ButtonPress-1>", self._on_left_press)
        self.canvas.bind("<ButtonRelease-1>", self._on_left_release)
        self.canvas.bind("<ButtonPress-3>", self._on_right_click)
        self.canvas.bind("<ButtonPress-2>", self._on_middle_click)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)

    # Pattern Recognition: one shortcut handler per action.
    def _bind_keys(self) -> None:
        """Keyboard shortcuts: R restart, 1/2/3 difficulty, Esc quit."""
        self.root.bind("<Key-r>", lambda _event: self._restart())
        self.root.bind("<Key-R>", lambda _event: self._restart())
        self.root.bind("<Key-1>", lambda _event: self._choose_beginner())
        self.root.bind("<Key-2>", lambda _event: self._choose_intermediate())
        self.root.bind("<Key-3>", lambda _event: self._open_custom_dialog())
        self.root.bind("<Escape>", lambda _event: self._quit())

    # ================================================================== #
    #  Geometry helpers
    # ================================================================== #
    # Maths: grid width = columns * cell size + padding.
    def _canvas_width(self) -> int:
        """Return the pixel width needed by the current grid."""
        return self.cols * self.cell_size + 2 * THEME["sizes"]["grid_pad"]

    # Maths: grid height = rows * cell size + padding.
    def _canvas_height(self) -> int:
        """Return the pixel height needed by the current grid."""
        return self.rows * self.cell_size + 2 * THEME["sizes"]["grid_pad"]

    # Maths: pixels -> matrix coordinates with integer division.
    def _event_cell(self, event: tk.Event) -> tuple[int, int] | None:
        """Convert pixel coordinates to a (row, col) cell, or None."""
        size = self.cell_size
        pad = THEME["sizes"]["grid_pad"]
        x = event.x - pad
        y = event.y - pad
        if x < 0 or y < 0:
            return None
        col = x // size
        row = y // size
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return int(row), int(col)
        return None

    # Algorithmic Thinking: measure the content, then resize and centre.
    def _fit_window(self) -> None:
        """Resize the window automatically to fit the current grid."""
        self.root.update_idletasks()
        width = max(
            self.root.winfo_reqwidth(),
            THEME["sizes"]["min_window_width"],
        )
        height = self.root.winfo_reqheight()

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = min(width, screen_width - THEME["sizes"]["screen_margin_x"])
        height = min(height, screen_height - THEME["sizes"]["screen_margin_y"])

        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    # Algorithmic Thinking: uniform scaling keeps large boards on screen.
    def _adapt_cell_size(self) -> None:
        """Shrink cells only when a large custom board would not fit the screen.

        Normal boards keep the full 36 px cell size.  For a big custom board the
        cells shrink uniformly (down to ``min_cell``), so the grid stays
        consistent and the window still fits without scrolling.
        """
        sizes = THEME["sizes"]
        pad = sizes["grid_pad"]

        # Measure everything except the canvas: top bar, difficulty bar,
        # status line, footer and window padding.
        chrome_width = max(
            0,
            self.root.winfo_reqwidth() - self._canvas_width(),
        )
        chrome_height = max(
            0,
            self.root.winfo_reqheight() - self._canvas_height(),
        )

        available_width = (
            self.root.winfo_screenwidth()
            - sizes["screen_margin_x"]
            - chrome_width
        )
        available_height = (
            self.root.winfo_screenheight()
            - sizes["screen_margin_y"]
            - chrome_height
        )

        cell_by_width = (available_width - 2 * pad) // self.cols
        cell_by_height = (available_height - 2 * pad) // self.rows
        adapted = max(
            sizes["min_cell"],
            min(sizes["cell"], cell_by_width, cell_by_height),
        )

        if adapted != self.cell_size:
            self.cell_size = adapted
            self.canvas.config(
                width=self._canvas_width(),
                height=self._canvas_height(),
            )

    # ================================================================== #
    #  New game / difficulty
    # ================================================================== #
    # Decomposition: reset view state around a fresh Board.
    def _new_game(
        self,
        rows: int,
        cols: int,
        num_mines: int,
        difficulty_key: str,
    ) -> None:
        """Start a fresh game while keeping session best times."""
        # Incrementing the generation invalidates every pending animation
        # callback from the previous board.
        self._generation += 1
        self._cancel_jobs()

        if self._win_overlay is not None:
            self._win_overlay.destroy()
            self._win_overlay = None

        self.rows = rows
        self.cols = cols
        self.num_mines = num_mines
        self.cell_size = THEME["sizes"]["cell"]
        self.difficulty_key = difficulty_key

        self.board = Board(rows, cols, num_mines)

        self._hover = None
        self._pressed_cell = None
        self._animating = False
        self._timer_started = False
        self._start_time = None
        self._end_time = None

        self.timer_var.set(self._format_led(0))
        self.score_var.set("Score: 0")
        self.mines_var.set(self._format_led(num_mines))

        self.canvas.config(
            width=self._canvas_width(),
            height=self._canvas_height(),
        )
        self.root.update_idletasks()
        self._adapt_cell_size()
        self._render_all()
        self._set_status()
        self._refresh_face()
        self._refresh_difficulty_buttons()
        self._update_best_label()
        self._fit_window()
        self.root.focus_set()

    # Abstraction: restart the current configuration.
    def _restart(self) -> None:
        """Restart the current difficulty with a fresh random board."""
        if self.board is None:
            return
        self._new_game(
            self.rows,
            self.cols,
            self.num_mines,
            self.difficulty_key,
        )

    # Abstraction: a named preset difficulty.
    def _choose_beginner(self) -> None:
        """Switch to the 8x8, 10-mine beginner board."""
        self._new_game(8, 8, 10, "beginner")

    # Abstraction: a named preset difficulty.
    def _choose_intermediate(self) -> None:
        """Switch to the 16x16, 40-mine intermediate board."""
        self._new_game(16, 16, 40, "intermediate")

    # Abstraction: accept already-validated custom settings.
    def start_custom_game(self, rows: int, cols: int, num_mines: int) -> None:
        """Called by the custom-dialog after validation succeeds."""
        self._new_game(rows, cols, num_mines, "custom")

    # Pattern Recognition: the same selected-style rule for every button.
    def _refresh_difficulty_buttons(self) -> None:
        """Highlight the selected difficulty in cyan."""
        colours = THEME["colours"]
        for key, button in self.difficulty_buttons.items():
            selected = key == self.difficulty_key
            button.config(
                bg=colours["accent"] if selected else colours["button_bg"],
                fg=colours["window_bg"] if selected else colours["text"],
                activebackground=(
                    colours["accent"] if selected else colours["button_hover"]
                ),
                activeforeground=(
                    colours["window_bg"] if selected else colours["text"]
                ),
            )

    # ================================================================== #
    #  Drawing
    # ================================================================== #
    # Decomposition: all drawing passes through one renderer.
    def _render_all(self, hide_mines: bool = False) -> None:
        """Redraw every cell.  ``hide_mines`` is used for the loss animation."""
        self.canvas.delete("all")
        if self.board is None:
            return
        for row in range(self.rows):
            for col in range(self.cols):
                if hide_mines and self.board.board[row][col].is_mine:
                    self._draw_cell(row, col, force_hidden=True)
                else:
                    self._draw_cell(row, col)

    # Pattern Recognition: one drawing rule for every cell state.
    def _draw_cell(
        self,
        row: int,
        col: int,
        force_hidden: bool = False,
    ) -> None:
        """Draw one cell using the current board state.

        The method contains **presentation logic only** (what colour to use,
        which symbol to show).  It reads state from the Board but never
        changes a rule.
        """
        if self.board is None:
            return

        colours = THEME["colours"]
        sizes = THEME["sizes"]
        fonts = THEME["fonts"]

        cell = self.board.board[row][col]
        tag = f"cell_{row}_{col}"
        self.canvas.delete(tag)

        size = self.cell_size
        pad = sizes["grid_pad"]
        x0 = pad + col * size
        y0 = pad + row * size
        x1 = x0 + size
        y1 = y0 + size
        centre_x = (x0 + x1) / 2
        centre_y = (y0 + y1) / 2

        hovered = (
            self._hover == (row, col)
            and not cell.is_revealed
            and self.board.state is GameState.PLAYING
            and not force_hidden
        )

        fill = colours["hidden"]
        outline = colours["hidden_border"]
        border_width = sizes["border_width"]
        text = ""
        text_colour = colours["text"]
        text_font = fonts["number"]
        show_glow = False
        crossed_flag = False

        if force_hidden:
            # Used only while mines are being revealed one-by-one after a loss.
            if hovered:
                fill = colours["hover"]
                outline = colours["hover_outline"]
                border_width = sizes["hover_width"]
            if cell.is_flagged:
                text = "⚑"
                text_colour = colours["flag"]
                text_font = fonts["flag"]

        elif cell.is_revealed:
            if cell.is_mine:
                # A revealed mine is bright red; the clicked one is brightest.
                if (
                    self.board.state is GameState.LOST
                    and self.board.exploded_cell == (row, col)
                ):
                    fill = colours["exploded_bg"]
                    text_colour = colours["white"]
                elif self.board.state is GameState.WON:
                    fill = colours["win_bg"]
                    text_colour = colours["win_green"]
                else:
                    fill = colours["mine_bg"]
                    text_colour = colours["mine"]
                outline = fill
                border_width = 0
                text = "*"
                text_font = fonts["mine"]
                show_glow = True
            else:
                # Revealed safe cells are flat and have no raised border.
                fill = colours["revealed"]
                outline = colours["revealed"]
                border_width = 0
                if cell.adjacent_mines > 0:
                    text = str(cell.adjacent_mines)
                    text_colour = colours[f"number_{cell.adjacent_mines}"]
                    text_font = fonts["number"]

        else:
            # Hidden cell.  On a win the remaining mines turn green.
            if self.board.state is GameState.WON and cell.is_mine:
                fill = colours["win_bg"]
                outline = colours["win_green"]
                border_width = sizes["border_width"]
                text = "⚑" if cell.is_flagged else "*"
                text_colour = colours["win_green"]
                text_font = fonts["flag"] if cell.is_flagged else fonts["mine"]
            elif cell.is_flagged:
                fill = colours["hover"] if hovered else colours["hidden"]
                outline = (
                    colours["hover_outline"] if hovered else colours["hidden_border"]
                )
                border_width = (
                    sizes["hover_width"] if hovered else sizes["border_width"]
                )
                text = "⚑"
                text_font = fonts["flag"]
                if self.board.state is GameState.LOST and not cell.is_mine:
                    # A wrong flag is shown crossed out in amber.
                    text_colour = colours["wrong_flag"]
                    crossed_flag = True
                else:
                    text_colour = colours["flag"]
            else:
                fill = colours["hover"] if hovered else colours["hidden"]
                outline = (
                    colours["hover_outline"] if hovered else colours["hidden_border"]
                )
                border_width = (
                    sizes["hover_width"] if hovered else sizes["border_width"]
                )

        self.canvas.create_rectangle(
            x0,
            y0,
            x1,
            y1,
            fill=fill,
            outline=outline,
            width=border_width,
            tags=(tag,),
        )

        # Subtle raised effect on covered cells: a light top/left edge.
        if fill == colours["hidden"]:
            inset = sizes["raised_inset"]
            self.canvas.create_line(
                x0 + inset,
                y0 + inset,
                x1 - inset,
                y0 + inset,
                fill=colours["hidden_highlight"],
                width=sizes["raised_line_width"],
                tags=(tag,),
            )
            self.canvas.create_line(
                x0 + inset,
                y0 + inset,
                x0 + inset,
                y1 - inset,
                fill=colours["hidden_highlight"],
                width=sizes["raised_line_width"],
                tags=(tag,),
            )

        if show_glow:
            radius = sizes["mine_glow_radius"]
            self.canvas.create_oval(
                centre_x - radius,
                centre_y - radius,
                centre_x + radius,
                centre_y + radius,
                fill=colours["mine_glow"],
                outline="",
                tags=(tag,),
            )

        if text:
            self.canvas.create_text(
                centre_x,
                centre_y,
                text=text,
                fill=text_colour,
                font=text_font,
                tags=(tag,),
            )

        if crossed_flag:
            inset = sizes["wrong_flag_inset"]
            width = sizes["wrong_flag_width"]
            self.canvas.create_line(
                x0 + inset,
                y0 + inset,
                x1 - inset,
                y1 - inset,
                fill=colours["wrong_flag"],
                width=width,
                tags=(tag,),
            )
            self.canvas.create_line(
                x1 - inset,
                y0 + inset,
                x0 + inset,
                y1 - inset,
                fill=colours["wrong_flag"],
                width=width,
                tags=(tag,),
            )

    # Algorithmic Thinking: a short non-blocking after() flash.
    def _flash_cell(
        self,
        row: int,
        col: int,
        colour: str,
        fill: bool = False,
    ) -> None:
        """Short click-feedback flash drawn above a cell."""
        size = self.cell_size
        pad = THEME["sizes"]["grid_pad"]
        flash_inset = THEME["sizes"]["flash_inset"]
        x0 = pad + col * size
        y0 = pad + row * size
        x1 = x0 + size
        y1 = y0 + size

        if fill:
            item = self.canvas.create_rectangle(
                x0 + flash_inset,
                y0 + flash_inset,
                x1 - flash_inset,
                y1 - flash_inset,
                fill=colour,
                outline=colour,
                stipple="gray50",
                tags=("flash",),
            )
        else:
            item = self.canvas.create_rectangle(
                x0 + flash_inset,
                y0 + flash_inset,
                x1 - flash_inset,
                y1 - flash_inset,
                outline=colour,
                width=THEME["sizes"]["hover_width"],
                tags=("flash",),
            )

        self.root.after(
            THEME["timing"]["flash_ms"],
            lambda: self.canvas.delete(item),
        )

    # ================================================================== #
    #  Hover and mouse events
    # ================================================================== #
    # Pattern Recognition: hover uses the same pixel-to-cell mapping.
    def _on_motion(self, event: tk.Event) -> None:
        """Highlight the hidden cell under the cursor with a cyan outline."""
        if self.board is None or self.board.state is not GameState.PLAYING:
            return
        cell = self._event_cell(event)
        if cell == self._hover:
            return

        old_hover = self._hover
        self._hover = cell
        if old_hover is not None:
            self._draw_cell(*old_hover)
        if cell is not None:
            self._draw_cell(*cell)

    # Pattern Recognition: clear the previous hover cell.
    def _on_leave(self, _event: tk.Event) -> None:
        """Remove the hover highlight when the pointer leaves the grid."""
        if self._hover is not None:
            old_hover = self._hover
            self._hover = None
            self._draw_cell(*old_hover)

    # Abstraction: the view only changes the face on press.
    def _on_left_press(self, event: tk.Event) -> None:
        """Show the surprised face while the mouse button is held down."""
        if self.board is None or self.board.state is not GameState.PLAYING:
            return
        if self._animating:
            return
        cell = self._event_cell(event)
        if cell is None:
            return
        self._pressed_cell = cell
        self._refresh_face()

    # Abstraction: delegate the actual reveal to the model.
    def _on_left_release(self, event: tk.Event) -> None:
        """Reveal the cell if press and release happened on the same cell."""
        pressed = self._pressed_cell
        self._pressed_cell = None
        cell = self._event_cell(event)
        if pressed is not None and cell == pressed:
            self._left_click(*cell)
        self._refresh_face()

    # Decomposition: model reveal first, view animation second.
    def _left_click(self, row: int, col: int) -> None:
        """Delegate a left click to the Board and animate the result."""
        if self.board is None or self.board.state is not GameState.PLAYING:
            return
        if self._animating:
            return

        cell = self.board.board[row][col]
        if cell.is_revealed or cell.is_flagged:
            return

        waves = self.board.reveal(row, col)
        self._after_board_change(waves, flash_cell=(row, col))

    # Abstraction: delegate flagging to Board.toggle_flag.
    def _on_right_click(self, event: tk.Event) -> None:
        """Delegate a right click to Board.toggle_flag."""
        if self.board is None or self.board.state is not GameState.PLAYING:
            return
        if self._animating:
            return
        cell = self._event_cell(event)
        if cell is None:
            return

        if self.board.toggle_flag(*cell):
            self._draw_cell(*cell)
            self._flash_cell(*cell, THEME["colours"]["flag"])
            self._update_hud()
            self._refresh_face()

    # Abstraction: delegate chording to Board.chord.
    def _on_middle_click(self, event: tk.Event) -> None:
        """Middle click performs a chord on a revealed number."""
        cell = self._event_cell(event)
        if cell is not None:
            self._chord(*cell)

    # Pattern Recognition: an alternate chord gesture.
    def _on_double_click(self, event: tk.Event) -> None:
        """Double-clicking a revealed number also performs a chord."""
        cell = self._event_cell(event)
        if cell is not None:
            self._chord(*cell)

    # Logical Reasoning: the Board decides whether flags match.
    def _chord(self, row: int, col: int) -> None:
        """Ask the Board for a chord reveal, then animate it."""
        if self.board is None or self.board.state is not GameState.PLAYING:
            return
        if self._animating:
            return

        cell = self.board.board[row][col]
        if not cell.is_revealed or cell.adjacent_mines == 0:
            return

        waves = self.board.chord(row, col)
        if waves:
            self._after_board_change(waves, flash_cell=(row, col))

    # ================================================================== #
    #  Board result handling
    # ================================================================== #
    # Decomposition: choose the loss, win or playing animation.
    def _after_board_change(
        self,
        waves: list[list[tuple[int, int]]],
        flash_cell: tuple[int, int] | None,
    ) -> None:
        """Update the HUD, start the timer, and choose the right animation."""
        if self.board is None:
            return

        self._start_timer_if_needed()
        self._update_hud()

        if self.board.state is GameState.LOST:
            self._stop_timer()
            self._animate_loss()
            return

        if self.board.state is GameState.WON:
            # Stop the clock at the winning move, then let the last wave play.
            self._stop_timer()
            elapsed = self._elapsed_seconds()
            self._animate_waves(
                waves,
                on_done=lambda: self._finish_win(elapsed),
                flash_cell=flash_cell,
            )
            return

        # Algorithmic Thinking: callback after the final reveal wave.
        def after_waves() -> None:
            """Refresh the face and counter once the animation is complete."""
            self._refresh_face()
            self._update_hud()

        self._animate_waves(waves, on_done=after_waves, flash_cell=flash_cell)

    # Algorithmic Thinking: after() chain over pre-computed BFS waves.
    def _animate_waves(
        self,
        waves: list[list[tuple[int, int]]],
        on_done: Callable[[], None],
        flash_cell: tuple[int, int] | None = None,
    ) -> None:
        """Animate a reveal in expanding BFS layers.

        The Board has already computed the full result; this method only
        reveals the pre-computed layers gradually.  ``root.after`` keeps the
        UI responsive, and the generation counter cancels old animations after
        a restart.
        """
        generation = self._generation
        self._animating = True

        if not waves:
            self._animating = False
            on_done()
            return

        # Algorithmic Thinking: schedule each wave without blocking the UI.
        def show_wave(index: int) -> None:
            """Draw one BFS wave and schedule the next one."""
            if generation != self._generation:
                return
            if index >= len(waves):
                self._animating = False
                on_done()
                return

            for row, col in waves[index]:
                self._draw_cell(row, col)
                if index == 0 and flash_cell == (row, col):
                    self._flash_cell(row, col, THEME["colours"]["accent"])

            self._update_hud()
            self.root.after(
                THEME["timing"]["flood_wave_ms"],
                lambda: show_wave(index + 1),
            )

        show_wave(0)

    # Algorithmic Thinking: reveal mines one-by-one with after().
    def _animate_loss(self) -> None:
        """Reveal mines one-by-one with red flashes, then shake the window."""
        if self.board is None:
            return

        generation = self._generation
        self._animating = True
        self._refresh_face()
        self._render_all(hide_mines=True)

        mines = list(self.board.mine_set)
        exploded = self.board.exploded_cell
        # Put the clicked mine first, then use coordinates for a stable order.
        mines.sort(key=lambda position: (position != exploded, position))

        # Algorithmic Thinking: schedule the next mine reveal.
        def show_mine(index: int) -> None:
            """Reveal one mine, flash it red, then schedule the next."""
            if generation != self._generation:
                return
            if index >= len(mines):
                self._animating = False
                self._finish_loss()
                return

            row, col = mines[index]
            self._draw_cell(row, col)
            self._flash_cell(row, col, THEME["colours"]["mine"], fill=True)
            self.root.after(
                THEME["timing"]["mine_reveal_ms"],
                lambda: show_mine(index + 1),
            )

        show_mine(0)

    # Logical Reasoning: final loss state, colours and shake.
    def _finish_loss(self) -> None:
        """Show the final loss state and shake the window."""
        if self.board is None or self.board.state is not GameState.LOST:
            return
        self._render_all()
        self._set_status()
        self._refresh_face()
        self._update_hud()
        self.score_var.set("Score: 0")
        self._shake_window(self._generation)

    # Logical Reasoning: final win state, best time and overlay.
    def _finish_win(self, elapsed: int) -> None:
        """Reveal green mines, record the best time, pulse and show overlay."""
        if self.board is None or self.board.state is not GameState.WON:
            return

        self._render_all()
        self._set_status()
        self._refresh_face()
        self._update_hud()

        is_new_best = self._record_best(elapsed)
        self._update_best_label()

        score = self._calculate_score(elapsed)
        self.score_var.set(f"Score: {score}")

        self._pulse_status(self._generation, THEME["timing"]["pulse_cycles"])

        generation = self._generation
        self.root.after(
            THEME["timing"]["win_overlay_delay_ms"],
            lambda: self._show_win_overlay(
                elapsed,
                score,
                is_new_best,
                generation,
            ),
        )

    # ================================================================== #
    #  Timer, score and best time
    # ================================================================== #
    # Algorithmic Thinking: start the clock on the first reveal.
    def _start_timer_if_needed(self) -> None:
        """Start the live timer on the first reveal, not before."""
        if self.board is None or self._timer_started:
            return
        if not self.board.first_click_made:
            return

        self._timer_started = True
        self._start_time = time.monotonic()
        self._end_time = None
        self._tick_timer(self._generation)

    # Algorithmic Thinking: repeating after() timer loop.
    def _tick_timer(self, generation: int) -> None:
        """Update the LED timer every 200 ms while the game is playing."""
        if generation != self._generation or not self._timer_started:
            return

        self.timer_var.set(self._format_led(self._elapsed_seconds()))

        if self.board is not None and self.board.state is GameState.PLAYING:
            self._timer_job = self.root.after(
                THEME["timing"]["timer_tick_ms"],
                lambda: self._tick_timer(generation),
            )
        else:
            self._stop_timer()

    # Algorithmic Thinking: freeze the elapsed time.
    def _stop_timer(self) -> None:
        """Stop the timer and freeze the displayed value."""
        if self._start_time is None:
            return
        if self._end_time is None:
            self._end_time = time.monotonic()
        self._timer_started = False
        if self._timer_job is not None:
            try:
                self.root.after_cancel(self._timer_job)
            except tk.TclError:
                pass
            self._timer_job = None
        self.timer_var.set(self._format_led(self._elapsed_seconds()))

    # Maths: difference of monotonic clock readings.
    def _elapsed_seconds(self) -> int:
        """Whole seconds elapsed since the first reveal."""
        if self._start_time is None:
            return 0
        end = self._end_time if self._end_time is not None else time.monotonic()
        return max(0, int(end - self._start_time))

    # Maths: fixed-width integer formatting for the LED display.
    def _format_led(self, value: int) -> str:
        """Format an LED number with the configured number of digits."""
        maximum = THEME["sizes"]["max_led_seconds"]
        digits = THEME["sizes"]["led_digits"]
        clamped = min(max(0, value), maximum)
        return f"{clamped:0{digits}d}"

    # Maths: keep the minimum time per difficulty.
    def _record_best(self, elapsed: int) -> bool:
        """Record the best time for the current difficulty; return True if new."""
        key = (self.rows, self.cols, self.num_mines)
        previous = self.best_times.get(key)
        if previous is None or elapsed < previous:
            self.best_times[key] = elapsed
            return True
        return False

    # Abstraction: show the session record for this board.
    def _update_best_label(self) -> None:
        """Show the session best for the current difficulty."""
        best = self.best_times.get((self.rows, self.cols, self.num_mines))
        if best is None:
            self.best_var.set("Best: --")
        else:
            self.best_var.set(f"Best: {best}s")

    # Maths: linear score formula based on mines and seconds.
    def _calculate_score(self, elapsed: int) -> int:
        """Optional score: 100 points per mine minus a small time penalty."""
        if self.board is None:
            return 0
        return max(0, self.board.num_mines * 100 - elapsed * 3)

    # ================================================================== #
    #  Status, face and HUD
    # ================================================================== #
    # Abstraction: synchronise the LED with the model counter.
    def _update_hud(self) -> None:
        """Refresh the mines-remaining LED from the Board's counter."""
        if self.board is None:
            return
        self.mines_var.set(self._format_led(self.board.flags_remaining))

    # Abstraction: map game state to text and colour.
    def _set_status(self) -> None:
        """Update the status line and its colour from the game state."""
        if self.board is None:
            return
        colours = THEME["colours"]
        self.status_var.set(self.board.status_text)
        colour = {
            GameState.PLAYING: colours["status_playing"],
            GameState.WON: colours["status_won"],
            GameState.LOST: colours["status_lost"],
        }[self.board.state]
        self.status_label.config(fg=colour)

    # Abstraction: map game state to the restart face.
    def _refresh_face(self) -> None:
        """Set the restart face: 🙂 playing, 😮 held, 😵 lost, 😎 won."""
        if self.board is None:
            face = "🙂"
        elif self.board.state is GameState.WON:
            face = "😎"
        elif self.board.state is GameState.LOST:
            face = "😵"
        elif self._pressed_cell is not None:
            face = "😮"
        else:
            face = "🙂"
        self.face_button.config(text=face)

    # Algorithmic Thinking: non-blocking status pulse.
    def _pulse_status(self, generation: int, cycles: int) -> None:
        """Pulse the win status colour using non-blocking after callbacks."""
        if generation != self._generation or self.board is None:
            return
        if self.board.state is not GameState.WON:
            return
        if cycles <= 0:
            self._set_status()
            return

        colours = THEME["colours"]
        current = self.status_label.cget("fg")
        self.status_label.config(
            fg=(
                colours["accent"]
                if current == colours["status_won"]
                else colours["status_won"]
            )
        )
        self._pulse_job = self.root.after(
            THEME["timing"]["pulse_ms"],
            lambda: self._pulse_status(generation, cycles - 1),
        )

    # ================================================================== #
    #  Win overlay and screen shake
    # ================================================================== #
    # Decomposition: build the win overlay from labels and a button.
    def _show_win_overlay(
        self,
        elapsed: int,
        score: int,
        is_new_best: bool,
        generation: int,
    ) -> None:
        """Show a dark overlay with time, score and a play-again button."""
        if generation != self._generation or self.board is None:
            return
        if self.board.state is not GameState.WON:
            return
        if self._win_overlay is not None:
            self._win_overlay.destroy()

        colours = THEME["colours"]
        sizes = THEME["sizes"]
        fonts = THEME["fonts"]

        overlay = tk.Frame(
            self.canvas,
            bg=colours["overlay_bg"],
            highlightbackground=colours["overlay_border"],
            highlightthickness=sizes["overlay_border_width"],
            padx=sizes["overlay_pad"],
            pady=sizes["overlay_pad"],
        )

        tk.Label(
            overlay,
            text="YOU WIN!",
            bg=colours["overlay_bg"],
            fg=colours["win_green"],
            font=fonts["title"],
        ).pack(pady=(0, sizes["overlay_gap"]))

        tk.Label(
            overlay,
            text=f"Time: {elapsed}s   ·   Score: {score}",
            bg=colours["overlay_bg"],
            fg=colours["text"],
            font=fonts["overlay"],
        ).pack(pady=(0, sizes["overlay_gap"]))

        if is_new_best:
            best_text = "New best time for this difficulty!"
        else:
            best = self.best_times.get((self.rows, self.cols, self.num_mines))
            best_text = f"Session best: {best}s"
        tk.Label(
            overlay,
            text=best_text,
            bg=colours["overlay_bg"],
            fg=colours["accent"],
            font=fonts["ui_bold"],
        ).pack(pady=(0, sizes["overlay_gap"]))

        tk.Button(
            overlay,
            text="PLAY AGAIN",
            command=self._restart,
            bg=colours["accent"],
            fg=colours["window_bg"],
            activebackground=colours["accent_dark"],
            activeforeground=colours["text"],
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=fonts["button"],
            padx=sizes["difficulty_pad_x"],
            pady=sizes["difficulty_pad_y"],
            cursor="hand2",
        ).pack()

        overlay.place(relx=0.5, rely=0.5, anchor="center")
        self._win_overlay = overlay

    # Algorithmic Thinking: after() chain for the screen shake.
    def _shake_window(self, generation: int) -> None:
        """Briefly offset the window left/right after a loss."""
        if generation != self._generation:
            return

        base_x = self.root.winfo_x()
        base_y = self.root.winfo_y()
        offsets = THEME["timing"]["shake_offsets"]

        # Algorithmic Thinking: apply one shake offset, then schedule the next.
        def step(index: int) -> None:
            """Apply one horizontal offset and restore the window at the end."""
            if generation != self._generation:
                return
            if index >= len(offsets):
                self.root.geometry(f"+{base_x}+{base_y}")
                return
            self.root.geometry(f"+{base_x + offsets[index]}+{base_y}")
            self.root.after(
                THEME["timing"]["shake_step_ms"],
                lambda: step(index + 1),
            )

        step(0)

    # ================================================================== #
    #  Custom difficulty dialog
    # ================================================================== #
    # Abstraction: one entry point for custom settings.
    def _open_custom_dialog(self) -> None:
        """Open a styled, validated custom-board dialog."""
        if self._custom_dialog is not None:
            try:
                if self._custom_dialog.winfo_exists():
                    self._custom_dialog.lift()
                    self._custom_dialog.focus_set()
                    return
            except tk.TclError:
                pass
        self._custom_dialog = CustomGameDialog(self)

    # ================================================================== #
    #  Cleanup and quit
    # ================================================================== #
    # Algorithmic Thinking: cancel pending timer and pulse callbacks.
    def _cancel_jobs(self) -> None:
        """Cancel pending timer and pulse jobs (animations use generation)."""
        for attribute in ("_timer_job", "_pulse_job"):
            job = getattr(self, attribute)
            if job is not None:
                try:
                    self.root.after_cancel(job)
                except tk.TclError:
                    pass
                setattr(self, attribute, None)

    # Abstraction: clean application exit.
    def _quit(self) -> None:
        """Close the Tk window and end the event loop."""
        self.root.destroy()


class CustomGameDialog(tk.Toplevel):
    """A small dark dialog for entering rows, columns and mines."""

    # Decomposition: wire the model, view state and theme together.
    def __init__(self, app: MinesweeperGUI) -> None:
        """Build the dark custom-difficulty dialog."""
        super().__init__(app.root)
        self.app = app

        colours = THEME["colours"]
        sizes = THEME["sizes"]
        fonts = THEME["fonts"]

        self.title("Custom difficulty")
        self.configure(bg=colours["window_bg"])
        self.resizable(False, False)
        self.transient(app.root)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        container = tk.Frame(self, bg=colours["window_bg"])
        container.pack(padx=sizes["dialog_pad"], pady=sizes["dialog_pad"])

        tk.Label(
            container,
            text="Custom game",
            bg=colours["window_bg"],
            fg=colours["accent"],
            font=fonts["title"],
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, sizes["dialog_gap"]))

        self.rows_var = tk.StringVar(master=self, value=str(app.rows))
        self.cols_var = tk.StringVar(master=self, value=str(app.cols))
        self.mines_var = tk.StringVar(master=self, value=str(app.num_mines))

        self.rows_entry = self._add_field(
            container,
            row=1,
            label=(
                f"Rows ({sizes['custom_min']}–{sizes['custom_max']})"
            ),
            variable=self.rows_var,
        )
        self.cols_entry = self._add_field(
            container,
            row=2,
            label=(
                f"Columns ({sizes['custom_min']}–{sizes['custom_max']})"
            ),
            variable=self.cols_var,
        )
        self.mines_entry = self._add_field(
            container,
            row=3,
            label="Mines (at least 1)",
            variable=self.mines_var,
        )

        self.error_label = tk.Label(
            container,
            text="",
            bg=colours["window_bg"],
            fg=colours["status_lost"],
            font=fonts["ui"],
            wraplength=sizes["dialog_wrap"],
            justify="left",
        )
        self.error_label.grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(sizes["dialog_gap"], 0),
        )

        button_row = tk.Frame(container, bg=colours["window_bg"])
        button_row.grid(
            row=5,
            column=0,
            columnspan=2,
            sticky="e",
            pady=(sizes["dialog_gap"], 0),
        )

        tk.Button(
            button_row,
            text="Cancel",
            command=self._cancel,
            bg=colours["button_bg"],
            fg=colours["text"],
            activebackground=colours["button_hover"],
            activeforeground=colours["text"],
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=fonts["button"],
            padx=sizes["difficulty_pad_x"],
            pady=sizes["difficulty_pad_y"],
            cursor="hand2",
        ).pack(side="left", padx=(0, sizes["difficulty_gap"]))

        tk.Button(
            button_row,
            text="Start",
            command=self._submit,
            bg=colours["accent"],
            fg=colours["window_bg"],
            activebackground=colours["accent_dark"],
            activeforeground=colours["text"],
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=fonts["button"],
            padx=sizes["difficulty_pad_x"],
            pady=sizes["difficulty_pad_y"],
            cursor="hand2",
        ).pack(side="left")

        self.bind("<Return>", lambda _event: self._submit())
        self.bind("<Escape>", lambda _event: self._cancel())

        self.update_idletasks()
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        x = app.root.winfo_x() + (app.root.winfo_width() - width) // 2
        y = app.root.winfo_y() + (app.root.winfo_height() - height) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

        self.rows_entry.focus_set()
        self.rows_entry.select_range(0, "end")

    # Pattern Recognition: the same dark entry style for each field.
    def _add_field(
        self,
        parent: tk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
    ) -> tk.Entry:
        """Add a labelled dark entry widget to the dialog grid."""
        colours = THEME["colours"]
        sizes = THEME["sizes"]
        fonts = THEME["fonts"]

        tk.Label(
            parent,
            text=label,
            bg=colours["window_bg"],
            fg=colours["text"],
            font=fonts["ui"],
        ).grid(row=row, column=0, sticky="w", pady=(0, sizes["dialog_field_gap"]))

        entry = tk.Entry(
            parent,
            textvariable=variable,
            width=sizes["entry_width"],
            justify="center",
            bg=colours["hidden"],
            fg=colours["text"],
            insertbackground=colours["accent"],
            relief="flat",
            bd=0,
            highlightthickness=sizes["entry_border_width"],
            highlightbackground=colours["hidden_border"],
            highlightcolor=colours["accent"],
            font=fonts["ui_bold"],
        )
        entry.grid(
            row=row,
            column=1,
            sticky="e",
            padx=(sizes["dialog_gap"], 0),
            pady=(0, sizes["dialog_field_gap"]),
        )
        return entry

    # Logical Reasoning: validate rows, columns and mines before starting.
    def _submit(self) -> None:
        """Validate all three fields before starting a custom game."""
        sizes = THEME["sizes"]
        minimum = sizes["custom_min"]
        maximum = sizes["custom_max"]

        try:
            rows = int(self.rows_var.get().strip())
            cols = int(self.cols_var.get().strip())
            mines = int(self.mines_var.get().strip())
        except ValueError:
            self.error_label.config(text="Rows, columns and mines must be whole numbers.")
            return

        if not minimum <= rows <= maximum:
            self.error_label.config(
                text=f"Rows must be between {minimum} and {maximum}."
            )
            return
        if not minimum <= cols <= maximum:
            self.error_label.config(
                text=f"Columns must be between {minimum} and {maximum}."
            )
            return

        maximum_mines = rows * cols - 1
        if not 1 <= mines <= maximum_mines:
            self.error_label.config(
                text=f"Mines must be between 1 and {maximum_mines} for {rows}×{cols}."
            )
            return

        self.app._custom_dialog = None
        self.destroy()
        self.app.start_custom_game(rows, cols, mines)

    # Abstraction: close the dialog without changing the game.
    def _cancel(self) -> None:
        """Close the dialog and release the application's dialog reference."""
        self.app._custom_dialog = None
        self.destroy()
