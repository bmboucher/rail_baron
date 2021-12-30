import csv
from pathlib import Path
from typing import Dict, List, Tuple

DATA_DIR = (Path(__file__) / '../../../../../data').resolve()
def read_route_payoffs(csv_path: Path | str | None = None) \
        -> Dict[str, Dict[str, int]]:
    csv_path = Path(csv_path) if csv_path else (DATA_DIR / 'payoffs.csv')
    routes: Dict[str, Dict[str, int]] = dict()
    with csv_path.open('rt') as csv_file:
        rdr = csv.reader(csv_file)
        col_hdrs = next(rdr)[1:]
        for i, row in enumerate(rdr):
            row_hdr, *str_values = row
            payoffs = list(map(int, str_values))
            assert payoffs.pop(i) == 0, "Diagonal payoffs should be 0"
            keys = col_hdrs.copy()
            assert keys.pop(i) == row_hdr, "Diagonal headers should match"
            routes[row_hdr] = dict(zip(keys, payoffs))
    return routes

def read_roll_tables(table_dir: Path | str | None = None) \
        -> Dict[str, List[Tuple[str, str]]]:
    table_dir = Path(table_dir) if table_dir else (DATA_DIR / 'roll_tables')
    tables: Dict[str, List[Tuple[str, str]]] = dict()
    for table_path in table_dir.glob('*.csv'):
        table_name = table_path.name[:-4].upper()
        with table_path.open('rt') as csv_file:
            rdr = csv.reader(csv_file)
            tables[table_name] = [(odd, even) for _, odd, even in rdr]
    return tables

if __name__ == "__main__":
    payoffs = read_route_payoffs()
    print(f'Read {len(payoffs)} cities')

    roll_tables = read_roll_tables()
    print(roll_tables)