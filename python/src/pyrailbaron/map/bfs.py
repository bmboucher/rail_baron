from pyrailbaron.map.datamodel import (
    Map, Waypoint, RailSegment, make_rail_seg, rail_segs_from_wps )
from collections import deque
from typing import List, Set, Deque

# Returns the list of shortest paths from pt_from to pt_to
def breadth_first_search(
        m: Map, pt_from: int, pt_to: int, 
        used_rail_segs: List[RailSegment] = [],
        path_length_flex: int = 0) -> List[List[Waypoint]]:
    search_paths: Deque[List[Waypoint]] = deque()
    shortest_paths: List[List[Waypoint]] = []
    min_path_length: int = len(m.points)

    # Initialize search paths with first WPs
    pts_searched: Set[int] = set([pt_from])
    for rr, conn_pts in m.points[pt_from].connections.items():
        for first_pt in conn_pts:
            if make_rail_seg(rr, pt_from, first_pt) not in used_rail_segs:
                search_paths.append([(rr,first_pt)])

    while len(search_paths) > 0:
        base_path = search_paths.popleft()

        # Each path has a distinct history
        path_used_segs = used_rail_segs + rail_segs_from_wps(pt_from, base_path)

        # Check if this is the current shortest path to pt_to
        end_pt = base_path[-1][1]
        if end_pt == pt_to and len(base_path) <= min_path_length + path_length_flex:
            if len(base_path) < min_path_length:
                min_path_length = len(base_path)
                shortest_paths = list(filter(
                    lambda p: len(p) <= min_path_length + path_length_flex, 
                    shortest_paths))
            shortest_paths.append(base_path)
            
        # If this path is short enough, add the next level to the queue
        if len(base_path) < min_path_length + path_length_flex:
            for rr, conn_pts in m.points[end_pt].connections.items():
                for next_pt in conn_pts:
                    rs = make_rail_seg(rr, end_pt, next_pt)
                    if rs not in path_used_segs and next_pt not in pts_searched:
                        search_paths.append(base_path + [(rr, next_pt)])                        
        
        # Mark the end of this path as searched
        pts_searched.add(end_pt)
    return shortest_paths