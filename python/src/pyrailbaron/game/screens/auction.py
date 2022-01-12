from pyrailbaron.game.constants import MIN_BID_INCR, SCREEN_W, SCREEN_H
from pyrailbaron.game.screens.base import PyGameScreen

from enum import Enum, auto

import pygame as pg

AP_BTN_H = 150
AP_BTN_M = 20
AP_BTN_T = SCREEN_H - AP_BTN_H - AP_BTN_M
AP_BTN_W = (SCREEN_W - 3 * AP_BTN_M) / 2

AP_BID_M = 10
BID_M = 20
BID_BTN_W = 150
BID_BTN_M = 10
BID_H = 200
BID_T = AP_BTN_T - AP_BID_M - BID_H
BID_LABEL_L = BID_M
BID_LABEL_T = BID_T + BID_M
BID_LABEL_W = SCREEN_W - 3 * BID_M - BID_BTN_W
BID_LABEL_H = BID_H - 2 * BID_M
BID_BTN_H = (BID_H - 3 * BID_BTN_M) / 2
BID_BTN_L = SCREEN_W - BID_BTN_W - BID_M

TOP_LABEL_M = 10
TOP_LABEL_H = BID_T - 2 * TOP_LABEL_M
TOP_LABEL_L = TOP_LABEL_M
TOP_LABEL_T = TOP_LABEL_M
TOP_LABEL_W = SCREEN_W - 2 * TOP_LABEL_M

BTN_TEXT_M = 5

class AuctionScreen(PyGameScreen):
    def __init__(self, screen: pg.surface.Surface, player_name: str, rr_name: str, min_bid: int, bank: int):
        super().__init__(screen)
        assert bank >= min_bid, "Can only ask for bids if bank >= min"
        self.player_name = player_name
        self.rr_name = rr_name
        self.min_bid = min_bid
        self.bank = bank
        self._bid = min_bid
        self._pass = False

    class Button(Enum):
        Bid = auto()
        Pass = auto()
        More = auto()
        Less = auto()

    @property
    def bid(self) -> int:
        return 0 if self._pass else self._bid

    def accept_bid(self):
        self._pass = False

    def pass_bid(self):
        self._pass = True

    def more(self):
        self._bid = min(self.bid + MIN_BID_INCR, self.bank)

    def less(self):
        self._bid = max(self.min_bid, self.bid - MIN_BID_INCR)

    def draw_button(self, label: str, bounds: pg.Rect):
        font_size = 120
        if label in [AuctionScreen.Button.Less.name, 
                     AuctionScreen.Button.More.name]:
            if label == AuctionScreen.Button.Less.name:
                enabled = self.bid > self.min_bid
            else:
                enabled = self.bid < self.bank
            color = pg.Color(255,255,255) if enabled else pg.Color(50,50,50)
            font_size = 50
        elif label == AuctionScreen.Button.Bid.name:
            color = pg.Color(0,255,0)
        else:
            color = pg.Color(255,0,0)

        pg.draw.rect(self.screen, color, bounds, 0, 10)
        text_bounds = pg.Rect(bounds.left + BTN_TEXT_M, bounds.top + BTN_TEXT_M,
            bounds.width - 2 * BTN_TEXT_M, bounds.height - 2 *BTN_TEXT_M)
        self.draw_text(label.upper(), 'Corrigan-ExtraBold', font_size,
            text_bounds, pg.Color(0,0,0))

    def draw(self, init: bool):
        self.screen.fill(pg.Color(0,0,0))
        
        self.draw_text(f'{self.player_name} > BID ON {self.rr_name}',
            'Corrigan-ExtraBold', 80,
            pg.Rect(TOP_LABEL_L, TOP_LABEL_T, TOP_LABEL_W, TOP_LABEL_H),
            pg.Color(255,255,255))

        self.draw_text(str(self.bid), 'Corrigan-ExtraBold', 200,
            pg.Rect(BID_LABEL_L, BID_LABEL_T, BID_LABEL_W, BID_LABEL_H),
            pg.Color(255,255,0))

        if init:
            self.buttons.clear()
            bid_btn_t = BID_T + BID_BTN_M
            self.add_button(AuctionScreen.Button.More.name,
                pg.Rect(BID_BTN_L, bid_btn_t, BID_BTN_W, BID_BTN_H), self.more)
            bid_btn_t += BID_BTN_H + BID_BTN_M
            self.add_button(AuctionScreen.Button.Less.name,
                pg.Rect(BID_BTN_L, bid_btn_t, BID_BTN_W, BID_BTN_H), self.less)

            ap_btn_l = AP_BTN_M
            self.add_button(AuctionScreen.Button.Bid.name,
                pg.Rect(ap_btn_l, AP_BTN_T, AP_BTN_W, AP_BTN_H), self.accept_bid, 
                close_after=True)
            ap_btn_l += AP_BTN_W + AP_BTN_M
            self.add_button(AuctionScreen.Button.Pass.name,
                pg.Rect(ap_btn_l, AP_BTN_T, AP_BTN_W, AP_BTN_H), self.pass_bid, 
                close_after=True)

if __name__ == '__main__':
    pg.init()
    test_s = pg.display.set_mode((SCREEN_W, SCREEN_H))
    while True:
        auct = AuctionScreen(test_s, 'TEST', 'CMSTP&P', 10000, 20000)
        auct.run()
        print(auct.bid)