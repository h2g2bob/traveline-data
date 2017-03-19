#!/usr/bin/python3

from io import TextIOWrapper
import csv
import logging
import os
import psycopg2
import zipfile


def process_all(conn):
	with conn.cursor() as cur:
		for postcode, lat, lng in latlng_from_zipfile("oscodepointdata/codepo_gb.zip"):
			postcode_no_spaces = postcode.replace(" ", "")
			cur.execute(
				"INSERT INTO oscodepointdata(postcode, display, location) VALUES (%s, %s, point(%s, %s));",
				(postcode_no_spaces, postcode, lat, lng,))


def latlng_from_zipfile(zip_filename):
	from convert_coordinates import convert_coordinates

	with zipfile.ZipFile(zip_filename) as container:
		for contentname in container.namelist():
			if not contentname.startswith("Data/CSV/"):
				continue
			with container.open(contentname) as csvfile:
				for row in csv.reader(TextIOWrapper(csvfile, encoding="utf8")):
					postcode, _quality, eastings, northings, _country, _nhs_regional, _nhs, _admin_county, _admin_district, _admin_ward = row
					lat, lng = convert_coordinates(int(eastings), int(northings))
					yield postcode, lat, lng
