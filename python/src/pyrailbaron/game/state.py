# pyright: reportPrivateUsage=information

from dataclasses import dataclass, field
from dataclasses_json import dataclass_json

from typing import List, Dict, Tuple, Optional
from enum import Enum

from pyrailbaron.game.constants import *
from pyrailbaron.map.datamodel import read_map, Map, Waypoint
from pyrailbaron.game.charts import read_route_payoffs, read_roll_tables

from random import randint

class Engine(Enum):
    Basic = 0
    Express = 1
    Superchief = 2

MIN_DECLARE_CASH = 200000

@dataclass_json
@dataclass
class PlayerState:
    index: int
    name: str
    
    # Cities have to be stored and read as strings
    _homeCity: Optional[str] = None
    _startCity: Optional[str] = None
    _destination: Optional[str] = None

    # Corresponding point IDs on the map are looked up once
    _homeCityIndex: int = -1
    _startCityIndex: int = -1
    _destinationIndex: int = -1

    @property
    def homeCity(self) -> Optional[str]:
        return self._homeCity
    @property
    def startCity(self) -> Optional[str]:
        return self._startCity
    @property
    def destination(self) -> Optional[str]:
        return self._destination

    @property
    def destinationIndex(self) -> int:
        return self._homeCityIndex if self.declared else self._destinationIndex

    @property
    def startCityIndex(self) -> int:
        return self._startCityIndex

    def _set_home_city(self, hc: str, hc_i: int):
        assert hc_i >= 0, "Cannot set negative _homeCityIndex"
        assert self._homeCity is None, "Can only set home city once"
        assert self._startCity is None, "Can only set home city at the beginning"
        self._homeCity = hc
        self._homeCityIndex = hc_i
        self._startCity = hc
        self._startCityIndex = hc_i

    def _set_destination(self, dest: str, dest_i: int):
        assert dest_i >= 0, "Cannot set negative destination"
        assert self.startCity is not None, "Can only set destination after start is set"
        assert dest != self.destination, "Cannot set the same destination"
        if self.destination:
            assert self.atDestination, "Must reach one destination before setting another"
            self._startCity = self._destination
            self._startCityIndex = self._destinationIndex
        self._destination = dest
        self._destinationIndex = dest_i
        self.history.clear()

    bank: int = 0
    engine: Engine = Engine.Basic
    rr: Optional[str] = None
    established_rate: Optional[int] = None
    rr_owned: List[str] = field(default_factory=list)
    history: List[Waypoint] = field(default_factory=list) 
        # List of rail lines (i.e. rr + pt) used this trip
    declared: bool = False

    @property
    def location(self) -> int:
        if len(self.history) == 0:
            return self._startCityIndex
        else:
            return self.history[-1][1]

    def move(self, waypoints: List[Waypoint]):
        assert len(waypoints) > 0, "Move must contain at least one waypoint"
        assert all(pt_i != self._destinationIndex for _, pt_i 
            in waypoints[:-1]), "The destination can only be the last waypoint"
        self.rr = waypoints[-1][0] # Store last RR visited
        self.history += waypoints

    @property
    def atDestination(self) -> bool:
        return self.destination is not None and self._destinationIndex == self.location

    @property
    def atHomeCity(self) -> bool:
        return self.homeCity is not None and self._homeCityIndex == self.location

    @property
    def canDeclare(self) -> bool:
        return self.atDestination and self.bank >= MIN_DECLARE_CASH

    @property
    def winner(self) -> bool:
        return self.atHomeCity and self.declared and self.bank >= MIN_DECLARE_CASH

    def check_bonus_roll(self, d1: int, d2: int) -> bool:
        return ((self.engine == Engine.Express and d1 == d2) or
            self.engine == Engine.Superchief)

@dataclass_json
@dataclass
class GameState:
    map: Map = field(default_factory=read_map)
    route_payoffs: Dict[str, Dict[str, int]] = field(default_factory=read_route_payoffs)
    roll_tables: Dict[str, List[Tuple[str, str]]] = field(default_factory=read_roll_tables)
    players: List[PlayerState] = field(default_factory=list)

    def set_player_home_city(self, player_i: int, hc: str):
        hc, hc_i = self.map.lookup_city(hc)
        self.players[player_i]._set_home_city(hc, hc_i)

    def set_player_destination(self, player_i: int, dest: str):
        dest, dest_i = self.map.lookup_city(dest)
        self.players[player_i]._set_destination(dest, dest_i)

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

    def get_roll_table_probabilities(self, table: str) -> Dict[str, float]:
        probs: Dict[str, float] = {}
        for i, (odd, even) in enumerate(self.roll_tables):
            p: float = (6 - abs(i - 5)) / 36  # i = 5 -> d = 7 -> most common
            probs[odd] += p / 2
            probs[even] += p / 2
        return probs

    def lookup_roll_table(self, table: str, d1: int, d2: int, d3: int) -> str:
        for d in [d1, d2, d3]:
            assert d >= 1 and d <= 6, "Die rolls must be 1-6"
        odd, even = self.roll_tables[table][d1 + d2 - 2]
        return even if d3 % 2 == 0 else odd

    def random_lookup(self, table: str) -> str:
        return self.lookup_roll_table(table, 
            randint(1,6), randint(1,6), randint(1,6))

    def get_player_purchase_opts(self, player_i: int) -> List[Tuple[str, int]]:
        ps = self.players[player_i]
        options: List[Tuple[str, int]] = []
        if ps.engine == Engine.Basic and ps.bank >= EXPRESS_FEE:
            options.append((Engine.Express.name, EXPRESS_FEE))
        if ps.engine != Engine.Superchief and ps.bank >= SUPERCHIEF_FEE:
            options.append((Engine.Superchief.name, SUPERCHIEF_FEE))
        for rr, rr_data in self.map.railroads.items():
            if self.get_owner(rr) == -1 and ps.bank >= rr_data.cost:
                options.append((rr, rr_data.cost))
        return options