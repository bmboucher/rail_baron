from pyrailbaron.game.screens.base import PyGameScreen
from pyrailbaron.game.constants import SCREEN_W, SCREEN_H, MIN_CASH_TO_WIN

import pygame as pg
from pyrailbaron.game.state import GameState

LABEL_FONT = 'Corrigan-ExtraBold'
TOP_LABEL_FONT_SIZE = 70
TOP_LABEL_C = pg.Color(255, 255, 0)
MID_LABEL_FONT_SIZE = 60
MID_LABEL_C = pg.Color(255,255,255)
BUTTON_FONT_SIZE = 60
BUTTON_LABEL_C = pg.Color(0, 0, 0)
DECLARE_BTN_C = pg.Color(0, 255, 0)
WAIT_BTN_C = pg.Color(255, 0, 0)

DECLARE = 'DECLARE'
WAIT = 'WAIT'

TOP_LABEL_H = 60
TOP_LABEL_M = 10
MID_LABEL_H = 150
MID_LABEL_M = 20
BUTTON_M = 15
BUTTON_R = 15

TOP_LABEL_T = TOP_LABEL_M
TOP_LABEL_L = TOP_LABEL_M
TOP_LABEL_W = SCREEN_W - 2 * TOP_LABEL_M
TOP_LABEL_B = pg.Rect(TOP_LABEL_L, TOP_LABEL_T, TOP_LABEL_W, TOP_LABEL_H)

MID_LABEL_L = MID_LABEL_M
MID_LABEL_T = TOP_LABEL_B.bottom + MID_LABEL_M
MID_LABEL_W = SCREEN_W - 2 * MID_LABEL_M
MID_LABEL_B = pg.Rect(MID_LABEL_L, MID_LABEL_T, MID_LABEL_W, MID_LABEL_H)

BUTTON_T = MID_LABEL_B.bottom + BUTTON_M
BUTTON_W = (SCREEN_W - 3 * BUTTON_M)/2
BUTTON_H = SCREEN_H - BUTTON_T - 2 * BUTTON_M
DECLARE_BTN_L = BUTTON_M
WAIT_BTN_L = DECLARE_BTN_L + BUTTON_W + BUTTON_M
DECLARE_BTN_B = pg.Rect(DECLARE_BTN_L, BUTTON_T, BUTTON_W, BUTTON_H)
WAIT_BTN_B = pg.Rect(WAIT_BTN_L, BUTTON_T, BUTTON_W, BUTTON_H)

class DeclareScreen(PyGameScreen):
    def __init__(self, screen: pg.surface.Surface, player_name: str, home_city: str):
        super().__init__(screen)
        self.player_name = player_name
        self.home_city = home_city
        self._declare = False

    @property
    def declare(self) -> bool:
        return self._declare

    def set_declare(self):
        self._declare = True

    def draw_button(self, label: str, bounds: pg.Rect):
        color = DECLARE_BTN_C if label == DECLARE else WAIT_BTN_C
        pg.draw.rect(self.screen, color, bounds, 0, BUTTON_R)
        self.draw_text(label, LABEL_FONT, BUTTON_FONT_SIZE, bounds,
            BUTTON_LABEL_C)

    def draw(self, init: bool):
        self.screen.fill(pg.Color(0,0,0))
        self.draw_text(f'{self.player_name}, READY FOR YOUR FINAL TRIP?',
            LABEL_FONT, TOP_LABEL_FONT_SIZE, TOP_LABEL_B, TOP_LABEL_C)
        self.draw_text(f'Return to {self.home_city}\nwith {MIN_CASH_TO_WIN} to win!',
            LABEL_FONT, MID_LABEL_FONT_SIZE, MID_LABEL_B, MID_LABEL_C)
        if init:
            self.buttons.clear()
            self.add_button(DECLARE, DECLARE_BTN_B, handler=self.set_declare,
                close_after=True)
            self.add_button(WAIT, WAIT_BTN_B, close_after=True)

if __name__ == '__main__':
    pg.init()
    test_s = pg.display.set_mode((SCREEN_W, SCREEN_H))
    s = GameState()
    while True:
        region = s.random_lookup('REGION')
        city = s.random_lookup(region)
        city, _ = s.map.lookup_city(city)
        dec_screen = DeclareScreen(test_s, 'TEST', city.replace("_",""))
        dec_screen.run()
        print(dec_screen.declare)