# -*- coding: utf-8 -*-
"""
Created on Tue Apr 07 15:11:49 2014
@author: Maurizio Napolitano <napo@fbk.eu>
The MIT License (MIT)
Copyright (c) 2016 Fondazione Bruno Kessler http://fbk.eu
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import os
import sys
import tempfile
import zipfile
import unicodecsv
import geojson
import networkx as nx
from itertools import groupby


# GTFS defines these route types
LRT_TYPE = '0'
SUBWAY_TYPE = '1'
RAIL_TYPE = '2'
BUS_TYPE = '3'
FERRY_TYPE = '4'
CABLE_CAR_TYPE = '5'
GONDOLA_TYPE = '6'
FUNICULAR_TYPE = '7'

# Root of the extracted GTFS file
DATA_ROOT = 'data/'

# You can filter the type of stop converted by placing the route types
# you're interested in in this list.
CONVERT_ROUTE_TYPES = [BUS_TYPE]

# This defines an optional mapping on station names. Because stations
# are uniquely identified by their station name, this can be used to
# merge two nodes (stations) into one.
STATION_MAP = {
}

# Sometimes there are stations you may want to discard altogether
# (including their edges). They can be added to this set.
DISCARD_STATIONS = set([
])

def read_from_zip(filename):
    """Read GTFS data from the specified zip file."""
    with zipfile.ZipFile(filename) as archive:
        temp_dir = tempfile.mkdtemp(suffix='data')
        archive.extractall(temp_dir)
    output = read_from_directory(temp_dir)
    return output 
    
def read_from_directory(directory):
    G=nx.Graph()
    nodes = {}
    trips_csv = unicodecsv.DictReader(file(directory+'/trips.txt'))
    stops_csv = unicodecsv.DictReader(file(directory+'/stops.txt'))
    stop_times_csv = unicodecsv.DictReader(file(directory+'/stop_times.txt'))
    routes_csv = unicodecsv.DictReader(file(directory+'/routes.txt'))
    routes = dict()
    for route in routes_csv:
        if route['route_type'] in CONVERT_ROUTE_TYPES:
            routes[route['route_id']] = route
    print 'routes', len(routes)

    trips = dict()
    for trip in trips_csv:
        if trip['route_id'] in routes:
            trip['color'] = routes[trip['route_id']]['route_color']
            trips[trip['trip_id']] = trip
    print 'trips', len(trips)

    stops = set()
    edges = dict()
    for trip_id, stop_time_iter in groupby(stop_times_csv, lambda stop_time: stop_time['trip_id']):
        if trip_id in trips:
            trip = trips[trip_id]
            prev_stop = stop_time_iter.next()['stop_id']
            stops.add(prev_stop)
            for stop_time in stop_time_iter:
                stop = stop_time['stop_id']
                edge = (prev_stop, stop)
                edges[edge] = trip['color']
                stops.add(stop)
                prev_stop = stop
    print 'stops', len(stops)
    print 'edges', len(edges)
    stops_used = set(DISCARD_STATIONS)
    for stop in stops_csv:
        if stop['stop_id'] in stops:
            node = {}
            stop_id = stop['stop_id']
            name = stop['stop_name']
            lat = stop['stop_lat']
            lon = stop['stop_lon']
            node['id'] = stop_id
            node['name'] = name
            node['lat'] = lat
            node['lon'] = lon
            nodes[stop_id] = node
            #if name not in stops_used:
            if stop_id not in stops_used:
                G.add_node(stop_id)
                stops_used.add(stop_id)

        
    edges_used = set()
    for (start_stop_id, end_stop_id), color in edges.iteritems():
        edge = min((start_stop_id, end_stop_id), (end_stop_id, start_stop_id))
        if edge not in edges_used:
            G.add_edge(start_stop_id, end_stop_id)
            edges_used.add(edge)
    for item in nx.degree(G).items():
        nodes[item[0]]['degree']=int(item[1])
    features = {}
    for node in nodes:
        latitude = float(nodes[node]['lat'])
        longitude = float(nodes[node]['lon'])
        feature = geojson.Feature(id=stop_id,
                                geometry=geojson.Point([longitude, latitude]),
                                properties={'degree': nodes[node]['degree'],
                                            'name': nodes[node]['name']})
        features[nodes[node]['id']] = feature
    geostations = geojson.FeatureCollection(features=features.values())
    
    features = {}
    idl = 0
    for edge in edges:
        latitude1 = float(nodes[edge[0]]['lat'])
        longitude1 = float(nodes[edge[0]]['lon'])
        latitude2 = float(nodes[edge[1]]['lat'])
        longitude2 = float(nodes[edge[1]]['lon'])
        feature = geojson.Feature(id=stop_id,
                                geometry=geojson.LineString([(longitude1, latitude1),(longitude2,latitude2)]),
                                properties={'from': edge[0],
                                            'to': edge[1]})
        features[idl] = feature
        idl += 1
        geoedge = geojson.FeatureCollection(features=features.values())
    return (geostations,geoedge)


def convert(filename):
    if not os.path.exists(filename):
        raise InputFileError('The specified file was not found: %s' % filename)
        data = None
    if filename.endswith('.zip'):
        data = read_from_zip(filename)
    elif os.path.isdir(filename):
        data = read_from_directory(filename)
    else:
        raise InputFileError('Unrecognized input file, must be zip or directory')
    #return stringify(output)
    out_file = open("stations.geojson","w")
    out_file.write(str(data[0]))
    out_file.close()
    out_file = open("lines.geojson","w")
    out_file.write(str(data[1]))
    out_file.close()
    return True 

def stringify(item):
    return geojson.dumps(item)

def main(argv):
    if len(argv) < 2:
        sys.exit('Usage: %s GTFS_DIRECTORY.' % argv[0])
    print convert(argv[1])

class Error(Exception):
    pass

class InputFileError(Error):
    pass

if __name__ == '__main__':
    main(sys.argv)

#data = convert("google_transit_urbano_tte.zip")
