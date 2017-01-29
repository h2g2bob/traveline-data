#!/usr/bin/python3

import datetime
import logging

NAMESPACES = {
	"tx": "http://www.transxchange.org.uk/",
}

def maybe_one(many):
	if len(many) == 1:
		return many[0]
	if len(many) == 0:
		return None
	raise ValueError(many)

def add_operator(elem, conn, source):
	operator_id = elem.get("id")
	[shortname] = elem.xpath("./tx:OperatorShortName/text()", namespaces=NAMESPACES)
	with conn.cursor() as cur:
		cur.execute("""
			INSERT INTO operator(source, operator_id, shortname)
			VALUES (%s, %s, %s)
			ON CONFLICT DO NOTHING
		""", (source, operator_id, shortname,))


def add_service(elem, conn, source):
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
				INSERT INTO journeypattern_service(source, journeypattern, servicecode, route, direction)
				VALUES (%s, %s, %s, %s, %s)
				ON CONFLICT DO NOTHING
			""", (source, jpref, servicecode, routeref, direction))

			for jpsectionref in jpsectionrefs:
				cur.execute("""
					INSERT INTO journeypattern_service_section(source, journeypattern, jpsection)
					VALUES (%s, %s, %s)
					ON CONFLICT DO NOTHING
				""", (source, jpref, jpsectionref))

def add_journeypatternsection(elem, conn, source):
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
				INSERT INTO jptiminglink(source, jptiminglink, jpsection, routelink, runtime, from_sequence, from_stoppoint, to_sequence, to_stoppoint)
				VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
				ON CONFLICT DO NOTHING
			""", (source, jptiminglink_id, jpsection_id, routelinkref_id, runtime, from_sequence, from_stoppoint, to_sequence, to_stoppoint))

def add_vehiclejourney(elem, conn, source):
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
			INSERT INTO vehiclejourney(source, vjcode, journeypattern, line_id, privatecode, days_mask, deptime, deptime_seconds)
			VALUES(%s, %s, %s, %s, %s, %s, %s, %s)
			ON CONFLICT DO NOTHING
		""", (source, vjcode_id, jpref_id, line_id, privatecode, days_bitmask, departuretime, departuretime_seconds))

def add_route(elem, conn, source):
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

def add_routesection(elem, conn, source):
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

def add_stoppoint(elem, conn, source):
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
