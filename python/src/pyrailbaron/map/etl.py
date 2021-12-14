import enum
from os import close
from .datamodel import Coordinate, Map, MapPoint, distance
from typing import Callable, List
from dataclasses import replace
from pathlib import Path
import urllib.request
import numpy as np

import re
import ezdxf
import csv
import zipfile
import json

from pyrailbaron.map.fit import fit_data
from pyrailbaron.map.svg import MapSvg, transform_dxf, transform_lcc
from pyrailbaron.map.states import get_border_data

def lookup_pt(p: Coordinate, pts: List[MapPoint], append: bool = False) -> int:
    for mp in pts:
        if distance(mp.dxf_coords, p) < 0.1:
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

def lookup_nearest(data_folder, point: MapPoint) -> MapPoint:
    tgt_lat, tgt_lon = point.geo_coords
    geonames_data = get_geonames_data(data_folder)
    min_lat, max_lat = tgt_lat - 5, tgt_lat + 5
    min_lon, max_lon = tgt_lon - 5, tgt_lon + 5
    min_d = 100
    best_parts = None
    with geonames_data.open('rt', encoding='utf-8') as us_file:
        for line in us_file:
            parts = line.split('\t')
            if parts[7] in ['ADM3', 'ADM4', 'ADM5', 'ADMD'] and re.match(r'.* of .*', parts[1]):
                lat, lon = float(parts[4]), float(parts[5])
                if lat < min_lat or lat > max_lat or lon < min_lon or lon > max_lon:
                    continue
                d = distance((lat,lon),(tgt_lat,tgt_lon))
                if d < min_d:
                    min_d = d
                    best_parts = parts.copy()
    if best_parts:
        city = re.sub(r'.* of (.*)$', r'\1', best_parts[1])
        state = best_parts[10]
        print(f'Closest place name to ({tgt_lat}, {tgt_lon}) = {city}, {state}')
        return replace(point, geonames_lookup = best_parts[1], state=state,
            place_name=city)
    else:
        print(f'NO NAME FOUND for ({tgt_lat}, {tgt_lon})')
        return point

def summarize(points: List[MapPoint]):
    x = [p.dxf_coords[0] for p in points]
    y = [p.dxf_coords[1] for p in points]
    lat = [p.geo_coords[0] for p in points if p.geo_coords]
    lon = [p.geo_coords[1] for p in points if p.geo_coords]
    print('Coordinate ranges:')
    print(f'\tX: [{min(x)}, {max(x)}]')
    print(f'\tY: [{min(y)}, {max(y)}]')
    print(f'\tlat: [{min(lat)}, {max(lat)}]')
    print(f'\tlon: [{min(lon)}, {max(lon)}]')

def read_data(data_folder) -> List[MapPoint]:
    points = scrape_network_dxf(Path(data_folder)/'dxf/network.dxf')
    scrape_rr_dxfs(Path(data_folder)/'dxf', points)
    read_cities(Path(data_folder)/'city_labels.csv', points)
    get_city_locations(data_folder, points)
    return points

def lookup_unnamed(data_folder, points: List[MapPoint]):
    for i in range(len(points)):
        p = points[i]
        if len(p.city_names) == 0:
            points[i] = lookup_nearest(data_folder, p)

def add_final_svg_coords(m: Map):
    for i,p in enumerate(m.points):
        m.points[i] = replace(p, 
            final_svg_coords = transform_dxf(
                m.map_transform(transform_lcc(p.geo_coords))))

MIN_DISTANCE_CONNECTED = 10
MIN_DISTANCE_UNCONNECTED = 6
def push_points_apart(m: Map):
    too_close = True
    while too_close:
        too_close = False
        deltas = [None] * len(m.points)
        for i,p in enumerate(m.points):
            deltas[i] = np.zeros(2)
            for j in range(i): 
                other_p = m.points[j]
                is_connected = False
                for rr in p.connections:
                    if j in p.connections[rr]:
                        is_connected = True
                min_distance = MIN_DISTANCE_CONNECTED if is_connected \
                    else MIN_DISTANCE_UNCONNECTED
                d = distance(p.final_svg_coords, other_p.final_svg_coords)
                if d < min_distance:
                    too_close = True
                    adj_distance = (min_distance - d) * 0.6
                    diff = np.array(p.final_svg_coords) - np.array(other_p.final_svg_coords)
                    deltas[i] += (adj_distance / d) * diff
                    deltas[j] -= (adj_distance / d) * diff
                    print(f'Points {i} and {j} are too close ({d} < {min_distance})')
        for i,p in enumerate(m.points):
            orig_x, orig_y = p.final_svg_coords
            if deltas[i][0] != 0 or deltas[i][1] != 0:
                m.points[i] = replace(p, final_svg_coords=(
                    orig_x + deltas[i][0], orig_y + deltas[i][1]))

if __name__ == '__main__':
    ROOT_DIR = (Path(__file__) / '../../../../../').resolve()

    map = Map(points=read_data(ROOT_DIR / 'data'))
    map = fit_data(map)
    lookup_unnamed(ROOT_DIR / 'data', map.points)
    summarize(map.points)
    add_final_svg_coords(map)
    push_points_apart(map)

    json_path = (ROOT_DIR / 'output/map.json')
    with json_path.open('w') as map_json:
        json.dump(map.to_dict(), map_json, indent=2)
    print(f'Wrote map data to {json_path}')

    svg_path = (ROOT_DIR / 'output/map.svg')
    svg = MapSvg(svg_path)

    states = svg.layer('states')
    rails = svg.layer('railroads')
    cities = svg.layer('cities')
    non_cities = svg.layer('non_cities')

    states.transforms.append(transform_lcc)     # Map lat, lon -> abstract LCC coords
    states.transforms.append(map.map_transform) # Map LCC coords -> original .dxf coords
    states.transforms.append(transform_dxf)     # Scale/flip .dxf to fit on .svg canvas

    borders = get_border_data(ROOT_DIR/'data')
    for s in borders:
        for l in borders[s]:
            states.path(l, stroke='green', stroke_width=1, fill='none')

    for p in map.points:
        if len(p.city_names) > 0:
            cities.circle(p.final_svg_coords, 2, 
                stroke='blue', stroke_width=1)
        else:
            non_cities.circle(p.final_svg_coords, 2,
                stroke='blue', stroke_width=1, fill='none')
        conn_pt = []
        for rr in p.connections:
            for p_id in p.connections[rr]:
                if p_id > p.index and p_id not in conn_pt:
                    conn_pt.append(p_id)
                    rails.line(p.final_svg_coords, map.points[p_id].final_svg_coords,
                        stroke='red', stroke_width=1)

    svg.save()