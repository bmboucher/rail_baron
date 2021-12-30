from pathlib import Path
import urllib.request
import zipfile
from xml.etree import ElementTree as ET
from pyrailbaron.map.datamodel import Coordinate, distance
from typing import Dict, List, Any, Optional

def download_zip(url: str, data_path: Path, inner_file: str | None = None):
    if data_path.exists():
        return
    print(f'Downloading zip file from {url}')
    zip_path, _ = urllib.request.urlretrieve(url)
    print(f'Extracting from temporary file {zip_path}')
    inner_file = inner_file or data_path.name
    with zipfile.ZipFile(zip_path, 'r') as zip:
        zip.extract(inner_file, data_path.parent)
    if inner_file != data_path.name:
        (data_path.parent / inner_file).rename(data_path)
    Path(zip_path).unlink()
    print(f'File {inner_file} extracted to {data_path}')

def extract_kml(data_path: Path, root_tag: str = 'Document') -> ET.Element:
    root: Optional[ET.Element] = None
    with (data_path).open('r') as data_file:
        cursor = ET.iterparse(data_file)
        for _, el in cursor:
            _, _, el.tag = el.tag.rpartition('}')
            if el.tag == root_tag:
                root = el
    if root:
        return root
    else:
        raise RuntimeError(f'{root_tag} node not found in {data_path}')

def simplify_coords(raw_coords: List[Coordinate]) -> List[Coordinate]:
    coords = [raw_coords[0]]
    for c in raw_coords[1:-1]:
        if distance(c, coords[-1]) > 0.05:
            coords.append(c)
    coords.append(raw_coords[-1])
    return coords    

def parse_kml_coords(coord_text: str) -> List[Coordinate]:
    def parse_coords(s: str) -> Coordinate:
        p = s.split(',')
        return float(p[1]), float(p[0]) # We use lat,lon convention
    raw_coords = list(map(parse_coords, 
        (c for c in coord_text.split(' ') if ',' in c)))
    return simplify_coords(raw_coords)

BorderData = Dict[str, List[List[Coordinate]]]
def get_border_data(data_folder: Path | str) -> BorderData:
    data_path = Path(data_folder) / 'st_us.kml'
    download_zip('https://www.nohrsc.noaa.gov/data/vector/master/st_us.kmz',
        data_path)
    root = extract_kml(data_path)

    borders: Dict[str, List[List[Coordinate]]] = dict()
    for folder in root.findall('Folder'):
        state: str = folder.find('name').text # type: ignore
        lines: List[List[Coordinate]] = []
        for line in folder.findall('./Placemark/MultiGeometry/LineString'):
            coord_text: str = line.find('coordinates').text # type: ignore
            lines.append(parse_kml_coords(coord_text))
        borders[state] = lines
    return borders

CANADA_URL = ('https://www12.statcan.gc.ca/census-recensement/2011' +
              '/geo/bound-limit/files-fichiers/gpr_000b11g_e.zip')
MAX_LAT = 53
def get_canada_data(data_folder: Path | str) -> List[List[Coordinate]]:
    data_path = Path(data_folder) / 'canada.gml'
    download_zip(CANADA_URL, data_path, 'lpr_000b16g_e.gml')
    root = extract_kml(data_path, root_tag='FeatureCollection')
    borders: List[List[Coordinate]] = []
    for border in root.findall('./featureMember/../LinearRing'):
        coord_text: str = border.find('posList').text # type: ignore
        border = parse_kml_coords(coord_text)
        if len(border) > 10 and any(lat <= MAX_LAT for lat,_ in border):
            print(f'Adding CA border of length {len(border)}')
            t_border = [(min(lat, MAX_LAT), lon) for lat,lon in border]
            borders.append(t_border)
    return borders

def get_region_border_points(
        border_data: BorderData, region_data: List[List[Any]]):
    pts: List[Coordinate] = []
    for row in region_data:
        if row[0] == 'M':
            pts.append(row[1])
            print(f'  Added point {pts[-1]}')
        else:
            state, border_idx, range = row
            border = border_data[state][border_idx]
            print(f'BORDER {state} #{border_idx} = {len(border)} points')
            segment = None
            do_reverse = False
            if range == 'all':
                segment = border
            elif isinstance(range, list):
                start: int; end: int
                start, end = range # type: ignore
                if (end >= 0 and start > end) or start < 0:
                    start, end = end, start
                    do_reverse = True
                if end == -1:
                    segment = border[start:]
                else:
                    segment = border[start:(end + 1)]
            if segment:
                if do_reverse:
                    segment = segment.copy()
                    segment.reverse()
                pts += segment
                print(f'  Added segment from {segment[0]} to {segment[-1]}')
    pts.append(pts[0])
    return pts

if __name__ == '__main__':
    get_border_data((Path(__file__) / '../../../../../data').resolve())