#!/usr/bin/python3
from lxml import etree
import zipfile
import logging

# Appears to be:
# <Place>
# 	<MainNptgLocalities>
#		<StopPoint>


def main():
	with zipfile.ZipFile("NaPTANxml.zip") as container:
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
						handle_stoppoint(elem)
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
		logging.info("float_content: %r", values)
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
		if elem.get("Status") != "active":
			return

		name = text_content(elem, ".//naptan:Descriptor/naptan:CommonName/text()")
		code = text_content(elem, ".//naptan:NaptanCode/text()")
		latitude = float_content(elem, ".//naptan:Latitude/text()")
		longitude = float_content(elem, ".//naptan:Longitude/text()")

		print(code, name, latitude, longitude)

	except Exception:
		logging.info('problem string %r', etree.tostring(elem))
		raise


if __name__ == '__main__':
	logging.basicConfig()
	main()
