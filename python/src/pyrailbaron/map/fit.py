import numpy as np
from sklearn import linear_model

from typing import List, Callable
from pyrailbaron.map.datamodel import Coordinate, Map, distance
from dataclasses import replace
from pyrailbaron.map.svg import calculate_lcc_n, transform_lcc, inv_transform_lcc

def fit_data(m: Map) -> Map:
    cities = [p for p in m.points if len(p.city_names) > 0]
    n_cities = len(cities)

    #ref_lat1 = min(p.geo_coords[0] for p in cities)
    #ref_lat2 = max(p.geo_coords[1] for p in cities)
    #n = calculate_lcc_n(ref_lat1, ref_lat2)
    def transform(geo_coords):
        return transform_lcc(geo_coords) #,n)
    def inv_transform(coords):
        return inv_transform_lcc(coords) #,n)

    X = np.ndarray((n_cities,2))
    Y = np.ndarray((n_cities,2))
    for i,p in enumerate(cities):
        X[i,:] = transform(p.geo_coords)
        Y[i,:] = p.dxf_coords
    reg = linear_model.LinearRegression()
    reg.fit(X,Y)
    transform_A = reg.coef_.tolist()
    transform_b = list(reg.intercept_)

    Yp=reg.predict(X)
    invA = np.linalg.inv(reg.coef_)
    for p in m.points:
        if len(p.city_names) > 0:
            continue
        delta = np.zeros(2)
        sum_wgt = 0.0
        D_PWR = -2
        for city_i, c_p in enumerate(cities):
            d = distance(c_p.dxf_coords, p.dxf_coords)
            delta += (Yp[city_i,:] - Y[city_i,:])*(d**D_PWR)
            sum_wgt += (d**D_PWR)
        delta /= sum_wgt
        adj_dxf_coords = np.array(p.dxf_coords) + delta
        adj_map_coords = np.matmul(invA, adj_dxf_coords - reg.intercept_)
        p.geo_coords = inv_transform(adj_map_coords)

    def transform(c: Coordinate) -> Coordinate:
        v = reg.predict(np.array(c).reshape(1,-1))
        return (v[0,0], v[0,1])
    return replace(m, map_transform_A = transform_A, map_transform_b = transform_b)