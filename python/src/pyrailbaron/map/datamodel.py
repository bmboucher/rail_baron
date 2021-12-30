from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from typing import Tuple, List, Set, Optional, Dict
from math import sqrt
from pathlib import Path

Coordinate = Tuple[float, float]

def distance(p1: Coordinate, p2: Coordinate):
    return sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

@dataclass_json
@dataclass
class MapPoint:
    index: int               # Numbered ordering of points
    dxf_coords: Coordinate   # Coordinates taken from raw DXF file
    city_names: List[str] = field(default_factory=list)
        # Use a list for pairs like San Francisco-Oakland
        # Will only be populated for named destination cities
    geonames_lookup: Optional[str] = field(default=None)
        # Name to lookup in geonames dump data
    place_name: Optional[str] = field(default=None)
        # Single place name for displays
    state: Optional[str] = field(default=None)
        # May be unknown before lat,lon are calculated
    geo_coords: Optional[Coordinate] = field(default=None)
        # Latitude/longitude (need to be calculated)
    connections: Dict[str, Set[int]] = field(default_factory=dict)
        # Indexes of connected MapPoints, grouped by railroad name
    final_svg_coords: Optional[Coordinate] = field(default=None)
        # Final coordinates in the .svg

    def _connect_to(self, other: 'MapPoint', rr: str):
        if rr not in self.connections:
            self.connections[rr] = set()
        self.connections[rr].add(other.index)

    def connect_to(self, other: 'MapPoint', rr: str):
        self._connect_to(other, rr)
        other._connect_to(self, rr)

@dataclass_json
@dataclass
class Railroad:
    id: str
    shortName: str
    longName: str
    cost: int

@dataclass_json
@dataclass
class Map:
    points: List[MapPoint] = field(default_factory=list)
    map_transform_A: List[List[float]] = field(default_factory=list)
    map_transform_b: List[float] = field(default_factory=list)
    railroads: Dict[str, Railroad] = field(default_factory=dict)

    def map_transform(self, c: Coordinate) -> Coordinate:
        x, y = c
        A, b = self.map_transform_A, self.map_transform_b
        return A[0][0] * x + A[0][1] * y + b[0], \
               A[1][0] * x + A[1][1] * y + b[1]

    def lookup_city(self, city: str) -> Tuple[str, int]:
        def canon(s: str) -> str:
            return s.upper().replace('.','').replace(' ','')
        for pt in self.points:
            for c in pt.city_names:
                if canon(c) == canon(city):
                    return c, pt.index

def read_map(json_path: Path = None) -> Map:
    if not json_path:
        json_path = (Path(__file__) / '../../../../../data/map.json').resolve()
    with json_path.open('r') as json_file:
        return Map.from_json(json_file.read())