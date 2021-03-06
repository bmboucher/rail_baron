from pyrailbaron.game.screens.base import PyGameScreen
from pyrailbaron.game.state import GameState, PlayerState
from pyrailbaron.map.datamodel import Waypoint
from pyrailbaron.game.constants import SCREEN_W, SCREEN_H
from pyrailbaron.game.moves import calculate_legal_moves, get_legal_moves_with_scores, MoveReport
from pyrailbaron.game.fees import calculate_user_fees
from pyrailbaron.game.screens.map import draw_map

from enum import Enum, auto

import pygame as pg
from typing import List
from time import time

FORCED_MOVE_TIME = 1.0

PROGRESS_H = 50
PROGRESS_T = SCREEN_H - PROGRESS_H
PROGRESS_IND_R = 10
PROGRESS_M = 50
PROG_LINE_W = 5
PROGRESS_W = SCREEN_W - 2 * PROGRESS_M
PROG_COST_W = 100

PROG_COMPLETED_COLOR = pg.Color(255,255,255)
PROG_UNCOMPLETED_COLOR = pg.Color(127,127,127)
PROG_DEST_COLOR = pg.Color(255,0,0)
NEXT_MOVE_COLOR = pg.Color(255,255,0)
BORDER_COLOR = pg.Color(200,200,0)
BUTTON_COLOR = pg.Color(200,200,200)
FINISH_BUTTON_COLOR = pg.Color(0,255,0)
FORCED_BUTTON_COLOR = pg.Color(100,100,100)

OPT_W = 300
LOGO_H = 220
LOGO_PAD = 10
DEST_LABEL_T = 40
COST_LABEL_T = 20

MAP_W = SCREEN_W - OPT_W
MAP_H = PROGRESS_T
MAP_EXPANSION = 1.2
MAP_LINE_W = 2
NEXT_MOVE_LINE_W = 5
MAP_PT_R = 4
BORDER_LINE_W = 4

OPT_LABEL_FONT = 'Corrigan-ExtraBold'
OPT_LABEL_FONT_SIZE = 25
COST_FONT = 'Corrigan-ExtraBold'
COST_FONT_SIZE = 35
BUTTON_FONT = 'Corrigan-ExtraBold'
BUTTON_FONT_SIZE = 25

BUTTON_MARGIN = 10
BUTTON_H = 40
BUTTON_CORNER_R = 10
class ButtonLabel(Enum):
    AcceptMove = auto()
    ForcedAcceptMove = auto()
    Next = auto()
    Previous = auto()
    FinishTurn = auto()
    FinishTrip = auto()

class MoveScreen(PyGameScreen):
    def __init__(self, screen: pg.surface.Surface, 
            s: GameState, player_i: int, d: int, 
            init_rr: str | None, moves_so_far: int):
        super().__init__(screen)
        self.state = s
        assert player_i >=0 and player_i < len(s.players), \
            f'Player index {player_i} not in range'
        self.player_i = player_i
        assert d > 0, "Roll must be positive"
        self.distance = d
        self.init_rr = init_rr
        self.moves_so_far = moves_so_far
        self.selected_moves: List[Waypoint] = []
        self._options: List[MoveReport] = []
        self._mark = time()
        self.calculate_options()
        self._finished = False
        self._current_selection = 0
        self._is_last_move = False

    @property
    def player(self) -> PlayerState:
        return self.state.players[self.player_i]

    @property
    def start_loc(self) -> int:
        return self.player.location

    @property
    def curr_loc(self) -> int:
        return self.start_loc if len(self.selected_moves) == 0 else self.selected_moves[-1][1]

    @property
    def established_rate(self) -> int|None:
        return self.player.established_rate

    @property
    def dest_index(self) -> int:
        return self.player.destinationIndex

    @property
    def turn_history(self) -> List[Waypoint]:
        history = self.player.history[-self.moves_so_far:] if self.moves_so_far > 0 else []
        return history + self.selected_moves

    @property
    def next_selected_move(self) -> Waypoint:
        return self._options[self._current_selection].move

    @property
    def cost_this_trip(self) -> int:
        player_rr = [p.rr_owned for p in self.state.players]
        fees, _ = calculate_user_fees(self.state.map, self.player_i,
            self.turn_history, player_rr, self.init_rr, self.established_rate,
            self.state.doubleFees)
        return -fees[self.player_i]

    def draw_progress(self):
        prog_surf = pg.surface.Surface((SCREEN_W, PROGRESS_H))
        progress_d = (PROGRESS_W - PROG_COST_W) // (self.distance)
        PROGRESS_MID = PROGRESS_H // 2
        for pt in range(self.distance + 1):
            pt_x = PROGRESS_M + pt * progress_d
            if pt < self.distance:
                color = (PROG_COMPLETED_COLOR if pt < len(self.selected_moves) 
                    else pg.Color(255,255,0) if pt == len(self.selected_moves)
                    else PROG_UNCOMPLETED_COLOR)
                pg.draw.line(prog_surf, color,
                    (pt_x, PROGRESS_MID), (pt_x + progress_d, PROGRESS_MID),
                    PROG_LINE_W)
            if pt <= len(self.selected_moves) + 1:
                if pt < len(self.selected_moves) + 1:
                    loc = self.start_loc if pt == 0 else self.selected_moves[pt - 1][1]
                    color = PROG_COMPLETED_COLOR
                else:
                    loc = self.next_selected_move[1]
                    color = pg.Color(255,255,0)
                if loc == self.dest_index:
                    color = PROG_DEST_COLOR
                if len(self.state.map.points[loc].city_names) > 0:
                    pg.draw.rect(prog_surf, color,
                        pg.Rect(pt_x - PROGRESS_IND_R, PROGRESS_MID - PROGRESS_IND_R,
                                2*PROGRESS_IND_R, 2*PROGRESS_IND_R), 0)
                else:                    
                    pg.draw.circle(prog_surf, color, 
                        (pt_x, PROGRESS_MID), PROGRESS_IND_R, 0)
            else:
                pg.draw.circle(prog_surf, PROG_UNCOMPLETED_COLOR, 
                    (pt_x, PROGRESS_MID), PROGRESS_IND_R, 0)
        
        # Add trip cost amount
        self.draw_text(str(self.cost_this_trip), COST_FONT, COST_FONT_SIZE,
            pg.Rect(SCREEN_W - PROG_COST_W - PROGRESS_M, 0, 
                    PROG_COST_W + PROGRESS_M, PROGRESS_H),
            pg.Color(255, 0, 0), buffer=prog_surf)

        self.screen.blit(prog_surf, (0, PROGRESS_T))

    def calculate_options(self):
        m = self.state.map
        ps = self.state.players[self.player_i]
        moves_this_turn = self.moves_so_far + len(self.selected_moves)
        player_rr = [p.rr_owned for p in self.state.players]
        self._options = get_legal_moves_with_scores(m, self.player.startCityIndex,
            self.player.history + self.selected_moves, 
            ps.destinationIndex, ps.rover_play_index, moves_this_turn,
            player_rr, self.player_i, self.init_rr, self.established_rate,
            self.state.doubleFees)
        self._current_selection = 0
        self._mark = time()

    def select_option(self, index: int):
        assert index >= 0 and index < len(self._options), f"Selected index {index} not in range"
        wp = self._options[index].move
        self.selected_moves.append(wp)
        self._finished = (wp[1] == self.dest_index or len(self.selected_moves) == self.distance)
        if not self._finished:
            self.calculate_options()
        self._mark = time()

    def previous(self):
        if len(self._options) <= 1:
            return
        if self._current_selection > 0:
            self._current_selection -= 1
        else:
            self._current_selection = len(self._options) - 1
        self.draw(False)

    def next(self):
        if len(self._options) <= 1:
            return
        if self._current_selection < len(self._options) - 1:
            self._current_selection += 1
        else:
            self._current_selection = 0
        self.draw(False)

    def accept(self):
        self.select_option(self._current_selection)
        self.draw(False)

    def draw_button(self, label: str, bounds: pg.Rect):
        text = label.upper()
        if label in [ButtonLabel.ForcedAcceptMove.name, ButtonLabel.AcceptMove.name]:
            text = 'ACCEPT'
        elif label == ButtonLabel.Next.name:
            text = '>'
        elif label == ButtonLabel.Previous.name:
            text = '<'

        color = BUTTON_COLOR # grey
        if label in [ButtonLabel.FinishTrip.name, ButtonLabel.FinishTurn.name]:
            text = 'FINISH'
            color = FINISH_BUTTON_COLOR # green
        elif label == ButtonLabel.ForcedAcceptMove.name:
            color = FORCED_BUTTON_COLOR # very light grey
        buffer = pg.surface.Surface(bounds.size)
        pg.draw.rect(buffer, color, buffer.get_bounding_rect(), 
            0, BUTTON_CORNER_R)
        if label == ButtonLabel.ForcedAcceptMove.name:
            pct = min(1.0, (time() - self._mark) / FORCED_MOVE_TIME)
            filled_bounds = buffer.get_bounding_rect()
            filled_bounds.width = int(filled_bounds.width * pct)
            pg.draw.rect(buffer, BUTTON_COLOR, filled_bounds, 0, BUTTON_CORNER_R)

        self.draw_text(text, BUTTON_FONT, BUTTON_FONT_SIZE,
            buffer.get_bounding_rect(), buffer=buffer)
        self.screen.blit(buffer, bounds.topleft)

    def draw_options(self):
        self.buttons.clear()
        if len(self._options) == 0:
            return

        # Load current selection
        sel = self._options[self._current_selection]
        rr, next_pt = sel.move

        # Initialize buffer
        opt_buffer = pg.surface.Surface((OPT_W, PROGRESS_T))

        # Draw logo
        pg.draw.rect(opt_buffer, pg.Color(255,255,255),
            pg.Rect(0,0,OPT_W,LOGO_H))
        rr_img = self.load_image(f'rr_logos/{rr}.png', 
            scale_size=(OPT_W-2*LOGO_PAD,LOGO_H-2*LOGO_PAD))
        opt_buffer.blit(rr_img, (LOGO_PAD, LOGO_PAD))

        # Draw destination/cost labels
        label_m = LOGO_H + DEST_LABEL_T
        next_name = f'TAKE THE {self.state.map.railroads[rr].shortName} TO\n{self.state.map.points[next_pt].display_name.upper()}'
        _, label_h = self.draw_text(next_name, OPT_LABEL_FONT, OPT_LABEL_FONT_SIZE,
            pg.Rect(0, label_m, OPT_W, 0), pg.Color(255,255,255), buffer=opt_buffer)
        label_m += label_h /2
        if sel.bank_deltas[self.player_i] != 0:
            label_m += COST_LABEL_T
            assert sel.bank_deltas[self.player_i] < 0, "Can only pay costs to travel"
            pay_to = 'BANK'
            for oth_p in self.state.players:
                j = oth_p.index
                if j != self.player_i and sel.bank_deltas[j] != 0:
                    assert sel.bank_deltas[j] > 0, "Non-moving players only receive"
                    pay_to = oth_p.name
            cost_label = f'PAY {-sel.bank_deltas[self.player_i]} TO {pay_to}'
            _, label_h = self.draw_text(cost_label, OPT_LABEL_FONT, OPT_LABEL_FONT_SIZE,
                pg.Rect(0, label_m, OPT_W, 0), pg.Color(255, 0, 0), buffer=opt_buffer)

        # Add buttons
        if len(self._options) > 1:
            button_t = PROGRESS_T - (BUTTON_MARGIN + BUTTON_H) * 2
            button_w = (OPT_W - 3 * BUTTON_MARGIN) // 2
            self.add_button(ButtonLabel.Previous.name,
                pg.Rect(MAP_W + BUTTON_MARGIN, button_t, button_w, BUTTON_H),
                self.previous)
            self.add_button(ButtonLabel.Next.name,
                pg.Rect(MAP_W + BUTTON_MARGIN * 2 + button_w, button_t, button_w, BUTTON_H),
                self.next)
        accept_label = ButtonLabel.AcceptMove.name
        close_after = False
        self._is_last_move = False
        if next_pt == self.dest_index:
            accept_label = ButtonLabel.FinishTrip.name
            close_after = True
            self._is_last_move = True
        elif len(self.selected_moves) + 1 == self.distance:
            accept_label = ButtonLabel.FinishTurn.name
            close_after = True
            self._is_last_move = True
        elif len(self._options) == 1:
            accept_label = ButtonLabel.ForcedAcceptMove.name
        button_t = PROGRESS_T - BUTTON_MARGIN - BUTTON_H
        button_w = OPT_W - 2 * BUTTON_MARGIN
        self.add_button(accept_label,
            pg.Rect(MAP_W + BUTTON_MARGIN, button_t, button_w, BUTTON_H),
            self.accept, close_after)

        self.screen.blit(opt_buffer, (MAP_W, 0))

    def draw_map(self):
        history = self.player.history + self.selected_moves
        moves_this_turn = self.moves_so_far + len(self.selected_moves)
        moves_remaining = self.distance - len(self.selected_moves)
        other_play_loc = [(ps.name, ps.location) for ps in self.state.players
            if ps.index != self.player_i]
        buffer = draw_map(self.state.map, (MAP_W, PROGRESS_T),
            self.player.startCityIndex, history, self.dest_index,
            moves_this_turn, moves_remaining,
            [r.move for r in self._options], 
            self._current_selection, other_play_loc)
        self.screen.blit(buffer, (0,0))

    def draw_borders(self):
        pg.draw.line(self.screen, BORDER_COLOR,
            (0, PROGRESS_T), (SCREEN_W, PROGRESS_T), BORDER_LINE_W)
        pg.draw.line(self.screen, BORDER_COLOR,
            (MAP_W, 0), (MAP_W, PROGRESS_T), BORDER_LINE_W)

    def draw(self, init: bool):
        self.solid_background()
        self.draw_progress()
        self.draw_options()
        self.draw_map()
        self.draw_borders()

    def check(self) -> bool:
        return not self._finished or time() - self._mark < FORCED_MOVE_TIME

    @property
    def forced_move(self) -> bool:
        return (len(self._options) == 1 and not self._finished 
            and not self._is_last_move)

    def animate(self) -> bool:
        if self.forced_move:
            curr_t = time()
            if (curr_t - self._mark >= FORCED_MOVE_TIME):
                # Automatically take forced moves after displaying them
                self.select_option(0)
                return True
            else:
                for b in self.buttons:
                    if b.label == ButtonLabel.ForcedAcceptMove.name:
                        self.draw_button(b.label, b.bounds)
                        pg.display.update(b.bounds)

        return False

if __name__ == '__main__':
    pg.init()
    screen = pg.display.set_mode((SCREEN_W, SCREEN_H))
    while True:
        s = GameState()
        for p_i in range(6):
            ps = PlayerState(p_i, f'PLAYER {p_i}')
            s.players.append(ps)
            home_region = s.random_lookup('REGION')
            home_city, home_city_i = s.map.lookup_city(s.random_lookup(home_region))
            s.set_player_home_city(p_i, home_city)

            dest_region = s.random_lookup('REGION')
            while dest_region == home_region:
                dest_region = s.random_lookup('REGION')
            dest, dest_i = s.map.lookup_city(s.random_lookup(dest_region))
            s.set_player_destination(p_i, dest)
            print(f'Generating test move from {home_city} ({home_city_i}) to {dest} ({dest_i})')

            for _ in range(2):
                ps.history.append(
                    calculate_legal_moves(s.map, ps.startCityIndex, 
                        ps.history, ps.destinationIndex, -1)[0])
        move_screen = MoveScreen(screen, s, 0, 12, None, 0)
        move_screen.run()
        print(move_screen.selected_moves)