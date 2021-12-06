from typing import NamedTuple, List, Dict, Tuple
from pathlib import Path
import re
import ezdxf

# This file is python/scripts/scrape_dxf.py
ROOT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = ROOT_DIR / 'data'
OUTPUT_DIR = ROOT_DIR / 'output'

# Output files
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
point_csv = OUTPUT_DIR / 'points.csv'
rr_csv = OUTPUT_DIR / 'railroads.csv'
graph = OUTPUT_DIR / 'graph.txt'
point_csv.unlink(missing_ok=True)
rr_csv.unlink(missing_ok=True)
graph.unlink(missing_ok=True)

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
TOLERANCE = 0.1
def get_point(x,y,append=False) -> int:
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
network_doc = ezdxf.readfile(network_path)
for e in network_doc.entities:
    x1,y1,z1 = e.dxf.start
    x2,y2,z2 = e.dxf.end
    p1 = get_point(x1,y1,append=True)
    p2 = get_point(x2,y2,append=True)
print(f'Found {len(points)} points')

rr_count = 0
for rr_path in (ROOT_DIR/'data').glob('rr_*.dxf'):
    rr_name = re.sub(r'rr_(.*)\.dxf', r'\1', rr_path.name)
    rr_doc = ezdxf.readfile(rr_path)
    for e in rr_doc.entities:
        x1,y1,z1 = e.dxf.start
        x2,y2,z2 = e.dxf.end
        p1 = get_point(x1,y1)
        p2 = get_point(x2,y2)
        points[p1].connect_to(points[p2], rr_name)
        with rr_csv.open('a') as rr_file:
            rr_file.write(f'{rr_name},{p1},{p2}\n')
    rr_count += 1
print(f'Found {rr_count} railroads')

with graph.open('w') as gfile:
    for p in points:
        gfile.write(f'{p.i},{p.x},{p.y}\n')
        for rr in p.connections:
            conn_list = ','.join(str(p2.i) for p2 in p.connections[rr])
            gfile.write(f'    {rr} -> {conn_list}\n')
        if len(p.connections) == 0:
            print(f'WARNING! Point #{p.i} ({p.x},{p.y}) has no connections')