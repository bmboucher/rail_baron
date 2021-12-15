from pathlib import Path
from typing import List, Callable, Dict
import json
import csv

from pyrailbaron.map.states import get_border_data, get_region_border_points
from pyrailbaron.map.svg import MapSvg, MapSvgLayer, transform_lcc, transform_dxf
from pyrailbaron.map.datamodel import Map, Coordinate

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

    states = svg.layer('states')
    states.transforms = geo_transforms.copy()

    borders = get_border_data(Path(root_dir) / 'data')
    for state in borders:
        for border in borders[state]:
            states.path(border, stroke='green', stroke_width=0.25, fill='none')

    with (root_dir / 'data/region_borders.json').open('rt') as region_file:
        regions = json.load(region_file)
    for region in regions:
        region_pts =  get_region_border_points(borders, regions[region]['border'])
        region_layer = svg.layer(region)
        region_layer.transforms = geo_transforms.copy()
        fill_color = regions[region]['fill']
        region_layer.path(region_pts, fill_opacity=0.6, stroke='black', 
            fill=fill_color, stroke_width=0.25)

    holes = svg.layer('holes')
    labels = svg.layer('labels')
    rr_layers: Dict[str, MapSvgLayer] = {}
    for p in map.points:
        holes.circle(p.final_svg_coords, 2.6, stroke='blue', stroke_width=0.01,
            fill = 'none')
        if len(p.city_names) > 0:
            #labels.text(p.place_name.upper(), p.final_svg_coords, font_size='5px')
            pass
        else:
            labels.text(str(p.index), p.final_svg_coords, font_size='4px')
        for rr in p.connections:
            if rr not in rr_layers:
                rr_layers[rr] = svg.layer(f'rr_{rr}')
            for j in p.connections[rr]:
                if p.index < j:
                    other_p = map.points[j]
                    rr_layers[rr].line(p.final_svg_coords, other_p.final_svg_coords,
                        stroke='red', stroke_width=1.0)

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