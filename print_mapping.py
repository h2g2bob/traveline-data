#!/usr/bin/python3
#
# Daytime frequency of bus services between bus stop pairs:
#
#
# python3 print_mapping.py | zip -9 > frequent.kmz
#
#
# ... but google maps can only show about 15,000 line segents, so we need to do something about that
# solution:
# round to one decimal place: round(naptan.*, 1)
# but that's also inconvenient. With the intermediate table we could keep querying for the displayed bounding box instead??
#




from collections import defaultdict
from lxml import etree
from xml.sax.saxutils import escape as xml_escape
import datetime
import logging
import os
import random
import sqlite3


KML_DOCUMENT_TOP = """
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{name}</name>
    <description>{description}</description>

    <Style id="Excellent">
      <LineStyle>
        <color>ff0000ff</color>
        <width>4</width>
      </LineStyle>
    </Style>

    <Style id="VeryGood">
      <LineStyle>
        <color>ff0033ff</color>
        <width>3</width>
      </LineStyle>
    </Style>

    <Style id="Good">
      <LineStyle>
        <color>ff0066ff</color>
        <width>3</width>
      </LineStyle>
    </Style>

    <Style id="Poor">
      <LineStyle>
        <color>ff0099ff</color>
        <width>2</width>
      </LineStyle>
    </Style>

    <Style id="VeryPoor">
      <LineStyle>
        <color>ff00ccff</color>
        <width>2</width>
      </LineStyle>
    </Style>

    <Style id="Awful">
      <LineStyle>
        <color>ff00ffff</color>
        <width>1</width>
      </LineStyle>
    </Style>
"""

KML_DOCUMENT_BOTTOM = """
  </Document>
</kml>
"""

PLACEMARK = """
    <Placemark>
      <styleUrl>#{style}</styleUrl>
      <name>{name}</name>
      <LineString>
        <altitudeMode>relative</altitudeMode>
        <coordinates>
		{from_long},{from_lat},0
		{to_long},{to_lat},0
        </coordinates>
      </LineString>
    </Placemark>
"""

def main():
	REGENERATE = False

	if REGENERATE:
		with sqlite3.connect("data.sqlite3", isolation_level="DEFERRED") as conn:
			logging.info("Generating source data table")
			regenerate_bus_stop_pair_frequency(conn)
			conn.commit()

	with sqlite3.connect("data.sqlite3", isolation_level="DEFERRED") as conn:
		bounding_boxes = list(uk_bounding_boxes())
		random.shuffle(bounding_boxes)
		for minlat, maxlat, minlng, maxlng in bounding_boxes:
			filename = 'kmlfiles/frequent_service_{:.1f}_{:.1f}.kml'.format(minlat, minlng)
			logging.info("Making file %s", filename)
			try:
				with open(filename, 'w') as outf:
					print_bus_stop_pair_frequency(conn, outf, minlat-0.1, maxlat+0.1, minlng-0.1, maxlng+0.1)
			except:
				os.unlink(filename)
				raise

def get_style_name(bph):
	if bph >= 10:
		return 'Excellent'
	elif bph >= 9:
		return 'VeryGood'
	elif bph >= 8:
		return 'Good'
	elif bph >= 7:
		return 'Poor'
	elif bph >= 6:
		return 'VeryPoor'
	elif bph >= 4:
		return 'Awful'
	else:
		return None

def regenerate_bus_stop_pair_frequency(conn):
	conn.execute("""
		drop table if exists bus_stop_pair_frequency;
		""")
	conn.execute("""
		create table bus_stop_pair_frequency(
			from_stoppoint text,
			from_lat int,
			from_long int,
			to_stoppoint text,
			to_lat int,
			to_long int,
			days_mask int,
			daytime_busses_per_hour int,
			line_names int);
		""")
	conn.execute("""
		insert into bus_stop_pair_frequency
		select
			jptl.from_stoppoint,
			n_from.latitude as from_lat,
			n_from.longitude as from_long,
			jptl.to_stoppoint,
			n_to.latitude as to_lat,
			n_to.longitude as to_long,
			days_mask,
			sum(hour_12) as daytime_busses_per_hour,
			group_concat(distinct l.line_name) as line_names
		from jptiminglink jptl
		join journeypattern_service jps on jps.jpsectionref = jptl.jpsection
		join vehiclejourney_per_hour vjph on vjph.jpref = jps.jpref
		left join naptan n_from on n_from.atcocode = jptl.from_stoppoint
		left join naptan n_to on n_to.atcocode = jptl.to_stoppoint
		left join line l on vjph.line_id = l.line_id
		group by 1, 2, 3, 4, 5, 6, 7;
	""")

def print_bus_stop_pair_frequency(conn, outf, minlat, maxlat, minlng, maxlng):
	#
	# For a simple example of the number of buses between two stops:
	# sqlite> select days_mask, deptime from vehiclejourney vj where jpref in (select jpref from journeypattern_service where jpsectionref in (select jpsection from jptiminglink where from_stoppoint = '390030720' and to_stoppoint = '390030272'));
	#
	cur = conn.cursor()
	cur.execute("""
		select
			from_stoppoint,
			from_lat,
			from_long,
			to_stoppoint,
			to_lat,
			to_long,
			sum(daytime_busses_per_hour),
			group_concat(line_names)
		from bus_stop_pair_frequency
		where days_mask & 1
		and (
			(from_lat between ? and ? and from_long between ? and ?)
			or (to_lat between ? and ? and to_long between ? and ?))
		group by 1, 2, 3, 4, 5, 6;
	""", (minlat, maxlat, minlng, maxlng, minlat, maxlat, minlng, maxlng))
	outf.write(KML_DOCUMENT_TOP.format(name="Frequent services", description="Parts of bus routes on which many busses run during the daytime"))
	for from_code, from_lat, from_long, to_code, to_lat, to_long, daytime_busses_per_hour, line_names in cur:
		line_names = ', '.join(sorted(set(line_names.split(','))))
		if from_lat is None or to_lat is None:
			logging.warn("Missign lat/long from %r (%r) -> %r (%r)", from_code, from_lat, to_code, to_lat)
			continue
		style = get_style_name(daytime_busses_per_hour)
		if style:
			outf.write(PLACEMARK.format(
				from_lat=from_lat,
				from_long=from_long,
				to_lat=to_lat,
				to_long=to_long,
				style=style,
				name=xml_escape("({} to {}) {} buses from: {}".format(from_code, to_code, daytime_busses_per_hour, line_names))))
	outf.write(KML_DOCUMENT_BOTTOM)

def uk_bounding_boxes():
	# sqlite> select max(latitude), min(latitude), max(longitude), min(longitude) from naptan;
	# max(latitude)   min(latitude)   max(longitude)  min(longitude)
	# --------------  --------------  --------------  --------------
	# 60.80901968737  49.89601188695  1.75900859376   -7.54355920783
	for lat10 in range(498, 609):
		lat = lat10/10.0
		for lng10 in range(-75, 18):
			lng = lng10/10.0
			yield (lat, lat+0.1, lng, lng+0.1)

if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	main()
