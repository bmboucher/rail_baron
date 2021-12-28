from abc import ABC, abstractmethod
from pyrailbaron.game.state import Engine, GameState, PlayerState
from typing import List, Tuple

INITIAL_BANK = 20000
MIN_CASH_TO_WIN = 200000

class Interface:
    # Roll for home city
    @abstractmethod
    def get_home_city(self, s: GameState, player_i: int) -> int:
        pass

    # Roll for destination city
    # (Use alt=True when rolling for alternate destination after declaring)
    @abstractmethod
    def get_destination(self, s: GameState, player_i: int, alt: bool = False) -> int:
        pass

    # Roll two die for distance
    @abstractmethod
    def roll_for_distance(self, player_i: int) -> Tuple[int, int]:
        pass

    # Roll single bonus die for distance
    @abstractmethod
    def bonus_roll(self, player_i: int) -> int:
        pass

    # Select rail lines
    @abstractmethod
    def get_player_move(self, s: GameState, player_i: int, d: int) -> List[Tuple[str, int]]:
        pass

    @abstractmethod
    def get_purchase(self, s: GameState, player_i: int) -> str:
        pass

    @abstractmethod
    def ask_to_declare(self, s: GameState, player_i: int) -> bool:
        pass

def init_game(n_players: int) -> GameState:
    s = GameState()
    for player_i in range(n_players):
        p = PlayerState(
            name=f'Player {player_i + 1}', # player_i is 0-indexed
            homeCity=-1,
            destination=-1,
            bank=INITIAL_BANK,
            engine=Engine.Basic)
        s.players.append(p)
    return s

def do_move(s: GameState, i: Interface, player_i: int, d: int):
    waypoints = i.get_player_move(s, player_i, d)

    s.players[player_i].move(waypoints)

def check_for_winner(s: GameState, i: Interface, player_i: int) -> bool:
    ps = s.players[player_i]

    if not ps.declared and ps.canDeclare:
        ps.declared = i.ask_to_declare(s, player_i)
        if ps.declared:
            # Set alternate destination
            ps.set_destination(i.get_destination(s, player_i, alt=True))

    if ps.declared:
        return ps.atHomeCity and ps.bank >= MIN_CASH_TO_WIN
    elif ps.destination < 0 or ps.atDestination:
        ps.set_destination(i.get_destination(s, player_i))
    return False

def run_game(n_players: int, i: Interface):
    s = init_game(n_players)
    for player_i in range(n_players):
        s.players[player_i].set_home_city(i.get_home_city(s, player_i))
    
    player_i = 0
    while True:
        if check_for_winner(s,i, player_i):
            break

        d1,d2 = i.roll_for_distance(player_i)
        do_move(s, i, player_i, d1 + d2)

        if check_for_winner(s,i, player_i):
            break

        if s.players[player_i].check_bonus_roll(d1, d2):
            do_move(s, i, player_i, i.bonus_roll(player_i))
        
        if check_for_winner(s,i, player_i):
            break

        player_i += 1
        player_i = 0 if player_i >= n_players else player_i