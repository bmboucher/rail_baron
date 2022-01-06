from dataclasses import dataclass
from pyrailbaron.game.fees import calculate_user_fees
from pyrailbaron.map.bfs import quick_network_distance
from pyrailbaron.map.datamodel import (
    Map, Waypoint, RailSegment, make_rail_seg, get_valid_waypoints)
from typing import List, MutableSet, Tuple

def calculate_legal_moves(m: Map, start_pt: int, history: List[Waypoint], dest_pt: int,
        rover_play_index: int) -> List[Waypoint]:
    # First, collect the rail segs used so far
    rail_segs_used: List[RailSegment] = []
    curr_pt = start_pt
    for rr, next_pt in history:
        rail_segs_used.append(make_rail_seg(rr, curr_pt, next_pt))
        curr_pt = next_pt

    # We need to identify "trapped" points, which we can't travel to because
    # they have only 0-1 remaining unused rail lines; this starts with points
    # we've traveled to and expands iteratively to points which are "trapped"
    # by those, etc...
    trapped_pts: List[int] = []
    def valid_wp(pt_i: int) -> List[Waypoint]:
        return get_valid_waypoints(m, pt_i, rail_segs_used, trapped_pts)
    def check_for_trapped(pt_i: int) -> bool:
        if pt_i == curr_pt or pt_i == dest_pt:
            return False
        if len(valid_wp(pt_i)) < 2:
            print(f'Point {m.points[pt_i].display_name} ({pt_i}) is trapped')
            return True
        else:
            return False
    trapped_pts += list(filter(check_for_trapped, 
        [start_pt] + [p for _,p in history]))

    # Iteratively expand trapped_pts
    found_new = True
    while found_new:
        found_new = False
        conn_pts: MutableSet[int] = set()
        for pt_i in trapped_pts:
            for conn_pt in m.points[pt_i].pts_connected_to:
                conn_pts.add(conn_pt)
        for pt_i in conn_pts:
            if pt_i in trapped_pts:
                continue
            if check_for_trapped(pt_i):
                trapped_pts.append(pt_i)
                found_new = True

    # We can't generally exclude "dead ends" like Tampa/Norfolk because they might
    # be our destination
    valid_moves: List[Waypoint] = []
    for rr in m.points[curr_pt].connections:
        for next_pt in m.points[curr_pt].connections[rr]:
            if make_rail_seg(rr, curr_pt, next_pt) in rail_segs_used:
                print(f"Can't take {rr} to {next_pt} - already used")
            elif next_pt in trapped_pts:
                print(f"Can't take {rr} to {next_pt} - trapped")
            elif next_pt == dest_pt:
                print(f'Adding {rr} to {next_pt} - is destination')
                valid_moves.append((rr,next_pt))
            else:
                next_legal_moves = valid_wp(next_pt)
                if len(next_legal_moves) > 1:
                    valid_moves.append((rr, next_pt))
                else:
                    print(f"Can't take {rr} to {next_pt} - no legal moves from there")

    test_valid_moves = [wp for wp in valid_wp(curr_pt)
        if wp[1] == dest_pt or len(valid_wp(wp[1])) > 1]
    assert valid_moves == test_valid_moves
    if len(valid_moves) == 0 and rover_play_index > 0:
        rover_start_pt = history[rover_play_index][1]
        valid_moves = calculate_legal_moves(m, rover_start_pt, 
            history[(rover_play_index + 1):], dest_pt, -1)
    assert len(valid_moves) > 0, "Must have a valid move available at all times"
    return valid_moves

@dataclass
class MoveReport:
    move: Waypoint
    bank_deltas: List[int]
    dest_dist: int

    @staticmethod
    def score(move: Waypoint, m: Map, start_pt: int, dest_pt: int,
            trip_history: List[Waypoint], moves_this_turn: int,
            player_rr: List[List[str]], player_i: int, 
            init_rr: str|None, established_rate: int|None, 
            doubleFees: bool) -> 'MoveReport':
        history = trip_history[-moves_this_turn:] if moves_this_turn > 0 else []
        fees_before, _ = calculate_user_fees(m, player_i, history, 
            player_rr, init_rr, established_rate, doubleFees)
        fees_after, _ = calculate_user_fees(m, player_i, history + [move],
            player_rr, init_rr, established_rate, doubleFees)
        bank_deltas = [fa - fb for fb,fa in zip(fees_before, fees_after)]
        dest_dist = quick_network_distance(m, start_pt, dest_pt, 
            trip_history+[move])
        return MoveReport(move, bank_deltas, dest_dist)

def get_legal_moves_with_scores(
        m: Map, start_pt: int, history: List[Waypoint], 
        dest_pt: int, rover_play_index: int, 
        moves_this_turn: int, player_rr: List[List[str]], player_i: int, 
        init_rr: str|None, established_rate: int|None, 
        doubleFees: bool) -> List[MoveReport]:
    moves = calculate_legal_moves(
        m, start_pt, history, dest_pt, rover_play_index)
    def score(wp: Waypoint) -> MoveReport:
        return MoveReport.score(wp, m, start_pt, dest_pt, history, 
            moves_this_turn, player_rr, player_i, 
            init_rr, established_rate, doubleFees)
    reports = list(map(score, moves))
    for r in reports:
        if r.dest_dist < 0:
            print(f'Removing {r.move[0]} to {r.move[1]} - dd < 0')
            reports.remove(r)
    def sort_key(r: MoveReport) -> Tuple[int, int, int]:
        return (0 if r.move[1] == dest_pt else 1,   # Rank all moves to dest 1st
                -r.bank_deltas[player_i],           # Then look at cost
                r.dest_dist)                        # Finally, look at rem dist
    return list(sorted(reports, key=sort_key))