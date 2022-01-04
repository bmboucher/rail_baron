from pyrailbaron.game.screens.base import PyGameScreen
from time import time

SPLASH_SCREEN_FILE = 'splash.png'
SPLASH_SCREEN_TIME: float = 5.0

class SplashScreen(PyGameScreen):
    def draw(self, init: bool):
        splash = self.load_image(SPLASH_SCREEN_FILE)
        self.screen.blit(splash, (0, 0))

    def check(self) -> bool:
        return time() - self.start_t <= SPLASH_SCREEN_TIME