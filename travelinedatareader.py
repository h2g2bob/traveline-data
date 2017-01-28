#!/usr/bin/python3
from collections import defaultdict
from lxml import etree
import datetime
import logging
import psycopg2
import zipfile
import os
import argparse

# Appears to be:
# <StopPoints>
# 	<AnnotatedStopPointRef>
# <RouteSections>
# 	<RouteSection>
# <Routes>
# 	<Route id="R_20-1-A-y08-1-H-1">
# <JourneyPatternSections>
# 	<JourneyPatternSection id="JPS_20-1-A-y08-1-1-1-H">
# <Operators>
# 	<Operator id="OId_SCCM">
# <Services>
# 	<Service>
# <VehicleJourneys>
# 	<VehicleJourney>

# How many times per hour is a section of route (in one direction) served by a given service, on mondays?
# sqlite> select lineref, jpref, deptime_seconds/3600 as hour, count(1) from vehiclejourney where days_mask & 1 group by 1,2,3 order by 4;

NAMESPACES = {
	"tx": "http://www.transxchange.org.uk/",
}



def database():
	# one database transation
	return psycopg2.connect("dbname=travelinedata")


def add_operator(conn, elem, source):
	operator_id = elem.get("id")
	[shortname] = elem.xpath("./tx:OperatorShortName/text()", namespaces=NAMESPACES)
	with conn.cursor() as cur:
		cur.execute("""
			INSERT INTO operator(source, operator_id, shortname)
			VALUES (%s, %s, %s)
			ON CONFLICT DO NOTHING
		""", (source, operator_id, shortname,))


def add_service(conn, elem, source):
	[servicecode] = elem.xpath("./tx:ServiceCode/text()", namespaces=NAMESPACES)
	privatecode = maybe_one(elem.xpath("./tx:PrivateCode/text()", namespaces=NAMESPACES))
	mode = maybe_one(elem.xpath("./tx:Mode/text()", namespaces=NAMESPACES))
	[description] = elem.xpath("./tx:Description/text()", namespaces=NAMESPACES)
	[operator] = elem.xpath("./tx:RegisteredOperatorRef/text()", namespaces=NAMESPACES)

	with conn.cursor() as cur:
		cur.execute("""
			INSERT INTO service(source, servicecode, privatecode, mode, operator_id, description)
			VALUES (%s, %s, %s, %s, %s, %s)
		""", (source, servicecode, privatecode, mode, operator, description))

	for lineelem in elem.xpath("./tx:Lines/tx:Line", namespaces=NAMESPACES):
		line_id = lineelem.get("id")
		[line_name] = lineelem.xpath("./tx:LineName/text()", namespaces=NAMESPACES)	
		with conn.cursor() as cur:
			cur.execute("""
				INSERT INTO line(source, line_id, servicecode, line_name)
				VALUES (%s, %s, %s, %s)
				ON CONFLICT DO NOTHING
			""", (source, line_id, servicecode, line_name))

	for jpelem in elem.xpath("./tx:StandardService/tx:JourneyPattern", namespaces=NAMESPACES):
		jpref = jpelem.get("id")
		[direction] = jpelem.xpath("./tx:Direction/text()", namespaces=NAMESPACES)
		routeref = maybe_one(jpelem.xpath("./tx:RouteRef/text()", namespaces=NAMESPACES))
		jpsectionrefs = jpelem.xpath("./tx:JourneyPatternSectionRefs/text()", namespaces=NAMESPACES)
		with conn.cursor() as cur:
			cur.execute("""
				INSERT INTO journeypattern_service(source, jpref, servicecode, routeref, direction)
				VALUES (%s, %s, %s, %s, %s)
				ON CONFLICT DO NOTHING
			""", (source, jpref, servicecode, routeref, direction))

			for jpsectionref in jpsectionrefs:
				cur.execute("""
					INSERT INTO journeypattern_service_section(source, jpref, jpsectionref)
					VALUES (%s, %s, %s)
					ON CONFLICT DO NOTHING
				""", (source, jpref, jpsectionref))

def add_journeypatternsection(conn, elem, source):
	jpsection_id = elem.get("id")
	for jptl in elem.xpath("./tx:JourneyPatternTimingLink", namespaces=NAMESPACES):
		jptiminglink_id = jptl.get("id")
		routelinkref_id = maybe_one(jptl.xpath("./tx:RouteLinkRef/text()", namespaces=NAMESPACES))
		[runtime] = jptl.xpath("./tx:RunTime/text()", namespaces=NAMESPACES)
		from_sequence = maybe_one(jptl.xpath("./tx:From/@SequenceNumber", namespaces=NAMESPACES))
		to_sequence = maybe_one(jptl.xpath("./tx:To/@SequenceNumber", namespaces=NAMESPACES))
		[from_stoppoint] = jptl.xpath("./tx:From/tx:StopPointRef/text()", namespaces=NAMESPACES)
		[to_stoppoint] = jptl.xpath("./tx:To/tx:StopPointRef/text()", namespaces=NAMESPACES)
		with conn.cursor() as cur:
			cur.execute("""
				INSERT INTO jptiminglink(source, jptiminglink, jpsection, routelinkref, runtime, from_sequence, from_stoppoint, to_sequence, to_stoppoint)
				VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
				ON CONFLICT DO NOTHING
			""", (source, jptiminglink_id, jpsection_id, routelinkref_id, runtime, from_sequence, from_stoppoint, to_sequence, to_stoppoint))

def add_vehiclejourney(conn, elem, source):
	[vjcode_id] = elem.xpath("./tx:VehicleJourneyCode/text()", namespaces=NAMESPACES)
	jpref_id = maybe_one(elem.xpath("./tx:JourneyPatternRef/text()", namespaces=NAMESPACES))
	[line_id] = elem.xpath("./tx:LineRef/text()", namespaces=NAMESPACES)
	privatecode = maybe_one(elem.xpath("./tx:PrivateCode/text()", namespaces=NAMESPACES))
	[departuretime] = elem.xpath("./tx:DepartureTime/text()", namespaces=NAMESPACES)

	MON = 1<<0
	TUE = 1<<1
	WED = 1<<2
	THUR = 1<<3
	FRI = 1<<4
	SAT = 1<<5
	SUN = 1<<6
	days_bitmask = 0
	for days in elem.xpath("./tx:OperatingProfile/tx:RegularDayType/tx:DaysOfWeek/*", namespaces=NAMESPACES):
		if days.tag == '{http://www.transxchange.org.uk/}MondayToFriday':
			days_bitmask |= MON|TUE|WED|THUR|FRI
		elif days.tag == '{http://www.transxchange.org.uk/}MondayToSaturday':
			days_bitmask |= MON|TUE|WED|THUR|FRI|SAT
		elif days.tag == '{http://www.transxchange.org.uk/}MondayToSunday':
			days_bitmask |= MON|TUE|WED|THUR|FRI|SAT|SUN
		elif days.tag == '{http://www.transxchange.org.uk/}Saturday':
			days_bitmask |= SAT
		elif days.tag == '{http://www.transxchange.org.uk/}Sunday':
			days_bitmask |= SUN
		elif days.tag == '{http://www.transxchange.org.uk/}Monday':
			days_bitmask |= MON
		elif days.tag == '{http://www.transxchange.org.uk/}Tuesday':
			days_bitmask |= TUE
		elif days.tag == '{http://www.transxchange.org.uk/}Wednesday':
			days_bitmask |= WED
		elif days.tag == '{http://www.transxchange.org.uk/}Thursday':
			days_bitmask |= THUR
		elif days.tag == '{http://www.transxchange.org.uk/}Friday':
			days_bitmask |= FRI
		else:
			raise ValueError(days.tag)


	departuretime_time = datetime.datetime.strptime(departuretime, "%H:%M:%S").time()
	departuretime_seconds = (departuretime_time.hour * 3600) + (departuretime_time.minute * 60) + departuretime_time.second

	with conn.cursor() as cur:
		cur.execute("""
			INSERT INTO vehiclejourney(source, vjcode, jpref, line_id, privatecode, days_mask, deptime, deptime_seconds)
			VALUES(%s, %s, %s, %s, %s, %s, %s, %s)
			ON CONFLICT DO NOTHING
		""", (source, vjcode_id, jpref_id, line_id, privatecode, days_bitmask, departuretime, departuretime_seconds))

def add_route(conn, elem, source):
	route_id = elem.get("id")
	privatecode = maybe_one(elem.xpath("./tx:PrivateCode/text()", namespaces=NAMESPACES))
	[description] = elem.xpath("./tx:Description/text()", namespaces=NAMESPACES)
	[routesection] = elem.xpath("./tx:RouteSectionRef/text()", namespaces=NAMESPACES)

	with conn.cursor() as cur:
		cur.execute("""
			INSERT INTO route(source, route_id, privatecode, routesection, description)
			VALUES (%s, %s, %s, %s, %s)
			ON CONFLICT DO NOTHING
		""", (source, route_id, privatecode, routesection, description,))

def add_routesection(conn, elem, source):
	routesection = elem.get("id")
	for linkelem in elem.xpath("./tx:RouteLink", namespaces=NAMESPACES):
		routelink = linkelem.get("id")
		[from_stoppoint] = linkelem.xpath("./tx:From/tx:StopPointRef/text()", namespaces=NAMESPACES)
		[to_stoppoint] = linkelem.xpath("./tx:To/tx:StopPointRef/text()", namespaces=NAMESPACES)
		[direction] = linkelem.xpath("./tx:Direction/text()", namespaces=NAMESPACES)

		with conn.cursor() as cur:
			cur.execute("""
				INSERT INTO routelink(source, routelink, routesection, from_stoppoint, to_stoppoint, direction)
				VALUES (%s, %s, %s, %s, %s, %s)
				ON CONFLICT DO NOTHING
			""", (source, routelink, routesection, from_stoppoint, to_stoppoint, direction,))

def maybe_one(many):
	if len(many) == 1:
		return many[0]
	if len(many) == 0:
		return None
	raise ValueError(many)

def add_stoppoint(conn, elem, source):
	[stoppoint] = elem.xpath("./tx:StopPointRef/text()", namespaces=NAMESPACES)
	[name] = elem.xpath("./tx:CommonName/text()", namespaces=NAMESPACES)
	indicator = maybe_one(elem.xpath("./tx:Indicator/text()", namespaces=NAMESPACES))
	locality_name = maybe_one(elem.xpath("./tx:LocalityName/text()", namespaces=NAMESPACES))
	locality_qualifier = maybe_one(elem.xpath("./tx:LocalityQualifier/text()", namespaces=NAMESPACES))
	with conn.cursor() as cur:
		cur.execute("""
			INSERT INTO stoppoint(source, stoppoint, name, indicator, locality_name, locality_qualifier)
			VALUES (%s, %s, %s, %s, %s, %s)
			ON CONFLICT DO NOTHING
		""", (source, stoppoint, name, indicator, locality_name, locality_qualifier,))

def create_tables(conn):
	with conn.cursor() as cur:
		cur.execute("""
			DROP TABLE IF EXISTS jptiminglink;
			""")
		cur.execute("""
			CREATE TABLE jptiminglink(
				source TEXT,
				jptiminglink TEXT PRIMARY KEY,
				jpsection TEXT,
				routelinkref TEXT,
				runtime TEXT,
				from_sequence INT,
				from_stoppoint TEXT,
				to_sequence INT,
				to_stoppoint TEXT);
			""")
		cur.execute("""
			DROP TABLE IF EXISTS vehiclejourney;
			""")
		cur.execute("""
			CREATE TABLE vehiclejourney(
				source TEXT,
				vjcode TEXT PRIMARY KEY,
				jpref TEXT,
				line_id TEXT,
				privatecode TEXT,
				days_mask INT,
				deptime TEXT,
				deptime_seconds INT);
			""")
		cur.execute("""
			DROP TABLE IF EXISTS service;
			""")
		cur.execute("""
			CREATE TABLE service(
				source TEXT,
				servicecode TEXT PRIMARY KEY,
				privatecode TEXT,
				mode TEXT,
				operator_id TEXT,
				description TEXT);
			""")
		cur.execute("""
			DROP TABLE IF EXISTS line;
			""")
		cur.execute("""
			CREATE TABLE line(
				source TEXT,
				line_id TEXT PRIMARY KEY,
				servicecode TEXT,
				line_name TEXT);
			""")
		cur.execute("""
			DROP TABLE IF EXISTS journeypattern_service;
			""")
		cur.execute("""
			CREATE TABLE journeypattern_service(
				source TEXT,
				jpref TEXT PRIMARY KEY,
				servicecode TEXT,
				routeref TEXT,
				direction TEXT);
			""")
		cur.execute("""
			DROP TABLE IF EXISTS journeypattern_service_section;
			""")
		cur.execute("""
			CREATE TABLE journeypattern_service_section(
				source TEXT,
				jpref TEXT,
				jpsectionref TEXT,
				PRIMARY KEY (jpref, jpsectionref));
			""")
		cur.execute("""
			DROP TABLE IF EXISTS operator;
			""")
		cur.execute("""
			CREATE TABLE operator(
				source TEXT,
				operator_id TEXT PRIMARY KEY,
				shortname TEXT);
			""")
		cur.execute("""
			DROP TABLE IF EXISTS route;
			""")
		cur.execute("""
			CREATE TABLE route(
				source TEXT,
				route_id TEXT PRIMARY KEY,
				privatecode TEXT,
				routesection TEXT,
				description TEXT);
			""")
		cur.execute("""
			DROP TABLE IF EXISTS routelink;
			""")
		cur.execute("""
			CREATE TABLE routelink(
				source TEXT,
				routelink TEXT PRIMARY KEY,
				routesection TEXT,
				from_stoppoint TEXT,
				to_stoppoint TEXT,
				direction TEXT);
			""")
		cur.execute("""
			DROP TABLE IF EXISTS stoppoint;
			""")
		cur.execute("""
			CREATE TABLE stoppoint(
				source TEXT,
				stoppoint TEXT PRIMARY KEY,
				name TEXT,
				indicator TEXT,
				locality_name TEXT,
				locality_qualifier TEXT);
			""")

PARSERS = {
	'Service': add_service,
	'VehicleJourney': add_vehiclejourney,
	'JourneyPatternSection': add_journeypatternsection,
	'Operator': add_operator,
	'AnnotatedStopPointRef': add_stoppoint,
	'RouteSection': add_routesection,
	'Route': add_route,
}

def main():
	args = parse_args()

	if args.destroy_create_tables:
		with database() as conn:
			create_tables(conn)

	if args.process:
		for zip_filename in list_zip_filenames():
			logging.info("Processing zip file %s...", zip_filename)
			process_zipfile(zip_filename)

def process_zipfile(zip_filename):
	with zipfile.ZipFile(zip_filename) as container:
		for contentname in container.namelist():
			source = zip_filename.split("/")[-1] + "/" + contentname
			with database() as conn:
				if not have_data_for_source(conn, source):
					with container.open(contentname) as f:
						try:
							process_xml_file(f, conn, source)
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


def parse_args():
	parser = argparse.ArgumentParser(prog='Process traveline data')
	parser.add_argument('--destroy_create_tables', help='Drop and re-create all the travelinedata tables', action="store_true", default=False)
	parser.add_argument('--process', help='import the data from the given zip file', action="store_true", default=False)

	return parser.parse_args()


def process_xml_file(f, conn, source):
	logging.info("Processing file %s", source)
	for tagname, elem in iter_elements(f):
		try:
			parser_func = PARSERS[tagname]
			parser_func(conn, elem, source)
		except Exception:
			logging.exception("error parsing element: %r %r", source, tagname)
			logging.info("detail: %s", etree.tostring(elem))
			raise # or return to ignore exceptions

def list_zip_filenames():
	return [
		"travelinedata/" + name
		for name in os.listdir("travelinedata/")
		if name.endswith(".zip")]

def iter_elements(f):
	parser = etree.XMLPullParser(events=("end",), no_network=True)
	while True:
		data = f.read(1024)
		if not data:
			break
		parser.feed(data)
		for action, elem in parser.read_events():
			tagname = elem.tag.split("}")[-1]
			if tagname in PARSERS.keys():
				yield tagname, elem
				cleanup(elem)
	parser.close()

def cleanup(element):
	element.clear()                 # clean up children
	while element.getprevious() is not None:
		del element.getparent()[0]  # clean up preceding siblings

if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	main()
