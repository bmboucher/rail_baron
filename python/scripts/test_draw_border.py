from re import M
from pyrailbaron.map.svg import MapSvg, transform_lcc, transform_dxf
from pyrailbaron.map.datamodel import Map, Coordinate
from pyrailbaron.map.states import get_border_data

from pathlib import Path
from typing import List

ROOT_DIR = (Path(__file__) / '../../..').resolve()
border_data = get_border_data(ROOT_DIR / 'data')

BORDERS_TO_DRAW = [
    [["MINNESOTA",0,[175,0]],
     ["M",[49,-98]],
     ["M",[49,-99]],
     ["M",[49,-100]],
     ["M",[49,-101]],
     ["M",[49,-102]],
     ["M",[40.5,-102]],
     ["M",[40.5,-108]],
     ["M",[37,-108]],
     ["COLORADO",0,[65,45]],
     ["OKLAHOMA",0,[200,33]],
     ["ARKANSAS",0,[0,8]],
     ["M",[36.5,-92.5]],
     ["M",[40.6,-92.5]],
     ["IOWA",0,[124,25]],
     ["WISCONSIN",0,[265,-1]]],
    [["M",[40.5,-108]],
    ["M",[40.5,-109]],
    ["M",[40.5,-110]],
    ["M",[40.5,-111]],
    ["M",[40.5,-112]],
     ["M",[40.5,-113]],
     ["M",[40.5,-114]],
    ["NEVADA",0,[12,0]],
    ["NEVADA",0,[-1,173]],
    ["CALIFORNIA",0,[15,0]],
    ["CALIFORNIA",0,[-1,158]],
    ["ARIZONA",0,[154,113]],
    ["NEW MEXICO",0,[65,52]],
    ["TEXAS",0,[700,606]],
    ["OKLAHOMA",0,[196,200]],
    ["COLORADO",0,[45,65]],
    ["M",[37,-108]]],
   [["TEXAS",0,[606,172]],
    ["LOUISIANA",0,[470,100]],
    ["MISSISSIPPI",0,[70,40]],
            ["M", [32.97, -88.47]],
        ["M", [32.97, -85.50]],
        ["KENTUCKY", 0, [263,150]],
        ["MISSOURI",0,[105,173]],
        ["OKLAHOMA",0,[33,196]]]
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
    for i, row in enumerate(rows):
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
                if len(pts) == 0:
                    l.circle(segment[0], 2, fill='black')
                    l.text('start', segment[0])
                pts += segment
                l.circle(pts[-1], 2, fill='black')
                l.text(str(i), pts[-1])
                print(f'  Added segment from {segment[0]} to {segment[-1]}')
    pts.append(pts[0])
    l.path(pts, stroke=colors[row_idx % 3], stroke_width=0.5, fill='none')

svg.save()