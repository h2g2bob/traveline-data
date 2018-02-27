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

@app.route('/postcode/location/<code>/')
def postcode_location(code):
	code = code.upper().replace(" ", "")
	with database() as conn:
		statement_timeout(conn, 10)
		with conn.cursor() as cur:
			cur.execute("""
				select lat, lng
				from postcodes
				where postcode = %s;
				""", (code,))
			[[lat, lng]] = cur.fetchall()
			return jsonify({"lat": lat, "lng": lng})

@app.route('/postcode/autocomplete/')
def postcode_complete():
	prefix = request.args.get("prefix", "")
	prefix = prefix.upper().replace(" ", "")
	with database() as conn:
		statement_timeout(conn, 10)
		with conn.cursor() as cur:
			cur.execute("""
				select postcode
				from postcodes
				where postcode like %s || '%%'
				order by postcode
				limit 10;
				""", (prefix,))
			data = [postcode for [postcode] in cur.fetchall()]
			return jsonify({"results": data})

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

def _one_feature(from_id, from_lat, from_lng, to_id, to_lat, to_lng, frequency, line_names):
	return {
		"type": "Feature",
		"geometry": {
			"type": "LineString",
			"coordinates": [
				[from_lng, from_lat],
				[to_lng, to_lat],
				]
			},
		"properties": {
			"popupContent": repr(line_names),
			"frequency": frequency
			},
		"id": 1
		}

DAY_OF_WEEK_CODE = {
	'': 0x01,
	'M': 0x01,
	'T': 0x02,
	'W': 0x04,
	'H': 0x08,
	'F': 0x10,
	'S': 0x20,
	'N': 0x40,
	}

@app.route('/geojson/')
def geojson_frequency():
	hour_column = 'hour_12'
	with database() as conn:
		statement_timeout(conn, 10)
		with conn.cursor() as cur:
			cur.execute("""
				WITH desired_bounding_box_table AS (
					SELECT box(point(%s, %s), point(%s, %s)) AS desired_bounding_box
				)
				SELECT
					bus_stop_pair_frequencies.from_stoppoint,
					n_from.latitude,
					n_from.longitude,
					bus_stop_pair_frequencies.to_stoppoint,
					n_to.latitude,
					n_to.longitude,
					bus_stop_pair_frequencies.frequency,
					bus_stop_pair_frequencies.line_names

				FROM (
					SELECT
						timing.from_stoppoint,
						timing.to_stoppoint,
						sum(case when days_mask & %s != 0 then """ + hour_column + """ else 0 end) AS frequency,
						array_agg(distinct line.line_name) AS line_names

					FROM jptiminglink timing
					JOIN journeypattern_service_section section USING (jpsection_id)
					JOIN mv_vehiclejourney_per_hour vjph USING (journeypattern_id)
					JOIN journeypattern_bounding_box jp_bbox USING (journeypattern_id)
					LEFT JOIN line line ON vjph.line_id = line.line_id
					WHERE jp_bbox.bounding_box && (select desired_bounding_box from desired_bounding_box_table)
					GROUP BY 1, 2
				) AS bus_stop_pair_frequencies
				JOIN naptan n_from ON n_from.atcocode_id = bus_stop_pair_frequencies.from_stoppoint
				JOIN naptan n_to ON n_to.atcocode_id = bus_stop_pair_frequencies.to_stoppoint

				-- if this was an "and" relation, it might speed things up by filtering out a large
				-- number of naptan points before joining... but currently it appears to make no
				-- difference to the query plan, so we can stick with an "or" here:
				WHERE point(n_from.latitude, n_from.longitude) <@ (select desired_bounding_box from desired_bounding_box_table)
				OR point(n_to.latitude, n_to.longitude) <@ (select desired_bounding_box from desired_bounding_box_table)
				""", (
					request.args.get('minlat'),
					request.args.get('minlng'),
					request.args.get('maxlat'),
					DAY_OF_WEEK_CODE[request.args.get('dow', '')]))

			return jsonify({
				"type": "FeatureCollection",
				"features": [
					_one_feature(*row)
					for row in cur
					]
				})


if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	app.run()
