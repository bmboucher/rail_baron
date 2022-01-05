from pyrailbaron.game.screens.base import PyGameScreen
from pyrailbaron.game.constants import SCREEN_W, SCREEN_H
import pygame as pg
from time import time

# qwerty rows
KEYBOARD_LAYOUT = [
    'QWERTYUIOP',
    'ASDFGHJKL',
    'ZXCVBNM'
]

# Special key labels
ACCEPT = 'accept'
BACKSPACE = 'backspace'

# Key parameters
KEY_SIZE = 75
KEY_SPACING = 5
KEY_BOTTOM = 10
KEY_INVERT_TIME = 0.5
KEY_OUTLINE_W = 5
KEY_CORNER_R = 10

# Font parameters
TEXT_FONT = 'Corrigan-ExtraBold'
KEY_FONT = 'Corrigan-ExtraBold'
KEY_BACKSPACE_FONT = 'Segoe UI Symbol'
KEY_BACKSPACE_SYM = '⮜'
KEY_FONT_SIZE = 55
LABEL_COLOR = pg.Color(255, 0, 0) #red
TEXT_FONT_SIZE = 125
LABEL_FONT_SIZE = 40
LABEL_TEXT_SEP = 80

class KeyboardScreen(PyGameScreen):
    def __init__(self, screen: pg.surface.Surface,
            label: str = 'PLAYER NAME'):
        super().__init__(screen)
        self._text = ''
        self._last_pressed = -1
        self._time_last_pressed: float | None = None
        self.label = label

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
        if label == ACCEPT:
            return # Only draw keys
        pg.draw.rect(self.screen, pg.Color(0,0,0), bounds, 
            KEY_OUTLINE_W, KEY_CORNER_R)
        invert = False
        if self._time_last_pressed:
            invert = (
                ((label == BACKSPACE and self._last_pressed == pg.K_BACKSPACE)
                    or self._last_pressed == pg.key.key_code(label)
                and (time() - self._time_last_pressed < KEY_INVERT_TIME)))
        text_color = pg.Color(255,255,255) if invert else pg.Color(0,0,0)
        if invert:
            pg.draw.rect(self.screen, pg.Color(0,0,0), bounds, 0, KEY_CORNER_R)
        if label == BACKSPACE:
            self.draw_text(KEY_BACKSPACE_SYM, KEY_BACKSPACE_FONT, KEY_FONT_SIZE, 
                bounds, text_color)
        elif len(label) == 1:
            self.draw_text(label, KEY_FONT, KEY_FONT_SIZE, 
                bounds, text_color)

    def accept(self):
        if len(self.text) > 0 and not self.text.startswith('CPU'):
            self.close()

    def draw(self, init: bool):
        self.solid_background(pg.Color(255, 255, 255))
        KEY_H = len(KEYBOARD_LAYOUT) * KEY_SIZE + (len(KEYBOARD_LAYOUT) - 1) * KEY_SPACING
        KEY_T = SCREEN_H - KEY_BOTTOM - KEY_H
        self.draw_text(self.label, TEXT_FONT, LABEL_FONT_SIZE,
            pg.Rect(0, KEY_T // 2 - LABEL_TEXT_SEP, SCREEN_W, 0), LABEL_COLOR)
        if len(self._text) > 0:
            self.draw_text('TAP TO ACCEPT', TEXT_FONT, LABEL_FONT_SIZE,
                pg.Rect(0, KEY_T // 2 + LABEL_TEXT_SEP, SCREEN_W, 0), LABEL_COLOR)
        if init:
            self.buttons.clear()
            key_t = KEY_T
            for i, row in enumerate(KEYBOARD_LAYOUT):
                n_keys = len(row) + (1 if i == len(KEYBOARD_LAYOUT)-1 else 0)
                row_w = n_keys * KEY_SIZE + (n_keys - 1) * KEY_SPACING
                key_l = (SCREEN_W - row_w) // 2
                get_key_bounds = lambda: pg.Rect(key_l, key_t, KEY_SIZE, KEY_SIZE)
                for k in row:
                    self.add_button(k, get_key_bounds(),
                        self.key_handler(pg.key.key_code(k)))
                    key_l += KEY_SIZE + KEY_SPACING
                if i == len(KEYBOARD_LAYOUT) - 1:
                    self.add_button(BACKSPACE, get_key_bounds(),
                        self.key_handler(pg.K_BACKSPACE))
                key_t += KEY_SIZE + KEY_SPACING
            self.add_button(ACCEPT, pg.Rect(0,0,SCREEN_W,KEY_T), self.accept)
        else:
            self.draw_text(self._text, TEXT_FONT, TEXT_FONT_SIZE,
                pg.Rect(0, KEY_T // 2, SCREEN_W, 0))
    
    def animate(self) -> bool:
        if self._time_last_pressed and time() - self._time_last_pressed >= KEY_INVERT_TIME:
            self._time_last_pressed = None
            return True
        return False

if __name__ == '__main__':
    pg.init()
    screen = pg.display.set_mode((SCREEN_W, SCREEN_H))
    keyboard = KeyboardScreen(screen)
    keyboard.run()
    print(keyboard.text)