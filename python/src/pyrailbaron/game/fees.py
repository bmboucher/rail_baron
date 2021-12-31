from pyrailbaron.game.state import GameState
from pyrailbaron.map.datamodel import Waypoint
from pyrailbaron.game.constants import *

from typing import List

# After all moves are completed on a player's turn, calculate the total charges
# to the bank and/or other players for rails used
def calculate_user_fees(s: GameState, player_i: int, 
        waypoints: List[Waypoint], init_rr: str | None = None) -> List[int]:
    ps = s.players[player_i]

    # Do a one-time check if all RRs are owned; if so, user fees double
    _other_user_fee = OTHER_USER_FEE * (2 if s.doubleFees else 1)

    # Determine who we have to pay charges to
    bank_charge = False
    player_charges = [False] * len(s.players)    
    on_first_rr = init_rr is not None
    for rr, _ in waypoints:
        if rr != init_rr:
            # As soon as we leave the RR we were on, the established rate no
            # longer applies
            on_first_rr = False
        elif on_first_rr:
            if ps.established_rate == 0 or rr in ps.rr_owned:
                continue # No charge if we started free or own it now
            elif ps.established_rate == BANK_USER_FEE:
                # If we established at the bank rate and we don't own it, we
                # pay the bank rate regardless
                bank_charge = True
                continue
        
        owner_i = s.get_owner(rr)
        if not on_first_rr:
            # Update established rate
            ps.established_rate = (
                0 if owner_i == player_i 
                else (BANK_USER_FEE if owner_i == -1 
                else OTHER_USER_FEE))
        if owner_i == -1:
            bank_charge = True
        elif owner_i != player_i:
            player_charges[owner_i] = True

    # Calculate total transaction amounts; this will trigger selling as needed
    bank_deltas = [0] * len(s.players)
    for charge_i, do_charge in enumerate(player_charges):
        if do_charge:
            assert charge_i != player_i, "Can't charge self user fees"
            bank_deltas[player_i] -= _other_user_fee
            bank_deltas[charge_i] += _other_user_fee
    if bank_charge:
        bank_deltas[player_i] -= BANK_USER_FEE
    return bank_deltas