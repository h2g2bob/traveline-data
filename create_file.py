#!/usr/bin/python3
# encoding: utf8

from tlparser.query_boundingbox import line_segments_in_boundingbox
import psycopg2
import json


def format_json(points):
	return json.dumps(points, indent=4)

def main():
	with psycopg2.connect("dbname=travelinedata") as conn:
		format_function = format_json
		print(format_function(line_segments_in_boundingbox(conn, 51.48, -2.52, 51.99, -2.40)))

if __name__ == '__main__':
	main()
