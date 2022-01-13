from pyrailbaron.game.screens.base import PyGameScreen
from pyrailbaron.game.state import GameState, PlayerState
from pyrailbaron.game.constants import SCREEN_W, SCREEN_H
from pyrailbaron.teensy.serial import Serial
from enum import Enum

import pygame as pg
from typing import Callable, List, Tuple, Any
from random import randint
from time import time

START_ROLL_TIME = 0.1
ROLL_INC_FACTOR = 1.5
END_ROLL_TIME = 0.75
DISPLAY_WAIT_TIME = 0.25
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

STR_RESULTS = [
    None, 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX',
    'SEVEN', 'EIGHT', 'NINE', 'TEN', 'ELEVEN', 'TWELVE']

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

class RollScreenStep(Enum):
    Wait = 0
    Roll = 1
    Display = 2

class RollScreen(PyGameScreen):
    def __init__(self, screen: pg.surface.Surface, 
            n_die: int, label: str, 
            handler: Callable[[List[int]], str|None] | None = None,
            wait_for_user: bool = True):
        super().__init__(screen)
        self.n_die = n_die
        self.label = label
        self.handler = handler

        self._step = RollScreenStep.Wait if wait_for_user else RollScreenStep.Roll
        self._mark = time()
        self._roll_period: float = START_ROLL_TIME
        self._roll: List[int] = [
            randint(1,6) for _ in range(self.n_die)]
        self._result: str|None = None
        self._blink: bool = False

    @property
    def roll(self) -> List[int]:
        return self._roll

    @property
    def result(self) -> str|None:
        return self._result

    def do_roll(self):
        if self._step != RollScreenStep.Roll:
            return
        self._roll = [randint(1,6) for _ in range(self.n_die)]
        self._mark = time()
        self._roll_period *= ROLL_INC_FACTOR
        if self.handler:
            self._result = self.handler(self._roll)
        else:
            self._result = STR_RESULTS[sum(self._roll)]

    def click(self):
        if self._step == RollScreenStep.Wait:
            self._step = RollScreenStep.Roll
            self.do_roll()
        elif self._step == RollScreenStep.Roll:
            self.do_roll()
            self.draw(False)
            self._step = RollScreenStep.Display
        elif self._step == RollScreenStep.Display:
            self.close()

    def draw(self, init: bool):
        if init:
            self.buttons.clear()
            self.add_button('Roll',pg.Rect(0,0,SCREEN_W,SCREEN_H), self.click)

        if self._step == RollScreenStep.Display:
            # We blink the result text directly to an (already drawn) screen
            assert self._result, "Can't finish roll without result"
            self.draw_text(self._result.replace('_',''), 'Corrigan-ExtraBold', 70,
                pg.Rect(0, RESULT_TOP, SCREEN_W, 0), 
                pg.Color(255,0,0) if self._blink else pg.Color(255,255,255))
            pg.display.update()
            return

        # Otherwise we fully render the screen to a buffer
        buffer = pg.surface.Surface((SCREEN_W, SCREEN_H))
        self.solid_background(buffer=buffer)
        self.draw_text(self.label, 'Corrigan-ExtraBold', 70,
            pg.Rect(0, ROLL_LABEL_TOP, SCREEN_W, 0), pg.Color(255,255,255),
            buffer=buffer)
        if self._roll and len(self._roll) == self.n_die:
            die_x = (SCREEN_W - (self.n_die - 1)*(DIE_SIZE + DIE_SPACING)) // 2
            for die_i in range(self.n_die):
                die_color = (pg.Color(255,0,0) 
                    if die_i == 2 else pg.Color(255,255,255))
                draw_die(buffer, die_x, SCREEN_H//2, 
                    self._roll[die_i], die_color)
                die_x += DIE_SIZE + DIE_SPACING
        if self._step == RollScreenStep.Wait:
            self.draw_text('TAP TO ROLL', 'Corrigan-ExtraBold', 70,
                pg.Rect(0, RESULT_TOP, SCREEN_W, 0), pg.Color(255, 0, 0), 
                buffer=buffer)            
        elif self._result:
            self.draw_text(self._result.replace('_',''), 'Corrigan-ExtraBold', 70,
                pg.Rect(0, RESULT_TOP, SCREEN_W, 0), 
                pg.Color(255,255,255), buffer=buffer)
        self.screen.blit(buffer, (0,0))

    def animate(self) -> bool:
        if self._step == RollScreenStep.Roll:
            if self._roll_period >= END_ROLL_TIME:
                if time() - self._mark >= DISPLAY_WAIT_TIME:
                    self._step = RollScreenStep.Display
                    self._mark = time()
                    return True
            else:
                if time() - self._mark >= self._roll_period:
                    self.do_roll()
                    return True
        elif self._step == RollScreenStep.Display:
            if time() - self._mark >= BLINK_PERIOD:
                self._blink = not self._blink
                self._mark = time()
                return True
        return False

class RegionRoll(RollScreen):
    def __init__(self, screen: pg.surface.Surface, s: GameState, player_i: int,
            tag: str, **kwargs: Any):
        player_n = s.players[player_i].name
        def handler(roll: List[int]) -> str:
            assert len(roll) == 3, "Must roll 3 for region"
            region = s.lookup_roll_table('REGION', *roll)
            Serial.show_region(region)
            return region
        super().__init__(screen, 3, f'{player_n} > {tag}', handler, **kwargs)

class CityRoll(RollScreen):
    def __init__(self, screen: pg.surface.Surface, s: GameState, player_i: int,
            region: str, tag: str, is_home_city: bool = False, **kwargs: Any):
        player_n = s.players[player_i].name
        def handler(roll: List[int]) -> str:
            assert len(roll) == 3, "Must roll 3 for region"
            lookup_city = s.lookup_roll_table(region, *roll)
            _, lookup_city_i = s.map.lookup_city(lookup_city)
            if is_home_city:
                Serial.show_home_city(lookup_city_i)
            else:
                start_i = s.players[player_i].location
                Serial.show_destination(start_i, lookup_city_i)
            return lookup_city
        super().__init__(screen, 3, f'{player_n} > {tag}', handler, 
            wait_for_user=False, **kwargs)

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