from pathlib import Path
from typing import List, Callable, Dict
import json
import csv

from pyrailbaron.map.states import get_border_data, get_region_border_points
from pyrailbaron.map.svg import MAX_SVG_WIDTH, MapSvg, MapSvgLayer, transform_lcc, transform_dxf, MAX_SVG_HEIGHT
from pyrailbaron.map.datamodel import Map, MapPoint, Coordinate, distance
from typing import List, Tuple
from math import atan2, pi, sin, cos, floor

# Parameters for laser cutter (LC) layer
LC_COLOR = 'blue'
LC_W = 0.5
LC_PARAMS = {'stroke': LC_COLOR, 'stroke_width': LC_W, 'fill': 'none'}
LED_R = 2.6

def main(root_dir):
    # Read raw map data
    map_json = Path(root_dir) / 'output/map.json'
    with map_json.open('rt') as map_file:
        m: Map = Map.from_json(map_file.read())
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
        triangles = [[r[0]] + list(map(int, r[1:])) 
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

    # Define layer to send to laser cutter
    draw_background(svg)
    draw_laser_cut_layer(m, svg)

    # Draw regions (bottom layers)
    for region_name, region_data in regions.items():
        region_layer = svg.layer(region_name)
        region_layer.transforms = geo_transforms.copy()
        draw_region(state_borders, region_data, region_layer)

    # Iterate over points to draw railroad connections
    # Each connection pi -> pj is drawn only when i < j to avoid duplication
    # Layers are added to the SVG only as each RR is found
    rr_layers = dict()
    for p in m.points:
        draw_rr_at_point(m, p, rr_patterns, triangles, svg, rr_layers)
    # We skip drawing two legs of each triangle, and fill in the bisector later:
    draw_rr_triangles(m, rr_patterns, triangles, rr_layers)

    # Draw the circle/square at each map point on top of the RR layers
    draw_map_points(m, svg)

    labels = svg.layer('labels')
    for text, posType, x_s, y_s in svg_text:
        x,y = float(x_s), float(y_s)
        if posType == 'c':
            draw_city_label(m, labels, text, x, y)
    
    labels.transforms.clear()
    labels.text("RAIL BARON", (510,365), 
        font_family='Corrigan ExtraBold', font_size='30px', 
        stroke="#2d6a97", fill="#2d6a97")

    svg.save()

def draw_background(svg):
    background = svg.layer('background')
    background.custom_path(
        d=f'M 0 0 l {MAX_SVG_WIDTH} 0 l 0 {MAX_SVG_HEIGHT} l -{MAX_SVG_WIDTH} 0 l 0 -{MAX_SVG_HEIGHT}',
        fill="#a0b8c4", fill_opacity=0.7)

def draw_laser_cut_layer(m, svg):
    laser_cut_layer = svg.layer('laser_cut')
    draw_led_holes(m, laser_cut_layer)
    laser_cut_layer.transforms.clear()
    draw_outline(laser_cut_layer)
    draw_touchscreen(laser_cut_layer)
    draw_7segment_leds(laser_cut_layer)
    draw_speaker_holes(laser_cut_layer)

TOUCHSCREEN_W = 121.5
TOUCHSCREEN_H = 76.5
TOUCHSCREEN_M = 25
def draw_touchscreen(laser_cut_layer):
    touchscreen_pts = [
        (TOUCHSCREEN_M, MAX_SVG_HEIGHT - TOUCHSCREEN_M - TOUCHSCREEN_H),
        (TOUCHSCREEN_M + TOUCHSCREEN_W, MAX_SVG_HEIGHT - TOUCHSCREEN_M - TOUCHSCREEN_H),
        (TOUCHSCREEN_M + TOUCHSCREEN_W, MAX_SVG_HEIGHT - TOUCHSCREEN_M),
        (TOUCHSCREEN_M, MAX_SVG_HEIGHT - TOUCHSCREEN_M)
    ]
    touchscreen_pts.append(touchscreen_pts[0])
    laser_cut_layer.path(touchscreen_pts, **LC_PARAMS)

LED_7SEG_W = 76
LED_7SEG_H = 19
LED_7SEG_M = 5
LED_TOUCHSCREEN_M = 10
N_LED_7SEG = 4

def draw_7segment_leds(laser_cut_layer: MapSvgLayer):
    start_x = TOUCHSCREEN_M + TOUCHSCREEN_W + LED_TOUCHSCREEN_M
    start_y = MAX_SVG_HEIGHT - TOUCHSCREEN_M - 2 * LED_7SEG_H - LED_7SEG_M
    for x in [start_x, start_x + LED_7SEG_W + LED_7SEG_M]:
        for y in [start_y, start_y + LED_7SEG_H + LED_7SEG_M]:
            laser_cut_layer.path([
                (x,y), (x+LED_7SEG_W,y), (x+LED_7SEG_W, y+LED_7SEG_H), 
                (x, y+LED_7SEG_H), (x,y)], **LC_PARAMS)

SPEAKER_HOLE_R = 1.25
SPEAKER_HOLE_S = 4.5
SPEAKER_H = 20
SPEAKER_W = 30
SPEAKER_TOUCHSCREEN_M = 5
def draw_speaker_holes(laser_cut_layer: MapSvgLayer):
    row_height = SPEAKER_HOLE_S * sin(pi/3)
    n = floor((SPEAKER_W - 2 * SPEAKER_HOLE_R)/SPEAKER_HOLE_S)
    n = 2 * floor((n - 1) / 2) + 1 # Bump to next odd
    x = TOUCHSCREEN_M + TOUCHSCREEN_W / 2 - ((n - 1) * SPEAKER_HOLE_S) / 2
    y = (MAX_SVG_HEIGHT - TOUCHSCREEN_M - TOUCHSCREEN_H 
        - SPEAKER_TOUCHSCREEN_M - SPEAKER_H/2)

    laser_cut_layer.custom_path(
        d=f'M {TOUCHSCREEN_M + TOUCHSCREEN_W / 2-SPEAKER_W/2+SPEAKER_H/2} {y-SPEAKER_H/2} ' +
          f'a {SPEAKER_H/2} {SPEAKER_H/2} 0 0 0 0 {SPEAKER_H} ' +
          f'l {SPEAKER_W-SPEAKER_H} 0 ' +
          f'a {SPEAKER_H/2} {SPEAKER_H/2} 0 0 0 0 {-SPEAKER_H} ' +
          f'l {-SPEAKER_W+SPEAKER_H} 0 ', 
        **LC_PARAMS)

    for _ in range(n):
        laser_cut_layer.circle((x,y), SPEAKER_HOLE_R, **LC_PARAMS)
        x += SPEAKER_HOLE_S
    x -= 1.5 * SPEAKER_HOLE_S
    for _ in range(n - 1):
        for y_c in [y - row_height, y + row_height]:
            laser_cut_layer.circle((x,y_c), SPEAKER_HOLE_R, **LC_PARAMS)
        x -= SPEAKER_HOLE_S

def draw_city_label(m: Map, label_layer: MapSvgLayer, text: str, x: float, y: float):
    try:
        search_text = text.replace(r'\n','').replace('/','').replace(' ','').upper()
        city_pt = next(p for p in m.points 
                    if p.place_name.upper().replace(' ','') == search_text
                    and len(p.city_names) > 0)
        city_x, city_y = city_pt.final_svg_coords
        for line in text.split(r'\n'):
            label_layer.text(line.replace('_',''), (city_x + x, city_y + y), 
                font_size='4px', font_family='Verdana')
            y += 4
    except StopIteration:
        print(f'Could not find city for {text}')

def draw_map_points(m, svg):
    cities = svg.layer('cities')
    for p in m.points:
        if len(p.city_names) == 0:
            cities.circle(p.final_svg_coords, 1.5, fill='white', stroke='black',
                stroke_width=1, stroke_linecap='round', stroke_linejoin='round')
        else:
            cities.square(p.final_svg_coords, 8, 0, fill='white', stroke='black',
                stroke_width=1.5, stroke_linecap='round', stroke_linejoin='round')

def draw_rr_triangles(m, rr_patterns, triangles, rr_layers):
    for rr, p1, p2, p3 in triangles:
        pattern_data = rr_patterns[rr]
        c1 = m.points[p1].final_svg_coords
        x2,y2 = m.points[p2].final_svg_coords
        x3,y3 = m.points[p3].final_svg_coords
        mid_p = ((x2+x3)/2,(y2+y3)/2)
        rr_layers[rr].draw_rr(c1,mid_p,rr,pattern_data)

def draw_rr_at_point(m: Map, p: MapPoint, rr_patterns, triangles, 
        svg: MapSvgLayer, rr_layers):
    conn_map = {}
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
        segs = get_parallels(p.final_svg_coords, other_p.final_svg_coords,
                n_segs, 2)
        for i,(p1,p2) in enumerate(segs):
            rr = conn_map[p_idx][i]
            if rr not in rr_layers:
                rr_layers[rr] = svg.layer(f'rr_{rr}'.upper())
            if rr in rr_patterns:
                pattern_data = rr_patterns[rr]
                rr_layers[rr].draw_rr(p1,p2,rr,pattern_data)
            else:
                rr_layers[rr].line(p1, p2, stroke='red', stroke_width=1.0)

OC_R = 20      # Outer corner radius
OC_HOLE_M = 15 # Outer corner hole margin (center to edge)
OC_HOLE_D = 4  # Outer corner hole diameter
def draw_outline(laser_cut_layer: MapSvgLayer):
    arc = f'a {OC_R} {OC_R} 0 0 1'
    laser_cut_layer.custom_path(
        d=f'M 0 {OC_R} ' + 
          f'{arc} {OC_R} {-OC_R} ' +
          f'L {MAX_SVG_WIDTH-OC_R} 0 ' +
          f'{arc} {OC_R} {OC_R} ' +
          f'L {MAX_SVG_WIDTH} {MAX_SVG_HEIGHT-OC_R} ' +
          f'{arc} {-OC_R} {OC_R} ' +
          f'L {OC_R} {MAX_SVG_HEIGHT} ' +
          f'{arc} {-OC_R} {-OC_R} ' +
          f'L 0 {OC_R}', **LC_PARAMS)
    def oc_hole(p: Coordinate):
        laser_cut_layer.circle(p, OC_HOLE_D/2, **LC_PARAMS)
    oc_hole((OC_HOLE_M,OC_HOLE_M))
    oc_hole((MAX_SVG_WIDTH - OC_HOLE_M, OC_HOLE_M))
    oc_hole((MAX_SVG_WIDTH - OC_HOLE_M, MAX_SVG_HEIGHT - OC_HOLE_M))
    oc_hole((OC_HOLE_M, MAX_SVG_HEIGHT - OC_HOLE_M))

def draw_led_holes(m: Map, laser_cut_layer: MapSvgLayer):
    for p in m.points:
        laser_cut_layer.circle(p.final_svg_coords, LED_R, **LC_PARAMS)

def draw_region(state_borders, region_data, region_layer):
    # Draw a closed region with styling
    def region_area(pts):
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