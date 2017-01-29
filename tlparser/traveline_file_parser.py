#!/usr/bin/python3

import logging
import os
import zipfile

from .xmlparser import process_xml_file
from .traveline_xml_parser import add_service, add_vehiclejourney, add_journeypatternsection, add_operator, add_stoppoint, add_routesection, add_route


PARSERS = {
	'Service': add_service,
	'VehicleJourney': add_vehiclejourney,
	'JourneyPatternSection': add_journeypatternsection,
	'Operator': add_operator,
	'AnnotatedStopPointRef': add_stoppoint,
	'RouteSection': add_routesection,
	'Route': add_route,
}

def process_all_files(conn):
	for zip_filename in list_zip_filenames():
		logging.info("Processing zip file %s...", zip_filename)
		process_zipfile(conn, zip_filename)

def list_zip_filenames():
	return [
		"travelinedata/" + name
		for name in os.listdir("travelinedata/")
		if name.endswith(".zip")]

def process_zipfile(conn, zip_filename):
	with zipfile.ZipFile(zip_filename) as container:
		for contentname in container.namelist():
			source = zip_filename.split("/")[-1] + "/" + contentname
			with conn as transaction_conn:
				if not have_data_for_source(transaction_conn, source):
					with container.open(contentname) as xmlfile:
						try:
							logging.info("Processing file %s", source)
							process_xml_file(xmlfile, PARSERS, args=(transaction_conn, source))
						except Exception:
							logging.exception("Skipping file %s", source)

def have_data_for_source(conn, source):
	with conn.cursor() as cur:
		cur.execute("select 1 from vehiclejourney where source = %s limit 1", (source,))
		num_rows = len(list(cur))
		if num_rows > 0:
			return True

		cur.execute("select 1 from service where source = %s limit 1", (source,))
		num_rows = len(list(cur))
		if num_rows > 0:
			return True

	return False
