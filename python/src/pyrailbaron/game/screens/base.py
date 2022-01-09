from dataclasses import dataclass
import pygame as pg
from typing import Callable, List, Dict, Tuple
from pathlib import Path
from time import time

from pyrailbaron.game.constants import SCREEN_W, SCREEN_H

@dataclass
class Button:
    label: str
    bounds: pg.Rect
    handler: Callable[[], None]|None = None
    _id: str|None = None

    @property
    def id(self) -> str:
        return self._id or self.label

FRAME_RATE = 30
ASSETS_DIR = (Path(__file__) / '../../assets').resolve()

class PyGameScreen:
    def __init__(self, screen: pg.surface.Surface):
        self.screen = screen
        self.buttons: List[Button] = []
        self.images: Dict[str, pg.surface.Surface] = {}
        self.fonts: Dict[str, pg.font.Font] = {}
        self.start_t = time()
        self._active: bool = True

    def add_button(self, label: str, bounds: pg.Rect, 
            handler: Callable[[], None] | None = None,
            close_after: bool = False):
        _handler = handler
        if close_after:
            def wrapped():
                if handler:
                    handler()
                self._active = False
            _handler = wrapped
        self.draw_button(label, bounds)
        self.buttons.append(Button(label, bounds, _handler))

    def load_image(self, path: Path | str, scale_size: Tuple[int,int]|None = None,
            background: pg.Color = pg.Color(255,255,255)) -> pg.surface.Surface:
        path = Path(path)
        if not path.is_absolute():
            path = ASSETS_DIR / path
        assert path.exists(), f'Image file {path} not found'
        key = path.name.split('.')[0]
        if key not in self.images:
            img = pg.image.load(path)
            if scale_size:
                scale_w, scale_h = scale_size
                scale = min(scale_w / img.get_width(),
                            scale_h / img.get_height())
                img_w = min(scale_w, int(scale * img.get_width()))
                img_h = min(scale_h, int(scale * img.get_height()))
                img = pg.transform.scale(img, (img_w, img_h))

                if img_w != scale_w or img_h != scale_h:
                    pad_img = pg.surface.Surface(scale_size)
                    pg.draw.rect(pad_img, background, pg.Rect(0,0,scale_w,scale_h), 0)
                    pad_x = (scale_w - img_w) // 2
                    pad_y = (scale_h - img_h) // 2
                    pad_img.blit(img, (pad_x, pad_y))
                    img = pad_img

            self.images[key] = img
        return self.images[key]

    def draw_background(self, path: Path | str):
        background = self.load_image(path)
        self.screen.blit(background, (0, 0))

    def solid_background(self, color: pg.Color = pg.Color(0,0,0),
            buffer: pg.surface.Surface|None = None):
        buffer = buffer or self.screen
        pg.draw.rect(buffer, color,
            pg.Rect(0, 0, SCREEN_W, SCREEN_H), 0)

    def draw(self, init: bool):
        pass

    def animate(self) -> bool:
        return False

    def draw_button(self, label: str, bounds: pg.Rect):
        pass

    def check(self) -> bool:
        return True

    def close(self):
        assert self._active, "Can only close once"
        self._active = False

    def get_font(self, font: str, font_size: int) -> pg.font.Font:
        key = f'{font}/{font_size}'
        if key not in self.fonts:
            for font_ext in ['otf', 'ttf']:
                font_path = (ASSETS_DIR / f'{font}.{font_ext}')
                if font_path.exists():
                    self.fonts[key] = pg.font.Font(font_path, font_size); break
        if key not in self.fonts:
            self.fonts[key] = pg.font.SysFont(font, font_size)
        return self.fonts[key]

    def render_text(self, text: str, font: str, font_size: int, max_w: int,
            color: pg.Color | List[pg.Color] = pg.Color(0, 0, 0), 
            line_spacing: float = 1.25) \
                -> Tuple[List[pg.surface.Surface],Tuple[int,int]]:
        assert line_spacing >= 1.0, "Line spacing can't be <1"
        def get_w():
            pg_font = self.get_font(font, font_size)
            if isinstance(color, list):
                labels = [pg_font.render(line, True, color[i % len(color)], None) for
                    i, line in enumerate(text.split('\n'))]
            else:
                labels = [pg_font.render(line, True, color, None) for
                    line in text.split('\n')]
            label_w = max(l.get_width() for l in labels)
            return labels, label_w
        labels, label_w = get_w()
        while label_w > max_w:
            font_size -= 1
            labels, label_w = get_w()
        
        label_h = (
            int(line_spacing * sum(l.get_height() for l in labels[:-1])) 
             + labels[-1].get_height())
        return labels, (label_w, label_h)

    def calculate_text_size(self, text: str, font: str, font_size: int, max_w: int, line_spacing: float = 1.25) -> Tuple[int,int]:
        _, size = self.render_text(text, font, font_size, max_w,
            pg.Color(0,0,0), line_spacing)
        return size

    def draw_text(self, text: str, font: str, font_size: int, bounds: pg.rect.Rect,
            color: pg.Color | List[pg.Color] = pg.Color(0, 0, 0), line_spacing: float = 1.25,
            buffer: pg.surface.Surface|None = None) -> Tuple[int, int]:
        labels, (label_w, label_h) = self.render_text(
            text, font, font_size, bounds.width,
            color, line_spacing)
        assert label_w <= bounds.width, "Rendered label too wide"
        label_t = bounds.top + (bounds.height - label_h) // 2
        _buffer = buffer or self.screen
        for label in labels:
            label_l = bounds.left + (bounds.width - label.get_width()) // 2
            _buffer.blit(label, (label_l, label_t))
            label_t += int(line_spacing * label.get_height())
        return (label_w, label_h)

    def run(self):
        self._active = True
        def _draw(init: bool):
            if not self._active:
                return
            self.draw(init)
            for btn in self.buttons:
                self.draw_button(btn.label, btn.bounds)
            pg.display.update()

        _draw(True)
        clock = pg.time.Clock()
        while self._active and self.check():
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    pg.quit()
                    exit(1)
                elif (event.type == pg.MOUSEBUTTONDOWN and
                        pg.mouse.get_pressed()[0]):
                    x, y = pg.mouse.get_pos()
                    for button in self.buttons:
                        if button.bounds.contains(pg.Rect(x-1,y-1,2,2)):
                            if button.handler:
                                button.handler()
                            _draw(False)
                            break
            if self.animate():
                _draw(False)
            clock.tick(FRAME_RATE)