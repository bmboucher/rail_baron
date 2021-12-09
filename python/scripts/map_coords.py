import enum
from pathlib import Path
import csv
import numpy as np
from sklearn import linear_model
from math import log, tan, sin, cos, sqrt, pi
import svgwrite

ROOT_DIR = Path(__file__).parent.parent.parent

with (ROOT_DIR/'output/points.csv').open('r') as points_file:
    points = [(float(p[1]), float(p[2])) 
        for p in csv.reader(points_file) if len(p) >= 3]
print(f'Found {len(points)} points')

with (ROOT_DIR/'output/city_coordinates.csv').open('r') as coord_file:
    cities = [r[:3] + [float(x) for x in r[3:]] 
        for r in csv.reader(coord_file) if len(r) >= 6]
print(f'Found {len(cities)} cities')

connections = [None] * len(points)
for i in range(len(points)):
    connections[i] = []
n_conn = 0
with (ROOT_DIR/'output/railroads.csv').open('r') as rr_file:
    for r in csv.reader(rr_file):
        if len(r) >= 3:
            p1,p2 = int(r[1]),int(r[2])
            if p1 < p2 and p2 not in connections[p1]:
                connections[p1].append(p2)
                n_conn += 1
            elif p2 < p1 and p1 not in connections[p2]:
                connections[p2].append(p1)
                n_conn += 1
print(f'Found {n_conn} connections')

X = np.ndarray(shape=(len(cities),2))
Y = np.ndarray(shape=(len(cities),2))
for pt_i, c in enumerate(cities):
    X[pt_i,0],X[pt_i,1],Y[pt_i,0],Y[pt_i,1] = c[3:]
X *= pi / 180

ref_lon = (np.max(X[:,0]) + np.min(X[:,0]))/2
ref_lat1 = np.min(X[:,1])
ref_lat2 = np.max(X[:,1]) + pi/8
n = log(cos(ref_lat1)/cos(ref_lat2))/(
    log(tan(pi/4 + ref_lat2/2)/tan(pi/4 + ref_lat1/2)))
def transform(lon, lat):
    rho = (1/tan(pi/4 + lat/2))**n
    return rho * sin(n*(lon - ref_lon)), \
           - rho * cos(n*(lon - ref_lon))
for pt_i in range(len(cities)):
    X[pt_i,0],X[pt_i,1] = transform(X[pt_i,0],X[pt_i,1])

#Y[:,0] -= np.min(Y[:,0])
#Y[:,1] = np.max(Y[:,1]) - Y[:,1]
regr = linear_model.LinearRegression()
regr.fit(X,Y)
Yp = regr.predict(X)
print(regr.coef_, regr.intercept_)

sum_d = 0
for pt_i in range(len(cities)):
    d = sqrt((Y[pt_i,0]-Yp[pt_i,0])**2 + (Y[pt_i,1]-Yp[pt_i,1])**2)
    #print(f'{pt_i},{Y[pt_i,0]},{Y[pt_i,1]},{Yp[pt_i,0]},{Yp[pt_i,1]},{d}')
    sum_d += d
print(f'Average distance = {sum_d/len(cities)}')

comp_svg = ROOT_DIR / 'output/map_compare.svg'
min_x = min(np.min(Yp[:,0]),0)
min_y = min(np.min(Yp[:,1]),0)
Y[:,0] -= min_x
Y[:,1] -= min_y
Yp[:,0] -= min_x
Yp[:,1] -= min_y
max_x = max(np.max(Yp[:,0]),np.max(Y[:,0]))
max_y = max(np.max(Yp[:,1]),np.max(Y[:,1]))
dwg = svgwrite.Drawing(comp_svg, size=(max_x,max_y),
    viewBox=f'0 0 {max_x} {max_y}')

LINE_D = 3
def draw_x(x,y,**kwargs):
    dwg.add(dwg.line((x-LINE_D,y-LINE_D),(x+LINE_D,y+LINE_D),**kwargs))
    dwg.add(dwg.line((x-LINE_D,y+LINE_D),(x+LINE_D,y-LINE_D),**kwargs))
def draw_plus(x,y,**kwargs):
    dwg.add(dwg.line((x-LINE_D,y),(x+LINE_D,y),**kwargs))
    dwg.add(dwg.line((x,y+LINE_D),(x,y-LINE_D),**kwargs))

for pt_i in range(len(cities)):
    draw_x(Y[pt_i,0], Y[pt_i,1], stroke_width=1, stroke='blue')
    draw_plus(Yp[pt_i,0], Yp[pt_i,1], stroke_width=1, stroke='red')
    dwg.add(dwg.line((Y[pt_i,0],Y[pt_i,1]),(Yp[pt_i,0],Yp[pt_i,1]),
        stroke='grey', stroke_width=2))

mapped_pts = [None] * len(points)
for pt_i, (x,y) in enumerate(points):
    x -= min_x
    y -= min_y
    delta = np.zeros(2)
    sum_wgt = 0
    for city_i, city in enumerate(cities):
        x_c,y_c = Y[city_i,:]
        if int(city[2]) == pt_i:
            mapped_pts[pt_i] = (Yp[city_i,0], Yp[city_i,1])
            break
        else:
            d = sqrt((x-x_c)**2+(y-y_c)**2)
            delta += (Yp[city_i,:] - Y[city_i,:])*(1/d)
            sum_wgt += 1/d
    if not mapped_pts[pt_i]:
        delta /= sum_wgt
        mapped_pts[pt_i] = (x + delta[0], y + delta[1])
        #print(f'{x} {y} -> {mapped_pts[pt_i]}')

for pt_i in range(len(points)):
    for pt_j in connections[pt_i]:
        dwg.add(dwg.line(mapped_pts[pt_i], mapped_pts[pt_j],
            stroke='green', stroke_width='0.5'))

dwg.save()