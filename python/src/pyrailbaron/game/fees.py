from pyrailbaron.map.datamodel import Map
from pyrailbaron.map.datamodel import Waypoint
from pyrailbaron.game.constants import *

from typing import List, Tuple

# After all moves are completed on a player's turn, calculate the total charges
# to the bank and/or other players for rails used

# Returns bank_deltas[0..n], new_established_rate
def calculate_user_fees(m: Map, player_i: int,
        waypoints: List[Waypoint], player_rr: List[List[str]],
        init_rr: str | None, established_rate: int | None = None,
        doubleFees: bool = False) -> Tuple[List[int], int | None]:
    def get_owner(rr: str) -> int:
        for i, rr_owned in enumerate(player_rr):
            if rr in rr_owned:
                return i
        return -1

    # Determine who we have to pay charges to
    bank_charge = False
    player_charges = [False] * len(player_rr)
    on_first_rr = init_rr is not None
    new_established_rate = established_rate
    for rr, _ in waypoints:
        if rr != init_rr:
            # As soon as we leave the RR we were on, the established rate no
            # longer applies
            on_first_rr = False
        elif on_first_rr:
            if established_rate == 0 or rr in player_rr[player_i]:
                continue # No charge if we started free or own it now
            elif established_rate == BANK_USER_FEE:
                # If we established at the bank rate and we don't own it, we
                # pay the bank rate regardless
                bank_charge = True
                continue
        
        owner_i = get_owner(rr)
        if not on_first_rr:
            # Update established rate
            new_established_rate = (
                0 if owner_i == player_i 
                else (BANK_USER_FEE if owner_i == -1 
                else OTHER_USER_FEE))
        if owner_i == -1:
            bank_charge = True
        elif owner_i != player_i:
            player_charges[owner_i] = True

    # Calculate total transaction amounts; this will trigger selling as needed
    bank_deltas = [0] * len(player_rr)
    for charge_i, do_charge in enumerate(player_charges):
        if do_charge:
            assert charge_i != player_i, "Can't charge self user fees"
            bank_deltas[player_i] -= OTHER_USER_FEE * (2 if doubleFees else 1)
            bank_deltas[charge_i] += OTHER_USER_FEE * (2 if doubleFees else 1)
    if bank_charge:
        bank_deltas[player_i] -= BANK_USER_FEE
    return bank_deltas, new_established_rate