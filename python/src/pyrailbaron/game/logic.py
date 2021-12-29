from abc import ABC, abstractmethod
import enum
from dataclasses_json.cfg import T
from pyrailbaron.map.datamodel import read_map
from pyrailbaron.game.state import Engine, GameState, PlayerState, Waypoint
from typing import List, Tuple

INITIAL_BANK = 20000
MIN_CASH_TO_WIN = 200000
BANK_USER_FEE = 1000
OTHER_USER_FEE = 5000
MIN_BID_INCR = 500
ROVER_PLAY_FEE = 50000

class Interface:
    @abstractmethod
    def get_player_name(self, player_i: int) -> str:
        pass

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

    # Select rail lines and points to move through given distance
    @abstractmethod
    def get_player_move(self, s: GameState, player_i: int, d: int) -> List[Tuple[str, int]]:
        pass

    # Display a change in bank balances (AFTER state s has been updated)
    @abstractmethod
    def update_bank_amts(self, s: GameState):
        pass

    # Update the displayed owners of railroads (AFTER state s has been updated)
    @abstractmethod
    def update_owners(self, s: GameState):
        pass

    @abstractmethod
    def display_shortfall(self, s: GameState, player_i: int, amt: int):
        pass

    # Select a railroad to sell when raising funds
    @abstractmethod
    def select_rr_to_sell(self, s: GameState, player_i: int) -> str:
        pass

    # Ask if the player wants to sell the RR to the bank immediately for 1/2 cost
    @abstractmethod
    def ask_to_auction(self, s: GameState, player_i: int, rr_to_sell: str) -> bool:
        pass

    # Ask another player to bid on a RR up for auction (return 0 to pass)
    @abstractmethod
    def ask_for_bid(self, s: GameState, selling_player_i: int, bidding_player_i: int, rr_to_sell: str, min_bid: int) -> int:
        pass

    # Select engine/rail line to purchase
    @abstractmethod
    def get_purchase(self, s: GameState, player_i: int) -> str:
        pass

    # Ask a player whether they want to declare before setting alternate destination
    @abstractmethod
    def ask_to_declare(self, s: GameState, player_i: int) -> bool:
        pass

    # Announce a rover play (i.e. crossing the path of a declared player)
    @abstractmethod
    def announce_rover_play(self, s: GameState, decl_player_i: int, rover_player_i: int):
        pass

    # Display the final winner
    @abstractmethod
    def show_winner(self, s: GameState, winner_i: int):
        pass

def init_game(i: Interface, n_players: int) -> GameState:
    s = GameState()

    # Ask each player their name and create initial states
    for player_i in range(n_players):
        p = PlayerState(
            name=i.get_player_name(player_i),
            homeCity=-1,
            destination=-1,
            bank=0,
            engine=Engine.Basic)
        s.players.append(p)

    # Deposit initial 20k
    do_transaction(s, i, [INITIAL_BANK] * n_players)

    # Roll for home city for each player
    for player_i in range(n_players):
        s.players[player_i].set_home_city(i.get_home_city(s, player_i))

    return s

def do_transaction(s: GameState, i: Interface, bank_deltas: List[int]):
    for player_i, delta in enumerate(bank_deltas):
        assert s.players[player_i].bank + delta >= 0, "Cannot set bank balance negative"
        s.players[player_i].bank += delta
    i.update_bank_amts(s)

def do_move(s: GameState, i: Interface, player_i: int, d: int) -> List[Waypoint]:
    # Ask user for RRs and points to move through
    waypoints = i.get_player_move(s, player_i, d)
    pts = [s.players[player_i].location] + [pt for _,pt in waypoints]

    # Update location
    s.players[player_i].move(waypoints)

    # Check for a rover play
    for player_j, other_ps in enumerate(s.players):
        if other_ps.declared and other_ps.location in pts:
            i.announce_rover_play(s, player_j, player_i)

            bank_deltas = [0] * len(s.players)
            bank_deltas[player_j] = -ROVER_PLAY_FEE
            bank_deltas[player_i] = ROVER_PLAY_FEE
            do_transaction(s, i, bank_deltas)

            other_ps.declared = False

    return waypoints

def raise_funds(s: GameState, i: Interface, player_i: int, min_amt: int):
    i.display_shortfall(s, player_i, min_amt)
    amt_raised = 0

    while amt_raised < min_amt and len(s.players[player_i].rr_owned) > 0:
        rr_to_sell = i.select_rr_to_sell(s, player_i)
        min_sell_amt = s.map.railroads[rr_to_sell].cost / 2
        assert rr_to_sell in s.players[player_i].rr_owned, "Must own RR to sell it"

        sell_to_bank = False
        bank_deltas = [0] * len(s.players)
        if i.ask_to_auction(s, player_i, rr_to_sell):
            highest_bidder = -1
            highest_bid = -1
            bidder_i = player_i
            def incr_bidder():
                nonlocal bidder_i
                bidder_i = (bidder_i + 1) % len(s.players)
            incr_bidder()
            while True:
                if highest_bidder == bidder_i:
                    # We've passed around the table without changing high bid
                    bank_deltas[player_i] = highest_bid
                    bank_deltas[highest_bidder] = -highest_bid
                    do_transaction(s, i, bank_deltas)

                    amt_raised += highest_bid
                    s.players[player_i].rr_owned.remove(rr_to_sell)
                    s.players[highest_bidder].rr_owned.append(rr_to_sell)
                    i.update_owners(s)
                    break

                # Ask for a bid/pass (update if bid)
                min_bid = (min_sell_amt if highest_bid < 0  
                    else highest_bid + MIN_BID_INCR)
                bid = i.ask_for_bid(s, player_i, bidder_i, rr_to_sell, min_bid)
                assert bid == 0 or bid >= min_bid, "Must pass or bid at least min"
                if bid >= min_bid:
                    highest_bid = bid
                    highest_bidder = bidder_i

                incr_bidder()
                if bidder_i == player_i:
                    if highest_bid < 0:
                        # We've passed around the table with no bids
                        sell_to_bank = True
                        break
                    incr_bidder()
        else:
            sell_to_bank = True

        if sell_to_bank:
            bank_deltas[player_i] = min_sell_amt
            do_transaction(s, i, bank_deltas)

            amt_raised += min_sell_amt
            s.players[player_i].rr_owned.remove(rr_to_sell)
            i.update_owners(s)

def charge_user_fees(s: GameState, i: Interface, player_i: int, waypoints: List[Waypoint], init_rr: str = None):
    ps = s.players[player_i]

    # One-time calculation, looks at ownership of all RRs
    doubleFeeFlag = s.doubleFees
    _other_user_fee = OTHER_USER_FEE * (2 if doubleFeeFlag else 1)

    # charges[j] = True => we traveled on player j's lines
    # For simplicity, charges[player_i] is the bank fee
    charges = [False] * len(s.players)
    
    on_first_rr = init_rr is not None
    for rr, _ in waypoints:
        if rr != init_rr:
            on_first_rr = False
        elif on_first_rr:
            if ps.established_rate == 0 or rr in ps.rr_owned:
                continue # No charge if we started free or own it now
            elif ps.established_rate == BANK_USER_FEE:
                # If we established at the bank rate and we don't own it, we
                # pay the bank rate regardless
                charges[player_i] = True
                continue
        
        owner_i = s.get_owner(rr)
        if not on_first_rr:
            # Update established rate
            ps.established_rate = (
                0 if owner_i == player_i 
                else (BANK_USER_FEE if owner_i == -1 
                else OTHER_USER_FEE))

        charges[player_i if owner_i == -1 else owner_i] = True
    
    bank_deltas = [0] * len(s.players)
    for charge_i, do_charge in enumerate(charges):
        if not do_charge:
            continue
        if charge_i == player_i:
            bank_deltas[player_i] -= BANK_USER_FEE
        else:
            bank_deltas[player_i] -= _other_user_fee
            bank_deltas[charge_i] += _other_user_fee

    if ps.bank + bank_deltas[player_i] < 0:
        raise_funds(s, i, player_i, -(ps.bank + bank_deltas[player_i]))
    
    do_transaction(s, i, bank_deltas)

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
    s = init_game(i, n_players)
    
    player_i = 0
    while True:
        if check_for_winner(s,i, player_i):
            break

        # Record initial RR for user fee calculation later
        init_rr = s.players[player_i].rr

        # Roll for distance and move
        d1,d2 = i.roll_for_distance(player_i)
        waypoints = do_move(s, i, player_i, d1 + d2)

        if check_for_winner(s,i, player_i):
            break

        # Make a bonus roll and move if possible
        if s.players[player_i].check_bonus_roll(d1, d2):
            waypoints += do_move(s, i, player_i, i.bonus_roll(player_i))

        if check_for_winner(s,i, player_i):
            break

        # Pay the bank and/or other players for use of rails
        charge_user_fees(s, i, player_i, waypoints, init_rr)

        if check_for_winner(s,i, player_i):
            break

        # Move to the next player
        player_i += 1
        player_i = 0 if player_i >= n_players else player_i
    i.show_winner(s, player_i)