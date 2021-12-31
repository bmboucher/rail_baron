"""Defines the basic game logic of Rail Baron, serves as an intermediary layer
between the GameState data model and an abstracted UI layer represented by
the Interface class"""
from pyrailbaron.game.interface import Interface
from pyrailbaron.game.state import Engine, GameState, PlayerState, Waypoint
from pyrailbaron.game.constants import *
from typing import List

# Basic game loop, will run to completion unless error
def run_game(n_players: int, i: Interface):
    # Setup the initial game state
    s = init_game(i, n_players)
    
    # Player index 0,1,2...n,0,1,2,... etc
    # Each loop is one player's turn, the loop only breaks when player_i wins
    player_i = 0
    while True:
        ps = s.players[player_i]

        # Roll for destination if needed
        check_destination(s, i, player_i)

        # Record initial RR for user fee calculation later
        init_rr = ps.rr

        # Roll for distance and move
        d1,d2 = i.roll_for_distance(s, player_i)
        # Need to check for bonus roll before move in case we buy an engine
        do_bonus = ps.check_bonus_roll(d1, d2)
        waypoints = do_move(s, i, player_i, d1 + d2)

        # Make a bonus roll and move if possible
        if do_bonus:
            # The first move could land in the home city for the win
            if check_for_winner(s, i, player_i):
                break

            # We may need a new destination
            check_destination(s, i, player_i)

            waypoints += do_move(s, i, player_i, i.bonus_roll(s, player_i))

        # Pay the bank and/or other players for use of rails
        charge_user_fees(s, i, player_i, waypoints, init_rr)

        # Collect payoff and/or win
        if check_for_winner(s,i, player_i):
            break

        # Move to the next player
        player_i = (player_i + 1) % n_players

    i.show_winner(s, player_i)

# Initialize the game state for all players
def init_game(i: Interface, n_players: int) -> GameState:
    s = GameState()

    # Ask each player their name and create initial states
    for player_i in range(n_players):
        p = PlayerState(
            index=player_i,
            name=i.get_player_name(player_i))
        s.players.append(p)

    # Deposit initial 20k
    update_balances(s, i, [INITIAL_BANK] * n_players)

    # Roll for home city for each player
    for player_i in range(n_players):
        s.set_player_home_city(player_i, i.get_home_city(s, player_i))

    return s

# Any time we need to update balances we call this method
def update_balances(s: GameState, i: Interface, bank_deltas: List[int],
        allow_selling: bool = False):
    # First check if any player will go negative, then sell/auction as needed
    for player_i, delta in enumerate(bank_deltas):
        new_balance = s.players[player_i].bank + delta
        if new_balance < 0:
            assert allow_selling, "Can only sell where explicitly allowed"
            raise_funds(s, i, player_i, -new_balance)

    # Update bank balances and display
    for player_i, delta in enumerate(bank_deltas):
        # Note that we floor negative balances at zero; its theoretically
        # possible for a player to sell all their RRs during raise_funds
        # and still not have enough balance to pay all fees - in this case,
        # the bank pays them (i.e. positive deltas are unaffected)
        ps = s.players[player_i]
        ps.bank = max(0, ps.bank + delta)
    i.update_bank_amts(s)

    # If a declared player falls below 200k they immediately become undeclared
    for ps in s.players:
        if ps.declared and ps.bank <= MIN_CASH_TO_WIN:
            ps.declared = False
            i.announce_undeclared(s, ps.index)
            check_destination(s, i, ps.index)

# During this step the user selects their moves for either the initial roll
# or the bonus roll; we don't collect user fees until both moves are done
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
            update_balances(s, i, bank_deltas)

            other_ps.declared = False

    # Check if player_i has reached destination for payoff/purchasing
    check_arrival(s, i, player_i)

    return waypoints

# Whenever a player needs to pay a higher fee than they have in the bank, they
# must sell or auction RRs to raise the needed funds
def raise_funds(s: GameState, i: Interface, player_i: int, min_amt: int):
    i.display_shortfall(s, player_i, min_amt)
    amt_raised = 0

    while amt_raised < min_amt and len(s.players[player_i].rr_owned) > 0:
        rr_to_sell = i.select_rr_to_sell(s, player_i)
        assert rr_to_sell in s.players[player_i].rr_owned, "Must own RR to sell it"
        min_sell_amt = s.map.railroads[rr_to_sell].cost // 2

        sell_to_bank = False
        if i.ask_to_auction(s, player_i, rr_to_sell):
            auction_price = auction(s, i, player_i, rr_to_sell, min_sell_amt)
            if auction_price > 0:
                amt_raised += auction_price
            else:
                sell_to_bank = True
        else:
            sell_to_bank = True

        if sell_to_bank:
            i.announce_sale_to_bank(s, player_i, rr_to_sell, min_sell_amt)

            bank_deltas = [0] * len(s.players)
            bank_deltas[player_i] = min_sell_amt
            update_balances(s, i, bank_deltas)

            amt_raised += min_sell_amt
            s.players[player_i].rr_owned.remove(rr_to_sell)
            i.update_owners(s)

# Auction a player's railroad and return the price (0 if no bids)
def auction(s: GameState, i: Interface, seller_i: int, rr_to_sell: str, min_sell_amt: int) -> int:
    highest_bidder = -1
    highest_bid = -1
    bidder_i = seller_i
    def incr_bidder():
        nonlocal bidder_i
        bidder_i = (bidder_i + 1) % len(s.players)
    incr_bidder()
    while True:
        if highest_bidder == bidder_i:
            # We've passed around the table without changing high bid,
            # so we close the sale
            assert highest_bid >= min_sell_amt, "Cannot close bidding less than min"
            i.announce_sale(s, 
                        seller_i, highest_bidder, rr_to_sell, highest_bid)
            bank_deltas = [0] * len(s.players)
            bank_deltas[seller_i] = highest_bid
            bank_deltas[highest_bidder] = -highest_bid
            update_balances(s, i, bank_deltas)

            s.players[seller_i].rr_owned.remove(rr_to_sell)
            s.players[highest_bidder].rr_owned.append(rr_to_sell)
            i.update_owners(s)
            return highest_bid

        # Ask for a bid/pass (update if bid)
        min_bid = (min_sell_amt if highest_bid < 0  
                    else highest_bid + MIN_BID_INCR)
        bid = i.ask_for_bid(s, seller_i, bidder_i, rr_to_sell, min_bid)
        assert bid == 0 or bid >= min_bid, "Must pass or bid at least min"
        assert bid <= s.players[bidder_i].bank, "Can't bid more than bank"
        if bid >= min_bid:
            highest_bid = bid
            highest_bidder = bidder_i

        incr_bidder()
        if bidder_i == seller_i:
            if highest_bid < 0:
                # We've passed around the table with no bids
                return 0
            incr_bidder()

# After all moves are completed on a player's turn, calculate the total charges
# to the bank and/or other players for rails used
def charge_user_fees(s: GameState, i: Interface, player_i: int, 
        waypoints: List[Waypoint], init_rr: str | None = None):
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
    update_balances(s, i, bank_deltas, allow_selling=True)

def check_destination(s: GameState, i: Interface, player_i: int) -> None:
    ps = s.players[player_i]
    needs_destination = (ps.destination is None or (
        ps.atDestination and not ps.declared))

    # Ask player if they want to declare when eligible
    if not ps.declared and ps.canDeclare:
        ps.declared = i.ask_to_declare(s, player_i)

    # Roll for destination (if declared, this is alt destination)
    if needs_destination:
        s.set_player_destination(player_i, i.get_destination(s, player_i))

def check_arrival(s: GameState, i: Interface, player_i: int):
    ps = s.players[player_i]
    if ps.declared or not ps.atDestination:
        # Haven't arrived yet
        return

    assert ps.startCity is not None, "Must know start city"
    assert ps.destination is not None, "Must know destination"

    # Calculate route payoff and distribute to player
    payoff = s.route_payoffs[ps.startCity][ps.destination]
    i.announce_route_payoff(s, player_i, payoff)
    bank_deltas = [0] * len(s.players)
    bank_deltas[player_i] = payoff
    update_balances(s, i, bank_deltas)

    # Allow player to purchase an engine or railroad
    do_purchase(s, i, player_i)
    
# Check if player_i meets the win condition
def check_for_winner(s: GameState, i: Interface, player_i: int) -> bool:
    ps = s.players[player_i]
    return ps.declared and ps.atHomeCity and ps.bank >= MIN_CASH_TO_WIN

# Purchase an engine or railroad after a payoff
def do_purchase(s: GameState, i: Interface, player_i: int):
    ps = s.players[player_i]
    purchase = i.get_purchase(s, player_i)
    if purchase is None:
        return # Player may not have enough funds, or may wish to skip purchase

    # Validate purchase and perform cash transaction
    if purchase == Engine.Express.name :
        assert ps.engine == Engine.Basic, "Can only upgrade basic -> express"
        purchase_amt = EXPRESS_FEE
    elif purchase == Engine.Superchief.name:
        assert ps.engine != Engine.Superchief, "Can't buy a superchief twice"
        purchase_amt = SUPERCHIEF_FEE
    else:
        assert purchase in s.map.railroads, "Must buy an engine or a railroad"
        assert purchase not in ps.rr_owned, "Can't buy a railroad twice"
        assert s.get_owner(purchase) == -1, "Can only buy RR from the bank"
        purchase_amt = s.map.railroads[purchase].cost
    assert purchase_amt <= ps.bank, "Can't spend more than bank on purchase"
    bank_deltas = [0] * len(s.players)
    bank_deltas[player_i] -= purchase_amt
    update_balances(s, i, bank_deltas)

    # Only apply the *results* of the purchase after the asserts :)
    if purchase == Engine.Express.name:
        ps.engine = Engine.Express
    elif purchase == Engine.Superchief.name:
        ps.engine = Engine.Superchief
    else:
        ps.rr_owned.append(purchase)
        i.update_owners(s)
