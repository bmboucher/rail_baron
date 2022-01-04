from pyrailbaron.game.main import main
from pyrailbaron.game.screens.main_menu import MainMenuScreen
from pyrailbaron.map.datamodel import Coordinate
from pyrailbaron.game.interface import Interface
from pyrailbaron.game.logic import run_game

import pygame as pg

from pyrailbaron.game.screens import SplashScreen
from pyrailbaron.game.constants import SCREEN_W, SCREEN_H

SCREENRECT = pg.Rect(0,0,SCREEN_W,SCREEN_H)

SPLASH_SCREEN_TIME: float = 5.0
BUTTON_MARGIN: int = 40

class PyGame_Interface():
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
        # run_game(n_players, self)

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