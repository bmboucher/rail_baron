from pathlib import Path
from typing import List, Callable, Dict
import json

from pyrailbaron.map.states import get_border_data, get_region_border_points
from pyrailbaron.map.svg import MapSvg, MapSvgLayer, transform_lcc, transform_dxf
from pyrailbaron.map.datamodel import Map, Coordinate

def main(root_dir):
    map_json = Path(root_dir) / 'output/map.json'
    with map_json.open('rt') as map_file:
        map: Map = Map.from_json(map_file.read())
    
    svg = MapSvg(Path(root_dir) / 'output/map.svg')
    geo_transforms = [transform_lcc, map.map_transform, transform_dxf]

    states = svg.layer('states')
    states.transforms = geo_transforms.copy()

    borders = get_border_data(Path(root_dir) / 'data')
    for state in borders:
        for border in borders[state]:
            states.path(border, stroke='green', stroke_width=1.0, fill='none')

    with (root_dir / 'data/region_borders.json').open('rt') as region_file:
        regions = json.load(region_file)
    for region in regions:
        region_pts =  get_region_border_points(borders, regions[region])
        region_layer = svg.layer(region)
        region_layer.transforms = geo_transforms.copy()
        region_layer.path(region_pts, stroke='black', 
            fill='blue', stroke_width=1.5)

    holes = svg.layer('holes')
    labels = svg.layer('labels')
    rr_layers: Dict[str, MapSvgLayer] = {}
    for p in map.points:
        holes.circle(p.final_svg_coords, 2.25, stroke='blue', stroke_width=0.5,
            fill = 'none' if len(p.city_names) == 0 else 'black')
        labels.text(str(p.index), p.final_svg_coords, font_size='5px')
        for rr in p.connections:
            if rr not in rr_layers:
                rr_layers[rr] = svg.layer(f'rr_{rr}')
            for j in p.connections[rr]:
                if p.index < j:
                    other_p = map.points[j]
                    rr_layers[rr].line(p.final_svg_coords, other_p.final_svg_coords,
                        stroke='red', stroke_width=1.0)
    svg.save()

if __name__ == '__main__':
    ROOT_DIR = (Path(__file__) / '../../../../..').resolve()
    main(ROOT_DIR)