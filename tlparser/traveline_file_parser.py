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

				# We don't know if we'll be told about things in the correct order
				# but each file should be self-consistent
				with transaction_conn.cursor() as cur:
					cur.execute("SET CONSTRAINTS ALL DEFERRED;")

				source_id = source_id_if_not_already_inserted(transaction_conn, source)
				if source_id:
					with container.open(contentname) as xmlfile:
						try:
							logging.info("Processing file %s (%r)", source, source_id)
							process_xml_file(xmlfile, PARSERS, args=(transaction_conn, source_id))
						except Exception:
							logging.exception("Skipping file %s (%r)", source, source_id)

def source_id_if_not_already_inserted(conn, source):
	# Only do the southend area
	USE_TESTING_DATA_ONLY = False
	if USE_TESTING_DATA_ONLY and not source.startswith("SE.zip/set_5-"):
		return None

	with conn.cursor() as cur:
		cur.execute("""
			insert into source(source) values (%s)
			on conflict do nothing
			returning source_id
			""", (source,))
		rows = list(cur)
		if len(rows) == 0:
			return None
		else:
			[[source_id]] = rows
			return source_id
