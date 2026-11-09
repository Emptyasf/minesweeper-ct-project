"""
test_board.py
=============

Unit tests for the pure game logic in :mod:`board`.

Run from this folder with:

    python -m unittest

The tests never create a Tkinter window, so they are fast and headless.
"""

from __future__ import annotations

import unittest

from board import Board, GameState
from cell import Cell


class TestBoardConstruction(unittest.TestCase):
    """Decomposition: the matrix, cells and mine count are separate concerns."""

    def test_3x3_5x5_10x10_dimensions(self) -> None:
        for size in (3, 5, 10):
            with self.subTest(size=size):
                board = Board(size, size, 3, seed=size)
                self.assertEqual(len(board.board), size)
                self.assertTrue(all(len(row) == size for row in board.board))
                self.assertEqual(len(board.mine_set), 3)
                self.assertEqual(
                    sum(
                        1
                        for row in board.board
                        for cell in row
                        if cell.is_mine
                    ),
                    3,
                )
                self.assertTrue(
                    all(
                        isinstance(cell, Cell)
                        for row in board.board
                        for cell in row
                    )
                )

    def test_invalid_configurations_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Board(0, 3, 1)
        with self.assertRaises(ValueError):
            Board(3, 3, 0)
        with self.assertRaises(ValueError):
            Board(3, 3, 9)  # all cells mined -> no safe first click


class TestNeighbours(unittest.TestCase):
    """Pattern Recognition: every cell uses the same eight offsets."""

    def test_corner_edge_and_middle_neighbour_counts(self) -> None:
        for size in (3, 5, 10):
            with self.subTest(size=size):
                board = Board(size, size, 1, seed=size)

                self.assertEqual(len(board.get_neighbours(0, 0)), 3)
                self.assertEqual(len(board.get_neighbours(0, 1)), 5)
                self.assertEqual(len(board.get_neighbours(size // 2, size // 2)), 8)
                self.assertEqual(len(board.get_neighbours(size - 1, size // 2)), 5)
                self.assertEqual(len(board.get_neighbours(size - 1, size - 1)), 3)

    def test_neighbours_are_always_inside_the_board(self) -> None:
        board = Board(5, 5, 4, seed=1)
        for row in range(5):
            for col in range(5):
                for neighbour_row, neighbour_col in board.get_neighbours(row, col):
                    self.assertTrue(0 <= neighbour_row < 5)
                    self.assertTrue(0 <= neighbour_col < 5)

    def test_out_of_bounds_neighbour_request_raises(self) -> None:
        board = Board(3, 3, 1, seed=1)
        with self.assertRaises(IndexError):
            board.get_neighbours(-1, 0)


class TestAdjacentMineCounting(unittest.TestCase):
    """Counting: Number(r, c) = mines in the valid eight neighbours."""

    def test_hand_built_3x3_board(self) -> None:
        # Mines on the main diagonal.  This makes every safe cell's count easy
        # to verify by hand.
        board = Board.from_mine_positions(
            3,
            3,
            {(0, 0), (1, 1), (2, 2)},
            seed=7,
        )

        expected = {
            (0, 1): 2,
            (0, 2): 1,
            (1, 0): 2,
            (1, 2): 2,
            (2, 0): 1,
            (2, 1): 2,
        }
        for position, expected_count in expected.items():
            with self.subTest(position=position):
                row, col = position
                self.assertEqual(
                    board.board[row][col].adjacent_mines,
                    expected_count,
                )
                self.assertEqual(
                    board.count_adjacent_mines(row, col),
                    expected_count,
                )

        # A mine is not a safe numbered cell.
        for row, col in board.mine_set:
            self.assertEqual(board.board[row][col].adjacent_mines, 0)

    def test_hand_built_5x5_board(self) -> None:
        board = Board.from_mine_positions(
            5,
            5,
            {(0, 0), (0, 4), (2, 2), (4, 1)},
            seed=11,
        )
        self.assertEqual(board.board[1][1].adjacent_mines, 2)  # (0,0), (2,2)
        self.assertEqual(board.board[0][1].adjacent_mines, 1)  # only (0,0)
        self.assertEqual(board.board[1][3].adjacent_mines, 2)  # (0,4), (2,2)
        self.assertEqual(board.board[2][1].adjacent_mines, 1)  # only (2,2)
        self.assertEqual(board.board[3][2].adjacent_mines, 2)  # (2,2), (4,1)
        self.assertEqual(board.board[3][1].adjacent_mines, 2)  # (2,2), (4,1)


class TestMinePlacement(unittest.TestCase):
    """Sets and loops: random mines must be unique and first click safe."""

    def test_mine_set_has_no_duplicates(self) -> None:
        for size in (3, 5, 10):
            with self.subTest(size=size):
                mines = 8
                board = Board(size, size, mines, seed=size * 17)
                self.assertEqual(len(board.mine_set), mines)
                self.assertEqual(
                    len(set(board.mine_set)),
                    mines,
                    "mine_set must contain unique coordinates",
                )
                for row, col in board.mine_set:
                    self.assertTrue(board.board[row][col].is_mine)

    def test_first_click_on_mine_moves_it_to_a_safe_cell(self) -> None:
        board = Board.from_mine_positions(3, 3, {(0, 0)}, seed=42)
        board.reveal(0, 0)

        self.assertFalse(board.is_lost())
        self.assertTrue(board.first_click_made)
        self.assertNotIn((0, 0), board.mine_set)
        self.assertFalse(board.board[0][0].is_mine)
        self.assertTrue(board.board[0][0].is_revealed)
        self.assertEqual(len(board.mine_set), 1)

        # The move must have refreshed every number on the board.
        for row in range(3):
            for col in range(3):
                cell = board.board[row][col]
                if not cell.is_mine:
                    self.assertEqual(
                        cell.adjacent_mines,
                        board.count_adjacent_mines(row, col),
                    )

    def test_first_click_on_safe_cell_keeps_the_layout(self) -> None:
        board = Board.from_mine_positions(3, 3, {(2, 2)}, seed=42)
        board.reveal(0, 0)
        self.assertEqual(board.mine_set, {(2, 2)})


class TestFloodFill(unittest.TestCase):
    """Algorithmic thinking: iterative BFS opens a zero region in waves."""

    def test_zero_region_opens_all_safe_cells_and_wins(self) -> None:
        board = Board.from_mine_positions(5, 5, {(0, 0)}, seed=3)
        waves = board.reveal(4, 4)

        self.assertTrue(board.is_won())
        self.assertEqual(board.revealed_count, 24)
        self.assertGreater(len(waves), 1, "BFS should produce several waves")
        self.assertFalse(board.board[0][0].is_revealed)

        for row in range(5):
            for col in range(5):
                if (row, col) != (0, 0):
                    self.assertTrue(board.board[row][col].is_revealed)

    def test_flood_fill_respects_flags(self) -> None:
        board = Board.from_mine_positions(5, 5, {(0, 0)}, seed=3)
        self.assertTrue(board.toggle_flag(4, 4))
        board.reveal(2, 2)

        self.assertTrue(board.board[4][4].is_flagged)
        self.assertFalse(board.board[4][4].is_revealed)
        self.assertFalse(board.is_won())
        self.assertEqual(board.state, GameState.PLAYING)

    def test_flood_fill_does_not_open_mines(self) -> None:
        board = Board.from_mine_positions(4, 4, {(0, 0)}, seed=5)
        board.reveal(3, 3)
        self.assertFalse(board.board[0][0].is_revealed)
        self.assertTrue(board.is_won())


class TestWinAndLoss(unittest.TestCase):
    """Logical reasoning: win and loss are precise Boolean conditions."""

    def test_losing_by_clicking_a_mine(self) -> None:
        board = Board.from_mine_positions(3, 3, {(0, 0)}, seed=4)
        board.reveal(0, 1)  # safe first click; this cell is a "1"
        self.assertEqual(board.state, GameState.PLAYING)

        board.reveal(0, 0)
        self.assertTrue(board.is_lost())
        self.assertEqual(board.exploded_cell, (0, 0))
        self.assertEqual(board.status_text, "Game Over")
        for row, col in board.mine_set:
            self.assertTrue(board.board[row][col].is_revealed)

    def test_winning_by_revealing_every_safe_cell(self) -> None:
        board = Board.from_mine_positions(3, 3, {(0, 0)}, seed=4)
        board.reveal(2, 2)

        self.assertTrue(board.is_won())
        self.assertEqual(board.status_text, "You Win!")
        self.assertEqual(board.revealed_count, 8)
        self.assertEqual(
            board.revealed_count,
            board.rows * board.cols - board.num_mines,
        )
        self.assertFalse(board.board[0][0].is_revealed)

    def test_maximum_number_of_mines(self) -> None:
        # Eight mines on a 3x3 board leave only the centre safe.  That centre
        # cell is adjacent to all eight mines.
        mines = {
            (row, col)
            for row in range(3)
            for col in range(3)
            if (row, col) != (1, 1)
        }
        board = Board.from_mine_positions(3, 3, mines, seed=5)
        self.assertEqual(len(board.mine_set), 8)
        self.assertEqual(board.board[1][1].adjacent_mines, 8)

        board.reveal(1, 1)
        self.assertTrue(board.is_won())
        self.assertEqual(board.revealed_count, 1)

    def test_single_mine_board(self) -> None:
        board = Board.from_mine_positions(3, 3, {(0, 0)}, seed=5)
        self.assertEqual(len(board.mine_set), 1)
        board.reveal(2, 2)
        self.assertTrue(board.is_won())


class TestFlagsAndChording(unittest.TestCase):
    """Logical reasoning: flags constrain reveals and enable chords."""

    def test_flag_toggle_updates_counter(self) -> None:
        board = Board(3, 3, 2, seed=1)
        self.assertEqual(board.flags_remaining, 2)

        self.assertTrue(board.toggle_flag(1, 1))
        self.assertTrue(board.board[1][1].is_flagged)
        self.assertEqual(board.flags_remaining, 1)

        self.assertTrue(board.toggle_flag(1, 1))
        self.assertFalse(board.board[1][1].is_flagged)
        self.assertEqual(board.flags_remaining, 2)

    def test_cannot_place_more_flags_than_mines(self) -> None:
        board = Board(3, 3, 1, seed=1)
        self.assertTrue(board.toggle_flag(0, 0))
        self.assertEqual(board.flags_remaining, 0)
        self.assertFalse(board.toggle_flag(1, 1))
        self.assertFalse(board.board[1][1].is_flagged)

    def test_flagging_a_revealed_cell_is_ignored(self) -> None:
        board = Board.from_mine_positions(3, 3, {(0, 0)}, seed=1)
        board.reveal(0, 1)
        self.assertTrue(board.board[0][1].is_revealed)

        before = board.flags_remaining
        self.assertFalse(board.toggle_flag(0, 1))
        self.assertEqual(board.flags_remaining, before)
        self.assertFalse(board.board[0][1].is_flagged)

    def test_clicking_a_flagged_cell_is_ignored(self) -> None:
        board = Board.from_mine_positions(3, 3, {(0, 0)}, seed=1)
        self.assertTrue(board.toggle_flag(0, 0))

        waves = board.reveal(0, 0)
        self.assertEqual(waves, [])
        self.assertEqual(board.state, GameState.PLAYING)
        self.assertFalse(board.board[0][0].is_revealed)

    def test_chord_reveals_neighbours_when_flags_match(self) -> None:
        board = Board.from_mine_positions(3, 3, {(0, 0)}, seed=1)
        self.assertTrue(board.toggle_flag(0, 0))
        board.reveal(0, 1)  # numbered boundary cell
        self.assertEqual(board.state, GameState.PLAYING)

        board.chord(0, 1)
        self.assertTrue(board.is_won())
        for row in range(3):
            for col in range(3):
                if (row, col) != (0, 0):
                    self.assertTrue(board.board[row][col].is_revealed)

    def test_chord_does_nothing_when_flags_do_not_match(self) -> None:
        board = Board.from_mine_positions(3, 3, {(0, 0)}, seed=1)
        board.reveal(0, 1)  # a "1", but no flag placed

        waves = board.chord(0, 1)
        self.assertEqual(waves, [])
        self.assertEqual(board.state, GameState.PLAYING)
        self.assertFalse(board.board[1][1].is_revealed)


class TestStateHelpers(unittest.TestCase):
    """Small abstractions used by the GUI and by these tests."""

    def test_game_state_strings(self) -> None:
        self.assertEqual(GameState.PLAYING.value, "Playing")
        self.assertEqual(GameState.WON.value, "You Win!")
        self.assertEqual(GameState.LOST.value, "Game Over")

    def test_game_over_property(self) -> None:
        board = Board(3, 3, 1, seed=1)
        self.assertFalse(board.is_game_over)
        self.assertFalse(board.is_won())
        self.assertFalse(board.is_lost())


if __name__ == "__main__":
    unittest.main(verbosity=2)
