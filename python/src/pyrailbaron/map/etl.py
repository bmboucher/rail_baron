import enum
from .datamodel import Coordinate, MapPoint
from typing import List
from dataclasses import replace
from math import sqrt
from pathlib import Path
import urllib.request

import re
import ezdxf
import csv
import zipfile
import json

def d(p1: Coordinate, p2: Coordinate):
    return sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def lookup_pt(p: Coordinate, pts: List[MapPoint], append: bool = False) -> int:
    for mp in pts:
        if d(mp.dxf_coords, p) < 0.1:
            return mp.index
    if append:
        mp = MapPoint(index=len(pts), dxf_coords=p)
        pts.append(mp)
        return mp.index
    else:
        raise RuntimeError(f'Could not find point {p}')

def scrape_network_dxf(dxf_path) -> List[MapPoint]:
    points: List[MapPoint] = []
    network_doc = ezdxf.readfile(dxf_path)
    for e in network_doc.entities:
        x1,y1,z1 = e.dxf.start
        x2,y2,z2 = e.dxf.end
        lookup_pt((x1,y1), points, True)
        lookup_pt((x2,y2), points, True)
    print(f'Found {len(points)} unique points in {dxf_path}')
    return points

def scrape_rr_dxfs(dxf_folder, points: List[MapPoint]):
    n_rr = 0
    for rr_dxf_path in Path(dxf_folder).glob('rr_*.dxf'):
        try:
            rr_name = re.sub(r'rr_(.*)\.dxf', r'\1', rr_dxf_path.name)
            rr_doc = ezdxf.readfile(rr_dxf_path)
            n_conn = 0
            for e in rr_doc.entities:
                x1,y1,z1 = e.dxf.start
                x2,y2,z2 = e.dxf.end
                p1 = lookup_pt((x1,y1), points)
                p2 = lookup_pt((x2,y2), points)
                points[p1].connect_to(points[p2], rr_name)
                n_conn += 1
            print(f'Found {n_conn} connections in {rr_dxf_path}')
            n_rr += 1
        except Exception as ex:
            print(f'ERROR processing {rr_dxf_path}: {ex}')
    print(f'Processed {n_rr} railroad files in {dxf_folder}')

def read_cities(csv_path, points: List[MapPoint]):
    with Path(csv_path).open() as city_csv:
        cities = [c for c in csv.reader(city_csv) if len(c) >= 3]
    for city in cities:
        pt_index = int(city[2])
        geonames_lookup = city[3] if len(city) > 3 else f'City of {city[0]}'
        points[pt_index] = replace(
            points[pt_index], state=city[1], 
            place_name=city[0],
            geonames_lookup=geonames_lookup)
        points[pt_index].city_names.append(city[0])
    print(f'Read {len(cities)} cities from {csv_path}')

def get_geonames_data(data_folder) -> Path:
    dest_path = Path(data_folder) / 'US.txt'
    if not dest_path.exists():
        print('Downloading geonames location data...')
        tmp, _ = urllib.request.urlretrieve(
            'http://download.geonames.org/export/dump/US.zip')
        print(f'Extracting from temporary download at {tmp}...')
        with zipfile.ZipFile(tmp, 'r') as tmpzip:
            tmpzip.extract('US.txt', dest_path.parent)
        Path(tmp).unlink()
    return dest_path

def get_city_locations(data_folder, points: List[MapPoint]):
    cities = [
        (i, p.geonames_lookup, p.state) 
            for (i,p) in enumerate(points)
            if p.geonames_lookup and p.state]
    geonames_data = get_geonames_data(data_folder)
    print(f'Searching for city coordinates in {geonames_data}')
    found_count = 0
    with geonames_data.open('rt',encoding='utf-8') as us_file:
        for line in us_file:
            parts = line.split('\t')
            if parts[7].startswith('ADM'):
                for i, city, state in cities:
                    if parts[1] == city and parts[10] ==state:
                        points[i].geo_coords = (
                            float(parts[4]), float(parts[5]))
                        found_count += 1
    print(f'Found locations for {found_count} / {len(cities)} cities')

def read_data(data_folder) -> List[MapPoint]:
    points = scrape_network_dxf(Path(data_folder)/'dxf/network.dxf')
    scrape_rr_dxfs(Path(data_folder)/'dxf', points)
    read_cities(Path(data_folder)/'city_labels.csv', points)
    get_city_locations(data_folder, points)
    return points

if __name__ == '__main__':
    ROOT_DIR = (Path(__file__) / '../../../../../').resolve()
    points = read_data(ROOT_DIR / 'data')
    points_data = [p.to_dict() for p in points]
    with (ROOT_DIR / 'output/map.json').open('w') as map_json:
        json.dump(points_data, map_json, indent=2)