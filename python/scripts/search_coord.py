from pathlib import Path
import csv
import urllib.request
import zipfile
import tempfile

ROOT_DIR = Path(__file__).parent.parent.parent

with (ROOT_DIR/'output/points.csv').open('rt') as point_file:
    points = [(float(p[1]), float(p[2])) for p in csv.reader(point_file) if len(p) >= 3]
print(f'Found {len(points)} total points')

with (ROOT_DIR/'data/city_labels.csv').open('r') as city_csv:
    cities = [r for r in csv.reader(city_csv) if len(r) >= 3]
print(f'Found {len(cities)} cities')

coords = [None] * len(cities)
geonames_data = ROOT_DIR/'data/US.txt'
if not geonames_data.exists():
    print('Downloading geonames location data...')
    tmp, _ = urllib.request.urlretrieve(
        'http://download.geonames.org/export/dump/US.zip')
    print(f'Extracting from temporary download at {tmp}...')
    with zipfile.ZipFile(tmp, 'r') as tmpzip:
        tmpzip.extract('US.txt', geonames_data.parent)
    Path(tmp).unlink()

print('Searching for city coordinates...')
found_count = 0
with (ROOT_DIR/'data/US.txt').open('rt',encoding='utf-8') as us_file:
    for line in us_file:
        parts = line.split('\t')
        if parts[7].startswith('ADM'):
            for idx, city_data in enumerate(cities):                
                state = city_data[1]
                if len(city_data) < 4:
                    city = f'City of {city_data[0]}'
                else:
                    city = city_data[3]
                if parts[1] == city and parts[10] == state:
                    coords[idx] = (float(parts[4]), float(parts[5]))
                    found_count += 1
print(f'Found locations for {found_count} / {len(cities)} cities')

with (ROOT_DIR/'output/city_coordinates.csv').open('w') as coord_file:
    coord_file.write('city,state,lon,lat,x,y\n')
    for idx, city_data in enumerate(cities):
        city, state, pt_idx = city_data[:3]
        pt = points[int(pt_idx)]
        if coords[idx]:
            coord_file.write(f'{city},{state},{coords[idx][1]},{coords[idx][0]},{pt[0]},{pt[1]}\n')
        else:
            print(f'WARNING! Could not find {city}, {state}')