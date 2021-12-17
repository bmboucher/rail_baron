from pathlib import Path
from typing import List, Callable, Dict
import json
import csv

from pyrailbaron.map.states import get_border_data, get_region_border_points
from pyrailbaron.map.svg import MapSvg, MapSvgLayer, transform_lcc, transform_dxf
from pyrailbaron.map.datamodel import Map, Coordinate, distance
from typing import List, Tuple
from math import atan2, pi, sin, cos, floor

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

def duplicate_border_pattern(rr_layer: MapSvgLayer, 
        p1: Coordinate, p2: Coordinate, 
        pattern, pattern_w: float, pattern_h: float):
    d = distance(p1,p2)
    n = floor(d / pattern_w)
    x1,y1 = p1
    x2,y2 = p2
    x_d,y_d = x2-x1,y2-y1
    a = atan2(y_d,x_d)
    start_d = (d - n * pattern_w)/2
    x,y = x1 + (start_d/d) * x_d + (pattern_h/2)*cos(a - pi/2), \
          y1 + (start_d/d) * y_d + (pattern_h/2)*sin(a - pi/2)
    for _ in range(n):
        rr_layer.use(pattern, (x,y), a)
        x += (pattern_w/d) * x_d
        y += (pattern_w/d) * y_d

def main(root_dir):
    map_json = Path(root_dir) / 'output/map.json'
    with map_json.open('rt') as map_file:
        map: Map = Map.from_json(map_file.read())
    
    def shift_up(c: Coordinate) -> Coordinate:
        x, y = c
        return x + 10, y - 10

    svg = MapSvg(Path(root_dir) / 'output/map.svg')
    svg.transforms = [shift_up]
    geo_transforms = [transform_lcc, map.map_transform, transform_dxf, shift_up]

    borders = get_border_data(Path(root_dir) / 'data')
    with (root_dir / 'data/region_borders.json').open('rt') as region_file:
        regions = json.load(region_file)
    for region in regions:
        region_pts =  get_region_border_points(borders, regions[region]['border'])
        region_layer = svg.layer(region)
        region_layer.transforms = geo_transforms.copy()
        fill_color = regions[region]['fill']
        region_layer.path(region_pts, fill_opacity=0.6, stroke='#a0a0a0', 
            fill=fill_color, stroke_width=0.25)
        
        for state, idx_from, idx_to in regions[region].get('islands',[]):
            islands = borders[state][idx_from:idx_to]
            for island in islands:
                region_layer.path(island, fill_opacity=0.6, stroke='#a0a0a0', 
            fill=fill_color, stroke_width=0.25)

    holes = svg.layer('holes')
    labels = svg.layer('labels')
    rr_layer = svg.layer('rr')
    with (root_dir / 'data/rr_patterns.json').open('r') as rr_patterns_file:
        rr_patterns = json.load(rr_patterns_file)

    pattern_defs = {}
    for rr, pattern in rr_patterns.items():
        if pattern['style'] == 'def':
            pattern_g = svg.defs.add(svg.g(id=f'{rr}_pattern'))
            for path_data in pattern['pattern']:
                p = svg.path(**path_data)
                pattern_g.add(p)
            pattern_defs[rr] = pattern_g

    for p in map.points:
        holes.circle(p.final_svg_coords, 2.6, stroke='blue', stroke_width=0.01,
            fill = 'none')
        if len(p.city_names) > 0:
            #labels.text(p.place_name.upper(), p.final_svg_coords, font_size='5px')
            pass
        else:
            labels.text(str(p.index), p.final_svg_coords, font_size='4px')
            pass
        conn_map = {}
        for rr in p.connections:
            for j in p.connections[rr]:
                if p.index < j:
                    if j not in conn_map:
                        conn_map[j] = []
                    conn_map[j].append(rr)
        for p_idx in conn_map:
            n_segs = len(conn_map[p_idx])
            other_p = map.points[p_idx]
            segs = get_parallels(p.final_svg_coords, other_p.final_svg_coords,
                n_segs, 2)
            for i,(p1,p2) in enumerate(segs):
                rr = conn_map[p_idx][i]
                if rr in rr_patterns:
                    pattern = rr_patterns[rr]
                    if pattern['style'] == 'line':
                        rr_layer.line(p1, p2, **pattern['args'])
                    elif pattern['style'] == 'def':
                        duplicate_border_pattern(rr_layer, p1, p2,
                            pattern_defs[rr], pattern['pattern_w'], pattern['pattern_h'])
                else:
                    rr_layer.line(p1, p2, stroke='red', stroke_width=1.0)

    cities = svg.layer('cities')
    for p in map.points:
        if len(p.city_names) == 0:
            cities.circle(p.final_svg_coords, 1.5, fill='white', stroke='black',
                stroke_width=1, stroke_linecap='round', stroke_linejoin='round')
        else:
            cities.square(p.final_svg_coords, 8, 0, fill='white', stroke='black',
                stroke_width=1.5, stroke_linecap='round', stroke_linejoin='round')

    labels2 = svg.layer('labels2')
    with (root_dir / 'data/svg_text.csv').open('rt') as svg_text_file:
        svg_text = list(csv.reader(svg_text_file))
    for text, posType, x_s, y_s in svg_text:
        x,y = float(x_s), float(y_s)
        if posType == 'c':
            try:
                search_text = text.replace(r'\n','').replace(' ','').upper()
                city_pt = next(p for p in map.points 
                    if p.place_name.upper().replace(' ','') == search_text
                    and len(p.city_names) > 0)
                city_x, city_y = city_pt.final_svg_coords
                for line in text.split(r'\n'):
                    labels2.text(line.replace('_',''), (city_x + x, city_y + y), font_size='4px', font_family='Verdana')
                    y += 4
            except StopIteration:
                print(f'Could not find city for {text}')

    svg.save()

if __name__ == '__main__':
    ROOT_DIR = (Path(__file__) / '../../../../..').resolve()
    main(ROOT_DIR)