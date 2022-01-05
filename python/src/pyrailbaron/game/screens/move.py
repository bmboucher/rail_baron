from pyrailbaron.game.screens.base import PyGameScreen
from pyrailbaron.game.state import GameState
from pyrailbaron.map.datamodel import Waypoint

import pygame as pg
from typing import List

class MoveScreen(PyGameScreen):
    def __init__(self, screen: pg.surface.Surface, 
            s: GameState, player_i: int, d: int, 
            init_rr: str | None, moves_so_far: int):
        super().__init__(screen)
        self.state = s
        assert player_i >=0 and player_i < len(s.players), \
            f'Player index {player_i} not in range'
        self.player_i = player_i
        assert d >= 2, "Minimum roll is 2"
        self.distance = d
        self.init_rr = init_rr
        self.moves_so_far = moves_so_far
        self.selected_moves: List[Waypoint] = []