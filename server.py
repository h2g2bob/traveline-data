#!/usr/bin/python3
# encoding: utf8

from tlparser.query_boundingbox import line_segments_in_boundingbox, line_segments_and_stops_in_boundingbox
import psycopg2
import json
import logging
from flask import Flask
from flask import request

app = Flask(__name__)


def database():
	return psycopg2.connect("dbname=travelinedata")

def boundingbox_from_request():
	height = float(request.args['height'])
	width = float(request.args['width'])
	if width * height > 0.25:
		raise ValueError("Area too large (forbidden)")
	return dict(
		minlat=float(request.args['lat']),
		minlng=float(request.args['lng']),
		maxlat=float(request.args['lat']) - height,
		maxlng=float(request.args['lng']) + width)

@app.route('/')
def map_page():
	with open("map_page.html") as f:
		return f.read()

@app.route('/json/')
def format_json():
	boundingbox = boundingbox_from_request()
	logging.info('%r', boundingbox)
	with database() as conn:
		pairs_and_stops = line_segments_and_stops_in_boundingbox(conn, min_freq=int(request.args.get('min_freq', 1)), **boundingbox)
		return json.dumps(pairs_and_stops, indent=4)

@app.route('/dot/')
def format_dot():
	boundingbox = boundingbox_from_request()
	with database() as conn:
		points = line_segments_in_boundingbox(conn, **boundingbox)
		return 'digraph {\n' + '\n'.join(
			'"{}" -> "{}";'.format(point['from']['id'], point['to']['id'])
			for point in points
		) + '\n}'

if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	app.run()
