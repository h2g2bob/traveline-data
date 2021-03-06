#!/usr/bin/python3
from .table_definitions import interned_atcocode
from lxml import etree
import logging
import zipfile

# Appears to be:
# <Place>
# 	<MainNptgLocalities>
#		<StopPoint>


def process_all_files(conn):
	with conn.cursor() as cur:
		for code, atcocode, name, latitude, longitude in get_datapoints_from_xml():
			atcocode_id = interned_atcocode(conn, atcocode)
			cur.execute("""
				INSERT INTO naptan (atcocode_id, code, name, latitude, longitude)
				VALUES (%s, %s, %s, %s, %s);
			""", (atcocode_id, code, name, latitude, longitude,))

def get_datapoints_from_xml():
	with zipfile.ZipFile("naptandata/NaPTANxml.zip") as container:
		[contentname] = container.namelist()
		with container.open(contentname) as f:
			parser = etree.XMLPullParser(events=("end",), no_network=True)
			while True:
				data = f.read(1024)
				if not data:
					break
				parser.feed(data)
				for action, elem in parser.read_events():
					if elem.tag.endswith('StopPoint'):
						if elem.get("Status") == "active":
							yield handle_stoppoint(elem)
						cleanup(elem)

def cleanup(element):
	element.clear()                 # clean up children
	while element.getprevious() is not None:
		del element.getparent()[0]  # clean up preceding siblings

def xpath(elem, path):
	return elem.xpath(path, namespaces={"naptan": "http://www.naptan.org.uk/"}, smart_strings=False)

def float_content(elem, path):
	values = xpath(elem, path)
	if len(values) == 1:
		return float(values[0])
	elif len(values) == 0:
		return None
	else:
		logging.debug("file contains multiple values for location, averaging: %r", values)
		return sum(float(x) for x in values) / len(values)

def text_content(elem, path):
	values = xpath(elem, path)
	if len(values) == 1:
		return values[0]
	elif len(values) == 0:
		return None
	else:
		logging.info("text_content: %r", values)
		return "".join(path)

def handle_stoppoint(elem):
	try:
		name = text_content(elem, ".//naptan:Descriptor/naptan:CommonName/text()")
		code = text_content(elem, ".//naptan:NaptanCode/text()")
		atcocode = text_content(elem, ".//naptan:AtcoCode/text()")
		latitude = float_content(elem, ".//naptan:Latitude/text()")
		longitude = float_content(elem, ".//naptan:Longitude/text()")

		return (code, atcocode, name, latitude, longitude)

	except Exception:
		logging.info('problem string %r', etree.tostring(elem))
		raise


if __name__ == '__main__':
	logging.basicConfig()
	main()
