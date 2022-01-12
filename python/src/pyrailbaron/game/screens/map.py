from pathlib import Path
import pygame as pg
from pyrailbaron.game.screens.base import PyGameScreen
from pyrailbaron.map.bfs import points_within

from pyrailbaron.map.datamodel import (
    Coordinate, Map, Waypoint, make_rail_seg, rail_segs_from_wps)
from typing import Callable, List, Tuple, Set
from math import sin, cos, pi, atan2, tan, sqrt

DEFAULT_MAP_PATH = (Path(__file__) / '../../assets/map.png').resolve()

_map_img: pg.surface.Surface|None = None
def get_map_image(path: Path|None = None):
    global _map_img
    if not _map_img:
        _map_img = pg.image.load(path or DEFAULT_MAP_PATH)
    return _map_img

MAP_SCALE = 10.0
MIN_SCALE = 0.3
MAX_SCALE = 0.6
MAP_EXPANSION = 1.2

RAIL_OUTER_W = 3
RAIL_INNER_W = 1.2
MARKER_OUTER_R = 2.25
MARKER_INNER_R = 1.25
MIN_PX_PER_MM = 5

DEST_ARROW_PAD = 5
DEST_ARROW_L = 30
DEST_ARROW_W = 25

OUTLINE_COLOR = pg.Color(0,0,0)
TURN_HISTORY_COLOR = pg.Color(255,255,255)
HISTORY_COLOR = pg.Color(120,120,255)
NEXT_MOVE_COLOR = pg.Color(255, 255, 0)
START_PT_COLOR = pg.Color(0, 255, 0)
TURN_START_PT_COLOR = pg.Color(0,0,255)
DEST_PT_COLOR = pg.Color(255, 0, 0)

OTH_PLAYER_F = 1.2
OTH_PLAYER_W = 1

def get_map_window(m: Map, show_pts: Set[int], size: Tuple[int,int]) -> pg.rect.Rect:
    map_img = get_map_image()
    if len(show_pts) == 1:
        pt, = show_pts
        center = m.points[pt].final_svg_coords
        assert center
        min_bounds = [c * MAP_SCALE - s * MIN_SCALE for c, s in zip(center, size)]
        max_bounds = [c * MAP_SCALE + s * MIN_SCALE for c, s in zip(center, size)]
    else:
        coords = [m.points[p].final_svg_coords for p in show_pts]
        min_bounds = [min(c[i] * MAP_SCALE for c in coords if c) for i in range(2)]
        max_bounds = [max(c[i] * MAP_SCALE for c in coords if c) for i in range(2)]
    orig_size = [(M - m) * MAP_EXPANSION for m, M in zip(min_bounds, max_bounds)]
    scale = min(size[i]/orig_size[i] for i in range(2) if orig_size[i] > 0)
    scale = min(MAX_SCALE, scale)
    orig_size = [min(D, s / scale) for s, D in zip(size, map_img.get_size())]
    scale = min(size[i]/orig_size[i] for i in range(2) if orig_size[i] > 0)
    orig_size = [s / scale for s in size]
    orig_offset = [max(0, min(D - os, (m + M - os) / 2)) for m, M, os, D in 
        zip(min_bounds, max_bounds, orig_size, map_img.get_size())]
    bounds = pg.Rect(*orig_offset, *orig_size)
    return bounds

def optimize_map_window(m: Map, size: Tuple[int, int],
    start_pt: int, history: List[Waypoint], dest_pt: int,
    moves_this_turn: int, moves_remaining: int,
    next_points: List[Waypoint]) -> pg.rect.Rect:
    turn_history = [] if moves_this_turn == 0 else history[-moves_this_turn:]
    turn_start_pt = (start_pt if moves_this_turn + 1 > len(history)
        else history[-(moves_this_turn + 1)][1])
    curr_pt = start_pt if len(history) == 0 else history[-1][1]

    pts_to_show: Set[int] = set([start_pt, turn_start_pt, curr_pt, dest_pt] 
        + [p for _,p in history + next_points])
    window = get_map_image().get_bounding_rect()
    img_w, img_h = get_map_image().get_size()
    def calculate_window():
        nonlocal window
        window = get_map_window(m, pts_to_show, size)
    max_w = min(size[0] / MIN_SCALE, img_w)
    max_h = min(size[1] / MIN_SCALE, img_h)
    def too_big() -> bool:
        return (window.width > max_w or window.height > max_h)
    
    calculate_window()

    if too_big():
        # First, drop history before this turn
        pts_to_show: Set[int] = set([turn_start_pt, curr_pt, dest_pt] 
            + [p for _,p in turn_history + next_points])
        calculate_window()

    if too_big():
        # Then, drop history altogether
        pts_to_show: Set[int] = set([curr_pt, dest_pt]
            + [p for _,p in next_points])
        calculate_window()

    d = moves_remaining
    while d > 0 and too_big():
        # It's possible the destination is too far; look at only the points
        # reachable this turn (plus this turn's history)
        reachable_pts = points_within(m, start_pt, dest_pt, history, d)
        curr_pt = start_pt if len(history) == 0 else history[-1][1]
        curr_dist = m.gc_distance(curr_pt, dest_pt)
        closer_pts = set(filter(
            lambda p: m.gc_distance(p, dest_pt) < curr_dist, reachable_pts))
        pts_to_show = closer_pts.union([curr_pt] 
            + [p for _,p in turn_history + next_points])
        calculate_window()

        if too_big():
            pts_to_show = closer_pts.union([curr_pt] 
                + [p for _,p in next_points])
            calculate_window()
        d -= 1
    
    if too_big():
        # If all else fails, just make sure we can show where we are and the
        # next options
        pts_to_show = set([curr_pt] + [p for _,p in next_points])
        calculate_window()

    return window

def draw_star(buffer: pg.surface.Surface, pt: Coordinate,
        inner_r: float, outer_r: float, color: pg.Color):
    a = -pi / 2
    outer_flag = True
    pts: List[Coordinate] = []
    c_x, c_y = pt
    for _ in range(10):
        r = outer_r if outer_flag else inner_r
        pts.append((c_x + r * cos(a), c_y + r * sin(a)))
        outer_flag = not outer_flag
        a += pi / 5
    pg.draw.polygon(buffer, color, pts, 0)

def draw_map(m: Map, size: Tuple[int, int],
        start_pt: int, history: List[Waypoint], dest_pt: int, 
        moves_this_turn: int, moves_remaining: int,
        next_points: List[Waypoint], next_point_selected: int,
        other_player_loc: List[Tuple[str,int]]) -> pg.surface.Surface:
    map_img = get_map_image()
    window = optimize_map_window(m, size, start_pt, history, dest_pt, 
        moves_this_turn, moves_remaining, next_points)

    buffer = pg.surface.Surface(size)
    pg.draw.rect(buffer, pg.Color(255,255,255), buffer.get_bounding_rect(), 0)
    buffer.blit(pg.transform.scale(map_img.subsurface(window), size), (0,0))
    def transform(pt_i: int):
        c = m.points[pt_i].final_svg_coords
        assert c, "Must have SVG coords"
        return ((c[0] * MAP_SCALE - window.left) * size[0] / window.width,
                (c[1] * MAP_SCALE - window.top) * size[1] / window.height)
    def in_window(pt_i: int):
        t_x, t_y = transform(pt_i)
        return t_x >= 0 and t_x <= size[0] and t_y >= 0 and t_y <= size[1]
    
    def make_pair(i: int, j: int) -> Tuple[int, int]:
        return (i, j) if i < j else (j, i)

    last_pt = start_pt if len(history) == 0 else history[-1][1]
    _, next_pt = next_points[next_point_selected]
    next_pair = make_pair(last_pt, next_pt)

    turn_history = [] if moves_this_turn == 0 else history[-moves_this_turn:]
    turn_start_pt = start_pt if moves_this_turn + 1 > len(history) else history[-(moves_this_turn+1)][1]
    turn_history_pairs: Set[Tuple[int, int]] = set()
    curr_pt = turn_start_pt
    for _, p in turn_history:
        turn_history_pairs.add(make_pair(curr_pt, p)); curr_pt = p

    history_pairs: Set[Tuple[int, int]] = set()
    curr_pt = start_pt
    for _, p in history:
        history_pairs.add(make_pair(curr_pt, p)); curr_pt = p

    turn_history_pts = set(p for _,p in turn_history)
    history_pts = set(p for _,p in history)
    
    def draw_all_pts(handler: Callable[[int], None]):
        for pt_i in range(len(m.points)):
            if in_window(pt_i):
                handler(pt_i)
    def draw_all_lines(handler: Callable[[str, int, int], None]):
        for p in m.points:
            for rr in p.connections:
                for oth_p in p.connections[rr]:
                    if p.index > oth_p:
                        continue
                    if not in_window(p.index) and not in_window(oth_p):
                        continue
                    handler(rr, p.index, oth_p)

    px_per_mm = max(MIN_PX_PER_MM, 
        min(s / ws for s, ws in zip(size, window.size)) * MAP_SCALE)
    def draw_line(rr: str, i: int, j: int, color: pg.Color, w: float):
        triangles = m.railroads[rr].triangles
        p = make_pair(i,j)
        if triangles:
            for v1,v2,v3 in triangles:
                if p in [make_pair(v1,v2), make_pair(v1,v3)]:
                    v2_t = transform(v2)
                    v3_t = transform(v3)
                    mid_pt = ((v2_t[0]+v3_t[0])/2, (v2_t[1]+v3_t[1])/2)
                    pts = [transform(v1), mid_pt]
                    pg.draw.line(buffer, color, transform(v1), mid_pt, int(w * px_per_mm))
                    if i == v2 or j == v2:
                        pts.append(transform(v2))
                    else:
                        pts.append(transform(v3))
                    pg.draw.lines(buffer, color, False, pts, int(w * px_per_mm))
                    return
        pg.draw.line(buffer, color, transform(i), transform(j), int(w * px_per_mm))
    def draw_pt(i: int, color: pg.Color, r: float):
        c_x, c_y = transform(i)
        if i in [start_pt, turn_start_pt, dest_pt]:
            draw_star(buffer, (c_x, c_y), r * px_per_mm, 2 * r * px_per_mm, color)
        elif len(m.points[i].city_names) > 0:
            pg.draw.rect(buffer, color,
                pg.Rect(c_x - r * px_per_mm, c_y - r * px_per_mm, 
                        2 * r * px_per_mm, 2 * r * px_per_mm), 0)
        else:
            pg.draw.circle(buffer, color, (c_x, c_y), r * px_per_mm, 0)

    def draw_rail_outline(rr: str, i: int, j: int):
        if make_pair(i,j) in history_pairs.union([next_pair]):
            draw_line(rr, i, j, OUTLINE_COLOR, RAIL_OUTER_W)
    def draw_city_outline(i: int):
        if i in [start_pt, curr_pt, next_pt, dest_pt] or i in history_pts:
            draw_pt(i, OUTLINE_COLOR, MARKER_OUTER_R)
    def draw_inner_marker(i: int):
        color = HISTORY_COLOR
        if i == start_pt:
            color = START_PT_COLOR
        elif i == next_pt:
            color = NEXT_MOVE_COLOR
        elif i == dest_pt:
            color = DEST_PT_COLOR
        elif i == turn_start_pt:
            color = TURN_START_PT_COLOR
        elif i in turn_history_pts:
            color = TURN_HISTORY_COLOR
        elif i not in history_pts:
            return
        draw_pt(i, color, MARKER_INNER_R)
    def draw_inner_rail(rr: str, i: int, j: int):
        p = make_pair(i, j)
        rs = make_rail_seg(rr, i, j)
        if p == next_pair and rs == make_rail_seg(rr, curr_pt, next_pt):
            color = NEXT_MOVE_COLOR
        elif p in turn_history_pairs:
            if rs not in rail_segs_from_wps(turn_start_pt, turn_history):
                return
            color = TURN_HISTORY_COLOR
        elif p in history_pairs:
            if rs not in rail_segs_from_wps(start_pt, history):
                return
            color = HISTORY_COLOR
        else:
            return
        draw_line(rr, i, j, color, RAIL_INNER_W)

    # Draw black outlines first
    draw_all_lines(draw_rail_outline)
    draw_all_pts(draw_city_outline)

    # Draw inners (order matters)
    draw_all_lines(draw_inner_rail)
    draw_all_pts(draw_inner_marker)

    if not in_window(dest_pt):
        w, h = size
        c_x, c_y = w/2, h/2
        d_x, d_y = transform(dest_pt)
        angles = atan2(d_y - c_y, d_x - c_x)
        tip_x, tip_y = 0,0
        if -pi/4 <= angles and angles < pi/4:
            tip_x = w
            tip_y = c_y + (w/2) * tan(angles)
        elif pi/4 <= angles and angles < 3 * pi/4:
            tip_y = h
            tip_x = w/2 + (h/2) * tan(pi/2 - angles)
        elif 3 * pi/4 <= angles or angles < -3 * pi/4:
            tip_x = 0
            tip_y = h/2 - (w/2) * tan(angles)
        elif -3 * pi/4 <= angles and angles < -pi/4:
            tip_y = 0
            tip_x = w/2 - (h/2) * tan(pi/2 - angles)
        tip_x -= DEST_ARROW_PAD * cos(angles)
        tip_y -= DEST_ARROW_PAD * sin(angles)
        base_x = tip_x - DEST_ARROW_L * cos(angles)
        base_y = tip_y - DEST_ARROW_L * sin(angles)
        pts = [(tip_x, tip_y), 
                (base_x - (DEST_ARROW_W/2)*sin(angles), base_y + (DEST_ARROW_W/2) * cos(angles)),
                (base_x + (DEST_ARROW_W/2)*sin(angles), base_y - (DEST_ARROW_W/2) * cos(angles))]
        pg.draw.polygon(buffer, pg.Color(255, 0, 0), pts, 0)
        pg.draw.polygon(buffer, pg.Color(0, 0, 0), pts, 5)

    for oth_pn, oth_loc in other_player_loc:
        if in_window(oth_loc):
            c_x, c_y = transform(oth_loc)
            s = int(OTH_PLAYER_F * MARKER_OUTER_R * px_per_mm)
            angles = [15 * pi/180, pi/4]
            angles.append(pi/2 - angles[0])
            radii = [s, s * 2 / sqrt(2), s]
            a_offset = 0
            for _ in range(4):
                pts = [(c_x + r * cos(a + a_offset), c_y + r * sin(a + a_offset)) 
                        for r,a in zip(radii, angles)]
                pg.draw.lines(buffer, pg.Color(255, 0, 0), False, pts, 
                    int(OTH_PLAYER_W * px_per_mm))
                a_offset += pi/2
            [label, ], (label_w, label_h) = PyGameScreen.render_text(
                oth_pn, 'Corrigan-ExtraBold', 20, 5 * s, pg.Color(255,0,0))
            buffer.blit(label, (c_x - label_w/2, c_y - s - 2 - label_h))

    return buffer