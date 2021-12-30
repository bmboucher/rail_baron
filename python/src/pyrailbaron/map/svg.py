from pyrailbaron.map.inkscape import InkscapeDrawing
from svgwrite.container import Group
from svgwrite.drawing import Defs
from svgwrite.path import Path
from svgwrite.container import Use
from typing import List, Callable, Any, Dict
from math import sin, cos, pi, log, tan, sqrt, atan, floor, atan2

from pyrailbaron.map.datamodel import Coordinate, distance

MAX_SVG_WIDTH = 787
MAX_SVG_HEIGHT = 381

Transform = Callable[[Coordinate], Coordinate]

class MapSvg(InkscapeDrawing):
    def __init__(self, *args: Any, **kwargs: Any):
        if 'size' not in kwargs:
            kwargs['size'] = (f'{MAX_SVG_WIDTH}mm', f'{MAX_SVG_HEIGHT}mm')
        if 'viewBox' not in kwargs:
            kwargs['viewBox'] = f'0 0 {MAX_SVG_WIDTH} {MAX_SVG_HEIGHT}'
        super().__init__(*args, **kwargs)
        self.layers: List[Group] = []
        self.transforms: List[Transform] = []
        self.patterns: Dict[str, Any] = dict()

    def map_layer(self, label: str, **kwargs: Any) -> 'MapSvgLayer':
        g: Group = super().layer(label=label, **kwargs) # type: ignore
        l = MapSvgLayer(self, g, self.transforms)
        self.layers.append(l.g)
        return l

    def add_pattern(self, name: str, paths: List[Any]):
        id = f'__{name}'
        pattern_g: Defs = self.defs.add(self.g(id=id)) # type: ignore
        for path_data in paths:
            p: Path = self.path(**path_data)
            pattern_g.add(p)
        self.patterns[name] = pattern_g

    def save(self, *args: Any, **kwargs: Any):
        for l in self.layers:
            self.add(l)
        super().save(*args, **kwargs)

class MapSvgLayer:
    def __init__(self, parent: MapSvg, g: Group, 
            transforms: List[Callable[[Coordinate], Coordinate]] | None = None):
        self.parent = parent
        self.g = g
        self.transforms = transforms.copy() if transforms else []

    def apply_transforms(self, p: Coordinate) -> Coordinate:
        new_p = (p[0],p[1])
        for t in self.transforms:
            new_p = t(new_p)
        return new_p

    def line(self, p1: Coordinate, p2: Coordinate, **kwargs: Any):
        self.g.add(self.parent.line(
            self.apply_transforms(p1),
            self.apply_transforms(p2), 
            **kwargs)) # type: ignore

    def path(self, pts: List[Coordinate], **kwargs: Any):
        p: Path = self.parent.path(d='M', **kwargs)
        for pt in pts:
            p.push(self.apply_transforms(pt))
        self.g.add(p)

    def custom_path(self, **kwargs: Any):
        p: Path = self.parent.path(**kwargs)
        self.g.add(p)

    def square(self, c: Coordinate, s: float, angle_deg: float, **kwargs: Any):
        c_x,c_y = self.apply_transforms(c)
        a = (angle_deg + 45) * pi/180
        d = s / (2 * sqrt(2))
        pts = [(c_x + d * cos(a + (i*pi)/2), 
                c_y + d * sin(a + (i*pi)/2)) for i in range(4)]
        pts.append(pts[0])
        p: Path = self.parent.path(d='M', **kwargs)
        for pt in pts:
            p.push(pt)
        self.g.add(p)

    def cross(self, p: Coordinate, l: float, angle_deg: float, **kwargs: Any):
        p = self.apply_transforms(p)
        a = angle_deg * pi / 180
        for _ in range(2):
            self.g.add(self.parent.line(
                (p[0] + l * cos(a), p[1] + l * sin(a)),
                (p[0] - l * cos(a), p[1] - l * sin(a)))) # type: ignore
            a += pi/2

    def circle(self, c: Coordinate, r: float, **kwargs: Any):
        c_x,c_y = self.apply_transforms(c)
        p: Path = self.parent.path(d=f'M {c_x - r} {c_y}', **kwargs)
        p.push_arc((2 * r, 0), 0, r, True, '-', False)
        p.push_arc((-2 * r, 0), 0, r, True, '-', False)
        self.g.add(p)

    def text(self, text: str, insert: Coordinate, **kwargs: Any):
        p = self.apply_transforms(insert)
        self.g.add(self.parent.text(text, insert=p, **kwargs)) # type: ignore

    def use(self, href: Defs, insert: Coordinate, rotation: float, **kwargs: Any):
        insert = self.apply_transforms(insert)
        u: Use = self.parent.use(href, insert=insert, **kwargs)
        u.rotate(rotation*180/pi, center=insert)
        self.g.add(u)

    def draw_rr(self, p1: Coordinate, p2: Coordinate, 
            rr: str, pattern_data: Dict[str, Any]):
        if pattern_data['style'] == 'line':
            self.line(p1, p2, **pattern_data['args'])
        elif pattern_data['style'] == 'def':
            if rr not in self.parent.patterns:
                self.parent.add_pattern(rr, pattern_data['pattern'])
            d = distance(p1,p2)
            pattern_w = pattern_data['pattern_w']
            n = floor(d / pattern_w)
            x1,y1 = p1
            x2,y2 = p2
            x_d,y_d = x2-x1,y2-y1
            a = atan2(y_d,x_d)
            start_d = (d - n * pattern_w)/2
            x,y = x1 + (start_d/d) * x_d, \
                y1 + (start_d/d) * y_d
            for _ in range(n):
                self.use(self.parent.patterns[rr], (x,y), a)
                x += (pattern_w/d) * x_d
                y += (pattern_w/d) * y_d

# The mapping from original .dxf files to the final assembled .svg is fixed
# in this file rather than recalculated based on data each time; this provides
# some consistency in the visualizations

# The coordinates taken from the original .dxf files are centered on (0,0)
# Positive Y is "up"
# The SVG has only positive coordinates, Y is "distance from top"
MIN_DXF_X = -352
MAX_DXF_X = 367
MIN_DXF_Y = -151
MAX_DXF_Y = 198
MIN_SVG_PADDING = 30

# Calculate scale to fit DXF inside SVG, centered vertically and right-aligned horiz
DXF_SCALE = min((MAX_SVG_WIDTH - 2 * MIN_SVG_PADDING)/(MAX_DXF_X - MIN_DXF_X),
                (MAX_SVG_HEIGHT - 2 * MIN_SVG_PADDING)/(MAX_DXF_Y - MIN_DXF_Y))
DXF_PAD_X = MAX_SVG_WIDTH - DXF_SCALE * (MAX_DXF_X - MIN_DXF_X) - MIN_SVG_PADDING
DXF_PAD_Y = (MAX_SVG_HEIGHT - DXF_SCALE * (MAX_DXF_Y - MIN_DXF_Y))/2

# Apply scale and flip y-axis
def transform_dxf(coords: Coordinate) -> Coordinate:
    x, y = coords
    return DXF_PAD_X + DXF_SCALE * (x - MIN_DXF_X), \
           DXF_PAD_Y + DXF_SCALE * (MAX_DXF_Y - y)

# Lambert Conformal Conic projection
# Maps lat,lon -> x,y

def calculate_lcc_n(ref_lat1: float, ref_lat2: float) -> float:
    l1 = ref_lat1 * pi/180
    l2 = ref_lat2 * pi/180
    return log(cos(l1)/cos(l2))/(log(tan(pi/4 + l2/2)/tan(pi/4 + l1/2)))

# Standardized for US maps: parallels at 33 deg and 45 deg
LCC_STD_LAT1 = 33
LCC_STD_LAT2 = 45
LCC_N = calculate_lcc_n(LCC_STD_LAT1, LCC_STD_LAT2)

def transform_lcc(geo: Coordinate, n: float = LCC_N) -> Coordinate:
    lat, lon = geo[0] * pi/180, geo[1] * pi/180
    rho = (tan(pi/4 + lat/2))**(-n)
    return rho * sin(n*lon), -rho * cos(n*lon)

def inv_transform_lcc(coords: Coordinate, n: float = LCC_N) -> Coordinate:
    x, y = coords
    rho = sqrt(x**2 + y**2)
    lon = atan(-x/y) / n
    while lon > 0:
        lon -= 2 * pi
    lat = 2*atan(rho**(-1/n)) - pi/2
    return lat * 180/pi, lon * 180/pi