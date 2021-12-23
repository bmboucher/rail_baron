from pyrailbaron.map.datamodel import Coordinate
from pyrailbaron.map.states import download_zip, extract_kml, simplify_coords, parse_kml_coords

from typing import List
from pathlib import Path

MEXICO_URL = ('https://biogeo.ucdavis.edu/data/gadm3.6/kmz/gadm36_MEX_0.kmz')
MIN_LAT = 25
def get_mexico_data(data_folder) -> List[List[Coordinate]]:
    data_path = Path(data_folder) / 'mexico.kml'
    download_zip(MEXICO_URL, data_path, 'gadm36_MEX_0.kml')
    root = extract_kml(data_path)
    borders: List[List[Coordinate]] = []
    for border in root.findall('.//Placemark//LinearRing/coordinates'):
        coords = parse_kml_coords(border.text)
        if len(coords) > 10 and any(lat >= MIN_LAT for lat, _ in coords):
            t_coords = [(max(lat, MIN_LAT), lon) for lat, lon in simplify_coords(coords)]
            print(f'Adding MX border of size {len(t_coords)}')
            borders.append(t_coords)
    return borders