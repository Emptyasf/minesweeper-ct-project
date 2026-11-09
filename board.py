"""
board.py
========

All Minesweeper rules live here.  There is **no Tkinter code in this file**,
which is the key separation of concerns for the project.

The model is a two-dimensional list of :class:`Cell` objects:

    board[row][col] -> Cell

Mathematics used in this module
-------------------------------
* Matrix indexing: a grid is an M x N matrix.  A cell is identified by its
  row and column, and both start at 0.
* Coordinate geometry: the eight neighbours of (r, c) are produced by adding
  every combination of -1, 0 and +1 to the coordinates, except (0, 0).
* Counting: for a safe cell,

      Number(r, c) = count of mines in its valid 8 neighbours.

* Sets: mine positions are stored as a set of (row, col) tuples.  A set
  cannot contain duplicates, which is exactly the property we need for
  unique mine placement.
* Graph search: a zero region is explored with breadth-first search (BFS)
  using a queue.  BFS is iterative, so it avoids Python's recursion limit and
  naturally produces expanding "waves" for the GUI animation.
* Boolean logic: the win condition is the single Boolean test

      revealed_count == rows * cols - num_mines

CT pillars demonstrated
-----------------------
* Decomposition: board creation, mine placement, neighbour finding, counting,
  reveal, flagging, chording and win/loss detection are separate methods.
* Pattern recognition: every cell uses the same eight-offset neighbour rule.
* Abstraction: the GUI only sees a Board and Cell; it never calculates rules.
* Algorithmic thinking: placement loop, BFS flood fill, win/loss state machine.
* Logical reasoning: flags, safe first click, chord conditions and the win
  condition are all expressed as precise Boolean rules.
"""

from __future__ import annotations

import random
from collections import deque
from enum import Enum
from typing import Iterable

from cell import Cell

# A coordinate is a (row, column) pair.
Coordinate = tuple[int, int]

# A grid is a 2D list of Cell objects.
Grid = list[list[Cell]]


class GameState(Enum):
    """The three possible states of a game.

    The enum values are also the strings shown in the GUI status line.
    """

    PLAYING = "Playing"
    WON = "You Win!"
    LOST = "Game Over"


class Board:
    """The complete Minesweeper game model.

    Parameters
    ----------
    rows:
        Number of rows (M).
    cols:
        Number of columns (N).
    num_mines:
        Number of mines.  At least one cell must remain safe, therefore
        1 <= num_mines <= rows * cols - 1.
    seed:
        Optional integer seed for the random generator.  Tests use this to
        make mine placement reproducible; the real game leaves it as None.
    """

    # Pattern Recognition: every cell is checked with the same eight offsets.
    # The (0, 0) offset is intentionally absent because a cell is not its
    # own neighbour.
    _OFFSETS: tuple[Coordinate, ...] = (
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1),
    )

    # ------------------------------------------------------------------ #
    # Construction
    # ------------------------------------------------------------------ #
    # Decomposition: build the model from independent parts.
    def __init__(
        self,
        rows: int,
        cols: int,
        num_mines: int,
        seed: int | None = None,
    ) -> None:
        """Create the cell matrix, place mines and calculate all numbers."""
        self._validate_configuration(rows, cols, num_mines)

        self.rows = rows
        self.cols = cols
        self.num_mines = num_mines

        # A private Random instance makes the model testable without changing
        # the global random state used by other programs.
        self._random = random.Random(seed)

        # Abstraction: the rest of the program thinks in Cell objects, not in
        # separate lists of booleans.
        self.board: Grid = [
            [Cell() for _ in range(cols)]
            for _ in range(rows)
        ]

        # A set guarantees uniqueness: adding the same coordinate twice does
        # not create a second mine.
        self.mine_set: set[Coordinate] = set()

        self.state: GameState = GameState.PLAYING
        self.first_click_made: bool = False
        self.revealed_count: int = 0
        self.flags_remaining: int = num_mines
        self.exploded_cell: Coordinate | None = None

        self._place_mines_randomly()
        self._recalculate_adjacent_counts()

    # Logical Reasoning: reject impossible board settings.
    @staticmethod
    def _validate_configuration(rows: int, cols: int, num_mines: int) -> None:
        """Logical reasoning: reject configurations that cannot be played."""
        if not isinstance(rows, int) or not isinstance(cols, int):
            raise TypeError("rows and cols must be integers")
        if not isinstance(num_mines, int):
            raise TypeError("num_mines must be an integer")

        if rows <= 0 or cols <= 0:
            raise ValueError("rows and cols must be positive")

        # The first click must always be safe, so at least one non-mine cell
        # has to exist.  rows * cols - 1 is therefore the maximum.
        maximum_mines = rows * cols - 1
        if not 1 <= num_mines <= maximum_mines:
            raise ValueError(
                f"num_mines must be between 1 and {maximum_mines} "
                f"for a {rows}x{cols} board"
            )

    # Abstraction: a testable factory for known mine layouts.
    @classmethod
    def from_mine_positions(
        cls,
        rows: int,
        cols: int,
        positions: Iterable[Coordinate],
        seed: int | None = None,
    ) -> "Board":
        """Build a board with known mine positions (used heavily by tests).

        This is a small factory method: it creates a normal board and then
        replaces the random layout with the supplied set.  The board still
        validates the positions, so tests cannot accidentally create an
        invalid layout.
        """
        position_list = list(positions)
        board = cls(rows, cols, len(position_list), seed=seed)
        board.set_mine_positions(position_list)
        return board

    # ------------------------------------------------------------------ #
    # Mine placement
    # ------------------------------------------------------------------ #
    # Algorithmic Thinking: loop and set until the mine count is reached.
    def _place_mines_randomly(self) -> None:
        """Place unique mines using random coordinates.

        Algorithmic thinking: a while loop keeps drawing coordinates until the
        set has exactly ``num_mines`` members.  Because a set ignores repeated
        coordinates, the loop automatically guarantees uniqueness.
        """
        all_positions: list[Coordinate] = [
            (row, col)
            for row in range(self.rows)
            for col in range(self.cols)
        ]

        while len(self.mine_set) < self.num_mines:
            self.mine_set.add(self._random.choice(all_positions))

        for row, col in self.mine_set:
            self.board[row][col].is_mine = True

    # Abstraction: replace the layout through one validated interface.
    def set_mine_positions(self, positions: Iterable[Coordinate]) -> None:
        """Replace the layout with known mine positions and reset the game.

        This is useful for unit tests and for demonstrating a hand-built
        board.  It validates that the number of positions equals
        ``num_mines`` and that every position is unique and inside the grid.
        """
        position_list = list(positions)

        if len(position_list) != self.num_mines:
            raise ValueError(
                f"expected {self.num_mines} mine positions, "
                f"got {len(position_list)}"
            )
        if len(set(position_list)) != len(position_list):
            raise ValueError("mine positions must be unique")
        for row, col in position_list:
            if not self.in_bounds(row, col):
                raise ValueError(f"mine position {(row, col)} is outside the board")

        # Clear every cell before applying the new layout.
        for row in range(self.rows):
            for col in range(self.cols):
                cell = self.board[row][col]
                cell.is_mine = False
                cell.is_revealed = False
                cell.is_flagged = False
                cell.adjacent_mines = 0

        self.mine_set = set(position_list)
        for row, col in self.mine_set:
            self.board[row][col].is_mine = True

        self.state = GameState.PLAYING
        self.first_click_made = False
        self.revealed_count = 0
        self.flags_remaining = self.num_mines
        self.exploded_cell = None
        self._recalculate_adjacent_counts()

    # Logical Reasoning: the first click must always be safe.
    def _make_first_click_safe(self, row: int, col: int) -> None:
        """Guarantee that the first revealed cell is not a mine.

        If the player's first click lands on a mine, that mine is removed from
        its old position and moved to a random safe position.  All adjacent
        counts are then recalculated because the move changes the numbers
        around both the old and the new location.
        """
        if self.first_click_made:
            return

        self.first_click_made = True
        clicked_cell = self.board[row][col]

        if not clicked_cell.is_mine:
            return

        # Remove the mine from the clicked coordinate.
        self.mine_set.remove((row, col))
        clicked_cell.is_mine = False

        # Every cell except the clicked cell and the remaining mines is a
        # valid new home.  There is always at least one candidate because the
        # configuration allows at most rows * cols - 1 mines.
        candidates: list[Coordinate] = [
            (candidate_row, candidate_col)
            for candidate_row in range(self.rows)
            for candidate_col in range(self.cols)
            if (candidate_row, candidate_col) not in self.mine_set
            and (candidate_row, candidate_col) != (row, col)
        ]
        new_row, new_col = self._random.choice(candidates)
        self.mine_set.add((new_row, new_col))
        self.board[new_row][new_col].is_mine = True

        # The number on a cell depends on mine positions, so recalculate.
        self._recalculate_adjacent_counts()

    # ------------------------------------------------------------------ #
    # Neighbours and counting
    # ------------------------------------------------------------------ #
    # Pattern Recognition: one boundary rule for every coordinate.
    def in_bounds(self, row: int, col: int) -> bool:
        """Return True when (row, col) lies inside the matrix."""
        return 0 <= row < self.rows and 0 <= col < self.cols

    # Pattern Recognition: same eight offsets for every cell.
    def get_neighbours(self, row: int, col: int) -> list[Coordinate]:
        """Return all valid neighbours of (row, col).

        Pattern Recognition: the same eight offsets are applied to every
        cell.  The boundary check removes offsets that fall outside the
        matrix.

        A corner has 3 neighbours, a non-corner edge cell has 5, and an
        interior cell has 8.
        """
        if not self.in_bounds(row, col):
            raise IndexError(f"cell {(row, col)} is outside the board")

        neighbours: list[Coordinate] = []
        for delta_row, delta_col in self._OFFSETS:
            neighbour_row = row + delta_row
            neighbour_col = col + delta_col
            if self.in_bounds(neighbour_row, neighbour_col):
                neighbours.append((neighbour_row, neighbour_col))
        return neighbours

    # Pattern Recognition + Maths: finite sum over valid neighbours.
    def count_adjacent_mines(self, row: int, col: int) -> int:
        """Count mines in the valid neighbours of a cell.

        Formula:
            Number(r, c) = count of mines in valid 8 neighbours.
        """
        return sum(
            1
            for neighbour_row, neighbour_col in self.get_neighbours(row, col)
            if self.board[neighbour_row][neighbour_col].is_mine
        )

    # Algorithmic Thinking: one linear scan refreshes every number.
    def _recalculate_adjacent_counts(self) -> None:
        """Refresh ``adjacent_mines`` for every safe cell.

        Algorithmic thinking: one nested loop visits every matrix position.
        Complexity is O(rows * cols * 8) = O(rows * cols), because each cell
        has at most eight neighbours.
        """
        for row in range(self.rows):
            for col in range(self.cols):
                cell = self.board[row][col]
                if cell.is_mine:
                    # A mine does not display a number.
                    cell.adjacent_mines = 0
                else:
                    cell.adjacent_mines = self.count_adjacent_mines(row, col)

    # ------------------------------------------------------------------ #
    # Revealing
    # ------------------------------------------------------------------ #
    # Decomposition + Logical Reasoning: the rule pipeline for one click.
    def reveal(self, row: int, col: int) -> list[list[Coordinate]]:
        """Reveal a cell and return the animation waves.

        Rules
        -----
        1. Ignore already revealed cells, flagged cells, and finished games.
        2. Make the very first reveal safe by moving a mine if necessary.
        3. If the cell is a mine -> lose and reveal all mines.
        4. If the cell has a positive number -> reveal only that cell.
        5. If the cell is zero -> flood fill the zero region.

        The return value is a list of waves.  Each wave is a list of
        coordinates that were revealed at the same BFS distance.  The GUI uses
        this to animate expanding rings without knowing any game rules.
        """
        if not self.in_bounds(row, col):
            raise IndexError(f"cell {(row, col)} is outside the board")
        if self.state is not GameState.PLAYING:
            return []

        cell = self.board[row][col]

        # Logical reasoning: a flag is a promise from the player.  Revealing
        # a flagged cell is ignored, and an already open cell cannot be
        # opened twice.
        if cell.is_revealed or cell.is_flagged:
            return []

        if not self.first_click_made:
            self._make_first_click_safe(row, col)
            # Re-fetch because the same Cell object remains in the matrix.
            cell = self.board[row][col]

        if cell.is_mine:
            self.exploded_cell = (row, col)
            self.state = GameState.LOST
            self._reveal_all_mines()
            return []

        # Safe reveal.  A numbered cell is a boundary of a zero region, so it
        # stops the flood fill immediately.
        if cell.adjacent_mines > 0:
            cell.is_revealed = True
            self.revealed_count += 1
            waves: list[list[Coordinate]] = [[(row, col)]]
        else:
            waves = self._flood_fill_zero_region(row, col)

        # Boolean logic: check the single win condition after every safe move.
        self._check_for_win()
        return waves

    # Algorithmic Thinking: iterative BFS produces the expanding waves.
    def _flood_fill_zero_region(
        self,
        start_row: int,
        start_col: int,
    ) -> list[list[Coordinate]]:
        """Open a connected zero region with iterative BFS.

        Algorithmic thinking: a queue stores zero cells that still need to be
        expanded.  Each expansion reveals the zero cell's hidden, unflagged
        neighbours.  Numbered neighbours are revealed but not queued, which
        creates the classic Minesweeper border around an empty area.

        Why BFS instead of recursion?
        * No recursion-limit crash on very large boards.
        * The queue layers naturally form the expanding animation waves.
        """
        start_cell = self.board[start_row][start_col]
        start_cell.is_revealed = True
        self.revealed_count += 1

        waves: dict[int, list[Coordinate]] = {0: [(start_row, start_col)]}

        # Each queue entry is (row, col, distance).  Only zero cells are
        # expanded; numbered cells are leaves in the BFS graph.
        queue: deque[tuple[int, int, int]] = deque([(start_row, start_col, 0)])
        expanded_zeros: set[Coordinate] = {(start_row, start_col)}

        while queue:
            current_row, current_col, distance = queue.popleft()

            for neighbour_row, neighbour_col in self.get_neighbours(
                current_row, current_col
            ):
                neighbour = self.board[neighbour_row][neighbour_col]

                # Flags are respected by flood fill.  Mines are never opened
                # by flood fill because a zero cell has no adjacent mines.
                if (
                    neighbour.is_revealed
                    or neighbour.is_flagged
                    or neighbour.is_mine
                ):
                    continue

                neighbour.is_revealed = True
                self.revealed_count += 1

                next_wave = distance + 1
                waves.setdefault(next_wave, []).append(
                    (neighbour_row, neighbour_col)
                )

                # Only zero cells continue the expansion.
                if (
                    neighbour.adjacent_mines == 0
                    and (neighbour_row, neighbour_col) not in expanded_zeros
                ):
                    expanded_zeros.add((neighbour_row, neighbour_col))
                    queue.append(
                        (neighbour_row, neighbour_col, next_wave)
                    )

        # Return a dense list of waves in increasing distance order.
        return [waves[distance] for distance in sorted(waves)]

    # Logical Reasoning: a loss exposes every mine.
    def _reveal_all_mines(self) -> None:
        """Mark every mine as revealed after a loss."""
        for row, col in self.mine_set:
            self.board[row][col].is_revealed = True

    # ------------------------------------------------------------------ #
    # Flagging and chording
    # ------------------------------------------------------------------ #
    # Logical Reasoning: flags constrain hidden cells and the counter.
    def toggle_flag(self, row: int, col: int) -> bool:
        """Flag or unflag a hidden cell.

        Returns True when the board changed.  Revealed cells cannot be
        flagged.  The number of flags is capped at ``num_mines`` so the
        counter never becomes negative.
        """
        if not self.in_bounds(row, col):
            raise IndexError(f"cell {(row, col)} is outside the board")
        if self.state is not GameState.PLAYING:
            return False

        cell = self.board[row][col]
        if cell.is_revealed:
            return False

        if cell.is_flagged:
            cell.is_flagged = False
            self.flags_remaining += 1
            return True

        if self.flags_remaining <= 0:
            # Logical reasoning: no more flags than mines are available.
            return False

        cell.is_flagged = True
        self.flags_remaining -= 1
        return True

    # Logical Reasoning: flags around a number must match that number.
    def chord(self, row: int, col: int) -> list[list[Coordinate]]:
        """Reveal neighbours of a number when its flags match the number.

        Logical reasoning: the condition is

            flags_around_cell == cell.adjacent_mines

        Only then may the remaining hidden neighbours be opened.  If the
        player's flags are wrong, a chord can reveal a mine and lose the game,
        exactly as in classic Minesweeper.
        """
        if not self.in_bounds(row, col):
            raise IndexError(f"cell {(row, col)} is outside the board")
        if self.state is not GameState.PLAYING:
            return []

        cell = self.board[row][col]
        if not cell.is_revealed or cell.adjacent_mines == 0:
            return []

        neighbours = self.get_neighbours(row, col)
        flags_around = sum(
            1
            for neighbour_row, neighbour_col in neighbours
            if self.board[neighbour_row][neighbour_col].is_flagged
        )
        if flags_around != cell.adjacent_mines:
            return []

        # Reveal each hidden, unflagged neighbour.  Waves from several
        # neighbours are merged by layer so the GUI can still animate them.
        merged_waves: list[list[Coordinate]] = []
        for neighbour_row, neighbour_col in neighbours:
            neighbour = self.board[neighbour_row][neighbour_col]
            if neighbour.is_revealed or neighbour.is_flagged:
                continue

            waves = self.reveal(neighbour_row, neighbour_col)
            for layer, wave in enumerate(waves):
                if layer == len(merged_waves):
                    merged_waves.append([])
                merged_waves[layer].extend(wave)

            # A wrong flag may cause the chord to hit a mine.  Stop as soon
            # as the game is no longer in progress.
            if self.state is not GameState.PLAYING:
                break

        return merged_waves

    # ------------------------------------------------------------------ #
    # Win / loss helpers
    # ------------------------------------------------------------------ #
    # Logical Reasoning: the one clear Boolean win condition.
    def _check_for_win(self) -> bool:
        """The one clear Boolean win condition.

        Win  <=>  every non-mine cell has been revealed.

        Instead of counting hidden safe cells each time, we maintain
        ``revealed_count``.  This makes the test O(1).
        """
        total_safe_cells = self.rows * self.cols - self.num_mines
        if self.revealed_count == total_safe_cells:
            self.state = GameState.WON
            return True
        return False

    # Abstraction: a simple state query for the GUI.
    @property
    def is_game_over(self) -> bool:
        """True when the game has been won or lost."""
        return self.state is not GameState.PLAYING

    # Abstraction: a simple state query for the GUI.
    def is_won(self) -> bool:
        """Convenience predicate used by tests and the GUI."""
        return self.state is GameState.WON

    # Abstraction: a simple state query for the GUI.
    def is_lost(self) -> bool:
        """Convenience predicate used by tests and the GUI."""
        return self.state is GameState.LOST

    # Abstraction: turn state into a human-readable label.
    @property
    def status_text(self) -> str:
        """The human-readable status shown in the GUI."""
        return self.state.value
