from abc import ABC, abstractmethod
from pyrailbaron.game.state import GameState
from typing import List, Tuple, Optional

class Interface(ABC):
    @abstractmethod
    def get_player_name(self, player_i: int) -> str:
        pass

    # Roll for home city
    @abstractmethod
    def get_home_city(self, s: GameState, player_i: int) -> str:
        pass

    # Announce the start of player i's turn
    @abstractmethod
    def announce_turn(self, s: GameState, player_i: int):
        pass

    # Roll for destination city
    @abstractmethod
    def get_destination(self, s: GameState, player_i: int) -> str:
        pass

    # Roll two die for distance
    @abstractmethod
    def roll_for_distance(self, s: GameState, player_i: int) -> Tuple[int, int]:
        pass

    # Roll single bonus die for distance
    @abstractmethod
    def bonus_roll(self, s: GameState, player_i: int) -> int:
        pass

    # Select rail lines and points to move through given distance
    @abstractmethod
    def get_player_move(self, s: GameState, player_i: int, d: int, init_rr: str | None, moves_so_far: int) -> List[Tuple[str, int]]:
        pass

    # Display a change in bank balances (AFTER state s has been updated)
    @abstractmethod
    def update_bank_amts(self, s: GameState):
        pass

    # Update the displayed owners of railroads (AFTER state s has been updated)
    @abstractmethod
    def update_owners(self, s: GameState):
        pass

    # Announce that a player needs to raise an amount of cash by selling/auctioning
    @abstractmethod
    def display_shortfall(self, s: GameState, player_i: int, amt: int):
        pass

    # Select a railroad to sell when raising funds
    @abstractmethod
    def select_rr_to_sell(self, s: GameState, player_i: int) -> str:
        pass

    @abstractmethod
    def announce_route_payoff(self, s: GameState, player_i: int, amt: int):
        pass

    # Ask if the player wants to sell the RR to the bank immediately for 1/2 cost
    @abstractmethod
    def ask_to_auction(self, s: GameState, player_i: int, rr_to_sell: str) -> bool:
        pass

    # Ask another player to bid on a RR up for auction (return 0 to pass)
    @abstractmethod
    def ask_for_bid(self, s: GameState, selling_player_i: int, bidding_player_i: int, rr_to_sell: str, min_bid: int) -> int:
        pass

    @abstractmethod
    def announce_sale(self, s: GameState, seller_i: int, buyer_i: int, rr: str, price: int):
        pass

    @abstractmethod
    def announce_sale_to_bank(self, s: GameState, seller_i: int, rr: str, price: int):
        pass

    # Select engine/rail line to purchase
    @abstractmethod
    def get_purchase(self, s: GameState, player_i: int, user_fee: int) -> Optional[str]:
        pass

    # Ask a player whether they want to declare before setting alternate destination
    @abstractmethod
    def ask_to_declare(self, s: GameState, player_i: int) -> bool:
        pass

    # Announce that a declared player has falled below MIN_CASH_TO_WIN
    @abstractmethod
    def announce_undeclared(self, s: GameState, player_i: int):
        pass

    # Announce a rover play (i.e. crossing the path of a declared player)
    @abstractmethod
    def announce_rover_play(self, s: GameState, decl_player_i: int, rover_player_i: int):
        pass

    # Display the final winner
    @abstractmethod
    def show_winner(self, s: GameState, winner_i: int):
        pass