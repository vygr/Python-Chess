#!/opt/local/bin/pypy -tt
#!/opt/local/bin/pypy -tt -m cProfile
# -*- coding: utf-8 -*-
# Copyright (C) 2013-2014 Chris Hinsley

import sys, os, time
from operator import itemgetter
from array import array

MAX_PLY = 10
MAX_TIME_PER_MOVE = 10
PIECE_VALUE_FACTOR = 3

KING_VALUE, QUEEN_VALUE, ROOK_VALUE = 1000000, 9 * PIECE_VALUE_FACTOR, 5 * PIECE_VALUE_FACTOR
BISHOP_VALUE, KNIGHT_VALUE, PAWN_VALUE = 3 * PIECE_VALUE_FACTOR, 3 * PIECE_VALUE_FACTOR, 1 * PIECE_VALUE_FACTOR

EMPTY, WHITE, BLACK = 0, 1, -1
NO_CAPTURE, MAY_CAPTURE, MUST_CAPTURE = 0, 1, 2

piece_type = dict([(piece, WHITE if piece < 'a' else BLACK) for piece in 'kqrbnpKQRBNP'] + [(' ', EMPTY)])
unicode_pieces = dict(zip('KQRBNPkqrbnp ', [unichr(piece) for piece in xrange(9812, 9824)] + [' ']))

def display_board(board):
	os.system(['clear','cls'][os.name=='nt'])
	print
	print '  a   b   c   d   e   f   g   h'
	print u'\u2501\u2501\u2501'.join([u'\u250f'] + [u'\u2533' for _ in xrange(7)] + [u'\u2513'])
	for row in xrange(8):
		print u'\u2503', u' \u2503 '.join([unicode_pieces[board[row * 8 + col]] for col in xrange(8)]), u'\u2503', 8 - row
		if row != 7:
			print u'\u2501\u2501\u2501'.join([u'\u2523'] + [u'\u254b' for _ in xrange(7)] + [u'\u252b'])
		else:
			print u'\u2501\u2501\u2501'.join([u'\u2517'] + [u'\u253b' for _ in xrange(7)] + [u'\u251b'])
	print

def piece_moves(board, index, vectors):
	piece = board[index]
	type = piece_type[piece]
	promote = 'QRBN' if type == WHITE else 'qrbn'
	cy, cx = divmod(index, 8)
	for dx, dy, length, flag in vectors:
		x, y = cx, cy
		if length == 0:
			if piece == 'p':
				length = 2 if (y == 1) else 1
			else:
				length = 2 if (y == 6) else 1
		while length > 0:
			x += dx; y += dy; length -= 1
			if (x < 0) or (x >= 8) or (y < 0) or (y >= 8):
				break
			newindex = y * 8 + x
			newpiece = board[newindex]
			newtype = piece_type[newpiece]
			if newtype == type:
				break
			if (flag == NO_CAPTURE) and (newtype != EMPTY):
				break
			if (flag == MUST_CAPTURE) and (newtype == EMPTY):
				break
			board[index] = ' '
			if (y == 0 or y == 7) and piece in 'Pp':
				for promote_piece in promote:
					board[newindex] = promote_piece
					yield board
			else:
				board[newindex] = piece
				yield board
			board[index], board[newindex] = piece, newpiece
			if (flag == MAY_CAPTURE) and (newtype != EMPTY):
				break

def piece_scans(board, index, vectors):
	cy, cx = divmod(index, 8)
	for dx, dy, length in vectors:
		x, y = cx, cy
		while length > 0:
			x += dx; y += dy; length -= 1
			if (0 <= x < 8) and (0 <= y < 8):
				piece = board[y * 8 + x]
				if piece != ' ':
					yield piece
					break

black_pawn_vectors = [(-1, 1, 1), (1, 1, 1)]
white_pawn_vectors = [(-1, -1, 1), (1, -1, 1)]
bishop_vectors = [(x, y, 7) for x, y in [(-1, -1), (1, 1), (-1, 1), (1, -1)]]
rook_vectors = [(x, y, 7) for x, y in [(0, -1), (-1, 0), (0, 1), (1, 0)]]
knight_vectors = [(x, y, 1) for x, y in [(-2, 1), (2, -1), (2, 1), (-2, -1), (-1, -2), (-1, 2), (1, -2), (1, 2)]]
queen_vectors = bishop_vectors + rook_vectors
king_vectors = [(x, y, 1) for x, y, _ in queen_vectors]

black_pawn_moves = [(0, 1, 0, NO_CAPTURE), (-1, 1, 1, MUST_CAPTURE), (1, 1, 1, MUST_CAPTURE)]
white_pawn_moves = [(x, -1, length, flag) for x, _, length, flag in black_pawn_moves]
rook_moves = [(x, y, length, MAY_CAPTURE) for x, y, length in rook_vectors]
bishop_moves = [(x, y, length, MAY_CAPTURE) for x, y, length in bishop_vectors]
knight_moves = [(x, y, length, MAY_CAPTURE) for x, y, length in knight_vectors]
queen_moves = bishop_moves + rook_moves
king_moves = [(x, y, 1, flag) for x, y, _, flag in queen_moves]

moves = {'p' : black_pawn_moves, 'P' : white_pawn_moves, 'R' : rook_moves, 'r' : rook_moves, \
		'B' : bishop_moves, 'b' : bishop_moves, 'N' : knight_moves, 'n' : knight_moves, \
		'Q' : queen_moves, 'q' : queen_moves, 'K' : king_moves, 'k' : king_moves}

white_scans = [('qb', bishop_vectors), ('qr', rook_vectors), ('n', knight_vectors), ('k', king_vectors), ('p', white_pawn_vectors)]
black_scans = [('QB', bishop_vectors), ('QR', rook_vectors), ('N', knight_vectors), ('K', king_vectors), ('P', black_pawn_vectors)]

def in_check(board, colour, king_index):
	if colour == BLACK:
		king_piece, scans = 'k', black_scans
	else:
		king_piece, scans = 'K', white_scans
	if board[king_index] != king_piece:
		king_index = array.index(board, king_piece)
	for test_pieces, vectors in scans:
		pieces = [piece for piece in piece_scans(board, king_index, vectors)]
		for piece in test_pieces:
			if piece in pieces:
				return True, king_index
	return False, king_index

def all_moves(board, colour):
	king_index = 0
	for index, piece in enumerate(board):
		if piece_type[piece] == colour:
			for new_board in piece_moves(board, index, moves[piece]):
				check, king_index = in_check(new_board, colour, king_index)
				if not check:
					yield new_board

piece_values = {'k' : (KING_VALUE, 0), 'K' : (0, KING_VALUE), 'q' : (QUEEN_VALUE, 0), 'Q' : (0, QUEEN_VALUE), \
				'r' : (ROOK_VALUE, 0), 'R' : (0, ROOK_VALUE), 'b' : (BISHOP_VALUE, 0), 'B' : (0, BISHOP_VALUE), \
				'n' : (KNIGHT_VALUE, 0), 'N' : (0, KNIGHT_VALUE), 'p' : (PAWN_VALUE, 0), 'P' : (0, PAWN_VALUE)}

generic_position_values =  [0, 0, 0, 0, 0, 0, 0, 0, \
							0, 1, 1, 1, 1, 1, 1, 0, \
							0, 1, 2, 2, 2, 2, 1, 0, \
							0, 1, 2, 3, 3, 2, 1, 0, \
							0, 1, 2, 3, 3, 2, 1, 0, \
							0, 1, 2, 2, 2, 2, 1, 0, \
							0, 1, 1, 1, 1, 1, 1, 0, \
							0, 0, 0, 0, 0, 0, 0, 0]

white_king_position_values =   [0, 0, 0, 0, 0, 0, 0, 0, \
								0, 0, 0, 0, 0, 0, 0, 0, \
								0, 0, 0, 0, 0, 0, 0, 0, \
								0, 0, 0, 0, 0, 0, 0, 0, \
								0, 0, 0, 0, 0, 0, 0, 0, \
								0, 0, 0, 0, 0, 0, 0, 0, \
								0, 0, 0, 0, 0, 0, 0, 0, \
								3, 3, 3, 3, 3, 3, 3, 3]

black_king_position_values =   [3, 3, 3, 3, 3, 3, 3, 3, \
								0, 0, 0, 0, 0, 0, 0, 0, \
								0, 0, 0, 0, 0, 0, 0, 0, \
								0, 0, 0, 0, 0, 0, 0, 0, \
								0, 0, 0, 0, 0, 0, 0, 0, \
								0, 0, 0, 0, 0, 0, 0, 0, \
								0, 0, 0, 0, 0, 0, 0, 0, \
								0, 0, 0, 0, 0, 0, 0, 0]

piece_positions =  {'k' : black_king_position_values, 'K' : white_king_position_values, \
					'p' : generic_position_values, 'P' : generic_position_values, \
					'n' : generic_position_values, 'N' : generic_position_values, \
					'b' : generic_position_values, 'B' : generic_position_values, \
					'r' : generic_position_values, 'R' : generic_position_values, \
					'q' : generic_position_values, 'Q' : generic_position_values}

def evaluate(board):
	black_score, white_score = 0, 0
	for index, piece in enumerate(board):
		type = piece_type[piece]
		if type != EMPTY:
			position_value = piece_positions[piece][index]
			if type == BLACK:
				black_score += position_value
			else:
				white_score += position_value
			black_value, white_value = piece_values[piece]
			black_score += black_value
			white_score += white_value
	return white_score - black_score

start_time = time.time()

def next_move(board, colour, alpha, beta, ply):
	global start_time
	if ply <= 0:
		return evaluate(board) * colour
	mate = True
	for new_board in all_moves(board[:], colour):
		mate = False
		alpha = max(alpha, -next_move(new_board, -colour, -beta, -alpha, ply - 1))
		if alpha >= beta:
			break
		if (time.time() - start_time) > MAX_TIME_PER_MOVE:
			break
	if mate:
		mate, _ = in_check(board, colour, 0)
		if mate:
			return colour * KING_VALUE * 100
		return colour * KING_VALUE * -100
	return alpha

def best_move(board, colour):
	global start_time
	all_boards = [(evaluate(new_board) * colour, new_board[:]) for new_board in all_moves(board, colour)]
	if not all_boards:
		return None
	all_boards = sorted(all_boards, key = itemgetter(0), reverse = True)
	best_board, best_ply_board, start_time = board, board, time.time()
	for ply in xrange(1, MAX_PLY):
		print '\nPly =', ply
		alpha, beta = -KING_VALUE * 10, KING_VALUE * 10
		for new_board in all_boards:
			score = -next_move(new_board[1], -colour, -beta, -alpha, ply - 1)
			if (time.time() - start_time) > MAX_TIME_PER_MOVE:
				return best_board
			if score > alpha:
				alpha, best_ply_board = score, new_board[1]
				print '\b*',
			else:
				print '\b.',
			sys.stdout.flush()
		best_board = best_ply_board
	return best_board

def main():
	history = []
	board = array('c', 'rnbqkbnrpppppppp                                PPPPPPPPRNBQKBNR')
	colour = WHITE
	display_board(board)
	while True:
		print 'White to move:' if colour == WHITE else 'Black to move:'
		new_board = best_move(board, colour)
		if not new_board:
			check, _ = in_check(board, colour, 0)
			if check:
				print '\n** Checkmate **'
			else:
				print '\n** Stalemate **'
			break
		if history.count(new_board) >= 3:
			print '\n** Draw **'
			break
		history += [new_board[:]]
		for _ in range(3):
			time.sleep(0.1)
			display_board(board)
			time.sleep(0.1)
			display_board(new_board)
		colour = -colour
		board = new_board

if __name__ == '__main__':
	main()
