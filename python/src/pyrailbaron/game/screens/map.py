from pathlib import Path
import pygame as pg

from pyrailbaron.map.datamodel import Map, Waypoint
from typing import List, Tuple, Set, Iterable

DEFAULT_MAP_PATH = (Path(__file__) / '../../assets/map.png').resolve()

_map_img: pg.surface.Surface|None = None
def get_map_image(path: Path|None = None):
    global _map_img
    if not _map_img:
        _map_img = pg.image.load(path or DEFAULT_MAP_PATH)
    return _map_img

MAP_SCALE = 10.0
MIN_SCALE = 0.1
MAP_EXPANSION = 1.1

def get_map_window(m: Map, show_pts: Iterable[int], size: Tuple[int,int]) -> pg.Rect:
    map_img = get_map_image()

    coords = [m.points[p].final_svg_coords for p in show_pts]
    min_bounds = [min(c[i] * MAP_SCALE for c in coords if c) for i in range(2)]
    max_bounds = [max(c[i] * MAP_SCALE for c in coords if c) for i in range(2)]
    orig_size = [(M - m) * MAP_EXPANSION for m, M in zip(min_bounds, max_bounds)]
    scale = min(size[i]/orig_size[i] for i in range(2) if orig_size[i] > 0)
    scale = max(MIN_SCALE, min(1.0, scale))
    orig_size = [min(D, s / scale) for s, D in zip(size, map_img.get_size())]
    scale = min(size[i]/orig_size[i] for i in range(2) if orig_size[i] > 0)
    orig_offset = [max(0, min(D - os, (m + M - os) / 2)) for m, M, os, D in 
        zip(min_bounds, max_bounds, orig_size, map_img.get_size())]
    bounds = pg.Rect(*orig_offset, *orig_size)
    return bounds

def draw_map(m: Map, show_pts: Iterable[int], size: Tuple[int, int],
        start_pt: int, history: List[Waypoint], dest_pt: int,
        next_points: List[Waypoint], next_point_selected: int) -> pg.surface.Surface:
    map_img = get_map_image()
    window = get_map_window(m, show_pts, size)

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

    curr_pt = start_pt
    last_pt = start_pt if len(history) == 0 else history[-1][1]
    next_pts = set([next_points[next_point_selected][1]])
    next_pairs = set([make_pair(last_pt, next_points[next_point_selected][1])])
    history_pairs: Set[Tuple[int, int]] = set()
    for _, next_pt in history:
        pair = make_pair(curr_pt, next_pt)
        if pair not in next_pairs:
            history_pairs.add(pair)
        curr_pt = next_pt
    history_pts = set(p for _,p in history if p != start_pt and p != dest_pt
        and p not in next_pts)
    
    # First, draw rails
    for p in m.points:
        for oth_p in p.pts_connected_to:
            if p.index > oth_p:
                continue
            if not in_window(p.index) and not in_window(oth_p):
                continue
            pair = make_pair(p.index, oth_p)
            if pair in next_pairs:
                pg.draw.line(buffer, pg.Color(255,255,0),
                    transform(p.index), transform(oth_p), 5)
            elif pair in history_pairs:
                pg.draw.line(buffer, pg.Color(0, 0, 255),
                    transform(p.index), transform(oth_p), 2)

    # Then draw points
    for p in m.points:
        color = pg.Color(0,0,255)
        if p.index == start_pt:
            color = pg.Color(0,255,0)
        elif p.index == dest_pt:
            color = pg.Color(255,0,0)
        elif p.index in next_pts:
            color = pg.Color(255,255,0)
        elif p.index not in history_pts:
            continue
        t_x, t_y = transform(p.index)
        if len(p.city_names) > 0:
            pg.draw.rect(buffer, color, pg.Rect(t_x - 5, t_y - 5, 10, 10), 0)
        else:
            pg.draw.circle(buffer, color, (t_x, t_y), 5, 0)

    return buffer