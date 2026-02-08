import random
from collections import Counter
from itertools import combinations

class PositionComboGame:
    """
    Manages the game state for Position Combo, with a simultaneous-submission
    match phase.
    """
    def __init__(self, test_mode=False):
        """Initializes a new game, with an optional test mode to skip placement."""
        self.players = {
            'player1': {'used_combinations': set(), 'score': 0},
            'player2': {'used_combinations': set(), 'score': 0}
        }
        self.all_valid_combinations = self._generate_all_valid_combinations()
        self.match_round = 0
        self.total_rounds = 14
        self.match_submissions = {'player1': None, 'player2': None}
        self.game_over = False
        self.winner = None

        if test_mode:
            self.phase = 'match'
            self.boards = {
                'player1': self._create_random_board(),
                'player2': self._create_random_board()
            }
            self.placement_sequence = []
            self.placement_step = 25 # Mark as complete
            self.placements_this_step = {'player1': True, 'player2': True}
        else:
            self.phase = 'placement'
            self.boards = {'player1': {}, 'player2': {}}
            self.placement_sequence = [random.randint(1, 10) for _ in range(25)]
            self.placement_step = 0
            self.placements_this_step = {'player1': False, 'player2': False}

    def _create_random_board(self):
        """Creates and returns a complete, randomly populated 5x5 board."""
        board = {}
        cells = list(self._COORDS.keys())
        random.shuffle(cells)
        for cell in cells:
            board[cell] = random.randint(1, 10)
        return board


    def submit_placement(self, player_id, cell_id):
        if self.phase != 'placement': return {"error": "Not in placement phase."}
        if self.placements_this_step[player_id]: return {"error": "You have already placed a number for this turn."}
        if cell_id in self.boards[player_id]: return {"error": "This cell is already occupied."}

        current_number = self.placement_sequence[self.placement_step]
        self.boards[player_id][cell_id] = current_number
        self.placements_this_step[player_id] = True

        if all(self.placements_this_step.values()):
            self.placement_step += 1
            self.placements_this_step = {'player1': False, 'player2': False}
            if self.placement_step >= len(self.placement_sequence):
                self.phase = 'match'
                return {"status": "match_started"}
            return {"status": "next_placement_turn"}
        return {"status": "waiting_for_opponent"}

    def submit_combination(self, player_id, cells):
        """ Stores a player's combination choice for the current round. """
        if self.phase != 'match': return {"error": "The match has not started yet."}
        if self.match_submissions[player_id] is not None: return {"error": "You have already submitted a combination for this round."}

        cell_combo = frozenset(cells)
        if cell_combo not in self.all_valid_combinations: return {"error": "The selected cells do not form a valid straight line of 4."}
        if cell_combo in self.players[player_id]['used_combinations']: return {"error": "You have already used this combination."}
        
        self.match_submissions[player_id] = cell_combo
        
        if all(self.match_submissions.values()):
            return self.resolve_round()
        
        return {"status": "waiting_for_opponent_submission"}

    _COORDS = {f"{col}{row}": (ord(col) - ord('a'), row - 1) for col in 'abcde' for row in range(1, 6)}

    def resolve_round(self):
        """ Calculates the results after both players have submitted their combinations. """
        player_data = {}
        for player_id, submission in self.match_submissions.items():
            player_board = self.boards[player_id]
            
            # Sort the submitted cells by their coordinates to get the on-board linear order
            ordered_cells = sorted(list(submission), key=lambda cell: self._COORDS[cell])
            ordered_cell_values = [player_board[c] for c in ordered_cells]

            hand_name, hand_rank_tuple = self.get_hand_rank(ordered_cell_values)
            
            self.players[player_id]['used_combinations'].add(submission)
            
            player_data[player_id] = {
                "player": player_id,
                "cells": sorted(list(submission)),
                "values": ordered_cell_values,
                "hand": hand_name,
                "rank_tuple": hand_rank_tuple, # Store the detailed rank for comparison
                "points_gained_this_round": 0
            }
        
        # Determine round winner based on the detailed hand_rank_tuple
        p1_rank_tuple = player_data['player1']['rank_tuple']
        p2_rank_tuple = player_data['player2']['rank_tuple']

        if p1_rank_tuple > p2_rank_tuple:
            self.players['player1']['score'] += 1
            player_data['player1']['points_gained_this_round'] = 1
        elif p2_rank_tuple > p1_rank_tuple:
            self.players['player2']['score'] += 1
            player_data['player2']['points_gained_this_round'] = 1
        
        # Finalize results for sending to UI (without the detailed tuple)
        for p_id in ['player1', 'player2']:
            player_data[p_id]['new_score'] = self.players[p_id]['score']
            player_data[p_id]['rank'] = player_data[p_id]['rank_tuple'][0] # Send simple rank to UI
            del player_data[p_id]['rank_tuple'] # Don't send the complex tuple

        round_results = [player_data['player1'], player_data['player2']]

        # Prepare for next round
        self.match_round += 1
        self.match_submissions = {'player1': None, 'player2': None}

        # Check for game over
        if self.match_round >= self.total_rounds:
            self.game_over = True
            if self.players['player1']['score'] > self.players['player2']['score']:
                self.winner = 'player1'
            elif self.players['player2']['score'] > self.players['player1']['score']:
                self.winner = 'player2'
            else: self.winner = 'draw'

        return {"status": "round_resolved", "results": round_results, "game_over": self.game_over, "winner": self.winner}

    def get_game_state(self):
        """Returns the complete current state of the game for serialization."""
        players_state = {
            p_id: {'score': p_data['score'], 'used_combinations': [sorted(list(c)) for c in p_data['used_combinations']]}
            for p_id, p_data in self.players.items()
        }
        
        return {
            'phase': self.phase,
            'boards': self.boards if self.phase == 'placement' else {}, # Hide boards after placement
            'players': players_state,
            'placement_info': self.get_placement_info(),
            'match_info': self.get_match_info(),
            'game_over': self.game_over,
            'winner': self.winner,
        }

    def get_placement_info(self):
        if self.phase != 'placement': return {}
        return {
            'step': self.placement_step,
            'current_number': self.placement_sequence[self.placement_step],
            'placements_this_step': self.placements_this_step
        }

    def get_match_info(self):
        if self.phase != 'match': return {}
        return {
            'round': self.match_round,
            'total_rounds': self.total_rounds,
            'submissions': {p: (v is not None) for p, v in self.match_submissions.items()}
        }
    
    # --- Static Helper Methods ---
    def _generate_all_valid_combinations(self):
        cell_names = list(self._COORDS.keys())
        valid_combos = set()
        for combo in combinations(cell_names, 4):
            if self._is_straight_line_coords([self._COORDS[c] for c in combo]):
                valid_combos.add(frozenset(combo))
        return valid_combos

    def _is_straight_line_coords(self, coord_list):
        if len(coord_list) != 4: return False
        cell_coords = sorted(coord_list)
        step_x = cell_coords[1][0] - cell_coords[0][0]
        step_y = cell_coords[1][1] - cell_coords[0][1]
        if step_x == 0 and step_y == 0: return False
        return all(
            cell_coords[i][0] == cell_coords[0][0] + i * step_x and \
            cell_coords[i][1] == cell_coords[0][1] + i * step_y
            for i in range(1, 4)
        )

    def get_hand_rank(self, ordered_cell_values):
        """
        Determines the rank of a hand of 4 numbers.
        The `ordered_cell_values` must be in their on-board sequence.
        Returns a tuple of (hand_name, (rank_tuple)).
        """
        # Check for Royal Straight based on on-board order
        if ordered_cell_values == [7, 8, 9, 10] or ordered_cell_values == [10, 9, 8, 7]:
            return "Royal Straight", (6,)

        # For all other hands, the sorted order matters
        counts = Counter(ordered_cell_values)
        sorted_values = sorted(ordered_cell_values, reverse=True)
        
        # Check for regular straight
        is_straight = all(sorted_values[i] - 1 == sorted_values[i+1] for i in range(3))
        
        # Check for pairs, triples, quads
        value_counts = sorted(counts.items(), key=lambda item: (-item[1], -item[0]))
        main_rank = value_counts[0][1]
        
        if main_rank == 4:
            quad_val = value_counts[0][0]
            return "Quads", (7, quad_val)
        
        if is_straight:
            return "Straight", (5, sorted_values[0])

        if main_rank == 3:
            triple_val = value_counts[0][0]
            kicker = value_counts[1][0]
            return "Triple", (3, triple_val, kicker)
            
        if main_rank == 2:
            if value_counts[1][1] == 2: # Two Pair
                high_pair = value_counts[0][0]
                low_pair = value_counts[1][0]
                return "Two Pair", (4, high_pair, low_pair)
            else: # One Pair
                pair_val = value_counts[0][0]
                kickers = [vc[0] for vc in value_counts[1:]]
                return "One Pair", (2, pair_val, kickers[0], kickers[1])
        
        # High Card
        return "High Card", (1, *sorted_values)
