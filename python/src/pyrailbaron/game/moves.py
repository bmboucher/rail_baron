from pyrailbaron.map.datamodel import Map, Waypoint, RailSegment, make_rail_seg, get_valid_waypoints
from typing import List, MutableSet

def calculate_legal_moves(m: Map, start_pt: int, history: List[Waypoint], dest_pt: int) -> List[Waypoint]:
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
        if pt_i == curr_pt:
            return False
        return len(valid_wp(pt_i)) < 2
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
    return [wp for wp in valid_wp(curr_pt)
        if wp[1] == dest_pt or len(valid_wp(wp[1])) > 1]