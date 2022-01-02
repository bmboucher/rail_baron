from pyrailbaron.game.constants import MIN_CASH_TO_WIN
from pyrailbaron.game.state import Engine, GameState
from pyrailbaron.map.datamodel import Map, Waypoint, rail_segs_from_wps
from pyrailbaron.map.bfs import breadth_first_search, DEFAULT_PATHS_FILE
from pyrailbaron.game.fees import calculate_user_fees
from typing import List, Optional, Callable, Dict, Tuple
from random import randint, sample
from pathlib import Path
import csv

N_PATH_ROLL_SIM = 100
def sim_roll(e: Engine) -> int:
    d1, d2 = randint(1,6), randint(1,6)
    d = d1 + d2
    if (d1 == d2 and e == Engine.Express) or e == Engine.Superchief:
        d += randint(1,6)
    return d

MAX_PATHS = 100

# Evaluate the cost of a given path with a known die roll d
# player_rr = ownership information (i.e. p.rr_owned for each p)
# init_rr, established_rate = "established" information
# doubleFees = all RRs owned
# previous_moves = moves already taken this turn (e.g. if this is a bonus roll)
def calculate_path_cost(m: Map, e: Engine, 
        player_i: int, path: List[Waypoint], d: int,
        player_rr: List[List[str]], init_rr: str | None, 
        established_rate: int | None, doubleFees: bool,
        previous_moves: List[Waypoint] = [], N: int = N_PATH_ROLL_SIM) -> int:
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
            sim_costs = simulate_rolls(m, e, player_i, path[d:], N, 
                player_rr, doubleFees, path[d-1][0], est_rate)
            average_cost = sum(sim_costs) // N
    
    return fixed_cost + average_cost

# Given a fixed path, simulate N traversals of the path (corresponding to random
# die rolls for distance) and return the costs by scenario
def simulate_rolls(m: Map, e: Engine, player_i: int, path: List[Waypoint], N: int,
        player_rr: List[List[str]], doubleFees: bool, 
        init_rr: str|None, established_rate: int|None) -> List[int]:
    cost_by_path: List[int] = [0] * N
    for sim_n in range(N):
        rem_path = path.copy()
        while len(rem_path) > 0:
            new_d = sim_roll(e)
            seg_path = rem_path[:new_d]
            fees, established_rate = calculate_user_fees(
                m, player_i, seg_path, 
                player_rr, init_rr, established_rate, doubleFees)
            rem_path = rem_path[new_d:]
            init_rr = seg_path[-1][0]
            cost_by_path[sim_n] += fees[player_i]
    return cost_by_path

# Reduce a collection of paths to below size N
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
        return calculate_path_cost(s.map, ps.engine, player_i, path, 
            d, player_rr, init_rr, ps.established_rate, 
            doubleFees, previous_moves)    

    start_pt = ps.location if len(forced_moves) == 0 else forced_moves[-1][1]
    d -= len(forced_moves)
    used_rail_segs = rail_segs_from_wps(ps.startCityIndex, ps.history + forced_moves)
    shortest_paths = breadth_first_search(
        s.map, start_pt, dest_pt, used_rail_segs, path_length_flex)
    print(f'  AI >> Found {len(shortest_paths)} paths')

    assert len(shortest_paths) > 0, "Must have at least one path to goal"
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

def get_paths_from_pt(start_pt: int,
        rr_paths_path: Path = DEFAULT_PATHS_FILE) -> List[List[Waypoint]]:
    paths: List[List[Waypoint]] = []
    counts_by_city: Dict[int, int] = {}
    with rr_paths_path.open('r') as rr_paths_file:
        rdr = csv.reader(rr_paths_file)
        for row in rdr:
            row_N = len(row) - 2
            if int(row[0]) != start_pt and int(row[1]) != start_pt:
                continue
            dest_pt = int(row[1]) if int(row[0]) == start_pt else int(row[0])
            if dest_pt not in counts_by_city:
                counts_by_city[dest_pt] = 1
            else:
                if counts_by_city[dest_pt] >= 20:
                    continue
                counts_by_city[dest_pt] += 1

            if int(row[0]) == start_pt:
                path = [(row[2*i + 2], int(row[2*i + 3])) for i in range(row_N // 2)]
                paths.append(path)
            elif int(row[1]) == start_pt:
                path = [(row[-2*i-2], int(row[-2*i-3])) for i in range((row_N-1)//2)]
                path.append((row[2], int(row[0])))
                paths.append(path)
    return paths

def simulate_costs(s: GameState, player_i: int, start_pt: int, player_rr: List[List[str]],
        init_rr: str|None, established_rate: int|None, doubleFees: bool,
        n_dest: int, n_rolls_per_dest: int, override_engine: Engine|None = None,
        paths: List[List[Waypoint]]|None = None,
        rr_paths_path: Path = DEFAULT_PATHS_FILE, dest_pt: int|None = None) -> List[int]:
    paths = paths or get_paths_from_pt(start_pt, rr_paths_path)

    best_paths: Dict[int, List[Waypoint]] = {}
    def get_best_path(end_pt: int) -> List[Waypoint]:
        if end_pt not in best_paths:
            best_path: List[Waypoint] = []
            min_cost: int = -1
            for path in paths:
                if path[-1][1] != end_pt:
                    continue
                cost = calculate_path_cost(s.map, 
                    override_engine or s.players[player_i].engine, 
                    player_i, path, 0, player_rr, 
                    init_rr, established_rate, doubleFees, N=10)
                if min_cost < 0 or cost < min_cost:
                    best_path = path
                    min_cost = cost
            best_paths[end_pt] = best_path
        return best_paths[end_pt]

    sim_costs: List[int] = []
    for _ in range(n_dest):
        if not dest_pt:
            dest_region = s.random_lookup('REGION')
            while dest_region == s.map.points[start_pt].region:
                dest_region = s.random_lookup('REGION')
            _, dest_pt = s.map.lookup_city(s.random_lookup(dest_region))
        sim_costs += simulate_rolls(s.map, s.players[player_i].engine, 
            player_i, get_best_path(dest_pt), n_rolls_per_dest,
            player_rr, doubleFees, init_rr, established_rate)
    return list(sorted(sim_costs))

def select_purchase_options(s: GameState, player_i: int, user_fee: int) -> str|None:
    ps = s.players[player_i]
    # We only consider options which leave us with > 0 balance after paying user fees
    raw_opts = s.get_player_purchase_opts(player_i)
    if len(raw_opts) == 0:
        return None

    # First, we filter out the options we "can't" purchase because they put
    # us at too much risk of going negative. This may require simulating future
    # trips from our current location assuming each purchase.
    N_DEST = 200             # Number of random destinations
    N_ROLL_PER_DEST = 10    # Number of rolls to simulate for each destination
    # The total number of "scenarios" is N_DEST * N_ROLL_PER_DEST
    CRIT_PCT = 0.05          # Critical percentile of costs (i.e. we must be able to pay them 1-CRIT_PCT of the time)
    MIN_SIM_THRESHOLD = 50000 # Don't simulate trips if we can spare at least this much
    MIN_BAL = 5000           # Don't let the expected ending balance go below this
    filtered_opts: List[Tuple[str, int]] = []
    base_player_rr = [p.rr_owned for p in s.players]

    paths: List[List[Waypoint]] | None = None

    has_engine: bool = False
    for opt, price in raw_opts:
        # If we'll go below MIN_BAL after user fees, definitely omit
        if ps.bank - price + user_fee <= MIN_BAL:
            continue

        # If we have a lot in the bank, no need to simulate
        if ps.bank - price + user_fee > MIN_SIM_THRESHOLD + MIN_BAL:
            filtered_opts.append((opt, price))
            continue

        if not paths:
            paths = get_paths_from_pt(ps.location)

        # Generate the simulated distribution assuming this purchase
        if opt in [Engine.Express.name, Engine.Superchief.name]:
            sim_costs = simulate_costs(s, player_i, ps.location,
                base_player_rr, ps.rr, ps.established_rate, s.doubleFees,
                N_DEST, N_ROLL_PER_DEST, 
                override_engine=(Engine.Express if opt == Engine.Express.name 
                    else Engine.Superchief), paths=paths)
        elif has_engine:
            continue
        else:
            adj_player_rr = [rr_owned.copy() for rr_owned in base_player_rr]
            adj_player_rr[player_i].append(opt)
            sim_costs = simulate_costs(s, player_i, ps.location,
                adj_player_rr, ps.rr, ps.established_rate, s.doubleFees, 
                N_DEST, N_ROLL_PER_DEST, paths=paths)
        next_trip_cost = sim_costs[int(CRIT_PCT * N_DEST * N_ROLL_PER_DEST)]
        est_bal = ps.bank - price + user_fee + next_trip_cost
        print(f'  AI >> Est balance after buying {opt} = {ps.bank} - {price} - {-user_fee} - {-next_trip_cost} = {est_bal}')
        if est_bal > MIN_BAL:
            if opt in [Engine.Express.name, Engine.Superchief.name]:
                has_engine = True
            filtered_opts.append((opt, price))
        else:
            print(f'  AI >> DROPPING {opt}')

    # If no options remain, do nothing
    if len(filtered_opts) == 0:
        return None
    # If only one option remains, do that without scoring
    if len(filtered_opts) == 1:
        return filtered_opts[0][0]
    # Always buy the largest engine possible if it's an option
    if any(o == Engine.Superchief.name for o,_ in filtered_opts):
        return Engine.Superchief.name
    elif any(o == Engine.Express.name for o,_ in filtered_opts):
        return Engine.Express.name

    best_rr: str|None = None
    best_score: int|None = None
    SCORE_PER_FREE_PT = 200
    SCORE_PER_LOCKED_PT = 150
    for opt, price in filtered_opts:
        score = -price
        for p in s.map.points:
            rrs = set(p.connections.keys())
            if opt not in rrs:
                continue
            if not any(rr in base_player_rr[player_i] for rr in rrs):
                score += SCORE_PER_FREE_PT
            rrs.remove(opt)
            locked_out = [True] * len(s.players)
            locked_out[player_i] = False
            for player_j, oth_rr_owned in enumerate(base_player_rr):
                if player_i == player_j:
                    continue
                for rr in oth_rr_owned:
                    if rr in rrs:
                        locked_out[player_j] = False
                        rrs.remove(rr)
            if len(rrs) == 0:
                score += sum(SCORE_PER_LOCKED_PT if l else 0 for l in locked_out)
        print(f'  AI >> SCORING {opt} = {score}')
        if not best_score or score > best_score:
            best_score = score
            best_rr = opt
    return best_rr

MIN_DECLARE_SIM_THRESH = MIN_CASH_TO_WIN * 5 // 4
def recommend_declare(s: GameState, player_i: int) -> bool:
    ps = s.players[player_i]
    if ps.bank >= MIN_DECLARE_SIM_THRESH:
        return True
    player_rr = [p.rr_owned for p in s.players]
    N_ROLL_SIM = 1000
    CRIT_PCT = 0.10
    sim_costs = simulate_costs(s, player_i, ps.location, player_rr,
        ps.rr, ps.established_rate, s.doubleFees, 
        1, N_ROLL_SIM, dest_pt=ps.homeCityIndex)
    crit_cost = sim_costs[int(CRIT_PCT * N_ROLL_SIM)]
    return ps.bank >= MIN_CASH_TO_WIN + crit_cost