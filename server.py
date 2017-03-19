#!/usr/bin/python3
# encoding: utf8

from tlparser.query_boundingbox import line_segments_and_stops_in_boundingbox
from tlparser.query_boundingbox import line_segments_in_boundingbox
from tlparser.query_boundingbox import journeypattern_ids_in_boundingbox
from tlparser.query_boundingbox import line_segments_and_stops_for_journeypattern
import psycopg2
import json
import logging
from flask import Flask
from flask import jsonify
from flask import request
from flask import send_from_directory

app = Flask(__name__, static_url_path='')


# Forbid requests for very large areas
# We're really protected by statement_timeout, so this can be fairly relaxed
AREA_TOO_LARGE=4.0


def database():
	return psycopg2.connect("dbname=travelinedata")

def statement_timeout(conn, seconds):
	millis = int(seconds*1000)
	with conn.cursor() as cur:
		cur.execute("SET statement_timeout TO %s;", (millis,))

def boundingbox_from_request():
	height = float(request.args['height'])
	width = float(request.args['width'])
	if width * height > AREA_TOO_LARGE:
		raise ValueError("Area too large (forbidden)")
	return dict(
		minlat=float(request.args['lat']),
		minlng=float(request.args['lng']),
		maxlat=float(request.args['lat']) - height,
		maxlng=float(request.args['lng']) + width)

@app.route('/')
def map_page():
	return send_from_directory("static", "map_page.html")

@app.route('/datasources/')
def datasources():
	return send_from_directory("static", "data_sources.html")

@app.route('/map_page.js')
def map_page_js():
	return send_from_directory("static", "map_page.js")

@app.route('/map_page.css')
def map_page_css():
	return send_from_directory("static", "map_page.css")

@app.route('/json/')
def format_json():
	boundingbox = boundingbox_from_request()
	logging.info('%r', boundingbox)
	with database() as conn:
		statement_timeout(conn, 10)
		pairs_and_stops = line_segments_and_stops_in_boundingbox(conn, min_freq=int(request.args.get('min_freq', 1)), **boundingbox)
		return json.dumps(pairs_and_stops, indent=4)

@app.route('/bbox/')
def format_journeypattern_ids_in_boundingbox():
	boundingbox = boundingbox_from_request()
	logging.info('%r', boundingbox)
	with database() as conn:
		statement_timeout(conn, 10)
		jpid_list = journeypattern_ids_in_boundingbox(conn, **boundingbox)
		return jsonify({"journeypatterns": jpid_list})

@app.route('/jp/<int:journeypattern_id>/')
def format_journeypattern(journeypattern_id):
	with database() as conn:
		statement_timeout(conn, 10)
		pairs_and_stops = line_segments_and_stops_for_journeypattern(conn, journeypattern_id)
		return jsonify(pairs_and_stops)

@app.route('/dot/')
def format_dot():
	boundingbox = boundingbox_from_request()
	with database() as conn:
		statement_timeout(conn, 10)
		points = line_segments_in_boundingbox(conn, **boundingbox)
		return 'digraph {\n' + '\n'.join(
			'"{}" -> "{}";'.format(point['from']['id'], point['to']['id'])
			for point in points
		) + '\n}'

@app.route('/postcode_to_ll/<postcode>')
def postcode_to_ll(postcode):
	with database() as conn:
		with conn.cursor() as cur:
			cur.execute("""
				SELECT location[0], location[1]
				FROM oscodepointdata
				WHERE postcode = %s;
				""", (postcode.strip(" ").upper(),))
			rows = list(cur)
			if rows:
				[[lat, lng]] = rows
				return jsonify({"result": True, "lat": lat, "lng": lng})
			else:
				return jsonify({"result": False})

if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	app.run()
