from pyrailbaron.game.screens.base import PyGameScreen
from pyrailbaron.game.state import Engine, GameState, PlayerState
from pyrailbaron.game.constants import SCREEN_W, SCREEN_H, REGIONS

from typing import List, Any, Tuple, Dict
import pygame as pg
from enum import Enum, auto

BUTTON_W = 250
BUTTON_SPACING = 10

COST_H = 40
OPT_W = SCREEN_W - BUTTON_W
OPT_H = SCREEN_H - COST_H
COST_M = 20
LOGO_W = 350
LOGO_H = 275
LOGO_PAD = 10
LABEL_LOGO_SEP = 10

LABEL_FONT = 'Corrigan-ExtraBold'
BUTTON_FONT_SIZE = 45
BUY_NOTHING_SIZE = 65
OPT_FONT_SIZE = 35
COST_FONT_SIZE = 30
MAX_CHUNK_SIZE = 25

BUY_COLOR = pg.Color(255,255,0)
OPT_COLOR = pg.Color(255,255,255)
COST_COLOR = pg.Color(255,0,0)
AVAIL_COLOR = pg.Color(125,125,125)

class SelectScreen(PyGameScreen):
    def __init__(self, screen: pg.surface.Surface, options: List[Any]):
        super().__init__(screen)
        self.options = options
        self._selected_index = 0

    class Buttons(Enum):
        Up = auto()
        Down = auto()
        Select = auto()

    @property
    def selected(self) -> Any:
        return self.options[self._selected_index]

    def draw_option(self):
        pass

    def draw_button(self, label: str, bounds: pg.Rect):
        buffer = pg.surface.Surface(bounds.size)
        w, h = bounds.size
        button_color = pg.Color(0, 255, 0) if label == SelectScreen.Buttons.Select.name else pg.Color(200,200,200)
        pg.draw.rect(buffer, button_color, (0,0,w,h), 0, 10)
        if label == SelectScreen.Buttons.Select.name:
            self.draw_text('SELECT', LABEL_FONT, BUTTON_FONT_SIZE,
                pg.Rect(0, 0, w, h), buffer=buffer)
        else:
            pg.draw.polygon(buffer, pg.Color(0,0,0),
                [(0.5*w, 0.2*h), (0.7*w, 0.8*h), (0.3*w, 0.8*h)], 0)
            if label == SelectScreen.Buttons.Down.name:
                buffer = pg.transform.flip(buffer, False, True)
        self.screen.blit(buffer, bounds.topleft)

    def up(self):
        if self._selected_index + 1 < len(self.options):
            self._selected_index += 1
        else:
            self._selected_index = 0

    def down(self):
        if self._selected_index > 0:
            self._selected_index -= 1
        else:
            self._selected_index = len(self.options) - 1

    def draw(self, init: bool):
        self.solid_background()
        self.draw_option()
        if init:
            self.buttons.clear()
            button_l = SCREEN_W - BUTTON_W + BUTTON_SPACING
            button_t = BUTTON_SPACING
            button_w = BUTTON_W - 2 * BUTTON_SPACING
            button_h = (SCREEN_H - 4 * BUTTON_SPACING) // 3
            self.add_button(SelectScreen.Buttons.Up.name, 
                pg.Rect(button_l, button_t, button_w, button_h), self.up)
            button_t += BUTTON_SPACING + button_h
            self.add_button(SelectScreen.Buttons.Down.name, 
                pg.Rect(button_l, button_t, button_w, button_h), self.down)
            button_t += BUTTON_SPACING + button_h
            self.add_button(SelectScreen.Buttons.Select.name, 
                pg.Rect(button_l, button_t, button_w, button_h), close_after=True)

class PurchaseSelectScreen(SelectScreen):
    def __init__(self, screen: pg.surface.Surface, s: GameState, player_i: int, 
            user_fee: int = 0, sell_flag: bool = False, amt_required: int = 0):
        options: List[Tuple[str, int] | None]
        if sell_flag:
            options = s.get_player_sell_opts(player_i, True) # type: ignore
        else:
            options = s.get_player_purchase_opts(player_i, True) # type: ignore
            options.insert(0, None)
        super().__init__(screen, options)
        self.map = s.map
        self.available = s.players[player_i].bank + user_fee
        self.amt_required = amt_required
        self.sell_flag = sell_flag

    def draw_option(self):
        opt_rect = pg.Rect(0, 0, OPT_W, OPT_H)
        selected: Tuple[str, int] | None = self.selected
        BS = 'SELL' if self.sell_flag else 'BUY'
        if not selected:
            self.draw_text(f'{BS}\nNOTHING', LABEL_FONT, BUY_NOTHING_SIZE,
                opt_rect, BUY_COLOR)
            price = 0
        else:
            opt, price = selected

            if opt in [Engine.Express.name, Engine.Superchief.name]:
                labelText = f'{BS} {opt.upper()}\n'
                if opt == Engine.Express.name:
                    labelText += 'Adds a bonus roll\nafter rolling doubles'
                else:
                    labelText += 'Adds a bonus roll\non every turn'
            else:
                assert opt in self.map.railroads, "Option must be a RR"
                rr = self.map.railroads[opt]
                
                labelText = f'{BS} {rr.shortName}\n'
                chunk = ''
                for word in rr.longName.split(' '):
                    if word in ['&', '-']:
                        chunk += ' ' + word
                    else:
                        if len(chunk) + len(word) + 1 <= MAX_CHUNK_SIZE:
                            chunk = f'{chunk} {word}'
                        else:
                            labelText += f'{chunk}\n'
                            chunk = word
                labelText += chunk

            label_w, label_h = PyGameScreen.calculate_text_size(labelText,
                LABEL_FONT, OPT_FONT_SIZE, OPT_W)
            
            total_opt_h = LOGO_H + LABEL_LOGO_SEP + label_h
            logo_t = (OPT_H - total_opt_h) // 2
            logo_l = (OPT_W - LOGO_W) // 2
            self.screen.fill(pg.Color(255,255,255),
                pg.Rect(logo_l, logo_t, LOGO_W, LOGO_H))
            self.screen.blit(self.load_image(f'rr_logos/{opt.lower()}.png', 
                (LOGO_W - 2 * LOGO_PAD, LOGO_H - 2 * LOGO_PAD)),
                (logo_l + LOGO_PAD, logo_t + LOGO_PAD))

            label_t = logo_t + LOGO_H + LABEL_LOGO_SEP
            label_l = (OPT_W - label_w) // 2
            self.draw_text(labelText, LABEL_FONT, OPT_FONT_SIZE,
                pg.Rect(label_l, label_t, label_w, label_h),
                [BUY_COLOR] + [OPT_COLOR] * 4)

            label_m = SCREEN_H - COST_H//2
            costLabel = f'{"MIN" if self.sell_flag else "COST"} {price}'
            label_w, _ = PyGameScreen.calculate_text_size(costLabel,
                LABEL_FONT, COST_FONT_SIZE, OPT_W // 2)
            self.draw_text(costLabel, LABEL_FONT, COST_FONT_SIZE,
                pg.Rect(COST_M, label_m, label_w, 0), COST_COLOR)

        availLabel = (f'{self.amt_required} REQUIRED' if self.sell_flag 
            else f'{self.available} AVAILABLE')
        label_m = SCREEN_H - COST_H//2
        label_w, _ = PyGameScreen.calculate_text_size(availLabel,
            LABEL_FONT, COST_FONT_SIZE, OPT_W // 2)
        self.draw_text(availLabel, LABEL_FONT, COST_FONT_SIZE,
            pg.Rect(OPT_W - COST_M - label_w, label_m, label_w, 0), AVAIL_COLOR)

class RegionSelectScreen(SelectScreen):
    def __init__(self, screen: pg.surface.Surface, payoffs: Dict[str, int]):
        sorted_regions = list(sorted(REGIONS, key=lambda r: payoffs[r]))
        super().__init__(screen, sorted_regions)
        self.payoffs = payoffs
        self._selected_index = len(sorted_regions)-1

    def draw_option(self):
        self.draw_text(self.selected.replace(' ','\n'), LABEL_FONT, 100,
            pg.Rect(50,0,OPT_W-100,SCREEN_H), pg.Color(255,255,255))
        self.draw_text(f'{self.payoffs[self.selected]} AVERAGE', LABEL_FONT, 50,
            pg.Rect(50, SCREEN_H-100,OPT_W-100,80), pg.Color(255,255,0))

if __name__ == '__main__':
    pg.init()
    screen = pg.display.set_mode((SCREEN_W, SCREEN_H))
    while True:
        ps = PlayerState(0, 'TEST')
        s = GameState()
        s.players.append(ps)
        ps.bank = 100000

        #ss = PurchaseSelectScreen(screen, s, 0, 10000)
        ss = RegionSelectScreen(screen, s.get_expected_region_payoffs('Portland_'))
        ss.run()
        print(ss.selected)