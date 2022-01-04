from os import path
from pathlib import Path
import csv
from typing import List, Tuple, Set
from random import randint, choice

from pyrailbaron.map.datamodel import Waypoint

ROOT_DIR = (Path(__file__) / '../../..').resolve()
input_path = ROOT_DIR / 'output/rr_paths.csv'
output_path = ROOT_DIR / 'data/test_paths.csv'

MAX_PATHS_PER_PAIR = 20
n_read_paths = 0
n_kept_paths = 0

current_pair: Tuple[int, int] | None = None

def select_paths(all_paths: List[List[Waypoint]]) -> List[List[Waypoint]]:
    global current_pair
    global n_kept_paths
    assert current_pair
    selected_paths: List[List[Waypoint]]
    if len(all_paths) <= MAX_PATHS_PER_PAIR:
        selected_paths = all_paths.copy()
        print(f'Keeping all {len(selected_paths)} paths for {current_pair}')
    else:
        selected_paths = []
        path_size = min(len(p) for p in all_paths)
        while len(selected_paths) < MAX_PATHS_PER_PAIR:
            eligible_paths = [p for p in all_paths if len(p) == path_size]
            all_paths = [p for p in all_paths if len(p) > path_size]
            if len(eligible_paths) + len(selected_paths) <= MAX_PATHS_PER_PAIR:
                print(f'Keeping {len(eligible_paths)} paths at size {path_size} for {current_pair}')
                selected_paths += eligible_paths
            else:
                curr_path = choice(eligible_paths)
                def score(next_path: List[Waypoint]) -> int:
                    curr_rrs = set(rr for rr,_ in curr_path)
                    next_rrs = set(rr for rr,_ in next_path)
                    return len(next_rrs.difference(curr_rrs))
                print(f'Selecting remaining {MAX_PATHS_PER_PAIR - len(selected_paths)} paths at size {path_size} for {current_pair}')
                selected_paths.append(curr_path)
                while len(selected_paths) < MAX_PATHS_PER_PAIR:
                    scores = list(map(score, eligible_paths))
                    max_score = max(scores)
                    curr_path = eligible_paths.pop(
                        choice([i for i in range(len(eligible_paths)) 
                            if scores[i] == max_score]))
                    selected_paths.append(curr_path)

            path_size += 1
    assert len(selected_paths) <= MAX_PATHS_PER_PAIR
    n_kept_paths += len(selected_paths)
    return selected_paths

paths_for_pair: List[List[Waypoint]] = []
with input_path.open('r') as input_file:
    with output_path.open('w',newline='') as output_file:
        csv_rdr = csv.reader(input_file)
        csv_wr = csv.writer(output_file)

        def select_and_write():
            selected_paths = select_paths(paths_for_pair)
            assert current_pair
            for path in selected_paths:
                wr_row: List[str | int] = list(current_pair)
                wr_row += [x for wp in path for x in wp]
                csv_wr.writerow(wr_row)

        for row in csv_rdr:
            if len(row) < 3:
                continue
            n_read_paths += 1
            this_pair: Tuple[int, int] = (int(row[0]), int(row[1]))
            if this_pair != current_pair:
                if current_pair:
                    select_and_write()
                current_pair = this_pair
                paths_for_pair.clear()
            paths_for_pair.append([(row[i - 1], int(row[i])) 
                for i in range(3, len(row), 2)])
        select_and_write()
print(f'Kept {n_kept_paths} / {n_read_paths} paths')