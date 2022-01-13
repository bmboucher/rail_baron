from pyrailbaron.game.screens.base import PyGameScreen
from pyrailbaron.game.constants import SCREEN_W, SCREEN_H
from pyrailbaron.game.moves import get_legal_moves_with_scores

import pygame as pg
from time import time
from random import shuffle, randint

from pyrailbaron.game.state import GameState, PlayerState
from typing import Tuple, List

OK_BUTTON_W = 130
OK_BUTTON_H = 40
OK_BUTTON_M = 10
OK_BUTTON_R = 10
OK_BUTTON_PROG_COLOR = pg.Color(0, 200, 0)
OK_BUTTON_COLOR = pg.Color(100, 255, 100)
OK_BUTTON_FONT = 'Corrigan-ExtraBold'
OK_BUTTON_FONT_SIZE = 18
OK_BUTTON_FONT_COLOR = pg.Color(0,0,0)

class AnnounceScreen(PyGameScreen):
    def __init__(self, screen: pg.surface.Surface, show_time: float):
        super().__init__(screen)
        self.show_time = show_time
        self._mark = time()

    def paint(self):
        pass # Override to define screen appearance

    def draw(self, init: bool):
        if init:
            self.screen.fill(pg.Color(0,0,0))
            self.paint()
            self.buttons.clear()
            self.add_button('OK', pg.Rect(0,0,SCREEN_W,SCREEN_H), 
                close_after=True)

    def animate(self) -> bool:
        t_elapsed = time() - self._mark
        if t_elapsed >= self.show_time:
            self.close(); return False
        pct = min(1.0, t_elapsed / self.show_time)
        if len(self.buttons) > 0 and pct > 0.1:
            assert self.buttons[0].label == 'OK', "Only button should be OK"
            ok_bounds = pg.Rect(
                SCREEN_W - OK_BUTTON_W - OK_BUTTON_M, 
                SCREEN_H - OK_BUTTON_H - OK_BUTTON_M, 
                OK_BUTTON_W, OK_BUTTON_H)
            pg.draw.rect(self.screen, OK_BUTTON_COLOR, ok_bounds, 0, OK_BUTTON_R)
            prog_bounds = pg.Rect(ok_bounds.left, ok_bounds.top, 
                ok_bounds.width * pct, ok_bounds.height)
            pg.draw.rect(self.screen, OK_BUTTON_PROG_COLOR, prog_bounds, 0, OK_BUTTON_R)
            self.draw_text('OK', OK_BUTTON_FONT, OK_BUTTON_FONT_SIZE,
                ok_bounds, OK_BUTTON_FONT_COLOR)
            pg.display.update(ok_bounds)
        return False

ANNOUNCE_TURN_TIME = 3.0
class AnnounceTurnScreen(AnnounceScreen):
    def __init__(self, screen: pg.surface.Surface, state: GameState, player_i: int):
        super().__init__(screen, ANNOUNCE_TURN_TIME)
        self.state = state
        self.player_i = player_i

    def paint(self):
        ps = self.state.players[self.player_i]
        self.draw_text(ps.name, 'Corrigan-ExtraBold', 75,
            pg.Rect(10,10,SCREEN_W,0), pg.Color(255,255,255), center=False)
        loc_n = self.state.map.points[ps.location].display_name
        dest_n = ('-' if ps.destinationIndex == -1 or ps.atDestination 
            else self.state.map.points[ps.destinationIndex].display_name)

        label_l = 100
        label_t = 120
        _, label_h = self.draw_text('LOCATION', 'Corrigan-ExtraBold', 20,
            pg.Rect(label_l,label_t,SCREEN_W-label_l,0), pg.Color(255,255,255),
            center=False)
        label_t += label_h * 1.25
        _, label_h = self.draw_text(loc_n, 'Corrigan-ExtraBold', 50,
            pg.Rect(label_l,label_t,SCREEN_W-label_l,0), pg.Color(255,255,255),
            center=False)
        label_t += label_h * 1.25 + 20
        _, label_h = self.draw_text('DESTINATION', 'Corrigan-ExtraBold', 20,
            pg.Rect(label_l,label_t,SCREEN_W-label_l,0), pg.Color(255,255,255),
            center=False)
        label_t += label_h * 1.25
        _, label_h = self.draw_text(dest_n, 'Corrigan-ExtraBold', 50,
            pg.Rect(label_l,label_t,SCREEN_W-label_l,0), pg.Color(255,255,255),
            center=False)
        label_t += label_h * 1.25 + 20
        _, label_h = self.draw_text(ps.engine.name.upper(), 'Corrigan-ExtraBold', 35,
            pg.Rect(label_l,label_t,SCREEN_W-label_l,0), pg.Color(255,255,255),
            center=False)
        label_t += label_h * 1.25
        if ps.declared:
            _, label_h = self.draw_text('CURRENTLY DECLARED', 'Corrigan-ExtraBold', 35,
                pg.Rect(label_l,label_t,SCREEN_W-label_l,0), pg.Color(255,255,0),
                center=False)
            label_t += label_h * 1.25

ANNOUNCE_ARRIVAL_TIME = 2.0
class AnnounceArrivalScreen(AnnounceScreen):
    def __init__(self, screen: pg.surface.Surface, city: str):
        super().__init__(screen, ANNOUNCE_ARRIVAL_TIME)
        self.img = self.load_image(f'city_welcome/{city.replace(".","").lower()}.jpg')

    def paint(self):
        img_w, _ = self.img.get_size()
        img_l = (SCREEN_W - img_w ) / 2
        self.screen.blit(self.img, (img_l, 0))

ANNOUNCE_PAYOFF_TIME = 5.0
PAYOFF_MAP_W = 420
PAYOFF_TEXT_M = 20
PAYOFF_TEXT_T = 60
class AnnouncePayoffScreen(AnnounceScreen):
    def __init__(self, screen: pg.surface.Surface, s: GameState, player_i: int):
        super().__init__(screen, ANNOUNCE_PAYOFF_TIME)
        self.state = s
        self.player_i = player_i
        assert self.state.players[player_i].atDestination, "Player must be at dest"

    @property
    def payoff(self) -> int:
        ps = self.state.players[self.player_i]
        assert ps.startCity, "Must know start city"
        assert ps.destination, "Must know destination"
        return self.state.route_payoffs[ps.startCity][ps.destination]

    @property
    def fees_paid(self) -> int:
        ps = self.state.players[self.player_i]
        return ps.trip_fees_paid

    @property
    def fees_received(self) -> int:
        ps = self.state.players[self.player_i]
        return ps.trip_fees_received

    def paint(self):
        self.screen.fill(pg.Color(0,0,0))
        m = self.state.map
        ps = self.state.players[self.player_i]

        label_l = PAYOFF_MAP_W + PAYOFF_TEXT_M
        label_t = PAYOFF_TEXT_T
        max_label_w = SCREEN_W - PAYOFF_TEXT_M - label_l
        _, label_h = self.draw_text('COMPLETED', 'Corrigan-ExtraBold', 35,
            pg.Rect(label_l, label_t, max_label_w, 0), pg.Color(255,0,0), center=False)
        label_t += 1.25 * label_h + 20
        _, label_h = self.draw_text(ps.displayStart, 'Corrigan-ExtraBold', 40,
            pg.Rect(label_l, label_t, max_label_w, 0), pg.Color(255,255,255), center=False)
        label_t += 1.25 * label_h
        _, to_label_h = self.draw_text('TO', 'Corrigan-ExtraBold', 20,
            pg.Rect(label_l, label_t, max_label_w, 0), pg.Color(255,255,255), center=False)
        label_t += to_label_h + 0.25 * label_h
        _, label_h = self.draw_text(ps.displayDestination, 'Corrigan-ExtraBold', 40,
            pg.Rect(label_l, label_t, max_label_w, 0), pg.Color(255,255,255), center=False)
        label_t += 1.25 * label_h + 20
        _, label_h = self.draw_text(f'{len(ps.history)} STOPS', 'Corrigan-ExtraBold',28,
            pg.Rect(label_l, label_t, max_label_w, 0), pg.Color(255,255,255), center=False)
        label_t += 1.25 * label_h + 15
        _, label_h = self.draw_text(f'{self.payoff} PAYOFF', 'Corrigan-ExtraBold', 28,
            pg.Rect(label_l, label_t, max_label_w, 0), pg.Color(255,255,0), center=False)
        label_t += 1.25 * label_h
        _, label_h = self.draw_text(f'{self.fees_paid} PAID', 'Corrigan-ExtraBold', 28,
            pg.Rect(label_l, label_t, max_label_w, 0), pg.Color(255,0,0), center=False)
        label_t += 1.25 * label_h
        _, label_h = self.draw_text(f'{self.fees_received} RECEIVED', 'Corrigan-ExtraBold', 28,
            pg.Rect(label_l, label_t, max_label_w, 0), pg.Color(0,255,0), center=False)

        trip_pts = [ps.startCityIndex] + [p for _,p in ps.history]
        trip_pt_coords = [m.points[pt_i].final_svg_coords for pt_i in trip_pts]
        min_coords = [min(p[i] for p in trip_pt_coords if p) for i in range(2)]
        max_coords = [max(p[i] for p in trip_pt_coords if p) for i in range(2)]
        coord_center = [(M + m) / 2 for m, M in zip(min_coords, max_coords)]
        coord_range = [max(1.2 * (M - m), 1e-6) for m, M in zip(min_coords, max_coords)]
        scale = min(PAYOFF_MAP_W/coord_range[0], SCREEN_H/coord_range[1])
        def transform(i: int) -> Tuple[float, float]:
            orig = m.points[trip_pts[i]].final_svg_coords
            assert orig, "Must know SVG coords"
            offset = [(o - c) * scale for o,c in zip(orig, coord_center)]
            return (PAYOFF_MAP_W/2 + offset[0], SCREEN_H/2 + offset[1])
        for i in range(1, len(trip_pts)):
            pg.draw.line(self.screen, pg.Color(255,255,255),
                transform(i - 1), transform(i), 2)
        for i in range(len(trip_pts)):
            color = (pg.Color(0,255,0) if i == 0 
                else pg.Color(255,0,0) if i == len(trip_pts) - 1 
                else pg.Color(255,255,255))
            pg.draw.circle(self.screen, color, transform(i), 4, 0)

ANNOUNCE_ORDER_TIME = 3.0
PLAYER_LABEL_FONT_SIZE = 40
PLAYER_LABEL_W = 250
PLAYER_LABEL_M = 40
PLAYER_NAME_FONT_SIZE = 60
PLAYER_ROW_SEP = 50

class AnnounceOrderScreen(AnnounceScreen):
    def __init__(self, screen: pg.surface.Surface, names: List[str]):
        super().__init__(screen, ANNOUNCE_ORDER_TIME)
        self.names = names

    def paint(self):
        labels: List[pg.surface.Surface] = []
        for i, name in enumerate(self.names):
            [pl, ], (pl_w, pl_h) = self.render_text(f'PLAYER {i+1}',
                'Corrigan-ExtraBold', PLAYER_LABEL_FONT_SIZE, 
                PLAYER_LABEL_W - PLAYER_LABEL_M, pg.Color(255,255,0))
            [pn, ], (_, pn_h) = self.render_text(name,
                'Corrigan-ExtraBold', PLAYER_NAME_FONT_SIZE,
                SCREEN_W - PLAYER_LABEL_W - PLAYER_LABEL_M, pg.Color(255,255,255))
            buf_h = max(pl_h, pn_h)
            buffer = pg.surface.Surface((SCREEN_W, buf_h))
            buffer.fill(pg.Color(0,0,0))
            buffer.blit(pl, (PLAYER_LABEL_W - pl_w, (buf_h - pl_h) / 2))
            buffer.blit(pn, (PLAYER_LABEL_W + PLAYER_LABEL_M, (buf_h - pn_h)/2))
            labels.append(buffer)
        self.screen.fill(pg.Color(0,0,0))
        total_label_h = (sum(l.get_height() for l in labels) 
            + (len(self.names) - 1) * PLAYER_ROW_SEP)
        label_t = (SCREEN_H - total_label_h)/2
        for label in labels:
            self.screen.blit(label, (0, label_t))
            label_t += label.get_height() + PLAYER_ROW_SEP

if __name__ == '__main__':
    pg.init()
    test_s = pg.display.set_mode((SCREEN_W, SCREEN_H))
    while True:
        s = GameState()
        ps = PlayerState(0, 'TEST')
        s.players.append(ps)

        home_region = s.random_lookup('REGION')
        home_city, home_city_i = s.map.lookup_city(s.random_lookup(home_region))

        dest_region = home_region
        while dest_region == home_region:
            dest_region = s.random_lookup('REGION')
        dest_city, dest_city_i = s.map.lookup_city(s.random_lookup(dest_region))

        s.set_player_home_city(0, home_city)
        s.set_player_destination(0, dest_city)
        moves_this_turn = 0
        while not ps.atDestination:
            moves = get_legal_moves_with_scores(s.map, ps.startCityIndex, ps.history,
                ps.destinationIndex, -1, moves_this_turn, [[]], 0, None, None, False)
            ps.history.append(moves[0].move)
        ps.bank = 25500

        names = ["ALEX","BRIAN","CHRIS","DENNIS"]
        shuffle(names)
        names = names[:randint(2,4)]
        order_screen = AnnounceOrderScreen(test_s, names)
        order_screen.run()

        turn_screen = AnnounceTurnScreen(test_s, s, 0)
        turn_screen.run()

        arrival_screen = AnnounceArrivalScreen(test_s, dest_city)
        arrival_screen.run()

        payoff_screen = AnnouncePayoffScreen(test_s, s, 0)
        payoff_screen.run()