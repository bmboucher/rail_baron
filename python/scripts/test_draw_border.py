from re import M
from pyrailbaron.map.svg import MapSvg, transform_lcc, transform_dxf
from pyrailbaron.map.datamodel import Map, Coordinate
from pyrailbaron.map.states import get_border_data

from pathlib import Path
from typing import List

ROOT_DIR = (Path(__file__) / '../../..').resolve()
border_data = get_border_data(ROOT_DIR / 'data')

BORDERS_TO_DRAW = [
    [["WEST VIRGINIA", 0, [256,-1]],
     ["WEST VIRGINIA", 0, [0,45]],
     ["MARYLAND",0,[172,15]],
     ["MARYLAND",1,[17,0]],
     ["MARYLAND",1,[131,39]],
     ["VIRGINIA",1,[57,0]],
     ["MARYLAND",1,[35,25]],
     ["DELAWARE",0,[35,5]],
     ["NEW JERSEY",0,[107,6]],
     ["NEW YORK",1,[100,0]],
     ["NEW YORK",1,[121,110]],
     ["NEW YORK",0,[83,78]],
     ["CONNECTICUT",0,[60,13]],
     ["RHODE ISLAND",0,[20,5]],
     ["MASSACHUSETTS",0,[95,19]],
     ["NEW HAMPSHIRE",0,[38,32]],
     ["MAINE",0,[285,0]],
     ["MAINE",0,[357,310]],
     ["NEW HAMPSHIRE",0,[10,0]],
     ["VERMONT",0,[10,0]],
     ["NEW YORK",0,[31,0]],
     ["NEW YORK",0,[-1,129]],
     ["PENNSYLVANIA",0,[16,0]]]
]

with (ROOT_DIR/'output/map.json').open('rt') as map_json:
    map: Map = Map.from_json(map_json.read())
(ROOT_DIR / 'output/border_test.svg').unlink(missing_ok=True)
svg = MapSvg(ROOT_DIR / 'output/border_test.svg')
svg.transforms = [transform_lcc, map.map_transform, transform_dxf]

colors = ['black', 'red', 'blue']
l = svg.layer('main')
for row_idx, rows in enumerate(BORDERS_TO_DRAW):
    pts: List[Coordinate] = []
    for row in rows:
        if row[0] == 'M':
            pts.append(row[1])
            print(f'  Added point {pts[-1]}')
        else:
            state, border_idx, range = row
            border = border_data[state][border_idx]
            print(f'BORDER {state} #{border_idx} = {len(border)} points')
            segment = None
            if range == 'all':
                segment = border
            elif isinstance(range, list):
                start, end = range
                do_reverse = False
                if (end >= 0 and start > end) or start < 0:
                    start, end = end, start
                    do_reverse = True
                if end == -1:
                    segment = border[start:]
                else:
                    segment = border[start:(end + 1)]
            if segment:
                if do_reverse:
                    segment = segment.copy()
                    segment.reverse()
                pts += segment
                print(f'  Added segment from {segment[0]} to {segment[-1]}')
    pts.append(pts[0])
    l.path(pts, stroke=colors[row_idx % 3], stroke_width=0.5, fill='none')
svg.save()