from dataclasses import dataclass, field
from dataclasses_json import dataclass_json

from typing import List, Tuple, Optional
from enum import Enum

from pyrailbaron.map.datamodel import read_map, Map

class Engine(Enum):
    Basic = 0
    Express = 1
    Superchief = 2

MIN_DECLARE_CASH = 200000

Waypoint = Tuple[str, int] # Railroad name, dot

@dataclass_json
@dataclass
class PlayerState:
    name: str
    startCity: int
    homeCity: int
    destination: int
    bank: int
    engine: Engine
    rr: Optional[str] = None
    established_rate: Optional[float] = None
    rr_owned: List[str] = field(default_factory=list)
    history: List[int] = field(default_factory=list) 
        # List of locations previously visited this trip
    declared: bool = field(default=False)
    
    @property
    def location(self) -> int:
        if len(self.history) == 0:
            return self.startCity
        else:
            return self.history[-1][1]

    def set_home_city(self, hc: int):
        assert hc >= 0, "Cannot set negative home city"
        assert self.homeCity < 0, "Home city can only be set once"
        self.homeCity = hc
        self.startCity = hc

    def set_destination(self, dest: int):
        assert dest >= 0, "Cannot set negative destination"
        assert self.startCity > 0, "Cannot set destination until start city is set"
        if self.destination >= 0:
            assert self.atDestination, "Must reach one destination before setting another"
        assert dest != self.destination, "Cannot set the same destination"
        self.startCity = self.location
        self.destination = dest
        self.history.clear()

    def move(self, pts: List[Tuple[str, int]]):
        assert len(pts) > 0, "Move must contain at least one waypoint"
        # TODO: Check continuity here
        assert all(p != self.destination for _,p in pts[:-1]), "The destination must be the last waypoint"
        assert all(wp not in self.history for wp in pts)
        self.rr = pts[-1][0]
        self.history += [p for _, p in pts]

    @property
    def atDestination(self) -> bool:
        if self.destination < 0 or len(self.history) == 0:
            return False
        return self.destination == self.history[-1]

    @property
    def atHomeCity(self) -> bool:
        return self.location == self.homeCity

    @property
    def canDeclare(self) -> bool:
        return self.atDestination and self.bank >= MIN_DECLARE_CASH

    def check_bonus_roll(self, d1: int, d2: int) -> bool:
        return ((self.engine == Engine.Express and d1 == d2) or
            self.engine == Engine.Superchief)

@dataclass_json
@dataclass
class GameState:
    map: Map = field(default_factory=read_map)
    players: List[PlayerState] = field(default_factory=list)

    def get_owner(self, rr: str) -> int:
        for i, ps in enumerate(self.players):
            if rr in ps.rr_owned:
                return i
        return -1

    @property
    def doubleFees(self) -> bool:
        for rr in self.map.railroads:
            if self.get_owner(rr) == -1:
                return False
        # Only double fees if all RRs are owned (i.e. none are owned by bank)
        return True