from pyrailbaron.game.screens.base import PyGameScreen
from pyrailbaron.game.constants import SCREEN_W, SCREEN_H
import pygame as pg
from time import time

KEY_SIZE = 75
KEY_SPACING = 5
keys = [
    'QWERTYUIOP',
    'ASDFGHJKL',
    'ZXCVBNM'
]
TEXT_TOP = 50
KEY_TOP = 150
KEY_INVERT_TIME = 0.5

class KeyboardScreen(PyGameScreen):
    def __init__(self, screen: pg.surface.Surface):
        super().__init__(screen)
        self._text = ''
        self._last_pressed = -1
        self._time_last_pressed: float | None = None

    @property
    def text(self) -> str:
        return self._text

    def key_handler(self, k: int):
        def handle():
            self._last_pressed = k
            self._time_last_pressed = time()
            if k == pg.K_BACKSPACE:
                self._text = self._text[:-1]
            else:
                self._text += pg.key.name(k).upper()
            self.draw(False)
        return handle

    def draw_button(self, label: str, bounds: pg.Rect):
        pg.draw.rect(self.screen, pg.Color(0,0,0), bounds, 5, 10)
        invert = False
        if self._time_last_pressed:
            invert = (
                ((label == 'backspace' and self._last_pressed == pg.K_BACKSPACE)
                    or self._last_pressed == pg.key.key_code(label)
                and (time() - self._time_last_pressed < KEY_INVERT_TIME)))
        text_color = pg.Color(255,255,255) if invert else pg.Color(0,0,0)
        if invert:
            pg.draw.rect(self.screen, pg.Color(0,0,0), bounds, 0, 10)
        if label == 'backspace':
            self.draw_text('⮜', 'Segoe UI Symbol', 45, bounds, text_color)
        elif len(label) == 1:
            self.draw_text(label, 'Corrigan-ExtraBold', 45, bounds, text_color)

    def draw(self, init: bool):
        self.solid_background(pg.Color(255, 255, 255))
        if init:
            self.buttons.clear()
            key_t = KEY_TOP
            for i, row in enumerate(keys):
                n_keys = len(row) + (1 if i == len(keys)-1 else 0)
                row_w = n_keys * KEY_SIZE + (n_keys - 1) * KEY_SPACING
                key_l = (SCREEN_W - row_w) // 2
                for k in row:
                    self.add_button(k, pg.Rect(key_l, key_t, KEY_SIZE, KEY_SIZE),
                        self.key_handler(pg.key.key_code(k)))
                    key_l += KEY_SIZE + KEY_SPACING
                if i == len(keys) - 1:
                    self.add_button('backspace', pg.Rect(key_l, key_t, KEY_SIZE, KEY_SIZE),
                        self.key_handler(pg.K_BACKSPACE))
                key_t += KEY_SIZE + KEY_SPACING
        else:
            self.draw_text(self._text, 'Corrigan-ExtraBold', 100,
                pg.Rect(0, TEXT_TOP, SCREEN_W, 0))
    
    def animate(self) -> bool:
        if self._time_last_pressed and time() - self._time_last_pressed >= KEY_INVERT_TIME:
            self._time_last_pressed = None
            return True
        return False

if __name__ == '__main__':
    pg.init()
    screen = pg.display.set_mode((SCREEN_W, SCREEN_H))
    KeyboardScreen(screen).run()