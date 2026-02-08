import random
from collections import Counter
from itertools import combinations

class PositionComboGame:
    """
    Manages the game state for Position Combo, with a simultaneous-submission
    match phase.
    """
    def __init__(self):
        self.phase = 'placement'
        self.boards = {'player1': {}, 'player2': {}}
        self.placement_sequence = [random.randint(1, 10) for _ in range(25)]
        self.placement_step = 0
        self.placements_this_step = {'player1': False, 'player2': False}

        self.players = {
            'player1': {'used_combinations': set(), 'score': 0},
            'player2': {'used_combinations': set(), 'score': 0}
        }
        self.all_valid_combinations = self._generate_all_valid_combinations()
        
        # New match phase logic
        self.match_round = 0
        self.total_rounds = 14 # Each player gets to call half of the 28 total combos
        self.match_submissions = {'player1': None, 'player2': None}
        
        self.game_over = False
        self.winner = None

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

    def resolve_round(self):
        """ Calculates the results after both players have submitted their combinations. """
        player_data = {}
        for player_id, submission in self.match_submissions.items():
            player_board = self.boards[player_id]
            cell_values = [player_board[c] for c in submission]
            hand_name, hand_rank = self.get_hand_rank(cell_values)
            
            self.players[player_id]['used_combinations'].add(submission)
            
            player_data[player_id] = {
                "player": player_id,
                "cells": sorted(list(submission)),
                "values": cell_values,
                "hand": hand_name,
                "rank": hand_rank,
                "points_gained_this_round": 0 # Initialize to 0
            }
        
        # Determine round winner based on hand_rank
        p1_rank = player_data['player1']['rank']
        p2_rank = player_data['player2']['rank']

        if p1_rank > p2_rank:
            self.players['player1']['score'] += 1
            player_data['player1']['points_gained_this_round'] = 1
            player_data['player1']['new_score'] = self.players['player1']['score']
            player_data['player2']['new_score'] = self.players['player2']['score']
        elif p2_rank > p1_rank:
            self.players['player2']['score'] += 1
            player_data['player2']['points_gained_this_round'] = 1
            player_data['player1']['new_score'] = self.players['player1']['score']
            player_data['player2']['new_score'] = self.players['player2']['score']
        else: # Draw
            player_data['player1']['new_score'] = self.players['player1']['score']
            player_data['player2']['new_score'] = self.players['player2']['score']
        
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
        coords = {f"{col}{row}": (ord(col) - ord('a'), row - 1) for col in 'abcde' for row in range(1, 6)}
        cell_names = list(coords.keys())
        valid_combos = set()
        for combo in combinations(cell_names, 4):
            if self._is_straight_line_coords([coords[c] for c in combo]):
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

    def get_hand_rank(self, cell_values):
        counts = Counter(cell_values)
        sorted_values = sorted(cell_values)
        is_quad = 4 in counts.values()
        num_pairs = list(counts.values()).count(2)
        is_triple = 3 in counts.values()
        is_straight = all(sorted_values[i] + 1 == sorted_values[i+1] for i in range(3))
        is_royal_straight = sorted_values == [7, 8, 9, 10]
        if is_quad: return "Quads", 7
        if is_royal_straight: return "Royal Straight", 6
        if is_straight: return "Straight", 5
        if num_pairs == 2: return "Two Pair", 4
        if is_triple: return "Triple", 3
        if num_pairs == 1: return "One Pair", 2
        return "High Card", 1
