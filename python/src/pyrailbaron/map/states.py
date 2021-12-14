from pathlib import Path
import urllib.request
import zipfile
from xml.etree import ElementTree as ET
from pyrailbaron.map.datamodel import Coordinate, distance
from typing import Dict, List, Any

BorderData = Dict[str, List[List[Coordinate]]]
def get_border_data(data_folder) -> BorderData:
    data_path = Path(data_folder) / 'st_us.kml'
    if not data_path.exists():
        print('Downloading state border data from NOAA...')
        zip_path, _ = urllib.request.urlretrieve(
            'https://www.nohrsc.noaa.gov/data/vector/master/st_us.kmz')
        print(f'Extracting from zip file at {zip_path}...')
        with zipfile.ZipFile(zip_path, 'r') as zip:
            zip.extract('st_us.kml', data_path.parent)
        Path(zip_path).unlink()
    root = None
    with (data_path).open('r') as data_file:
        cursor = ET.iterparse(data_file)
        for _, el in cursor:
            _, _, el.tag = el.tag.rpartition('}')
            if el.tag == 'Document':
                root = el

    borders = dict()
    for folder in root.findall('Folder'):
        state = folder.find('name').text
        lines = []
        for line in folder.findall('./Placemark/MultiGeometry/LineString'):
            def parse_coords(s: str) -> Coordinate:
                p = s.split(',')
                return float(p[1]), float(p[0]) # We use lat,lon convention
            coord_text = line.find('coordinates').text
            raw_coords = list(map(parse_coords, 
                (c for c in coord_text.split(' ') if ',' in c)))
            coords = [raw_coords[0]]
            for c in raw_coords[1:-1]:
                if distance(c, coords[-1]) > 0.05:
                    coords.append(c)
            coords.append(raw_coords[-1])
            lines.append(coords)
        borders[state] = lines
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
            if range == 'all':
                segment = border
            elif isinstance(range, list):
                start, end = range
                do_reverse = False
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