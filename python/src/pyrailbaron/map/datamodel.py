from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from typing import Tuple, List, Set, Optional, Dict, Iterable
from math import sqrt, asin, sin, cos, pi
from pathlib import Path

Coordinate = Tuple[float, float]

def distance(p1: Coordinate, p2: Coordinate):
    return sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

R_EARTH = 3959.0
def gc_distance(geo1: Coordinate, geo2: Coordinate, R: float = R_EARTH):
    lat1, lon1 = geo1[0] * pi/180, geo1[1] * pi/180
    lat2, lon2 = geo2[0] * pi/180, geo2[1] * pi/180
    rhs = (sin((lat2-lat1)/2)**2) + cos(lat1)*cos(lat2)*(sin((lon2-lon1)/2)**2)
    return 2*R*asin(sqrt(rhs))

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
    region: Optional[str] = None

    @property
    def display_name(self) -> str:
        return f'{(self.place_name or "").replace("_","")}, {self.state}'

    def _connect_to(self, other: 'MapPoint', rr: str):
        if rr not in self.connections:
            self.connections[rr] = set()
        self.connections[rr].add(other.index)

    def connect_to(self, other: 'MapPoint', rr: str):
        self._connect_to(other, rr)
        other._connect_to(self, rr)

    @property
    def pts_connected_to(self) -> List[int]:
        return list(sorted(set(
            pt_j for pts in self.connections.values() for pt_j in pts)))

@dataclass_json
@dataclass
class Railroad:
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
        raise StopIteration

    def gc_distance(self, pt_i: int, pt_j: int, R: float = R_EARTH) -> float:
        geo1 = self.points[pt_i].geo_coords
        geo2 = self.points[pt_j].geo_coords
        assert geo1, "Must have geo coords"
        assert geo2, "Must have geo coords"
        return gc_distance(geo1, geo2, R)

def read_map(json_path: Path | None = None) -> Map:
    if not json_path:
        json_path = (Path(__file__) / '../../../../../data/map.json').resolve()
    with json_path.open('r') as json_file:
        return Map.from_json(json_file.read()) # type: ignore

Waypoint = Tuple[str, int]         # Railroad name, dot
RailSegment = Tuple[str, int, int] # Railroad name + 2 dots (in order)

def make_rail_seg(rr: str, pt_i: int, pt_j: int) -> RailSegment:
    assert pt_i != pt_j, "Rail segment must connect two different points"
    return (rr, pt_i, pt_j) if pt_i < pt_j else (rr, pt_j, pt_i)

def rail_segs_from_wps(start_pt: int, wp: List[Waypoint]) -> List[RailSegment]:
    curr_pt = start_pt
    rail_segs: List[RailSegment] = []
    for rr, next_pt in wp:
        assert curr_pt != next_pt, f"Invalid history {wp} from {start_pt} -> duplicate {curr_pt}"
        rail_segs.append(make_rail_seg(rr, curr_pt, next_pt)); curr_pt = next_pt
    return rail_segs

def get_valid_waypoints(m: Map, pt_i: int, 
        exclude_rs: List[RailSegment] = [], 
        exclude_pts: Iterable[int] = []) -> List[Waypoint]:
    wps: List[Waypoint] = []
    for rr, conn_pts in m.points[pt_i].connections.items():
        for pt_j in conn_pts:
            rs = make_rail_seg(rr, pt_i, pt_j)
            if pt_j not in exclude_pts and rs not in exclude_rs:
                wps.append((rr, pt_j))
    return wps