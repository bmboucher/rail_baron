from pyrailbaron.game.screens.base import PyGameScreen
from pyrailbaron.game.state import GameState, PlayerState
from pyrailbaron.game.constants import SCREEN_W, SCREEN_H

import pygame as pg
from typing import Callable, List, Tuple, Any
from random import randint
from time import time

START_ROLL_TIME = 0.1
ROLL_INC_FACTOR = 1.25
END_ROLL_TIME = 1.0
LAST_ROLL_HANG_TIME = 0.5
BLINK_PERIOD = 0.4

DIE_CORNER_R = 30
DIE_PIP_R = 17
DIE_SIZE = 180
DIE_SPACING = 50
PIP_PATTERNS: List[List[Tuple[float, float]]] = [
    [(2,2)],
    [(1,1), (3,3)],
    [(1,1), (2,2), (3,3)],
    [(1,1), (1,3), (3,1), (3,3)],
    [(1,1), (2,2), (3,3), (1,3), (3,1)],
    [(1,1), (1,2), (1,3), (3,1), (3,2), (3,3)]]
LABEL_D = 300
ROLL_LABEL_TOP = (SCREEN_H - LABEL_D)//2
RESULT_TOP = (SCREEN_H + LABEL_D)//2

def draw_die(screen: pg.surface.Surface, c_x: int, c_y: int, n: int,
        die_color: pg.Color = pg.Color(255,255,255)):
    assert 1 <= n and n <= 6, f'Roll {n} must be in [1,6]'
    pips = PIP_PATTERNS[n - 1]
    assert len(pips) == n, 'Die pips must match roll'
    pg.draw.rect(screen, die_color, 
        pg.Rect(c_x - DIE_SIZE//2, c_y - DIE_SIZE//2, DIE_SIZE, DIE_SIZE),
        0, DIE_CORNER_R)
    for pip_x, pip_y in pips:
        pg.draw.circle(screen, pg.Color(0,0,0),
            (c_x + ((DIE_SIZE * (pip_x - 2))//4),
             c_y + ((DIE_SIZE * (pip_y - 2))//4)), DIE_PIP_R, 0)

class RollScreen(PyGameScreen):
    def __init__(self, screen: pg.surface.Surface, 
            n_die: int, label: str, 
            handler: Callable[[List[int]], str|None] | None = None,
            odd_even_die: bool = False, wait_for_user: bool = True):
        super().__init__(screen)
        self.n_die = n_die
        self.label = label
        self.handler = handler
        self.odd_even_die = odd_even_die
        self.wait_for_user = wait_for_user
        self._roll_period: float = START_ROLL_TIME
        self._last_roll = self.start_t
        self._current_roll: List[int] = [
            randint(1,6) for _ in range(self.n_die)]
        self._result: str|None = None
        self._waiting: bool = self.wait_for_user
        self._last_blink_time: float = time()
        self._blink: bool = False

    @property
    def roll(self) -> List[int]:
        return self._current_roll

    @property
    def result(self) -> str|None:
        return self._result

    def do_roll(self):
        self._current_roll = [randint(1,6) for _ in range(self.n_die)]
        if self.handler:
            self._result = self.handler(self._current_roll)
        print(f'Rolled {self._current_roll} -> {self._result}')

    def click(self):
        if not self._waiting:
            return
        self._waiting = False
        if self.roll_finished:
            self._active = False
        else:
            self._last_roll = time()
            self.do_roll()

    def draw(self, init: bool):
        if init:
            self.buttons.clear()
            self.add_button('Roll',pg.Rect(0,0,SCREEN_W,SCREEN_H), self.click)

        # We blink the result text directly to an (already drawn) screen
        if self.roll_finished:
            assert self._result, "Can't finish roll without result"
            self.draw_text(self._result.replace('_',''), 'Corrigan-ExtraBold', 70,
                pg.Rect(0, RESULT_TOP, SCREEN_W, 0), 
                pg.Color(255,0,0) if self._blink else pg.Color(255,255,255))
            pg.display.update()
            return

        buffer = pg.surface.Surface((SCREEN_W, SCREEN_H))
        self.solid_background(buffer=buffer)
        self.draw_text(self.label, 'Corrigan-ExtraBold', 70,
            pg.Rect(0, ROLL_LABEL_TOP, SCREEN_W, 0), pg.Color(255,255,255),
            buffer=buffer)
        if self._current_roll and len(self._current_roll) == self.n_die:
            die_x = (SCREEN_W - (self.n_die - 1)*(DIE_SIZE + DIE_SPACING)) // 2
            for die_i in range(self.n_die):
                die_color = (pg.Color(255,0,0) 
                    if self.odd_even_die and die_i == self.n_die - 1
                    else pg.Color(255,255,255))
                draw_die(buffer, die_x, SCREEN_H//2, 
                    self._current_roll[die_i], die_color)
                die_x += DIE_SIZE + DIE_SPACING
        if self._result:
            self.draw_text(self._result.replace('_',''), 'Corrigan-ExtraBold', 70,
                pg.Rect(0, RESULT_TOP, SCREEN_W, 0), 
                pg.Color(255,255,255), buffer=buffer)
        elif self._waiting:
            self.draw_text('CLICK TO ROLL', 'Corrigan-ExtraBold', 70,
                pg.Rect(0, RESULT_TOP, SCREEN_W, 0), pg.Color(255, 0, 0), 
                buffer=buffer)
        screen.blit(buffer, (0,0))

    @property
    def roll_finished(self) -> bool:
        return (self._roll_period > END_ROLL_TIME and
            time() - self._last_roll >= LAST_ROLL_HANG_TIME)

    def check(self) -> bool:
        return self._waiting or not self.roll_finished

    def animate(self) -> bool:
        if self._waiting and not self._result:
            return False
        redraw_flag = self._current_roll is None
        now = time()
        if now - self._last_roll >= self._roll_period:
            self._last_roll = now
            self._roll_period *= ROLL_INC_FACTOR
            if self._roll_period <= END_ROLL_TIME:
                redraw_flag = True
            else:
                self._waiting = True
                self._last_blink_time = time()
        if redraw_flag:
            self.do_roll()
        if self.roll_finished and time() - self._last_blink_time >= BLINK_PERIOD:
            self._blink = not self._blink
            self._last_blink_time = time()
            redraw_flag = True
        return redraw_flag

class RegionRoll(RollScreen):
    def __init__(self, screen: pg.surface.Surface, s: GameState, player_i: int,
            tag: str, **kwargs: Any):
        player_n = s.players[player_i].name
        def handler(roll: List[int]) -> str:
            assert len(roll) == 3, "Must roll 3 for region"
            # TODO: Flash regions on LEDs
            return s.lookup_roll_table('REGION', *roll)
        super().__init__(screen, 3, f'{player_n} > {tag}', handler,
            odd_even_die=True, **kwargs)

class CityRoll(RollScreen):
    def __init__(self, screen: pg.surface.Surface, s: GameState, player_i: int,
            region: str, tag: str, **kwargs: Any):
        player_n = s.players[player_i].name
        def handler(roll: List[int]) -> str:
            assert len(roll) == 3, "Must roll 3 for region"
            # TODO: Flash cities on LEDs
            return s.lookup_roll_table(region, *roll)
        super().__init__(screen, 3, f'{player_n} > {tag}', handler,
            odd_even_die=True, wait_for_user=False, **kwargs)

if __name__ == '__main__':
    pg.init()
    screen = pg.display.set_mode((SCREEN_W, SCREEN_H))
    s = GameState()
    s.players.append(PlayerState(0, 'TEST'))
    region_roll = RegionRoll(screen, s, 0, 'HOME REGION')
    region_roll.run()
    region = region_roll.result
    assert region

    city_roll = CityRoll(screen, s, 0, region, 'HOME CITY')
    city_roll.run()
    city = city_roll.result
    assert city