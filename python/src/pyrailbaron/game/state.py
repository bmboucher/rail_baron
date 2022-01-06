# pyright: reportPrivateUsage=information

from dataclasses import dataclass, field
from dataclasses_json import dataclass_json

from typing import List, Dict, Tuple, Optional
from enum import Enum

from pyrailbaron.game.constants import *
from pyrailbaron.map.datamodel import make_rail_seg, rail_segs_from_wps, read_map, Map, Waypoint
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
    def startCityIndex(self) -> int:
        return self._startCityIndex
    @property
    def destinationIndex(self) -> int:
        return self._homeCityIndex if self.declared else self._destinationIndex
    @property
    def homeCityIndex(self) -> int:
        return self._homeCityIndex

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
            self.trips_completed += 1
        self._destination = dest
        self._destinationIndex = dest_i
        self.history.clear()
        self.trip_turns = 0
        self.trip_fees_paid = 0
        self.trip_fees_received = 0
        self.trip_miles = 0.0
        self.rover_play_index = -1

    bank: int = 0
    engine: Engine = Engine.Basic
    rr: Optional[str] = None
    established_rate: Optional[int] = None
    rr_owned: List[str] = field(default_factory=list)
    history: List[Waypoint] = field(default_factory=list) 
        # List of rail lines (i.e. rr + pt) used this trip
    declared: bool = False

    # Game statistics
    total_fees_paid: int = 0
    total_fees_received: int = 0
    total_route_payoffs: int = 0
    total_miles: float = 0.0
    rover_play_wins: int = 0
    rover_play_losses: int = 0
    times_declared: int = 0
    trips_completed: int = 0

    # Current trip statistics
    trip_turns: int = 0
    trip_fees_paid: int = 0
    trip_fees_received: int = 0
    rover_play_index: int = -1
    trip_miles: float = 0.0
    def record_turn_start(self):
        self.trip_turns += 1
    def record_user_fees(self, bank_deltas: List[int]):
        fee = bank_deltas[self.index]
        if fee > 0:
            self.total_fees_received += fee
            self.trip_fees_received += fee
        else:
            self.total_fees_paid -= fee
            self.trip_fees_paid -= fee
    def record_route_payoff(self, payoff: int):
        self.total_route_payoffs += payoff
    def record_rover_play(self, winner: bool, rover_play_index: int):
        if winner:
            self.rover_play_wins += 1
        else:
            assert rover_play_index == len(self.history) - 1, "Can only lose a rover play at last location"
            self.rover_play_losses += 1
        self.rover_play_index = rover_play_index

    def declare(self):
        assert self.canDeclare, "Can't declare right now"
        self.declared = True
        self.times_declared += 1

    @property
    def location(self) -> int:
        if len(self.history) == 0:
            return self._startCityIndex
        else:
            return self.history[-1][1]

    def move(self, m: Map, waypoints: List[Waypoint]):
        assert len(waypoints) > 0, "Move must contain at least one waypoint"
        assert all(pt_i != self.destinationIndex for _, pt_i 
            in waypoints[:-1]), "The destination can only be the last waypoint"
        curr_pt = self.location
        used_segs = rail_segs_from_wps(self.startCityIndex, self.history)
        alt_used_segs = used_segs.copy()
        if self.rover_play_index >= 0:
            rover_pt = self.history[self.rover_play_index][1]
            alt_used_segs = rail_segs_from_wps(rover_pt, self.history[self.rover_play_index + 1:])
        seg_miles: float = 0.0
        for rr, next_pt in waypoints:
            assert rr in m.points[curr_pt].connections, f"Can't take {rr} from {curr_pt}"
            assert next_pt in m.points[curr_pt].connections[rr], f"Can't take {rr} from {curr_pt} to {next_pt}"
            rs = make_rail_seg(rr, curr_pt, next_pt)
            if rs in used_segs:
                # This had to be added to cover the corner case that a player
                # may have a rover pulled on them near their home city, in a
                # way that prevents any legal moves to the (alternate) destination.
                # The player who pulls the rover move may similarly be too aggressive
                # and leave no options to continue to their own destination; however,
                # this is somewhat handled by checking before attempting the rover
                # at all. It's REALLY hard to program the AI to avoid this, and
                # I'm not sure what a human would even do on the receiving end, so
                # we cover this corner case by just relaxing the rules a little if
                # a rover has occurred this trip. Just a little ;)
                assert self.rover_play_index >= 0, "Can only reuse rail segs after a rover play"
                assert rs not in alt_used_segs, "Can only reuse rail segs from BEFORE the rover"
            used_segs.append(rs)
            seg_miles += m.gc_distance(curr_pt, next_pt)
            curr_pt = next_pt

        self.trip_miles += seg_miles
        self.total_miles += seg_miles
        self.rr = waypoints[-1][0] # Store last RR visited
        self.history += waypoints
        if self.trip_turns == 0:
            # We may be on the bonus roll after destination changes
            self.trip_turns = 1

    @property
    def atDestination(self) -> bool:
        return self.destination is not None and self._destinationIndex == self.location

    @property
    def atHomeCity(self) -> bool:
        return self.homeCity is not None and self._homeCityIndex == self.location

    @property
    def canDeclare(self) -> bool:
        return not self.declared and self.atDestination and self.bank >= MIN_DECLARE_CASH

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