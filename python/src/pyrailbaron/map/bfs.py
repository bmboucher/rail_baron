from pyrailbaron.map.datamodel import (
    Map, Waypoint, RailSegment, read_map,
    get_valid_waypoints, make_rail_seg, rail_segs_from_wps )
from collections import deque
from typing import List, Set, Deque, Tuple, Dict
from time import time
from datetime import timedelta
from pathlib import Path

def quick_network_distance(m: Map, start_pt: int, dest_pt: int, history: List[Waypoint] = []) -> int:
    curr_pt = start_pt if len(history) ==  0 else history[-1][1]
    if curr_pt == dest_pt:
        return 0
    search_paths: Deque[List[Waypoint]] = deque()
    pts_searched: Set[int] = set()
    rail_segs_used = rail_segs_from_wps(start_pt, history)

    for start_step in get_valid_waypoints(m, curr_pt, rail_segs_used):
        search_paths.append([start_step])
    pts_searched.add(curr_pt)

    while len(search_paths) > 0:
        base_path = search_paths.popleft()
        end_pt = base_path[-1][1]
        if end_pt == dest_pt:
            return len(base_path)
        rail_segs_used = rail_segs_from_wps(start_pt, history + base_path)
        next_wp = get_valid_waypoints(m, end_pt, rail_segs_used, pts_searched)
        for rr, next_pt in next_wp:
            if next_pt == dest_pt:
                return len(base_path) + 1
            else:
                search_paths.append(base_path + [(rr, next_pt)])
                pts_searched.add(next_pt)
    return -1

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

def search_all_paths(m: Map, start_pt: int, skip_cities: List[int] = []) -> Dict[int, List[List[Waypoint]]]:
    search_paths: Deque[List[Waypoint]] = deque()
    for wp in get_valid_waypoints(m, start_pt):
        search_paths.append([wp])

    def count_transitions(p: List[Waypoint]) -> int:
        return sum(1 if p[i][0] != p[i - 1][0] else 0 
                   for i in range(1, len(p)))

    MAX_IN_QUEUE = 50000
    KeyType = Tuple[int, str] # Found paths are indexed by end pt, rrs used
    found_paths: Dict[KeyType, List[Waypoint]] = {}
    start_t = time()
    min_paths_by_city: Dict[int, int] = {}
    while len(search_paths) > 0:
        base_path = search_paths.popleft()
        rail_segs_used = rail_segs_from_wps(start_pt, base_path)
        end_pt = base_path[-1][1]

        if end_pt in skip_cities:
            continue

        if len(m.points[end_pt].city_names) > 0:
            t_el = timedelta(seconds=int(time() - start_t))
            rrs_used: str = ",".join(list(sorted(set(rr for rr, _ in base_path))))
            
            if end_pt not in min_paths_by_city:
                min_paths_by_city[end_pt] = len(base_path)
            elif len(base_path) >= min_paths_by_city[end_pt] + 6:
                continue
            else:
                min_paths_by_city[end_pt] = min(
                    min_paths_by_city[end_pt], len(base_path))

            key = (end_pt, rrs_used)
            if key not in found_paths:
                print(f'[{t_el}] Found first path from {m.points[start_pt].display_name} to {m.points[end_pt].display_name} - {rrs_used}')
                found_paths[key] = base_path
            else:
                curr_path = found_paths[key]
                if len(base_path) < len(curr_path) or (
                    len(base_path) == len(curr_path) and 
                    count_transitions(base_path) < count_transitions(curr_path)):
                    print(f'[{t_el}] Overwriting path from {m.points[start_pt].display_name} to {m.points[end_pt].display_name} - {rrs_used}')
                    found_paths[key] = base_path

        pts_traveled = [start_pt] + [p for _,p in base_path]
        curr_rr = base_path[-1][0]
        rr_pref = [curr_rr] + list(sorted(set(rr for rr,_ in base_path if rr != curr_rr)))
        rr_pref += list(sorted(set(rr for rr in m.points[end_pt].connections if rr not in rr_pref)))
        for rr in rr_pref:
            conn_pts = m.points[end_pt].connections.get(rr, [])
            for next_pt in conn_pts:
                rs = make_rail_seg(rr, end_pt, next_pt)
                if next_pt not in pts_traveled and rs not in rail_segs_used and len(search_paths) < MAX_IN_QUEUE:
                    search_paths.append(base_path + [(rr, next_pt)])
    cities = [pt.index for pt in m.points if len(pt.city_names) > 0]
    return dict((c, [p for k,p in found_paths.items() if k[0] == c]) for c in cities)

DEFAULT_PATHS_FILE = (Path(__file__) / '../../../../../data/test_paths.csv').resolve()

def write_all_paths(m: Map, output_path: Path = DEFAULT_PATHS_FILE):
    cities = [pt.index for pt in m.points if len(pt.city_names) > 0]

    total_paths = 0
    t_start = time()

    for start_pt in cities:
        print(f'Mapping all routes from {m.points[start_pt].display_name}')
        all_routes = search_all_paths(m, start_pt)
        for city, city_routes in all_routes.items():
            if city <= start_pt:
                continue
            total_paths += len(city_routes)
            with output_path.open('a') as output_file:
                for route in city_routes:
                    output_file.write(f'{start_pt},{city},{",".join(rr+","+str(p) for rr,p in route)}\n')                
            if len(city_routes) > 0:
                shortest = min(len(p) for p in city_routes)
                longest = max(len(p) for p in city_routes)
                print(f'{len(city_routes)} paths from {m.points[start_pt].display_name} to {m.points[city].display_name} (between {shortest} and {longest})')
            else:
                print(f'NO PATHS TO {m.points[city].display_name}')
    print(f'{total_paths} TOTAL PATHS FOUND IN {time() - t_start} SECONDS')

if __name__ == '__main__':
    m = read_map()
    write_all_paths(m)