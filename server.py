#!/usr/bin/python3
# encoding: utf8

from tlparser.query_boundingbox import line_segments_in_boundingbox, line_segments_and_stops_in_boundingbox
import psycopg2
import json
from flask import Flask

app = Flask(__name__)

boundingbox = (51.00, -3.00, 52.00, -2.00)


def database():
	return psycopg2.connect("dbname=travelinedata")

@app.route('/')
def map_page():
	with open("map_page.html") as f:
		return f.read()

@app.route('/json/')
def format_json():
	with database() as conn:
		pairs_and_stops = line_segments_and_stops_in_boundingbox(conn, *boundingbox)
		return "map_paint({});".format(json.dumps(pairs_and_stops, indent=4))

@app.route('/dot/')
def format_dot():
	with database() as conn:
		points = line_segments_in_boundingbox(conn, *boundingbox)
		return 'digraph {\n' + '\n'.join(
			'"{}" -> "{}";'.format(point['from']['id'], point['to']['id'])
			for point in points
		) + '\n}'

if __name__ == '__main__':
	app.run()
