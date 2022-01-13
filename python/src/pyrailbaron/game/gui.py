from pyrailbaron.game.screens.move import MoveScreen
from pyrailbaron.game.state import GameState
from pyrailbaron.map.datamodel import Coordinate
from pyrailbaron.game.interface import Interface
from pyrailbaron.game.logic import run_game
from pyrailbaron.teensy.serial import Serial

import pygame as pg

from pyrailbaron.game.screens import (
    SplashScreen, MainMenuScreen, RollScreen, RegionRoll, CityRoll, KeyboardScreen,
    PurchaseSelectScreen, RegionSelectScreen, AnnounceTurnScreen, AnnounceArrivalScreen,
    AnnouncePayoffScreen, SellOrAuctionScreen, AuctionScreen, DeclareScreen,
    AnnounceOrderScreen)
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

    def _draw_buttons(self, start_pt: Coordinate, size: Coordinate, n_buttons: int = 1):
        x, y = start_pt
        w, h = size
        button_w = (w - (n_buttons-1)*BUTTON_MARGIN) // n_buttons
        button_c = (170,170,170)
        for _ in range(n_buttons):
            pg.draw.rect(self.screen, button_c, pg.Rect(x, y, button_w, h), 0, 10)
            x += button_w + BUTTON_MARGIN

    def display_splash(self):
        SplashScreen(self.screen).run()

    def run_game(self, n_players: int):
        assert n_players > 1, "Must have at least two players"
        run_game(n_players, self)

    def get_player_name(self) -> str:
        keyboard = KeyboardScreen(self.screen)
        keyboard.run()
        assert len(keyboard.text) > 0, "Player name must have >0 characters"
        assert not keyboard.text.startswith('CPU'), "Player names cannot start with CPU"
        return keyboard.text

    def announce_player_order(self, s: GameState):
        names = [ps.name for ps in s.players]
        ord_screen = AnnounceOrderScreen(self.screen, names)
        ord_screen.run()

    def get_home_city(self, s: GameState, player_i: int) -> str:
        Serial.set_active_player(player_i, len(s.players))

        roll_screen = RegionRoll(self.screen, s, player_i, 'HOME REGION')
        roll_screen.run()
        home_region = roll_screen.result
        assert home_region, "Must have home region aftet roll"

        roll_screen = CityRoll(self.screen, s, player_i, home_region, 
            'HOME CITY', is_home_city=True)
        roll_screen.run()
        home_city = roll_screen.result
        assert home_city, "Must have home city after roll"
        return home_city

    def announce_turn(self, s: GameState, player_i: int):
        Serial.set_active_player(player_i, len(s.players))
        ann = AnnounceTurnScreen(self.screen, s, player_i)
        ann.run()

    def get_destination(self, s: GameState, player_i: int) -> str:
        home_region = s.map.points[s.players[player_i].location].region
        assert home_region, "Must know start region to get destination"

        roll_screen = RegionRoll(self.screen, s, player_i, 'DEST REGION')
        roll_screen.run()
        dest_region = roll_screen.result
        if dest_region == home_region:
            reg_sel_screen = RegionSelectScreen(self.screen)
            reg_sel_screen.run()
            dest_region = reg_sel_screen.selected
        assert dest_region, "Must have dest region after roll"

        roll_screen = CityRoll(self.screen, s, player_i, dest_region, 'DESTINATION')
        roll_screen.run()
        destination = roll_screen.result
        assert destination, "Must have home city after roll"
        return destination

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
        # TODO: Implement
        pass

    def display_shortfall(self, s: GameState, player_i: int, amt: int):
        # TODO: Implement
        pass

    def select_rr_to_sell(self, s: GameState, player_i: int, amt_required: int) -> str:
        assert len(s.players[player_i].rr_owned) > 0, "Must have at least 1 RR to sell"
        sell_screen = PurchaseSelectScreen(self.screen, s, player_i, 0, True, amt_required)
        sell_screen.run()
        return sell_screen.selected[0]

    def announce_route_payoff(self, s: GameState, player_i: int, payoff: int):
        ps = s.players[player_i]
        loc = s.map.points[ps.location]
        city_name = ps.destination
        assert city_name in loc.city_names, "Should only announce route payoff at destination"
        arr_screen = AnnounceArrivalScreen(self.screen, city_name)
        arr_screen.run()

        payoff_screen = AnnouncePayoffScreen(self.screen, s, player_i)
        payoff_screen.run()

    def ask_to_auction(self, s: GameState, player_i: int, rr_to_sell: str) -> bool:
        rr_name = s.map.railroads[rr_to_sell].shortName
        min_amt = s.map.railroads[rr_to_sell].cost // 2
        if not any(ps.index != player_i and ps.bank >= min_amt
            for ps in s.players):
            return False
        soa_screen = SellOrAuctionScreen(self.screen, rr_name, min_amt)
        soa_screen.run()
        return soa_screen.do_auction

    def ask_for_bid(self, s: GameState, selling_player_i: int, bidding_player_i: int, rr_to_sell: str, min_bid: int) -> int:
        ps = s.players[bidding_player_i]
        if ps.bank < min_bid:
            return 0
        rr_name = s.map.railroads[rr_to_sell].shortName
        auct_screen = AuctionScreen(self.screen, ps.name, rr_name, min_bid, ps.bank)
        auct_screen.run()
        return auct_screen.bid

    def announce_sale(self, s: GameState, seller_i: int, buyer_i: int, rr: str, price: int):
        # TODO: Implement
        pass

    def announce_sale_to_bank(self, s: GameState, seller_i: int, rr: str, price: int):
        # TODO: Implement
        pass

    def get_purchase(self, s: GameState, player_i: int, user_fee: int) -> str|None:
        if len(s.get_player_purchase_opts(player_i)) == 0:
            return None
        ps = PurchaseSelectScreen(self.screen, s, player_i, user_fee)
        ps.run()
        opt: Tuple[str, int]|None = ps.selected
        if opt:
            return opt[0]
        else:
            return None

    def ask_to_declare(self, s: GameState, player_i: int) -> bool:
        ps = s.players[player_i]
        dec_screen = DeclareScreen(self.screen, ps.name, ps.displayHomeCity)
        dec_screen.run()
        return dec_screen.declare

    def announce_undeclared(self, s: GameState, player_i: int):
        # TODO: Implement
        pass
    
    def announce_rover_play(self, s: GameState, decl_player_i: int, rover_player_i: int):
        # TODO: Implement
        pass

    def show_winner(self, s: GameState, winner_i: int):
        # TODO: Implement
        pass
        
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