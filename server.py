#!/usr/bin/python3
# encoding: utf8

import psycopg2
import logging
from flask import Flask
from flask import jsonify
from flask import request

app = Flask(__name__, static_url_path='')

DEC2FLOAT = psycopg2.extensions.new_type(
    psycopg2.extensions.DECIMAL.values,
    'DEC2FLOAT',
    lambda value, curs: float(value) if value is not None else None)
psycopg2.extensions.register_type(DEC2FLOAT)

BASIC_INFO = {
	"copyright": "Contains public sector information licensed under the Open Government Licence v3.0 from <a href=\"http://www.travelinedata.org.uk/\">Traveline National Dataset (TNDS)</a> and Naptan. Data provided by <a href=\"https://github.com/h2g2bob/traveline-data\">traveline-data</a> under a <a href=\"https://www.gnu.org/licenses/agpl-3.0.en.html\">AGPLv3 License</a>.",
}


def database():
	return psycopg2.connect("dbname=travelinedata")

def statement_timeout(conn, seconds):
	millis = int(seconds*1000)
	with conn.cursor() as cur:
		cur.execute("SET statement_timeout TO %s;", (millis,))

def json_response(data):
	data.update(BASIC_INFO)
	return jsonify(data)

@app.route('/')
def index():
	return json_response({})

@app.route('/postcode/location/<code>/')
def postcode_location(code):
	code = code.upper().replace(" ", "")
	with database() as conn:
		statement_timeout(conn, 10)
		with conn.cursor() as cur:
			cur.execute("""
				SELECT lat, lng
					FROM postcodes_short
					WHERE postcode = %(postcode)s
				UNION ALL
				SELECT lat, lng
					FROM postcodes
					WHERE postcode = %(postcode)s
				""", {"postcode": code})
			[[lat, lng]] = cur.fetchall()
			return json_response({"lat": lat, "lng": lng})

@app.route('/postcode/autocomplete/')
def postcode_complete():
	prefix = request.args.get("prefix", "")
	prefix = prefix.upper().replace(" ", "")
	if prefix == "":
		return json_response({"results": [
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
				SELECT * FROM (
					SELECT true as is_short, postcode
						FROM postcodes_short
						WHERE postcode LIKE %(prefix)s || '%%'
						ORDER BY postcode
						LIMIT 10
					) AS short_codes
				UNION ALL
				SELECT * FROM (
					SELECT false as is_short, postcode
						FROM postcodes
						WHERE postcode LIKE %(prefix)s || '%%'
						ORDER BY postcode
						LIMIT 10
					) AS long_codes
				ORDER BY is_short desc, postcode
				LIMIT 10;
				""", {'prefix': prefix})
			data = [postcode for [_short, postcode] in cur.fetchall()]
			return json_response({"results": data})

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


if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	app.run()
