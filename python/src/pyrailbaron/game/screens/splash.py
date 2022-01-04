from pyrailbaron.game.screens.base import PyGameScreen
from time import time

SPLASH_SCREEN_FILE = 'splash.png'
SPLASH_SCREEN_TIME: float = 1.0

class SplashScreen(PyGameScreen):
    def draw(self, init: bool):
        self.draw_background(SPLASH_SCREEN_FILE)

    def check(self) -> bool:
        return time() - self.start_t <= SPLASH_SCREEN_TIME