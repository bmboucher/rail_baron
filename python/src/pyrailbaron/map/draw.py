from pathlib import Path
from typing import List, MutableSet, Callable, Dict, Any
import json
import csv

from pyrailbaron.map.canada import get_canada_data
from pyrailbaron.map.mexico import get_mexico_data
from pyrailbaron.map.states import BorderData, get_border_data, get_region_border_points
from pyrailbaron.map.svg import MAX_SVG_WIDTH, MapSvg, MapSvgLayer, transform_lcc, transform_dxf, MAX_SVG_HEIGHT
from pyrailbaron.map.datamodel import read_map, Map, MapPoint, Coordinate
from typing import List, Tuple
from math import atan2, pi, sin, cos, floor
from random import choice

# Parameters for laser cutter (LC) layer
LC_COLOR = 'blue'
LC_W = 0.001
LC_PARAMS = {'stroke': LC_COLOR, 'stroke_width': LC_W, 'fill': 'none'}
LED_R = 2.6

LOGO_COLOR = "#2d6a97"
BACKGROUND_COLOR = "#a0b8c4"

def test_piece(root_dir : Path):
    with (root_dir / 'data/rr_patterns.json').open('r') as rr_patterns_file:
        rr_patterns = json.load(rr_patterns_file)
    
    TEST_W = 100
    TEST_H = 100
    TEST_N = 4
    TEST_M = 12

    svg = MapSvg(Path(root_dir)/'output/test_piece.svg',
        size=(f'{TEST_W}mm',f'{TEST_H}mm'), viewBox=f'0 0 {TEST_W} {TEST_H}')

    draw_background(svg, TEST_W, TEST_H)
    alum_layer = svg.map_layer('aluminum_lc')
    acr_layer = svg.map_layer('acrylic_lc')
    for lc_layer in [alum_layer, acr_layer]:
        draw_outline(lc_layer, TEST_W, TEST_H, **LC_PARAMS)
        draw_oc_holes(lc_layer, TEST_W, TEST_H, **LC_PARAMS)

    rr_layer = svg.map_layer('rr')
    top_layer = svg.map_layer('top')
    chosen_rrs: MutableSet[str] = set()
    def repeat(pattern: Callable[[float, float], None], y: float):
        x = TEST_W / 2 - ((TEST_N - 1) * TEST_M) / 2
        rr = choice(list(rr_patterns.keys()))
        while rr in chosen_rrs:
            rr = choice(list(rr_patterns.keys()))
        chosen_rrs.add(rr)
        for i in range(TEST_N):
            pattern(x,y)
            if i > 0:
                rr_layer.draw_rr((x - TEST_M, y), (x,y), rr, rr_patterns[rr])
            x += TEST_M
    label_x = TEST_W / 2 + ((TEST_N - 1) * TEST_M) / 2 + 5
    label_y_shift = 1.5

    def basic_row(r: float):
        def pt(x: float, y: float):
            draw_led_circle(top_layer, alum_layer, acr_layer, (x,y), r, 1)
        return pt
    def city_row():
        alt: bool = False
        def pt(x: float, y: float):
            nonlocal alt
            if alt:
                draw_led_circle(top_layer, alum_layer, acr_layer, (x,y), 1.5, 1)
            else:
                draw_led_square(top_layer, alum_layer, acr_layer, (x,y), 8, 1.5)
            alt = not alt
        return pt
    test_r = 1.0
    test_y = 20
    while test_r <= 2.0:
        repeat(basic_row(test_r), test_y)
        top_layer.text(
            f'{test_r}mm', (label_x, test_y + label_y_shift),
            font_size='5px')
        test_r += 0.25
        test_y += 8
    test_y += 2
    # Test alternating square-circle-square
    repeat(city_row(), test_y)
    test_y += 15
    # Test rows at minimum separation
    repeat(basic_row(1.5), test_y)
    test_y += 6
    repeat(basic_row(1.5), test_y)

    test_led_x = TEST_W - label_x - 3
    test_y = 15
    test_r = 2.45
    while test_r <= 2.7:
        acr_layer.circle((test_led_x, test_y), test_r, **LC_PARAMS)
        test_r += 0.025
        test_y += 2 * test_r + 2

    blackout_layer = svg.map_layer('blackout')
    blackout_outline_corners(blackout_layer, TEST_W, TEST_H)
    draw_outline(blackout_layer, TEST_W, TEST_H,
        stroke='black', stroke_width=0.5, fill='none')
    draw_oc_holes(blackout_layer, TEST_W, TEST_H, 
        stroke='none', stroke_width=0, fill='black')

    svg.save()    

def main(root_dir: Path):
    # Read raw map data
    map_json = root_dir / 'output/map.json'
    m: Map = read_map(map_json)
    # Read state borders geo data
    state_borders = get_border_data(Path(root_dir) / 'data')
    # Read region definitions
    with (root_dir / 'data/region_borders.json').open('rt') as region_file:
        regions = json.load(region_file)
    # Read RR pattern data
    with (root_dir / 'data/rr_patterns.json').open('r') as rr_patterns_file:
        rr_patterns = json.load(rr_patterns_file)
    # Read triangle sets (points p1,p2,p3 where p1p2 and p1p3 are not drawn)
    with (root_dir / 'data/triangles.csv').open('r') as triangles_file:
        triangles: List[List[str | int]] = [[r[0]] + list(map(int, r[1:])) # type: ignore
            for r in csv.reader(triangles_file) if len(r) >= 4]
    # Read SVG text data (i.e. city labels)
    with (root_dir / 'data/svg_text.csv').open('rt') as svg_text_file:
        svg_text = list(csv.reader(svg_text_file))

    # Create SVG file
    svg = MapSvg(Path(root_dir) / 'output/map.svg')

    # Define transformations
    def map_final_adj(c: Coordinate) -> Coordinate:
        # Final transform: shift map up and to right (from centered vertically)
        x, y = c
        return x + 10, y - 10
    svg.transforms = [map_final_adj]
    geo_transforms = [transform_lcc, m.map_transform, transform_dxf, 
                      map_final_adj]

    # Solid blue background before all other layers
    draw_background(svg)

    # Define aluminum/acrylic layers to send to laser cutter
    alum_layer, acr_layer = make_laser_cut_layers(svg)

    # Read state borders geo data
    canada = get_canada_data(root_dir / 'data')
    mexico = get_mexico_data(root_dir / 'data')
    na_layer = svg.map_layer('na')
    na_layer.transforms = geo_transforms.copy()
    for nation in [canada, mexico]:
        for area in nation:
            na_layer.path(area, fill='white', stroke='none', stroke_width=0.5)

    # Draw regions (bottom layers)
    for region_name, region_data in regions.items():
        region_layer = svg.map_layer(region_name)
        region_layer.transforms = geo_transforms.copy()
        draw_region(state_borders, region_data, region_layer)

    # Iterate over points to draw railroad connections
    # Each connection pi -> pj is drawn only when i < j to avoid duplication
    # Layers are added to the SVG only as each RR is found
    rr_layers: Dict[str, MapSvgLayer] = dict()
    for p in m.points:
        draw_rr_at_point(m, p, rr_patterns, triangles, svg, rr_layers)
    # We skip drawing two legs of each triangle, and fill in the bisector later:
    draw_rr_triangles(m, rr_patterns, triangles, rr_layers)

    # Draw the circle/square at each map point on top of the RR layers
    draw_map_points(m, svg, alum_layer, acr_layer)

    label_layer = svg.map_layer('labels')
    for text, posType, x_s, y_s in svg_text:
        x,y = float(x_s), float(y_s)
        if posType == 'c':
            draw_city_label(m, label_layer, text, x, y)
        elif posType == 'r':
            draw_region_label(label_layer, text, x, y)
        elif posType == 'rr':
            rr = text.replace('&','').lower()
            rr_data = rr_patterns[rr]
            draw_rr_label(rr_data, label_layer, text, x, y)
    
    logo_layer = svg.map_layer('logo')
    logo_layer.transforms.clear()
    logo_layer.text("RAIL BARON", (510,365), 
        font_family='Corrigan ExtraBold', font_size='30px', 
        stroke=LOGO_COLOR, fill=LOGO_COLOR)
    
    draw_player_labels(svg, alum_layer, acr_layer)

    draw_legend(rr_patterns, svg, alum_layer, acr_layer)
    draw_blackout_layer(svg)

    svg.save()

LEGEND_START_X = 35
LEGEND_START_Y = 18
LEGEND_SPACING = 9.25
LEGEND_LINE_W = 26
LEGEND_TEXT_M = 3
LEGEND_TEXT_H = 4
LEGEND_LED_M = 5
def draw_legend(rr_patterns: Dict[str, Any], svg: MapSvg, alum_layer: MapSvgLayer, acr_layer: MapSvgLayer):
    legend_layer = svg.map_layer('legend')
    legend_layer.transforms.clear()
    sorted_rr_names = list(sorted(sorted(rr_patterns.keys()), 
        key = lambda rr: rr_patterns[rr]['price']))
    x = LEGEND_START_X
    y = LEGEND_START_Y
    for rr in sorted_rr_names:
        rr_data = rr_patterns[rr]
        if rr_data['style'] == 'line':
            rr_color = rr_data['args']['stroke']
        else:
            first_path = rr_data['pattern'][0]
            rr_color = first_path['stroke'] if 'stroke' in first_path else first_path['fill']
        legend_layer.draw_rr((x,y),(x+LEGEND_LINE_W,y),rr,rr_patterns[rr])
        legend_layer.text(rr_data['label'], (x+LEGEND_LINE_W+LEGEND_TEXT_M,y+LEGEND_TEXT_H/2), 
            fill=rr_color, font_family='Verdana', font_size='5px', font_weight='bold')
        draw_led_circle(legend_layer, alum_layer, acr_layer,
            (x - LEGEND_LED_M, y), 2, 1)
        y += LEGEND_SPACING

def draw_background(svg: MapSvg, w: float = MAX_SVG_WIDTH, h: float = MAX_SVG_HEIGHT):
    background = svg.map_layer('background')
    background.custom_path(
        d=f'M 0 0 l {w} 0 l 0 {h} l {-w} 0 l 0 {-h}',
        fill=BACKGROUND_COLOR, fill_opacity=0.7)

def make_laser_cut_layers(svg: MapSvg):
    alum_layer = svg.map_layer('aluminum_lc')
    acr_layer = svg.map_layer('acrylic_lc')
    for laser_cut_layer in [alum_layer, acr_layer]:
        laser_cut_layer.transforms.clear()
        draw_outline(laser_cut_layer, **LC_PARAMS)
        draw_oc_holes(laser_cut_layer, **LC_PARAMS)
        draw_touchscreen(laser_cut_layer, **LC_PARAMS)
        draw_7segment_leds(laser_cut_layer, **LC_PARAMS)
    draw_speaker_holes(alum_layer, **LC_PARAMS)
    draw_speaker_outline(acr_layer, **LC_PARAMS)
    return alum_layer, acr_layer

def draw_blackout_layer(svg: MapSvg):
    blackout_layer = svg.map_layer('blackout')
    blackout_layer.transforms.clear()
    BLACKOUT = {'stroke_width': 0, 'fill': 'black'}
    draw_oc_holes(blackout_layer, **BLACKOUT)
    draw_touchscreen(blackout_layer, **BLACKOUT)
    draw_7segment_leds(blackout_layer, **BLACKOUT)
    draw_speaker_holes(blackout_layer, **BLACKOUT)
    blackout_outline_corners(blackout_layer, **BLACKOUT)
    draw_outline(blackout_layer, stroke='black', stroke_width=0.5, fill='none')

TOUCHSCREEN_W = 121.5
TOUCHSCREEN_H = 76.5
TOUCHSCREEN_MX = 25
TOUCHSCREEN_MY = 20
def draw_touchscreen(layer: MapSvgLayer, **kwargs: Any):
    touchscreen_pts: List[Coordinate] = [
        (TOUCHSCREEN_MX, MAX_SVG_HEIGHT - TOUCHSCREEN_MY - TOUCHSCREEN_H),
        (TOUCHSCREEN_MX + TOUCHSCREEN_W, MAX_SVG_HEIGHT - TOUCHSCREEN_MY - TOUCHSCREEN_H),
        (TOUCHSCREEN_MX + TOUCHSCREEN_W, MAX_SVG_HEIGHT - TOUCHSCREEN_MY),
        (TOUCHSCREEN_MX, MAX_SVG_HEIGHT - TOUCHSCREEN_MY)
    ]
    touchscreen_pts.append(touchscreen_pts[0])
    layer.path(touchscreen_pts, **kwargs)

LED_7SEG_W = 76
LED_7SEG_H = 19
LED_7SEG_MX = 5
LED_7SEG_MY = 3
LED_TOUCHSCREEN_M = 10
N_LED_7SEG = 4
LED_7SEG_LABEL_H = 3.5
LED_7SEG_LABEL_W = 20
def draw_7segment_leds(layer: MapSvgLayer, **kwargs: Any):
    start_x = TOUCHSCREEN_MX + TOUCHSCREEN_W + LED_TOUCHSCREEN_M
    start_y = MAX_SVG_HEIGHT - TOUCHSCREEN_MY - 2 * LED_7SEG_H - 5*LED_7SEG_MY - 2*LED_7SEG_LABEL_H
    for x in [start_x, start_x + LED_7SEG_W + LED_7SEG_MX]:
        for y in [start_y, start_y + LED_7SEG_H + 4*LED_7SEG_MY + LED_7SEG_LABEL_H]:
            layer.path([
                (x,y), (x+LED_7SEG_W,y), (x+LED_7SEG_W, y+LED_7SEG_H), 
                (x, y+LED_7SEG_H), (x,y)], **kwargs)

def draw_player_labels(svg: MapSvg, alum_layer: MapSvgLayer, acr_layer: MapSvgLayer):
    label_layer = svg.map_layer('player_label')
    label_layer.transforms.clear()
    start_x = TOUCHSCREEN_MX + TOUCHSCREEN_W + LED_TOUCHSCREEN_M + LED_7SEG_W/2 - LED_7SEG_LABEL_W/2
    start_y = MAX_SVG_HEIGHT - TOUCHSCREEN_MY - LED_7SEG_H - 4*LED_7SEG_MY - LED_7SEG_LABEL_H
    i = 1
    for y in [start_y, start_y + LED_7SEG_H + 4*LED_7SEG_MY + LED_7SEG_LABEL_H]:
        for x in [start_x, start_x + LED_7SEG_W + LED_7SEG_MX]:
            label_layer.text(f'PLAYER {i}', (x,y),
                font_family='Corrigan ExtraBold', font_size='5px')
            draw_led_circle(label_layer, alum_layer, acr_layer,
                (x - 5, y - LED_7SEG_LABEL_H/2), 2, 1)
            i += 1

SPEAKER_HOLE_R = 1.25
SPEAKER_HOLE_S = 4.5
SPEAKER_H = 20
SPEAKER_W = 30
SPEAKER_OFFSET_R = 20
SPEAKER_TOUCHSCREEN_M = 5

def draw_speaker_holes(layer: MapSvgLayer, **kwargs: Any):
    row_height = SPEAKER_HOLE_S * sin(pi/3)
    n = floor((SPEAKER_W - 2 * SPEAKER_HOLE_R)/SPEAKER_HOLE_S)
    n = 2 * floor((n - 1) / 2) + 1 # Bump to next odd
    x = TOUCHSCREEN_MY + TOUCHSCREEN_W / 2 - ((n - 1) * SPEAKER_HOLE_S) / 2 + SPEAKER_OFFSET_R
    y = (MAX_SVG_HEIGHT - TOUCHSCREEN_MY - TOUCHSCREEN_H 
        - SPEAKER_TOUCHSCREEN_M - SPEAKER_H/2)

    for _ in range(n):
        layer.circle((x,y), SPEAKER_HOLE_R, **kwargs)
        x += SPEAKER_HOLE_S
    x -= 1.5 * SPEAKER_HOLE_S
    for _ in range(n - 1):
        for y_c in [y - row_height, y + row_height]:
            layer.circle((x,y_c), SPEAKER_HOLE_R, **kwargs)
        x -= SPEAKER_HOLE_S

def draw_speaker_outline(layer: MapSvgLayer, **kwargs: Any):
    y = (MAX_SVG_HEIGHT - TOUCHSCREEN_MY - TOUCHSCREEN_H 
        - SPEAKER_TOUCHSCREEN_M - SPEAKER_H/2)
    layer.custom_path(
            d=f'M {TOUCHSCREEN_MY + TOUCHSCREEN_W / 2-SPEAKER_W/2+SPEAKER_H/2 + SPEAKER_OFFSET_R} {y-SPEAKER_H/2} ' +
            f'a {SPEAKER_H/2} {SPEAKER_H/2} 0 0 0 0 {SPEAKER_H} ' +
            f'l {SPEAKER_W-SPEAKER_H} 0 ' +
            f'a {SPEAKER_H/2} {SPEAKER_H/2} 0 0 0 0 {-SPEAKER_H} ' +
            f'l {-SPEAKER_W+SPEAKER_H} 0 ', 
            **kwargs)

def draw_city_label(m: Map, label_layer: MapSvgLayer, text: str, x: float, y: float):
    try:
        search_text = text.replace(r'\n','').replace('/','').replace(' ','').upper()
        city_pt = next(p for p in m.points 
                    if p.place_name and p.place_name.upper().replace(' ','') == search_text
                    and len(p.city_names) > 0)
        assert city_pt.final_svg_coords, "Must have SVG coords"
        city_x, city_y = city_pt.final_svg_coords
        for line in text.split(r'\n'):
            label_layer.text(line.replace('_',''), (city_x + x, city_y + y), 
                font_size='4px', font_family='Verdana')
            y += 4
    except StopIteration:
        print(f'Could not find city for {text}')

def draw_region_label(label_layer: MapSvgLayer, text: str, x: float, y: float):
    for line in text.split(r'\n'):
        label_layer.text(line, (x,y), font_family='Impact', stroke='black',
            stroke_width=0.25, fill='none', font_size='10px')
        y += 12

def draw_rr_label(rr_data: Dict[str, Any], label_layer: MapSvgLayer, text: str, x: float, y: float):
    if rr_data['style'] == 'line':
        rr_color = rr_data['args']['stroke']
    else:
        first_path = rr_data['pattern'][0]
        rr_color = first_path['stroke'] if 'stroke' in first_path else first_path['fill']
    label_layer.text(text, (x,y), font_family='Verdana', stroke='none',
        font_weight='bold', fill=rr_color, font_size='4px')

def draw_led_circle(
        top_layer: MapSvgLayer, 
        mask_layer: MapSvgLayer,
        bottom_layer: MapSvgLayer,
        p: Coordinate, r: float, stroke_width: float):
    top_layer.circle(p, r, stroke='black', fill='white',
        stroke_width=stroke_width, 
        stroke_linecap='round', stroke_linejoin='round')
    mask_layer.circle(p, r-stroke_width/2, **LC_PARAMS)
    bottom_layer.circle(p, LED_R, **LC_PARAMS)

def draw_led_square(
        top_layer: MapSvgLayer,
        mask_layer: MapSvgLayer,
        bottom_layer: MapSvgLayer,
        p: Coordinate, s: float, stroke_width: float):
    top_layer.square(p, s, 0, stroke='black', fill='white',
        stroke_width=stroke_width, stroke_linecap='round', stroke_linejoin='round')
    mask_layer.square(p, s-stroke_width, 0, **LC_PARAMS)
    bottom_layer.circle(p, LED_R, **LC_PARAMS)

def draw_map_points(
        m: Map, svg: MapSvg, alum_layer: MapSvgLayer, acr_layer: MapSvgLayer):
    alum_layer.transforms = svg.transforms.copy()
    acr_layer.transforms = svg.transforms.copy()
    cities = svg.map_layer('cities')
    for p in m.points:
        assert p.final_svg_coords, "Must have SVG coordinates"
        if len(p.city_names) == 0:
            draw_led_circle(cities, alum_layer, acr_layer, p.final_svg_coords, 1.5, 1)
        else:
            draw_led_square(cities, alum_layer, acr_layer, p.final_svg_coords, 8, 1.5)
    alum_layer.transforms.clear()
    acr_layer.transforms.clear()

def draw_rr_triangles(m: Map, rr_patterns: Dict[str, Any], 
        triangles: List[List[str|int]], rr_layers: Dict[str, MapSvgLayer]):
    rr: str; p1: int; p2: int; p3: int
    for rr, p1, p2, p3 in triangles: # type: ignore
        pattern_data = rr_patterns[rr]
        c1: Coordinate = m.points[p1].final_svg_coords # type: ignore
        x2: float; y2: float; x3: float; y3: float
        x2, y2 = m.points[p2].final_svg_coords # type: ignore
        x3, y3 = m.points[p3].final_svg_coords # type: ignore
        mid_p: Coordinate = ((x2+x3)/2,(y2+y3)/2) # type: ignore
        rr_layers[rr].draw_rr(c1,mid_p,rr,pattern_data)

def draw_rr_at_point(m: Map, p: MapPoint, rr_patterns: Dict[str, Any], 
        triangles: List[List[str|int]], svg: MapSvg, 
        rr_layers: Dict[str, MapSvgLayer]):
    conn_map: Dict[int, List[str]] = {}
    for rr in p.connections:
        for j in p.connections[rr]:
            if p.index < j:
                triangle_skip = False
                for t in triangles:
                        # Don't draw two legs of each triangle
                        # i.e. for A,B,C -> replace AB and AC with A(midBC)
                    if ((p.index == t[1] and j in t[2:]) or 
                            (p.index in t[2:]) and j == t[1]):
                        triangle_skip = True
                        break
                if triangle_skip:
                    continue
                if j not in conn_map:
                    conn_map[j] = []
                conn_map[j].append(rr)
    for p_idx in conn_map:
        n_segs = len(conn_map[p_idx])
        other_p = m.points[p_idx]
        assert p.final_svg_coords, "Must have SVG coords"
        assert other_p.final_svg_coords, "Must have SVG coords"
        segs = get_parallels(p.final_svg_coords, other_p.final_svg_coords,
                n_segs, 2)
        for i,(p1,p2) in enumerate(segs):
            rr = conn_map[p_idx][i]
            if rr not in rr_layers:
                rr_layers[rr] = svg.map_layer(f'rr_{rr}'.upper())
            if rr in rr_patterns:
                pattern_data = rr_patterns[rr]
                rr_layers[rr].draw_rr(p1,p2,rr,pattern_data)
            else:
                rr_layers[rr].line(p1, p2, stroke='red', stroke_width=1.0)

OC_R = 10      # Outer corner radius
OC_HOLE_M = 13 # Outer corner hole margin (center to edge)
OC_HOLE_D = 4  # Outer corner hole diameter
def draw_outline(laser_cut_layer: MapSvgLayer, w: float = MAX_SVG_WIDTH,
        h: float = MAX_SVG_HEIGHT, **kwargs: Any):
    arc = f'a {OC_R} {OC_R} 0 0 1'
    laser_cut_layer.custom_path(
        d=f'M 0 {OC_R} ' + 
          f'{arc} {OC_R} {-OC_R} ' +
          f'L {w-OC_R} 0 ' +
          f'{arc} {OC_R} {OC_R} ' +
          f'L {w} {h-OC_R} ' +
          f'{arc} {-OC_R} {OC_R} ' +
          f'L {OC_R} {h} ' +
          f'{arc} {-OC_R} {-OC_R} ' +
          f'L 0 {OC_R}', **kwargs)

def draw_oc_holes(layer: MapSvgLayer, 
        w: float = MAX_SVG_WIDTH, h: float = MAX_SVG_HEIGHT, **kwargs: Any):
    def oc_hole(p: Coordinate):
        layer.circle(p, OC_HOLE_D/2, **kwargs)
    oc_hole((OC_HOLE_M,OC_HOLE_M))
    oc_hole((w - OC_HOLE_M, OC_HOLE_M))
    oc_hole((w - OC_HOLE_M, h - OC_HOLE_M))
    oc_hole((OC_HOLE_M, h - OC_HOLE_M))

def blackout_outline_corners(blackout_layer: MapSvgLayer, 
    w: float = MAX_SVG_WIDTH, h: float = MAX_SVG_HEIGHT, **kwargs: Any):
    blackout_layer.custom_path(
        d=f'M 0 0 l {OC_R} 0 a {OC_R} {OC_R} 0 0 0 {-OC_R} {OC_R} l 0 {-OC_R}',
        **kwargs)
    blackout_layer.custom_path(
        d=f'M {w} 0 l 0 {OC_R} a {OC_R} {OC_R} 0 0 0 {-OC_R} {-OC_R} l {OC_R} 0',
        **kwargs)
    blackout_layer.custom_path(
        d=f'M {w} {h} l 0 {-OC_R} a {OC_R} {OC_R} 0 0 1 {-OC_R} {OC_R} l {OC_R} 0',
        **kwargs)
    blackout_layer.custom_path(
        d=f'M 0 {h} l {OC_R} 0 a {OC_R} {OC_R} 0 0 1 {-OC_R} {-OC_R} l 0 {OC_R}',
        **kwargs)

def draw_region(state_borders: BorderData, 
        region_data: Dict[str, List[List[str]]], region_layer: MapSvgLayer):
    # Draw a closed region with styling
    def region_area(pts: List[Coordinate]):
        region_layer.path(pts, stroke='#a0a0a0', 
            fill=region_data['fill'], stroke_width=0.7)

    # The primary section of each region consists of multiple state borders
    # joined together
    region_area(get_region_border_points(state_borders, region_data['border']))
        
    # The secondary sections are small islands located in a single state
    for state, idx_from, idx_to in region_data.get('islands',[]):
        islands = state_borders[state][idx_from:idx_to]
        for island in islands:
            region_area(island)

def get_parallels(p1: Coordinate, p2: Coordinate, n: int, spacing: float) \
        -> List[Tuple[Coordinate, Coordinate]]:
    x1,y1 = p1
    x2,y2 = p2
    x_d,y_d=x2-x1,y2-y1
    a=atan2(y_d,x_d) + pi/2
    start_shift = -((n - 1) * spacing) / 2
    c_x,c_y = x1 + start_shift*cos(a), y1 + start_shift*sin(a)
    inc_x, inc_y = spacing * cos(a), spacing * sin(a)
    parallels: List[Tuple[Coordinate, Coordinate]] = []
    for _ in range(n):
        parallels.append(((c_x,c_y), (c_x+x_d,c_y+y_d)))
        c_x += inc_x
        c_y += inc_y
    return parallels

if __name__ == '__main__':
    ROOT_DIR = (Path(__file__) / '../../../../..').resolve()
    main(ROOT_DIR)
    test_piece(ROOT_DIR)