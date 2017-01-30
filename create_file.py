#!/usr/bin/python3
# encoding: utf8

from tlparser.query_boundingbox import line_segments_in_boundingbox
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
	format_type='dot'
	with psycopg2.connect("dbname=travelinedata") as conn:
		format_function = {
			'json': format_json,
			'dot': format_dot
		}[format_type]
		print(format_function(line_segments_in_boundingbox(conn, 51.48, -2.52, 51.99, -2.40)))

if __name__ == '__main__':
	main()
