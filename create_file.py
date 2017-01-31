#!/usr/bin/python3
# encoding: utf8

from tlparser.query_boundingbox import line_segments_in_boundingbox, line_segments_and_stops_in_boundingbox
import psycopg2
import json


def format_json(points):
	return json.dumps(points, indent=4)

def format_dot(points):
	return 'digraph {\n' + '\n'.join(
		'"{}" -> "{}";'.format(point['from']['id'], point['to']['id'])
		for point in points
	) + '\n}'

def main():
	format_type = 'pairs_json'
	boundingbox = (51.48, -2.52, 51.99, -2.40)

	with psycopg2.connect("dbname=travelinedata") as conn:
		if format_type == 'dot':
			print(format_dot(line_segments_in_boundingbox(conn, *boundingbox)))
		elif format_type == 'json':
			print(format_json(line_segments_in_boundingbox(conn, *boundingbox)))
		elif format_type == 'pairs_json':
			pairs_and_stops = line_segments_and_stops_in_boundingbox(conn, *boundingbox)
			print(format_json(pairs_and_stops))
		else:
			raise ValueError(format_type)

if __name__ == '__main__':
	main()
