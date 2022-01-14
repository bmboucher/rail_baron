from pyrailbaron.game.screens.announce import AnnounceWinnerScreen
from pyrailbaron.game.screens.move import MoveScreen
from pyrailbaron.game.state import GameState
from pyrailbaron.game.interface import Interface
from pyrailbaron.game.logic import run_game
from pyrailbaron.teensy.serial import Serial

import pygame as pg

from pyrailbaron.game.screens import (
    SplashScreen, MainMenuScreen, RollScreen, RegionRoll, CityRoll, KeyboardScreen,
    PurchaseSelectScreen, RegionSelectScreen, AnnounceTurnScreen, AnnounceArrivalScreen,
    AnnouncePayoffScreen, SellOrAuctionScreen, AuctionScreen, DeclareScreen,
    AnnounceOrderScreen, AnnounceShortfallScreen, AnnounceSaleScreen,
    AnnounceUndeclaredScreen, AnnounceRoverScreen)
from pyrailbaron.game.constants import SCREEN_W, SCREEN_H

from typing import List, Tuple

SCREENRECT = pg.Rect(0,0,SCREEN_W,SCREEN_H)

SPLASH_SCREEN_TIME: float = 5.0
BUTTON_MARGIN: int = 40

class PyGame_Interface(Interface):
    def __init__(self):
        super().__init__()
        pg.init()
        self.screen = pg.display.set_mode(SCREENRECT.size)
        self.n_cpu_players: int = 0

    def display_splash(self):
        SplashScreen(self.screen).run()

    def run_game(self, n_players: int):
        assert n_players > 1, "Must have at least two players"
        run_game(n_players, self)

    def get_player_name(self) -> str:
        name = KeyboardScreen(self.screen).run().text
        assert name == name.upper(), "Player name should be uppercase"
        assert len(name) > 0, "Player name must have >0 characters"
        assert not name.startswith('CPU'), "Player names cannot start with CPU"
        return name

    def announce_player_order(self, s: GameState):
        names = [ps.name for ps in s.players]
        AnnounceOrderScreen(self.screen, names).run()

    def get_home_city(self, s: GameState, player_i: int) -> str:
        Serial.set_active_player(player_i, len(s.players))

        home_region = RegionRoll(self.screen, s, player_i, 
            'HOME REGION').run().result
        assert home_region, "Must have home region after roll"

        home_city = CityRoll(self.screen, s, player_i, home_region, 
            'HOME CITY', is_home_city=True).run().result
        assert home_city, "Must have home city after roll"
        return home_city

    def announce_turn(self, s: GameState, player_i: int):
        Serial.set_active_player(player_i, len(s.players))
        AnnounceTurnScreen(self.screen, s, player_i).run()

    def get_destination(self, s: GameState, player_i: int) -> str:
        ps = s.players[player_i]
        start_loc = ps.location
        start_region = s.map.points[start_loc].region
        assert start_region, "Must know start region to get destination"

        dest_region = RegionRoll(self.screen, s, player_i, 
            'DEST REGION').run().result
        if dest_region == start_region:
            curr_city = ps.destination or ps.homeCity or ''
            region_payoffs = s.get_expected_region_payoffs(curr_city)
            dest_region = RegionSelectScreen(self.screen, region_payoffs).run().selected
        assert dest_region, "Must have dest region after roll"

        def get_dest():
            dest = CityRoll(self.screen, s, player_i, dest_region, 
                'DESTINATION').run().result
            assert dest, "Must have destination after roll"
            return s.map.lookup_city(dest)
        dest, dest_i = get_dest()
        while dest_i == start_loc:
            dest, dest_i = get_dest()
        return dest

    def roll_for_distance(self, s: GameState, player_i: int) -> Tuple[int, int]:
        pn = s.players[player_i].name
        roll_screen = RollScreen(self.screen, 2, f'{pn} > DISTANCE')
        roll_screen.run()
        roll = roll_screen.roll
        assert len(roll) == 2, 'Roll for distance must return 2 die'
        return (roll[0], roll[1])

    def bonus_roll(self, s: GameState, player_i: int) -> int:
        pn = s.players[player_i].name
        roll_screen = RollScreen(self.screen, 1, f'{pn} > BONUS ROLL')
        roll_screen.run()
        roll = roll_screen.roll
        assert len(roll) == 1, 'Roll for distance must return 2 die'
        return roll[0]

    def get_player_move(self, 
            s: GameState, player_i: int, d: int, 
            init_rr: str | None, moves_so_far: int) -> List[Tuple[str, int]]:
        move_screen = MoveScreen(self.screen, s, player_i, 
            d, init_rr, moves_so_far)
        move_screen.run()
        return move_screen.selected_moves

    def update_bank_amts(self, s: GameState):
        Serial.update_bank_amounts(s)

    def update_owners(self, s: GameState):
        Serial.update_owners(s)

    def display_shortfall(self, s: GameState, player_i: int, amt: int):
        ps = s.players[player_i]
        rr_owned = [s.map.railroads[rr].shortName for rr in ps.rr_owned]
        rr_sell_value = sum(s.map.railroads[rr].cost for rr in ps.rr_owned) // 2
        AnnounceShortfallScreen(self.screen, ps.name, amt, rr_owned, rr_sell_value).run()

    def select_rr_to_sell(self, s: GameState, player_i: int, amt_required: int) -> str:
        assert len(s.players[player_i].rr_owned) > 0, "Must have at least 1 RR to sell"
        return PurchaseSelectScreen(self.screen, s, player_i, 0, True, amt_required).run().selected[0]

    def announce_route_payoff(self, s: GameState, player_i: int, payoff: int):
        ps = s.players[player_i]
        loc = s.map.points[ps.location]
        city_name = ps.destination
        assert city_name in loc.city_names, "Should only announce route payoff at destination"
        AnnounceArrivalScreen(self.screen, city_name).run()
        AnnouncePayoffScreen(self.screen, s, player_i).run()

    def ask_to_auction(self, s: GameState, player_i: int, rr_to_sell: str) -> bool:
        rr_name = s.map.railroads[rr_to_sell].shortName
        min_amt = s.map.railroads[rr_to_sell].cost // 2
        if len([ps for ps in s.players 
                if ps.index != player_i and ps.bank >= min_amt]) < 2:
            # If 0 players can bid, will immediately sell to bank anyways
            # If 1 player can bid, no incentive to auction
            return False
        return SellOrAuctionScreen(self.screen, rr_name, min_amt).run().do_auction

    def ask_for_bid(self, s: GameState, selling_player_i: int, bidding_player_i: int, rr_to_sell: str, min_bid: int) -> int:
        ps = s.players[bidding_player_i]
        if ps.bank < min_bid:
            return 0
        rr_name = s.map.railroads[rr_to_sell].shortName
        return AuctionScreen(self.screen, ps.name, rr_name, min_bid, ps.bank).run().bid

    def announce_sale(self, s: GameState, seller_i: int, buyer_i: int, rr: str, price: int):
        seller_n = s.players[seller_i].name
        buyer_n = s.players[buyer_i].name
        rr_name = s.map.railroads[rr].shortName
        AnnounceSaleScreen(self.screen, seller_n, buyer_n, rr_name, price).run()

    def announce_sale_to_bank(self, s: GameState, seller_i: int, rr: str, price: int):
        seller_n = s.players[seller_i].name
        rr_name = s.map.railroads[rr].shortName
        AnnounceSaleScreen(self.screen, seller_n, 'THE BANK', rr_name, price).run()

    def get_purchase(self, s: GameState, player_i: int, user_fee: int) -> str|None:
        if len(s.get_player_purchase_opts(player_i)) == 0:
            return None
        opt = PurchaseSelectScreen(self.screen, s, player_i, user_fee).run().selected
        if opt:
            return opt[0]
        else:
            return None

    def ask_to_declare(self, s: GameState, player_i: int) -> bool:
        ps = s.players[player_i]
        return DeclareScreen(self.screen, ps.name, ps.displayHomeCity).run().declare

    def announce_undeclared(self, s: GameState, player_i: int):
        AnnounceUndeclaredScreen(self.screen, s.players[player_i].name).run()
    
    def announce_rover_play(self, s: GameState, decl_player_i: int, rover_player_i: int):
        AnnounceRoverScreen(self.screen,
            s.players[decl_player_i].name,
            s.players[rover_player_i].name,
            s.map.points[s.players[decl_player_i].location].display_name).run()

    def show_winner(self, s: GameState, winner_i: int):
        AnnounceWinnerScreen(self.screen, s.players[winner_i].name).run()
        
    def run(self):
        self.display_splash()
        while True:
            main_menu = MainMenuScreen(self.screen)
            main_menu.run()
            if main_menu.start_game:
                print('Running game')
                self.run_game(main_menu.n_players)

if __name__ == '__main__':
    i = PyGame_Interface()
    i.run()