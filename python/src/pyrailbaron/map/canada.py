from pyrailbaron.map.datamodel import Coordinate
from pyrailbaron.map.states import download_zip, extract_kml, simplify_coords

from typing import List
from pathlib import Path
from math import log, atan, cos, pi, tan, sqrt

FALSE_EASTING = 6200000
FALSE_NORTHING = 3000000
CENTRAL_MERIDIAN = -91.866667 * (pi/180)
STD_PARALLEL_1 = 49 * (pi/180)
STD_PARALLEL_2 = 77 * (pi/180)
LATITUDE_OF_ORIGIN = 63.390675 * (pi/180)
R_EARTH = 6378137

LCC_N = (
    log(cos(STD_PARALLEL_1)/cos(STD_PARALLEL_2))
        / log(tan(pi/4 + STD_PARALLEL_2/2)/tan(pi/4 + STD_PARALLEL_1/2)))
LCC_F = (
    cos(STD_PARALLEL_1)
        * (tan(pi/4 + STD_PARALLEL_1/2)**LCC_N)    
        / LCC_N )
def rho(lat: float) -> float:
    return R_EARTH * LCC_F * ( tan(pi/4 + lat/2) ** (-LCC_N))
def lat_of_rho(r: float) -> float:
    return 2*atan((r / (R_EARTH * LCC_F))**(-1/LCC_N)) - pi/2
RHO_AT_ORIGIN = rho(LATITUDE_OF_ORIGIN)

def invert_lcc(c: Coordinate) -> Coordinate:
    x,y = c[0] - FALSE_EASTING, c[1] - FALSE_NORTHING
    rho = sqrt(x**2 + (y - RHO_AT_ORIGIN)**2)
    lat = lat_of_rho(rho)
    lon = ( atan(x/(RHO_AT_ORIGIN-y)) / LCC_N ) + CENTRAL_MERIDIAN
    lat, lon = lat * 180/pi, lon * 180/pi
    return lat, lon

CANADA_URL = ('http://www12.statcan.gc.ca/census-recensement/2011/geo/bound-limit/files-fichiers/2016/lpr_000b16g_e.zip')
MAX_LAT = 53
def get_canada_data(data_folder: Path | str) -> List[List[Coordinate]]:
    data_path = Path(data_folder) / 'canada.gml'
    download_zip(CANADA_URL, data_path, 'lpr_000b16g_e.gml')
    root = extract_kml(data_path, root_tag='FeatureCollection')
    borders: List[List[Coordinate]] = []
    for border in root.findall('./featureMember//LinearRing/posList'):
        coord_text = border.text or ''
        coord_text_values = list(map(float, coord_text.split(' ')))
        xy_coords: List[Coordinate] = [
            (coord_text_values[2*i], coord_text_values[2*i+1])
            for i in range(len(coord_text_values)//2)]
        t_coords = list(map(invert_lcc, xy_coords))
        coords = simplify_coords(t_coords)
        if len(coords) > 20 and any(lat <= MAX_LAT for lat, _ in coords):
            print(f'Adding CA border with {len(coords)} points')
            cap_coords = [(min(lat, MAX_LAT), lon) for lat, lon in coords]
            borders.append(cap_coords)
    return borders