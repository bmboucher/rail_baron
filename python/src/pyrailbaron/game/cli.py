#pyright: reportPrivateUsage=information
from pyrailbaron.game.constants import MIN_CASH_TO_WIN
from pyrailbaron.game.interface import Interface
from pyrailbaron.game.state import GameState, Waypoint
from pyrailbaron.game.moves import calculate_legal_moves
from pyrailbaron.game.logic import run_game

from random import randint
from typing import Tuple, List, Optional

def roll2() -> Tuple[int, int]:
    rolls = randint(1,6), randint(1,6)
    print(f'  ROLLS: {rolls}')
    return rolls

def roll3() -> Tuple[int, int, int]:
    rolls = randint(1,6), randint(1,6), randint(1,6)
    print(f'  ROLLS: {rolls}')
    return rolls

REGIONS: List[str] = [
    'NORTHWEST','SOUTHWEST','PLAINS',
    'NORTH CENTRAL','SOUTH CENTRAL','NORTHEAST','SOUTHEAST']

class CLI_Interface(Interface):
    def get_player_name(self, player_i: int) -> str:
        return input(f'Player {player_i + 1} name: ')

    def get_home_city(self, s: GameState, player_i: int) -> str:
        pn = s.players[player_i].name
        print(f'{pn} >> ROLL FOR HOME CITY')
        region = s.lookup_roll_table('REGION', *roll3())
        print(f'  Region = {region}')
        city = s.lookup_roll_table(region, *roll3())
        city, _ = s.map.lookup_city(city)
        print(f'  Home city = {city}\n')
        return city

    def get_destination(self, s: GameState, player_i: int) -> str:
        ps = s.players[player_i]
        print(f'{ps.name} >> ROLL FOR DESTINATION')
        region = s.lookup_roll_table('REGION', *roll3())
        print(f'  Region = {region}')
        player_region = s.map.points[ps.location].region
        if region == player_region:
            print('  YOU CHOOSE: ')
            for i,r in enumerate(REGIONS):
                print(f'    [{i}] {r}')
            region = REGIONS[int(input(f'  {ps.name} >> Select region: '))]
        city = s.lookup_roll_table(region, *roll3())
        city, city_i = s.map.lookup_city(city)
        while city_i == ps.location:
            city = s.lookup_roll_table(region, *roll3())
            city, city_i = s.map.lookup_city(city)
        print(f'  Destination = {city}\n')
        return city
    
    def roll_for_distance(self, s: GameState, player_i: int) -> Tuple[int, int]:
        print(f'{s.players[player_i].name} >> ROLL FOR DISTANCE')
        return roll2()

    def bonus_roll(self, s: GameState, player_i: int) -> int:
        print(f'{s.players[player_i].name} >> BONUS ROLL')
        roll = randint(1,6)
        print(f'You rolled a {roll}')
        return roll

    def get_player_move(self, s: GameState, player_i: int, d: int) -> List[Waypoint]:
        ps = s.players[player_i]
        print(f'{ps.name} >>> MOVE {d} SPACES')
        print(f'  Current location: {s.map.points[ps.location].place_name} ({ps.location})')
        dest_i = ps._destinationIndex if not ps.declared else ps._homeCityIndex
        print(f'  Destination: {ps.destination if not ps.declared else ps.homeCity} ({dest_i})\n')
        waypoints: List[Waypoint] = []
        def move_str(wp: Waypoint):
            rr, pt_i = wp
            return f'Take the {s.map.railroads[rr].shortName} to {s.map.points[pt_i].place_name} ({pt_i})'
        curr_pt = ps.location
        for _ in range(d):           
            moves = calculate_legal_moves(s.map, ps._startCityIndex, ps.history + waypoints)
            assert len(moves) > 0, "Must have at least one legal move!"
            if len(moves) == 1:
                print(f'AUTO >> {move_str(moves[0])}')
                next_wp = moves[0]
            else:
                def dist_to_dest(pt_i: int) -> float:
                    return s.map.gc_distance(dest_i, pt_i)
                curr_dist = dist_to_dest(curr_pt)
                moves = list(sorted(moves, key=lambda wp: dist_to_dest(wp[1])))
                print('You must choose...')
                for i, wp in enumerate(moves):
                    delta = dist_to_dest(wp[1]) - curr_dist
                    delta_str = f'{-delta:.1f}mi closer' if delta < 0 else f'{delta:.1f}mi farther'
                    print(f'  [{i}] {move_str(wp)} ({delta_str})')
                next_wp = moves[int(input('YOUR CHOICE >>> '))]
            waypoints.append(next_wp)
            curr_pt = next_wp[1]
            if curr_pt == dest_i:
                break
        return waypoints

    def update_bank_amts(self, s: GameState):
        print('========\nBANK SUMMARY:')
        for ps in s.players:
            print(f'  {ps.name:10} = {ps.bank:10}')
        print()

    def update_owners(self, s: GameState):
        print('========\nRAILROADS OWNED:')
        for ps in s.players:
            print(f'  {ps.name:10} = {", ".join(ps.rr_owned)}')
        print()

    def display_shortfall(self, s: GameState, player_i: int, amt: int):
        ps = s.players[player_i]
        print(f'{ps.name} >> FUNDS OF {ps.bank} ARE INSUFFICIENT BY {amt}')

    def select_rr_to_sell(self, s: GameState, player_i: int) -> str:
        ps = s.players[player_i]
        assert len(ps.rr_owned) > 0, "Can't ask to sell RRs when none owned"
        print(f'{ps.name} >> SELECT A RAILROAD TO SELL')
        for i,rr in enumerate(ps.rr_owned):
            rr_data = s.map.railroads[rr]
            print(f'  [{i}] {rr_data.shortName} (COST = {rr_data.cost})')
        return ps.rr_owned[int(input('YOUR CHOICE >>> '))]

    def announce_route_payoff(self, s: GameState, player_i: int, amt: int):
        ps = s.players[player_i]
        print(f'{ps.name} HAS COMPLETED {ps.startCity} TO {ps.destination}!')
        print(f'{len(ps.history)} stops, payoff = {amt}')

    def ask_to_auction(self, s: GameState, player_i: int, rr_to_sell: str) -> bool:
        print('Choose...')
        print('  [A] Auction to other players')
        print('  [S] Sell immediately to bank')
        return input('A or S: ').upper().strip() == 'A'

    def ask_for_bid(self, s: GameState, selling_player_i: int, bidding_player_i: int, rr_to_sell: str, min_bid: int) -> int:
        ps = s.players[bidding_player_i]
        if ps.bank >= min_bid:
            return int(input(f'{ps.name} >>> ENTER BID (MIN = {min_bid}, MAX = {ps.bank}, PASS = 0): '))
        else:
            print(f'{ps.name} PASSES (NOT ENOUGH BANK)')
            return 0

    def announce_sale(self, s: GameState, seller_i: int, buyer_i: int, rr: str, price: int):
        print(f'SOLD! {s.players[buyer_i].name} BUYS {rr} FOR {price} FROM {s.players[seller_i].name}')

    def announce_sale_to_bank(self, s: GameState, seller_i: int, rr: str, price: int):
        print(f'{s.players[seller_i].name} SELLS {rr} TO THE BANK FOR {price}')

    def get_purchase(self, s: GameState, player_i: int) -> Optional[str]:
        options: List[Tuple[str, int]] = s.get_player_purchase_opts(player_i)
        print(f'{s.players[player_i].name} >>> SELECT PURCHASE')
        print('  [0] NONE')
        for opt_i, (opt, p) in enumerate(options):
            print(f'  [{opt_i+1}] {opt:10} {p:10}')
        sel = int(input('Your choice: '))
        if sel == 0:
            return None
        else:
            return options[sel - 1][0]

    def ask_to_declare(self, s: GameState, player_i: int) -> bool:
        ps = s.players[player_i]
        print(f'{ps.name} >>> DO YOU WANT TO DECLARE?')
        print(f'You currently have {ps.bank} - you will need to return to {ps.homeCity} with {MIN_CASH_TO_WIN} to win')
        return input('Declare for your trip home (Y/N)? ').upper().strip() == 'Y'

    def announce_undeclared(self, s: GameState, player_i: int):
        ps = s.players[player_i]
        print(f'{ps.name} HAS BECOME UNDECLARED (BANK {ps.bank} FELL BELOW {MIN_CASH_TO_WIN})')

    def announce_rover_play(self, s: GameState, decl_player_i: int, rover_player_i: int):
        dec_pn = s.players[decl_player_i].name
        rov_pn = s.players[rover_player_i].name
        loc_n = s.map.points[s.players[decl_player_i].location].place_name
        print(f'{rov_pn} HAS PULLED OFF A ROVER PLAY AT {loc_n}')
        print(f'{dec_pn} IS NO LONGER DECLARED')

    def show_winner(self, s: GameState, winner_i: int):
        print(f'{s.players[winner_i].name} IS THE WINNER !!!!!')
        print('\nFINAL SUMMARY')
        print('         PLAYER       BANK   RRS')
        for p in s.players:
            print(f'{p.name:15} {p.bank:10} {len(p.rr_owned):6}')

if __name__ == '__main__':
    i = CLI_Interface()
    run_game(2,i)