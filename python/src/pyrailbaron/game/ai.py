from pyrailbaron.game.state import GameState
from pyrailbaron.map.datamodel import Map, Waypoint, rail_segs_from_wps
from pyrailbaron.map.bfs import breadth_first_search
from pyrailbaron.game.fees import calculate_user_fees
from typing import List, Optional, Callable
from random import randint, sample

N_PATH_ROLL_SIM = 100
def sim_roll() -> int:
    return randint(1,6) + randint(1,6)

MAX_PATHS = 100

# Evaluate the cost of a given path with a known die roll d
# player_rr = ownership information (i.e. p.rr_owned for each p)
# init_rr, established_rate = "established" information
# doubleFees = all RRs owned
# previous_moves = moves already taken this turn (e.g. if this is a bonus roll)
def calculate_path_cost(m: Map, player_i: int, path: List[Waypoint], d: int,
        player_rr: List[List[str]], init_rr: str | None, 
        established_rate: int | None, doubleFees: bool,
        previous_moves: List[Waypoint] = []) -> int:
    fixed_fees, est_rate = calculate_user_fees(
        m, player_i, previous_moves + path[:d], player_rr, 
        init_rr, established_rate, doubleFees)
    fixed_cost = fixed_fees[player_i]
    average_cost = 0
    if len(path) > d:
        if len(path) <= d + 2:
            # If the next "hop" is <= 2 spaces, we don't need to simulate rolls
            fixed_cost += calculate_user_fees(m, player_i, path[d:],
                player_rr, init_rr, est_rate, doubleFees)[0][player_i]
        else:
            # Simulate N_SIM rolls to determine the average cost
            for _ in range(N_PATH_ROLL_SIM):
                rem_path = path[d:]
                my_est_rate = est_rate
                my_init_rr = path[d - 1][0]
                while len(rem_path) > 0:
                    new_d = sim_roll()
                    seg_path = rem_path[:new_d]
                    fees, my_est_rate = calculate_user_fees(
                        m, player_i, seg_path, 
                        player_rr, my_init_rr, my_est_rate, doubleFees)
                    average_cost += fees[player_i]
                    rem_path = rem_path[new_d:]
                    my_init_rr = seg_path[-1][0]
            average_cost = average_cost // N_PATH_ROLL_SIM
    
    return fixed_cost + average_cost

def reduce_paths(paths: List[List[Waypoint]], N: int,
    history: List[Waypoint] = []) -> List[List[Waypoint]]:
    if len(paths) <= N:
        return paths # Nothing to do

    def filter_by_metric(metric: Callable[[List[Waypoint]], int]):
        nonlocal paths
        met = list(map(metric, paths))
        min_val = min(met)
        paths = [p for p, v in zip(paths, met) if v == min_val]
    
    # First, try to reduce count by keeping only the paths which touch the
    # smallest NUMBER of railroads
    def count_rrs(path: List[Waypoint]):
        rr_set = set([rr for rr,_ in history] + [rr for rr,_ in path])
        return len(rr_set)
    filter_by_metric(count_rrs)
    if len(paths) <= N:
        return paths

    # If that isn't enough, keep paths with the minimum number of TRANSITIONS
    def count_trans(path: List[Waypoint]):
        curr_rr: str | None = None
        t_count: int = 0
        for rr, _ in history + path:
            if rr != curr_rr:
                curr_rr = rr; t_count += 1
        return t_count
    filter_by_metric(count_trans)

    if len(paths) > N:
        # If we still have too many, take a random sample
        paths = sample(paths, N)
    return paths

# Plan the best move sequence given a known die roll d
# init_rr = previously recorded RR player_i was on when turn began
# moves_so_far = # of moves taken previously this turn (already in the history)
# forced_moves = required fixed moves at the beginning (used when planning rovers)
# dest_pt = override player_i destination (used when planning rovers)
# path_length_flex = used to allow path lengths longer than minimum to be checked
def plan_best_moves(
        s: GameState, player_i: int, d: int,
        init_rr: Optional[str] = None, moves_so_far: int = 0,
        forced_moves: List[Waypoint] = [],
        dest_pt: int = -1, path_length_flex: int = 0) -> List[Waypoint]:
    ps = s.players[player_i]
    dest_pt = ps.destinationIndex if dest_pt < 0 else dest_pt
    previous_moves = ps.history[(-moves_so_far):] if moves_so_far > 0 else []
    assert ps.startCity, "Must know start city"
    assert ps.destination, "Must know destination"
    player_rr = [p.rr_owned for p in s.players]
    doubleFees = s.doubleFees
    def path_cost(path: List[Waypoint]):
        return calculate_path_cost(s.map, player_i, path, d, player_rr,
            init_rr, ps.established_rate, doubleFees, previous_moves)    

    start_pt = ps.location if len(forced_moves) == 0 else forced_moves[-1][1]
    d -= len(forced_moves)
    used_rail_segs = rail_segs_from_wps(ps.startCityIndex, ps.history + forced_moves)
    shortest_paths = breadth_first_search(
        s.map, start_pt, dest_pt, used_rail_segs, path_length_flex)
    print(f'  AI >> Found {len(shortest_paths)} paths')

    if len(shortest_paths) > MAX_PATHS:
        shortest_paths = reduce_paths(shortest_paths, MAX_PATHS, ps.history)
        print(f'  AI >> Reduced to {len(shortest_paths)} paths')

    costs = list(map(path_cost, shortest_paths))
    best_path, cost = list(sorted(zip(shortest_paths, costs), key=lambda pair: -pair[1]))[0]
    print(f'  AI >> Best path has length {len(best_path)} stops and cost {cost}')

    final_path: List[Waypoint] = []
    for rr, p in forced_moves + best_path[:d]:
        final_path.append((rr,p))
        if p == ps.destinationIndex:
            break

    return final_path