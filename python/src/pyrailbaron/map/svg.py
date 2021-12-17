from pyrailbaron.map.inkscape import InkscapeDrawing
from svgwrite.container import Group
from typing import Tuple, List, Callable
from math import sin, cos, pi, log, tan, sqrt, atan

from pyrailbaron.map.datamodel import Coordinate

MAX_SVG_WIDTH = 787
MAX_SVG_HEIGHT = 381

class MapSvg(InkscapeDrawing):
    def __init__(self, *args, **kwargs):
        if 'size' not in kwargs:
            kwargs['size'] = (f'{MAX_SVG_WIDTH}mm', f'{MAX_SVG_HEIGHT}mm')
        if 'viewBox' not in kwargs:
            kwargs['viewBox'] = f'0 0 {MAX_SVG_WIDTH} {MAX_SVG_HEIGHT}'
        super().__init__(*args, **kwargs)
        self.layers = []
        self.transforms = []

    def layer(self, label: str, **kwargs) -> 'MapSvgLayer':
        g = super().layer(label=label, **kwargs)
        l = MapSvgLayer(self, g, self.transforms)
        self.layers.append(l.g)
        return l

    def save(self, *args, **kwargs):
        for l in self.layers:
            self.add(l)
        super().save(*args, **kwargs)

class MapSvgLayer:
    def __init__(self, parent: MapSvg, g: Group, transforms: List[Callable[[Coordinate], Coordinate]] = None):
        self.parent = parent
        self.g = g
        self.transforms = transforms.copy() if transforms else []

    def apply_transforms(self, p: Coordinate) -> Coordinate:
        new_p = (p[0],p[1])
        for t in self.transforms:
            new_p = t(new_p)
        return new_p

    def line(self, p1: Coordinate, p2: Coordinate, **kwargs):
        self.g.add(self.parent.line(
            self.apply_transforms(p1),
            self.apply_transforms(p2), 
            **kwargs))

    def path(self, pts: List[Coordinate], **kwargs):
        p = self.parent.path(d='M', **kwargs)
        for pt in pts:
            p.push(self.apply_transforms(pt))
        self.g.add(p)

    def square(self, c: Coordinate, s: float, angle_deg: float, **kwargs):
        c_x,c_y = self.apply_transforms(c)
        a = (angle_deg + 45) * pi/180
        d = s / (2 * sqrt(2))
        pts = [(c_x + d * cos(a + (i*pi)/2), 
                c_y + d * sin(a + (i*pi)/2)) for i in range(4)]
        pts.append(pts[0])
        p = self.parent.path(d='M', **kwargs)
        for pt in pts:
            p.push(pt)
        self.g.add(p)

    def cross(self, p: Coordinate, l: float, angle_deg: float, **kwargs):
        p = self.apply_transforms(p)
        a = angle_deg * pi / 180
        for _ in range(2):
            self.g.add(self.parent.line(
                (p[0] + l * cos(a), p[1] + l * sin(a)),
                (p[0] - l * cos(a), p[1] - l * sin(a))))
            a += pi/2

    def circle(self, c: Coordinate, r: float, **kwargs):
        c_x,c_y = self.apply_transforms(c)
        p = self.parent.path(d=f'M {c_x - r} {c_y}', **kwargs)
        p.push_arc((2 * r, 0), 0, r, True, '-', False)
        p.push_arc((-2 * r, 0), 0, r, True, '-', False)
        self.g.add(p)

    def text(self, text: str, insert: Coordinate, **kwargs):
        p = self.apply_transforms(insert)
        self.g.add(self.parent.text(text, insert=p, **kwargs))

    def use(self, href, insert: Coordinate, rotation: float, **kwargs):
        insert = self.apply_transforms(insert)
        u = self.parent.use(href, insert=insert, **kwargs)
        u.rotate(rotation*180/pi, center=insert)
        self.g.add(u)

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