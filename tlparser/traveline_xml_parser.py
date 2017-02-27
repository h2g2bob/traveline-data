#!/usr/bin/python3

import datetime
import logging
from .table_definitions import interned_journeypattern, interned_jpsection, interned_jptiminglink, interned_vjcode, interned_service, interned_line, interned_route, interned_routelink, id_from_actocode

NAMESPACES = {
	"tx": "http://www.transxchange.org.uk/",
}

def maybe_one(many):
	if len(many) == 1:
		return many[0]
	if len(many) == 0:
		return None
	raise ValueError(many)

def add_operator(elem, conn, source_id):
	operator_id = elem.get("id")
	[shortname] = elem.xpath("./tx:OperatorShortName/text()", namespaces=NAMESPACES)
	with conn.cursor() as cur:
		cur.execute("""
			INSERT INTO operator(source_id, operator_id, shortname)
			VALUES (%s, %s, %s)
			ON CONFLICT DO NOTHING
		""", (source_id, operator_id, shortname,))


def add_service(elem, conn, source_id):
	[servicecode] = elem.xpath("./tx:ServiceCode/text()", namespaces=NAMESPACES)
	privatecode = maybe_one(elem.xpath("./tx:PrivateCode/text()", namespaces=NAMESPACES))
	mode = maybe_one(elem.xpath("./tx:Mode/text()", namespaces=NAMESPACES))
	description = maybe_one(elem.xpath("./tx:Description/text()", namespaces=NAMESPACES))
	[operator] = elem.xpath("./tx:RegisteredOperatorRef/text()", namespaces=NAMESPACES)

	with conn.cursor() as cur:
		service_id = interned_service(conn, source_id, servicecode)
		cur.execute("""
			INSERT INTO service(source_id, service_id, privatecode, mode, operator_id, description)
			VALUES (%s, %s, %s, %s, %s, %s)
		""", (source_id, service_id, privatecode, mode, operator, description))

	for lineelem in elem.xpath("./tx:Lines/tx:Line", namespaces=NAMESPACES):
		linecode = lineelem.get("id")
		[line_name] = lineelem.xpath("./tx:LineName/text()", namespaces=NAMESPACES)	
		with conn.cursor() as cur:
			line_id = interned_line(conn, source_id, linecode)
			cur.execute("""
				INSERT INTO line(source_id, line_id, servicecode, line_name)
				VALUES (%s, %s, %s, %s)
			""", (source_id, line_id, servicecode, line_name))

	for jpelem in elem.xpath("./tx:StandardService/tx:JourneyPattern", namespaces=NAMESPACES):
		jpref = jpelem.get("id")
		[direction] = jpelem.xpath("./tx:Direction/text()", namespaces=NAMESPACES)
		routeref = maybe_one(jpelem.xpath("./tx:RouteRef/text()", namespaces=NAMESPACES))
		jpsectionrefs = jpelem.xpath("./tx:JourneyPatternSectionRefs/text()", namespaces=NAMESPACES)
		with conn.cursor() as cur:
			jpintern = interned_journeypattern(conn, source_id, jpref)
			routeintern = interned_route(conn, source_id, routeref) if routeref is not None else None
			cur.execute("""
				INSERT INTO journeypattern_service(source_id, journeypattern_id, service_id, route_id, direction)
				VALUES (%s, %s, %s, %s, %s)
			""", (source_id, jpintern, service_id, routeintern, direction))

			for jpsectionref in jpsectionrefs:
				jpsectionintern = interned_jpsection(conn, source_id, jpsectionref)
				cur.execute("""
					INSERT INTO journeypattern_service_section(source_id, jpsection_id, journeypattern_id)
					VALUES (%s, %s, %s)
				""", (source_id, jpsectionintern, jpintern))

def add_journeypatternsection(elem, conn, source_id):
	jpsection = elem.get("id")
	with conn.cursor() as cur:
		jpsectionintern = interned_jpsection(conn, source_id, jpsection)

	for jptl in elem.xpath("./tx:JourneyPatternTimingLink", namespaces=NAMESPACES):
		jptiminglink = jptl.get("id")
		routelinkref = maybe_one(jptl.xpath("./tx:RouteLinkRef/text()", namespaces=NAMESPACES))
		[runtime] = jptl.xpath("./tx:RunTime/text()", namespaces=NAMESPACES)
		from_sequence = maybe_one(jptl.xpath("./tx:From/@SequenceNumber", namespaces=NAMESPACES))
		to_sequence = maybe_one(jptl.xpath("./tx:To/@SequenceNumber", namespaces=NAMESPACES))
		[from_stoppoint] = jptl.xpath("./tx:From/tx:StopPointRef/text()", namespaces=NAMESPACES)
		[to_stoppoint] = jptl.xpath("./tx:To/tx:StopPointRef/text()", namespaces=NAMESPACES)
		with conn.cursor() as cur:
			jptiminglinkintern = interned_jptiminglink(conn, source_id, jptiminglink)
			routelinkintern = interned_routelink(conn, source_id, routelinkref) if routelinkref is not None else None
			from_stoppoint_id = id_from_actocode(conn, from_stoppoint)
			to_stoppoint_id = id_from_actocode(conn, to_stoppoint)
			cur.execute("""
				INSERT INTO jptiminglink(source_id, jptiminglink_id, jpsection_id, routelink_id, runtime, from_sequence, from_stoppoint, to_sequence, to_stoppoint)
				VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
			""", (source_id, jptiminglinkintern, jpsectionintern, routelinkintern, runtime, from_sequence, from_stoppoint_id, to_sequence, to_stoppoint_id))

def add_vehiclejourney(elem, conn, source_id):
	[vjcode] = elem.xpath("./tx:VehicleJourneyCode/text()", namespaces=NAMESPACES)

	# a vehiclejourney will either have a reference to a journeypattern...
	jpref_id = maybe_one(elem.xpath("./tx:JourneyPatternRef/text()", namespaces=NAMESPACES))
	# ... or a reference to another vehiclejourney (which hopefully has a reference to a journeypattern)
	other_vjcode = maybe_one(elem.xpath("./tx:VehicleJourneyRef/text()", namespaces=NAMESPACES))
	# (let's check this is really true...)
	assert (
		(other_vjcode is None and jpref_id is not None) or
		(other_vjcode == vjcode and jpref_id is not None) or
		(other_vjcode != vjcode and jpref_id is None))

	[linecode] = elem.xpath("./tx:LineRef/text()", namespaces=NAMESPACES)
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
		jpintern = interned_journeypattern(conn, source_id, jpref_id) if jpref_id is not None else None
		vjintern = interned_vjcode(conn, source_id, vjcode) if vjcode is not None else None
		lineintern = interned_line(conn, source_id, linecode)
		othervjintern = interned_vjcode(conn, source_id, other_vjcode) if other_vjcode is not None else None
		cur.execute("""
			INSERT INTO vehiclejourney(source_id, vjcode_id, other_vjcode_id, journeypattern_id, line_id, privatecode, days_mask, deptime, deptime_seconds)
			VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)
		""", (source_id, vjintern, othervjintern, jpintern, lineintern, privatecode, days_bitmask, departuretime, departuretime_seconds))

def add_route(elem, conn, source_id):
	routecode = elem.get("id")
	privatecode = maybe_one(elem.xpath("./tx:PrivateCode/text()", namespaces=NAMESPACES))
	[description] = elem.xpath("./tx:Description/text()", namespaces=NAMESPACES)
	[routesection] = elem.xpath("./tx:RouteSectionRef/text()", namespaces=NAMESPACES)

	with conn.cursor() as cur:
		route_id = interned_route(conn, source_id, routecode)
		cur.execute("""
			INSERT INTO route(source_id, route_id, privatecode, routesection, description)
			VALUES (%s, %s, %s, %s, %s)
		""", (source_id, route_id, privatecode, routesection, description,))

def add_routesection(elem, conn, source_id):
	routesection = elem.get("id")
	for linkelem in elem.xpath("./tx:RouteLink", namespaces=NAMESPACES):
		routelinkcode = linkelem.get("id")
		[from_stoppoint] = linkelem.xpath("./tx:From/tx:StopPointRef/text()", namespaces=NAMESPACES)
		[to_stoppoint] = linkelem.xpath("./tx:To/tx:StopPointRef/text()", namespaces=NAMESPACES)
		[direction] = linkelem.xpath("./tx:Direction/text()", namespaces=NAMESPACES)

		with conn.cursor() as cur:
			routelink_id = interned_routelink(conn, source_id, routelinkcode)
			from_stoppoint_id = id_from_actocode(conn, from_stoppoint)
			to_stoppoint_id = id_from_actocode(conn, to_stoppoint)
			cur.execute("""
				INSERT INTO routelink(source_id, routelink_id, routesection, from_stoppoint, to_stoppoint, direction)
				VALUES (%s, %s, %s, %s, %s, %s)
			""", (source_id, routelink_id, routesection, from_stoppoint_id, to_stoppoint_id, direction,))

def add_stoppoint(elem, conn, source_id):
	[stoppoint] = elem.xpath("./tx:StopPointRef/text()", namespaces=NAMESPACES)
	[name] = elem.xpath("./tx:CommonName/text()", namespaces=NAMESPACES)
	indicator = maybe_one(elem.xpath("./tx:Indicator/text()", namespaces=NAMESPACES))
	locality_name = maybe_one(elem.xpath("./tx:LocalityName/text()", namespaces=NAMESPACES))
	locality_qualifier = maybe_one(elem.xpath("./tx:LocalityQualifier/text()", namespaces=NAMESPACES))
	with conn.cursor() as cur:
		atcocode_id = id_from_actocode(conn, stoppoint)
		cur.execute("""
			INSERT INTO stoppoint(source_id, atcocode_id, name, indicator, locality_name, locality_qualifier)
			VALUES (%s, %s, %s, %s, %s, %s)
			ON CONFLICT DO NOTHING
		""", (source_id, atcocode_id, name, indicator, locality_name, locality_qualifier,))
