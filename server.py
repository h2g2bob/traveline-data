#!/usr/bin/python3
# encoding: utf8

import psycopg2
import json
import logging
from flask import Flask
from flask import jsonify
from flask import request
from flask import send_from_directory

app = Flask(__name__, static_url_path='')


DEC2FLOAT = psycopg2.extensions.new_type(
    psycopg2.extensions.DECIMAL.values,
    'DEC2FLOAT',
    lambda value, curs: float(value) if value is not None else None)
psycopg2.extensions.register_type(DEC2FLOAT)


# Forbid requests for very large areas
# We're really protected by statement_timeout, so this can be fairly relaxed
AREA_TOO_LARGE=4.0


def database():
	return psycopg2.connect("dbname=travelinedata")

def statement_timeout(conn, seconds):
	millis = int(seconds*1000)
	with conn.cursor() as cur:
		cur.execute("SET statement_timeout TO %s;", (millis,))

@app.route('/')
def map_page():
	return send_from_directory("static", "map.html")

@app.route('/map.js')
def map_page_js():
	return send_from_directory("static", "map.js")

@app.route('/map.css')
def map_page_css():
	return send_from_directory("static", "map.css")

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
	if prefix == "":
		return jsonify({"results": [
			"DE12FD",  # Derby bus station
			"EX1",  # Exeter
			"L18JX",  # Liverpool bus station
			"NR1",  # Norwich
			"OX41AA",  # Oxford
			"SS1",  # Southend-on-sea
			"W1",  # Central London
			]})

	with database() as conn:
		statement_timeout(conn, 10)
		with conn.cursor() as cur:
			cur.execute("""
				with data as (
					select
						postcode,
						rank() over (partition by substring(postcode, 1, length(%(prefix)s)+1) order by postcode) as ranking
					from postcodes
					where postcode like %(prefix)s || '%%'
					order by postcode
				)
				select
					postcode
				from data
				where ranking = 1
				order by postcode
				limit 10;
				""", {'prefix': prefix})
			data = [postcode for [postcode] in cur.fetchall()]
			return jsonify({"results": data})

def _one_feature_v3(from_id, to_id, from_lat, from_lng, to_lat, to_lng, weekday, length, min_runtime, max_runtime, all_services_array, one_service_array):
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
			"length": length,
			"frequencies": {
				weekday : {
					"single_service": one_service_array,
					"all_services": all_services_array,
					},
				},
			"runtime": {
				"min": min_runtime,
				"max": max_runtime,
				}
			},
		"id": 1
		}


@app.route('/geojson/v3/links/')
def geojson_frequency_v3():
	with database() as conn:
		statement_timeout(conn, 10)
		with conn.cursor() as cur:
			cur.execute("""
				with bus_per_hour_for_day as (
					select
						from_stoppoint,
						to_stoppoint,
						first_value(line_segment) over (partition by from_stoppoint, to_stoppoint) as line_segment,
						min(min_runtime) over (partition by from_stoppoint, to_stoppoint) as min_runtime,
						max(max_runtime) over (partition by from_stoppoint, to_stoppoint) as max_runtime,
						hourarray_sum(hour_array_total::int[24]) over (partition by from_stoppoint, to_stoppoint) as hour_array_total,
						hourarray_sum(hour_array_best_service::int[24]) over (partition by from_stoppoint, to_stoppoint) as hour_array_best_service
					from mv_link_frequency3
					where lseg_bbox && box(point(%(minlat)s, %(minlng)s), point(%(maxlat)s, %(maxlng)s))
					and weekday = %(weekday)s
				)
				select
					from_stoppoint,
					to_stoppoint,
					(line_segment[0]::point)[0],
					(line_segment[0]::point)[1],
					(line_segment[1]::point)[0],
					(line_segment[1]::point)[1],
					%(weekday)s as weekday,
					length(line_segment),
					min_runtime,
					max_runtime,
					hour_array_total,
					hour_array_best_service

				from bus_per_hour_for_day;

				""", dict(
					minlat=request.args.get('minlat'),
					minlng=request.args.get('minlng'),
					maxlat=request.args.get('maxlat'),
					maxlng=request.args.get('maxlng'),
					weekday=request.args.get('weekday', 'M')))

			return jsonify({
				"type": "FeatureCollection",
				"features": [
					_one_feature_v3(*row)
					for row in cur
					]
				})

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

def _one_feature(from_id, to_id, from_lat, from_lng, to_lat, to_lng, length, min_runtime, max_runtime, frequency_array):
	frequency_array = [float(freq) for freq in frequency_array]  # Damn you Decimal module
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
			"length": length,
			"frequencies": frequency_array,
			"min_runtime": min_runtime,
			"max_runtime": max_runtime,
			},
		"id": 1
		}

@app.route('/geojson/')
def geojson_frequency():
	hour_column = 'hour_12'
	with database() as conn:
		statement_timeout(conn, 10)
		with conn.cursor() as cur:
			cur.execute("""
				with bus_per_hour_for_day as (
					select
						from_stoppoint,
						to_stoppoint,
						first_value(line_segment) over (partition by from_stoppoint, to_stoppoint) as line_segment,
						min((select min(r) from unnest(runtimes) AS r)) over (partition by from_stoppoint, to_stoppoint) as min_runtime,
						max((select max(r) from unnest(runtimes) AS r)) over (partition by from_stoppoint, to_stoppoint) as max_runtime,
						sum(hour_0) over (partition by from_stoppoint, to_stoppoint) as hour_0,
						sum(hour_1) over (partition by from_stoppoint, to_stoppoint) as hour_1,
						sum(hour_2) over (partition by from_stoppoint, to_stoppoint) as hour_2,
						sum(hour_3) over (partition by from_stoppoint, to_stoppoint) as hour_3,
						sum(hour_4) over (partition by from_stoppoint, to_stoppoint) as hour_4,
						sum(hour_5) over (partition by from_stoppoint, to_stoppoint) as hour_5,
						sum(hour_6) over (partition by from_stoppoint, to_stoppoint) as hour_6,
						sum(hour_7) over (partition by from_stoppoint, to_stoppoint) as hour_7,
						sum(hour_8) over (partition by from_stoppoint, to_stoppoint) as hour_8,
						sum(hour_9) over (partition by from_stoppoint, to_stoppoint) as hour_9,
						sum(hour_10) over (partition by from_stoppoint, to_stoppoint) as hour_10,
						sum(hour_11) over (partition by from_stoppoint, to_stoppoint) as hour_11,
						sum(hour_12) over (partition by from_stoppoint, to_stoppoint) as hour_12,
						sum(hour_13) over (partition by from_stoppoint, to_stoppoint) as hour_13,
						sum(hour_14) over (partition by from_stoppoint, to_stoppoint) as hour_14,
						sum(hour_15) over (partition by from_stoppoint, to_stoppoint) as hour_15,
						sum(hour_16) over (partition by from_stoppoint, to_stoppoint) as hour_16,
						sum(hour_17) over (partition by from_stoppoint, to_stoppoint) as hour_17,
						sum(hour_18) over (partition by from_stoppoint, to_stoppoint) as hour_18,
						sum(hour_19) over (partition by from_stoppoint, to_stoppoint) as hour_19,
						sum(hour_20) over (partition by from_stoppoint, to_stoppoint) as hour_20,
						sum(hour_21) over (partition by from_stoppoint, to_stoppoint) as hour_21,
						sum(hour_22) over (partition by from_stoppoint, to_stoppoint) as hour_22,
						sum(hour_23) over (partition by from_stoppoint, to_stoppoint) as hour_23
					from mv_link_frequency2
					where lseg_bbox && box(point(%(minlat)s, %(minlng)s), point(%(maxlat)s, %(maxlng)s))
					and days_mask & %(dow)s > 0
				)
				select
					from_stoppoint,
					to_stoppoint,
					(line_segment[0]::point)[0],
					(line_segment[0]::point)[1],
					(line_segment[1]::point)[0],
					(line_segment[1]::point)[1],
					length(line_segment),
					min_runtime,
					max_runtime,
					ARRAY[
						hour_0,
						hour_1,
						hour_2,
						hour_3,
						hour_4,
						hour_5,
						hour_6,
						hour_7,
						hour_8,
						hour_9,
						hour_10,
						hour_11,
						hour_12,
						hour_13,
						hour_14,
						hour_15,
						hour_16,
						hour_17,
						hour_18,
						hour_19,
						hour_20,
						hour_21,
						hour_22,
						hour_23]

				from bus_per_hour_for_day;

				""", dict(
					minlat=request.args.get('minlat'),
					minlng=request.args.get('minlng'),
					maxlat=request.args.get('maxlat'),
					maxlng=request.args.get('maxlng'),
					dow=DAY_OF_WEEK_CODE[request.args.get('dow', '')]))

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
