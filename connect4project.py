# -*- coding: utf-8 -*-
"""
Created on Mon Nov 18 16:38:11 2024

@author: bpatn
"""

import asyncio
import websockets
import math
import random

ROWS = 6
COLS = 7
playerPiece = 1
AIpiece = 2


def calculate_move(message):
    rows = message.split(';')
    board = [list(map(int, row.split(','))) for row in rows]

    def is_valid_location(board, col):
        """Checks if a column has at least one empty space."""
        return board[0][col] == 0

    def get_next_open_row(board, col):
        """Finds the next available row in the given column."""
        for r in range(ROWS - 1, -1, -1):
            if board[r][col] == 0:
                return r

    def winning_move(board, piece):
        """Checks if the given piece has a winning move."""
        # Check horizontal
        for c in range(COLS - 3):
            for r in range(ROWS):
                if all(board[r][c + i] == piece for i in range(4)):
                    return True

        # Check vertical
        for c in range(COLS):
            for r in range(ROWS - 3):
                if all(board[r + i][c] == piece for i in range(4)):
                    return True

        # Check positively sloped diagonals
        for c in range(COLS - 3):
            for r in range(ROWS - 3):
                if all(board[r + i][c + i] == piece for i in range(4)):
                    return True

        # Check negatively sloped diagonals
        for c in range(COLS - 3):
            for r in range(3, ROWS):
                if all(board[r - i][c + i] == piece for i in range(4)):
                    return True

        return False

    def score_position(board, piece):
        """Scores the board based on how favorable it is for the AI."""
        score = 0

        centerCol = [board[r][COLS // 2] for r in range(ROWS)]
        centerCount = centerCol.count(piece)
        score += centerCount * 6

        # Score horizontal
        for r in range(ROWS):
            row_array = board[r]
            for c in range(COLS - 3):
                window = row_array[c:c + 4]
                score += evaluate_window(window, piece)

        # Score vertical
        for c in range(COLS):
            col_array = [board[r][c] for r in range(ROWS)]
            for r in range(ROWS - 3):
                window = col_array[r:r + 4]
                score += evaluate_window(window, piece)

        # Score diagonals
        for r in range(ROWS - 3):
            for c in range(COLS - 3):
                window = [board[r + i][c + i] for i in range(4)]
                score += evaluate_window(window, piece)

            for c in range(3, COLS):
                window = [board[r + i][c - i] for i in range(4)]
                score += evaluate_window(window, piece)

        return score

    def evaluate_window(window, piece):
        opponent_piece = playerPiece if piece == AIpiece else AIpiece
        score = 0

        if window.count(piece) == 4:
            score += 100
        elif window.count(piece) == 3 and window.count(0) == 1:
            score += 5
        elif window.count(piece) == 2 and window.count(0) == 2:
            score += 2

        if window.count(opponent_piece) == 3 and window.count(0) == 1:
            score -= 4

        return score

    def checkGameEnd(board):
        return winning_move(board, playerPiece) or winning_move(board, AIpiece) or not get_valid_locations(board)

    def get_valid_locations(board):
        return [c for c in range(COLS) if is_valid_location(board, c)]

    def minimax(board, depth, a, b, maximizing_player):
        valid_locations = get_valid_locations(board)
        endGame = checkGameEnd(board)

        if depth == 0 or endGame:
            if endGame:
                if winning_move(board, AIpiece):
                    return None, 10000000
                elif winning_move(board, playerPiece):
                    return None, -10000000
                else:
                    return None, 0
            else:
                return None, score_position(board, AIpiece)

        if maximizing_player:
            value = -math.inf
            best_col = random.choice(valid_locations)
            for col in valid_locations:
                row = get_next_open_row(board, col)
                temp_board = [row.copy() for row in board]
                temp_board[row][col] = AIpiece
                i, new_score = minimax(temp_board, depth - 1, a, b, False)
                if new_score > value:
                    value = new_score
                    best_col = col
                a = max(a, value)
                if a >= b:
                    break
            return best_col, value

        else:
            value = math.inf
            best_col = random.choice(valid_locations)
            for col in valid_locations:
                row = get_next_open_row(board, col)
                temp_board = [row.copy() for row in board]
                temp_board[row][col] = playerPiece
                i, new_score = minimax(temp_board, depth - 1, a, b, True)
                if new_score < value:
                    value = new_score
                    best_col = col
                b = min(b, value)
                if a >= b:
                    break
            return best_col, value

    best_col, j = minimax(board, 5, -math.inf, math.inf, True)
    return best_col

def get_next_open_row(board, col):
    """Finds the next available row in the given column."""
    for r in range(ROWS - 1, -1, -1):
        if board[r][col] == 0:
            return r
async def gameloop(socket, created):
    board = [[0] * COLS for w in range(ROWS)]
    active = True
    while active:
        message = (await socket.recv()).split(':')
        match message[0]:
            case 'GAMESTART':
                if created:
                    col = calculate_move(";".join([",".join(map(str, row)) for row in board]))
                    row = get_next_open_row(board, col)
                    board[row][col] = AIpiece  # Update AI's move on the board
                    await socket.send(f'PLAY:{col}')
            case 'OPPONENT':
                opponent_col = int(message[1])
                opponent_row = get_next_open_row(board, opponent_col)
                board[opponent_row][opponent_col] = playerPiece
                
                col = calculate_move(";".join([",".join(map(str, row)) for row in board]))
                row = get_next_open_row(board, col)
                board[row][col] = AIpiece  # Update AI's move
                await socket.send(f'PLAY:{col}')
            case 'WIN' | 'LOSS' | 'DRAW' | 'TERMINATED':
                print(message[0])
                active = False


async def create_game(server):
    async with websockets.connect(f'ws://{server}/create') as socket:
        await gameloop(socket, True)


async def join_game(server, id):
    async with websockets.connect(f'ws://{server}/join/{id}') as socket:
        await gameloop(socket, False)


if __name__ == '__main__':
    server = input('Server IP: ').strip()
    protocol = input('Join game or create game? (j/c): ').strip()

    match protocol:
        case 'c':
            asyncio.run(create_game(server))
        case 'j':
            id = input('Game ID: ').strip()
            asyncio.run(join_game(server, id))
        case _:
            print('Invalid protocol!')
