from pyrailbaron.game.screens.base import PyGameScreen
from pyrailbaron.game.constants import SCREEN_W, SCREEN_H

import pygame as pg

MENU_SCREEN_FILE = 'menu.png'

# Button layout
#   *****************           ********  *****************
#   *               *           *  UP  *  *               *
#   *   PLAY GAME   * n_players ********  *    SETTINGS   *
#   *               *           ********  *               *
#   *               *           * DOWN *  *               *
#   *****************           ********  *****************

# Dimensions
BUTTON_PAD_HORIZ = 40
BUTTON_PAD_VERT = 30
BUTTON_H = 120
BUTTON_M = 20
N_PLAYERS_LABEL_W = 100
UP_DOWN_BUTTON_W = 100
SETTINGS_BUTTON_W = 200
UP_DOWN_BUTTON_M = 10

# Range of n_players
START_PLAYERS = 4
MIN_PLAYERS = 2
MAX_PLAYERS = 4
assert MIN_PLAYERS <= START_PLAYERS and START_PLAYERS <= MAX_PLAYERS

# Label fonts/sizes
BUTTON_LABEL_FONT = 'Corrigan-ExtraBold'
BUTTON_LABEL_FONT_SIZE = 55
SETTINGS_LABEL_FONT_SIZE = 35
UP_DOWN_BUTTON_LABEL_FONT_SIZE = 25
N_PLAYERS_LABEL_FONT = 'Corrigan-ExtraBold'
N_PLAYERS_LABEL_FONT_SIZE = 120

# Button text
START_GAME_TEXT = 'START\nGAME'
UP_TEXT = 'MORE'
DOWN_TEXT = 'LESS'
SETTINGS_TEXT = 'SETTINGS'

# Button parameters 
BUTTON_COLOR = (255,255,255)
BUTTON_RADIUS = 10

# Calculate button locations
START_BUTTON_W = (SCREEN_W - 2 * BUTTON_PAD_HORIZ - 3 * BUTTON_M -
    N_PLAYERS_LABEL_W - UP_DOWN_BUTTON_W - SETTINGS_BUTTON_W)
BUTTON_TOP = SCREEN_H - BUTTON_PAD_VERT - BUTTON_H
UP_DOWN_BUTTON_H = (BUTTON_H - UP_DOWN_BUTTON_M) // 2
_btn_x = BUTTON_PAD_HORIZ
START_GAME_BTN_RECT      = pg.Rect(
    _btn_x, BUTTON_TOP, START_BUTTON_W, BUTTON_H)
_btn_x += START_BUTTON_W + BUTTON_M
NUM_PLAYERS_LABEL_POS    = (_btn_x, BUTTON_TOP)
_btn_x += N_PLAYERS_LABEL_W + BUTTON_M
UP_PLAYERS_BTN_RECT      = pg.Rect(
    _btn_x, BUTTON_TOP, UP_DOWN_BUTTON_W, UP_DOWN_BUTTON_H)
DOWN_PLAYERS_BTN_RECT    = pg.Rect(
    _btn_x, BUTTON_TOP + UP_DOWN_BUTTON_M + UP_DOWN_BUTTON_H, 
    UP_DOWN_BUTTON_W, UP_DOWN_BUTTON_H)
_btn_x += UP_DOWN_BUTTON_W + BUTTON_M
SETTINGS_BTN_RECT        = pg.Rect(
    _btn_x, BUTTON_TOP, SETTINGS_BUTTON_W, BUTTON_H)

class MainMenuScreen(PyGameScreen):
    def __init__(self, screen: pg.surface.Surface):
        super().__init__(screen)
        self._start_game: bool = False
        self._n_players: int = START_PLAYERS

    @property
    def start_game(self) -> bool:
        return self._start_game

    @property
    def n_players(self) -> int:
        return self._n_players

    def draw_button(self, label: str, bounds: pg.Rect):
        pg.draw.rect(self.screen, BUTTON_COLOR, bounds, 0, BUTTON_RADIUS)
        font_size = BUTTON_LABEL_FONT_SIZE
        if label in [UP_TEXT, DOWN_TEXT]:
            font_size = UP_DOWN_BUTTON_LABEL_FONT_SIZE
        elif label == SETTINGS_TEXT:
            font_size = SETTINGS_LABEL_FONT_SIZE
        self.draw_text(label, BUTTON_LABEL_FONT, font_size, bounds)

    def start_handler(self):
        assert not self.start_game, "Can only set start_game flag once"
        self._start_game = True

    def up_players(self):
        if self._n_players < MAX_PLAYERS:
            self._n_players += 1
            print(f'{self._n_players} players')

    def down_players(self):
        if self._n_players > MIN_PLAYERS:
            self._n_players -= 1
            print(f'{self._n_players} players')

    def settings(self):
        pass

    def draw_n_players(self):
        self.draw_text(str(self.n_players), N_PLAYERS_LABEL_FONT, N_PLAYERS_LABEL_FONT_SIZE,
            pg.Rect(*NUM_PLAYERS_LABEL_POS, N_PLAYERS_LABEL_W, BUTTON_H))

    def draw(self, init: bool):
        self.draw_background(MENU_SCREEN_FILE)
        self.draw_n_players()
        # TODO: Draw _n_players
        if init:
            self.buttons.clear()
            self.add_button(START_GAME_TEXT, START_GAME_BTN_RECT, 
                self.start_handler, close_after=True)
            self.add_button(UP_TEXT, UP_PLAYERS_BTN_RECT, self.up_players)
            self.add_button(DOWN_TEXT, DOWN_PLAYERS_BTN_RECT, self.down_players)
            self.add_button(SETTINGS_TEXT, SETTINGS_BTN_RECT, self.settings)