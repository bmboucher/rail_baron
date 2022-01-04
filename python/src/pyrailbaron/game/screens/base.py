from dataclasses import dataclass
import pygame as pg
from typing import Callable, List, Dict
from pathlib import Path
from time import time

@dataclass
class Button:
    bounds: pg.Rect
    handler: Callable[[], None]

FRAME_RATE = 30
ASSETS_DIR = (Path(__file__) / '../../assets').resolve()

class PyGameScreen:
    def __init__(self, screen: pg.surface.Surface):
        self.screen = screen
        self.buttons: List[Button] = []
        self.images: Dict[str, pg.surface.Surface] = {}
        self.start_t = time()

    def add_button(self, bounds: pg.Rect, handler: Callable[[], None]):
        self.buttons.append(Button(bounds, handler))

    def load_image(self, path: Path | str) -> pg.surface.Surface:
        path = Path(path)
        if not path.is_absolute():
            path = ASSETS_DIR / path
        assert path.exists(), f'Image file {path} not found'
        key = path.name.split('.')[0]
        if key not in self.images:
            self.images[key] = pg.image.load(path)
        return self.images[key]

    def draw(self, init: bool):
        pass

    def check(self) -> bool:
        return True

    def run(self):
        self.draw(True)
        pg.display.update()
        clock = pg.time.Clock()
        while self.check():
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    pg.quit()
                elif (event.type == pg.MOUSEBUTTONDOWN and
                        pg.mouse.get_pressed()[0]):
                    x, y = pg.mouse.get_pos()
                    for button in self.buttons:
                        if button.bounds.contains(pg.Rect(x-1,y-1,2,2)):
                            button.handler()
                            self.draw(False)
                            pg.display.update()
                            break
            clock.tick(FRAME_RATE)