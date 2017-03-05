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
			cur.execute(
				"INSERT INTO oscodepointdata(postcode, location) VALUES (%s, point(%s, %s));",
				(postcode, lat, lng,))


def latlng_from_zipfile(zip_filename):
	with zipfile.ZipFile(zip_filename) as container:
		for contentname in container.namelist():
			if not contentname.startswith("Data/CSV/"):
				continue
			with container.open(contentname) as csvfile:
				for row in csv.reader(TextIOWrapper(csvfile, encoding="utf8")):
					postcode, _quality, eastings, northings, _country, _nhs_regional, _nhs, _admin_county, _admin_district, _admin_ward = row

					# Lat/Lng values from elsewhere are likely EPSG:3857 (Web Marcator) ...?
					# But this is some sort of Eastings and Northings thing!
					#
					# The definition is here:
					# https://www.ordnancesurvey.co.uk/docs/support/guide-coordinate-systems-great-britain.pdf#page=42
					#
					# OS provides BSD software which does this transformation (nice!)
					# Source code: https://bitbucket.org/PaulFMichell/gridinquestii
					# Lots of downloads: https://www.ordnancesurvey.co.uk/business-and-government/help-and-support/navigation-technology/os-net/formats-for-developers.html
					# Probably the easiest is to use the InQuestII .so file and cffi?

					yield postcode, lat, lng
