from pyrailbaron.game.screens.base import PyGameScreen
from pyrailbaron.game.constants import SCREEN_W, SCREEN_H

import pygame as pg

BUTTON_M = 20
BUTTON_H = 2 * SCREEN_H // 3
BUTTON_T = SCREEN_H - BUTTON_H - BUTTON_M
BUTTON_W = (SCREEN_W - 3 * BUTTON_M) / 2

LABEL_M = 30
LABEL_L = LABEL_M
LABEL_T = LABEL_M
LABEL_H = BUTTON_T - 2 * LABEL_M
LABEL_W = SCREEN_W - 2 * LABEL_M

class SellOrAuctionScreen(PyGameScreen):
    def __init__(self, screen: pg.surface.Surface, rr_to_sell: str, min_amt: int):
        super().__init__(screen)
        self.rr_to_sell = rr_to_sell
        self.min_amt = min_amt 
        self._auction = False

    @property
    def do_auction(self) -> bool:
        return self._auction

    def sell(self):
        self._auction = False

    def auction(self):
        self._auction = True

    def draw_button(self, label: str, bounds: pg.Rect):
        pg.draw.rect(self.screen, pg.Color(255,255,255),
            bounds, 0, 10)
        self.draw_text(label, 'Corrigan-ExtraBold', 60, bounds,
            pg.Color(0,0,0))

    def draw(self, init: bool):
        self.screen.fill(pg.Color(0,0,0))
        self.draw_text(f'Sell or auction {self.rr_to_sell}?',
            'Corrigan-ExtraBold', 70, 
            pg.Rect(LABEL_L, LABEL_T, LABEL_W, LABEL_H),
            pg.Color(255,255,255))
        self.buttons.clear()
        button_l = BUTTON_M
        self.add_button(f'SELL NOW\nTO BANK\nFOR\n{self.min_amt}',
            pg.Rect(button_l, BUTTON_T, BUTTON_W, BUTTON_H), 
            handler=self.sell, close_after=True)
        button_l += BUTTON_W + BUTTON_M
        self.add_button('AUCTION TO\nOTHER\nPLAYERS',
            pg.Rect(button_l, BUTTON_T, BUTTON_W, BUTTON_H), 
            handler=self.auction, close_after=True)

if __name__ == '__main__':
    pg.init()
    test_s = pg.display.set_mode((SCREEN_W, SCREEN_H))
    while True:
        sora = SellOrAuctionScreen(test_s, "B&O", 10000)
        sora.run()
        print(sora.do_auction)