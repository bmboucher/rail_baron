from typing import NamedTuple, List, Dict, Any
from pathlib import Path
import re
import ezdxf
from svgwrite import mm
from pyrailbaron.map.inkscape import InkscapeDrawing

# This file is python/scripts/scrape_dxf.py
ROOT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = ROOT_DIR / 'data'
OUTPUT_DIR = ROOT_DIR / 'output'

# Output files
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
point_csv = OUTPUT_DIR / 'points.csv'
rr_csv = OUTPUT_DIR / 'railroads.csv'
graph = OUTPUT_DIR / 'graph.txt'
svg_file = OUTPUT_DIR / 'all.svg'
point_csv.unlink(missing_ok=True)
rr_csv.unlink(missing_ok=True)
graph.unlink(missing_ok=True)
svg_file.unlink(missing_ok=True)

class Point(NamedTuple):
    i: int
    x: float
    y: float
    connections: Dict[str, List['Point']]

    @staticmethod
    def new(i: int, x: float, y: float):
        return Point(i, x, y, {})

    def connect_to(self, p: 'Point', rr: str, recurse: bool = True):
        if rr not in self.connections:
            self.connections[rr] = []
        if p not in self.connections[rr]:
            self.connections[rr].append(p)
        if recurse:
            p.connect_to(self, rr, False)
    
points: List[Point] = []
TOLERANCE = 0.5
def get_point(x: float, y: float, append: bool = False) -> int:
    for i,p in enumerate(points):
        if (p.x-x)**2 + (p.y-y)**2 < TOLERANCE:
            return i
    if append:
        points.append(Point.new(len(points),x,y))
        with point_csv.open('a') as point_file:
            point_file.write(f'{len(points)-1},{x},{y}\n')
        return len(points) - 1
    else:
        raise RuntimeError(f'Point ({x},{y}) not found')

network_path = ROOT_DIR / 'data/network.dxf'
network_doc = ezdxf.readfile(network_path) # type: ignore
for e in network_doc.entities:
    x1,y1,z1 = e.dxf.start
    x2,y2,z2 = e.dxf.end
    p1 = get_point(x1,y1,append=True)
    p2 = get_point(x2,y2,append=True)
print(f'Found {len(points)} points')

rr_list: List[str] = []
for rr_path in (ROOT_DIR/'data').glob('rr_*.dxf'):
    rr_name = re.sub(r'rr_(.*)\.dxf', r'\1', rr_path.name)
    rr_doc = ezdxf.readfile(rr_path) # type: ignore
    for e in rr_doc.entities:
        x1,y1,z1 = e.dxf.start
        x2,y2,z2 = e.dxf.end
        p1 = get_point(x1,y1)
        p2 = get_point(x2,y2)
        points[p1].connect_to(points[p2], rr_name)
        with rr_csv.open('a') as rr_file:
            rr_file.write(f'{rr_name},{p1},{p2}\n')
    rr_list.append(rr_name)
print(f'Found {len(rr_list)} railroads')

with graph.open('w') as gfile:
    for p in points:
        gfile.write(f'{p.i},{p.x},{p.y}\n')
        for rr in p.connections:
            conn_list = ','.join(str(p2.i) for p2 in p.connections[rr])
            gfile.write(f'    {rr} -> {conn_list}\n')
        if len(p.connections) == 0:
            print(f'WARNING! Point #{p.i} ({p.x},{p.y}) has no connections')

X_SIZE = 787
Y_SIZE = 381
MIN_PAD = 30

min_x = min(p.x for p in points)
max_x = max(p.x for p in points)
min_y = min(p.y for p in points)
max_y = max(p.y for p in points)
scale = min((X_SIZE - 2 * MIN_PAD)/(max_x - min_x),
            (Y_SIZE - 2 * MIN_PAD)/(max_y - min_y))
act_padding_x = X_SIZE - scale * (max_x - min_x) - MIN_PAD
act_padding_y = Y_SIZE - scale * (max_y - min_y) - MIN_PAD
print(f'Calculated scale {scale} (padding = {act_padding_x},{act_padding_y})')

def transform(x: float, y: float):
    return (x - min_x) * scale + act_padding_x, \
           (max_y - y) * scale + act_padding_y

dwg = InkscapeDrawing(svg_file, size=(X_SIZE*mm,Y_SIZE*mm), profile='full',
    viewBox=(f'0 0 {X_SIZE} {Y_SIZE}'))
def circle(c_x: float, c_y: float, r: float, **kwargs: Any):
    p = dwg.path(d=f'M {c_x-r} {c_y}', **kwargs)
    p.push_arc((2*r, 0), 0, r, True, '-', False)
    p.push_arc((-2*r, 0), 0, r, True, '-', False)
    return p

hole_layer = dwg.layer(label='holes')
label_layer = dwg.layer(label='labels')

for p in points:
    t_x, t_y = transform(p.x,p.y)
    hole_layer.add(circle(t_x, t_y, 2.5, 
        fill='none', stroke='blue', stroke_width=0.25))
    label_layer.add(dwg.text(str(p.i),insert=(t_x, t_y),font_size='5px'))
dwg.add(hole_layer)
dwg.add(label_layer)

for rr in rr_list:
    rr_layer = dwg.layer(label=f'rr_{rr}')
    for p in points:
        if rr in p.connections:
            for p2 in p.connections[rr]:
                if p2.i > p.i:
                    rr_layer.add(dwg.line(transform(p.x,p.y),transform(p2.x,p2.y),
                        stroke='red', stroke_width=0.5))
    dwg.add(rr_layer)

dwg.save()