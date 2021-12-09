from pyrailbaron.map.inkscape import InkscapeDrawing
from svgwrite.container import Group
from typing import Tuple, List, Callable
from math import sin, cos, pi

class MapSvg(InkscapeDrawing):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layers = []
        self.transforms = []

    def layer(self, label: str, **kwargs) -> 'MapSvgLayer':
        g = super().layer(label=label, **kwargs)
        l = MapSvgLayer(g, self.transforms)
        self.layers.append(l)
        return l

    def save(self, *args, **kwargs):
        for l in self.layers:
            self.add(l)
        super().save(*args, **kwargs)

Point = Tuple[float, float]
class MapSvgLayer:
    def __init__(self, g: Group, transforms: List[Callable[[Point], Point]] = None):
        self.g = g
        self.transforms = transforms.copy() if transforms else []

    def apply_transforms(self, p: Point) -> Point:
        for t in self.transforms:
            p = t(p)
        return p

    def line(self, p1: Point, p2: Point, **kwargs):
        self.g.add(self.g.line(
            self.apply_transforms(p1),
            self.apply_transforms(p2), 
            **kwargs))

    def cross(self, p: Point, l: float, angle_deg: float, **kwargs):
        p = self.apply_transforms(p)
        a = angle_deg * pi / 180
        for _ in range(2):
            self.g.add(self.g.line(
                p[0] + l * cos(a), p[1] + l * sin(a),
                p[0] - l * cos(a), p[1] - l * sin(a)))
            a += pi/2

    def circle(self, c: Point, r: float, **kwargs):
        for t in self.transforms:
            c = t(c)
        p = self.g.path(d=f'M {c[0] - r} {c[1]}', **kwargs)
        p.push_arc((2 * r, 0), 0, r, True, '-', False)
        p.push_arc((-2 * r, 0), 0, r, True, '-', False)
        self.g.add(p)