#!/usr/bin/python3
#
# Daytime frequency of bus services between bus stop pairs:
#
#
# python3 print_mapping.py | zip > frequent.kmz
#
from collections import defaultdict
from lxml import etree
from xml.sax.saxutils import escape as xml_escape
import datetime
import logging
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
	with sqlite3.connect("data.sqlite3", isolation_level="DEFERRED") as conn:
		print_bus_stop_pair_frequency(conn)

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

def print_bus_stop_pair_frequency(conn):
	#
	# For a simple example of the number of buses between two stops:
	# sqlite> select days_mask, deptime from vehiclejourney vj where jpref in (select jpref from journeypattern_service where jpsectionref in (select jpsection from jptiminglink where from_stoppoint = '390030720' and to_stoppoint = '390030272'));
	#
	cur = conn.cursor()
	cur.execute("""
		select
			jptl.from_stoppoint,
			n_from.latitude as from_lat,
			n_from.longitude as from_long,
			jptl.to_stoppoint,
			n_to.latitude as to_lat,
			n_to.longitude as to_long,
			sum(hour_12) as daytime_busses_per_hour,
			count(distinct vjph.line_id) as different_lines,
			group_concat(distinct l.line_name) as line_names
		from jptiminglink jptl
		join journeypattern_service jps on jps.jpsectionref = jptl.jpsection
		join vehiclejourney_per_hour vjph on vjph.jpref = jps.jpref
		left join naptan n_from on n_from.atcocode = jptl.from_stoppoint
		left join naptan n_to on n_to.atcocode = jptl.to_stoppoint
		left join line l on vjph.line_id = l.line_id
		where days_mask & 1
		group by 1, 2, 3, 4, 5, 6;
	""")
	print(KML_DOCUMENT_TOP.format(name="Frequent services", description="Parts of bus routes on which many busses run during the daytime"))
	for from_code, from_lat, from_long, to_code, to_lat, to_long, daytime_busses_per_hour, different_lines, line_names in cur:
		if from_lat is None or to_lat is None:
			logging.warn("Missign lat/long from %r (%r) -> %r (%r)", from_code, from_lat, to_code, to_lat)
			continue
		style = get_style_name(daytime_busses_per_hour)
		if style:
			print(PLACEMARK.format(
				from_lat=from_lat,
				from_long=from_long,
				to_lat=to_lat,
				to_long=to_long,
				style=style,
				name=xml_escape("({} to {}) {} buses from: {}".format(from_code, to_code, daytime_busses_per_hour, line_names))))
	print(KML_DOCUMENT_BOTTOM)

if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	main()
