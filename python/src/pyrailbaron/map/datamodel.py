from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from typing import Tuple, List, Set, Optional, Dict

Coordinate = Tuple[float, float]

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

    def _connect_to(self, other: 'MapPoint', rr: str):
        if rr not in self.connections:
            self.connections[rr] = set()
        self.connections[rr].add(other.index)

    def connect_to(self, other: 'MapPoint', rr: str):
        self._connect_to(other, rr)
        other._connect_to(self, rr)
