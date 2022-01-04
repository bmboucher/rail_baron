from pyrailbaron.map.datamodel import Coordinate
from pyrailbaron.game.interface import Interface
from pyrailbaron.game.logic import run_game

import pygame as pg

from pyrailbaron.game.screens import SplashScreen

SCREEN_W: int = 800
SCREEN_H: int = 480
SCREENRECT = pg.Rect(0,0,SCREEN_W,SCREEN_H)

SPLASH_SCREEN_TIME: float = 5.0
BUTTON_MARGIN: int = 40

class PyGame_Interface:
    def __init__(self):
        super().__init__()
        pg.init()
        #bestdepth = pg.display.mode_ok(SCREENRECT.size, 0, 32)
        self.screen = pg.display.set_mode(SCREENRECT.size) #, 0, bestdepth)

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

if __name__ == '__main__':
    i = PyGame_Interface()
    i.display_splash()
    pg.quit()