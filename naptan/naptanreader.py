#!/usr/bin/python3
from lxml import etree
import zipfile

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

def avg(values):
	values = tuple(values)
	return sum(values) / len(values)

def xpath(elem, path):
	return elem.xpath(path, namespaces={"naptan": "http://www.naptan.org.uk/"}, smart_strings=False)

def maybe_content(elem, path):
	values = xpath(elem, path)
	if len(values) == 1:
		return values[0]
	elif len(values) == 0:
		return None
	else:
		raise ValueError(values)

def handle_stoppoint(elem):
	try:
		if elem.get("Status") != "active":
			return

		name = maybe_content(elem, ".//naptan:Descriptor/naptan:CommonName/text()")
		code = maybe_content(elem, ".//naptan:NaptanCode/text()")
		latitude = avg(float(x) for x in xpath(elem, ".//naptan:Latitude/text()"))
		longitude = avg(float(x) for x in xpath(elem, ".//naptan:Longitude/text()"))

		print(code, name, latitude, longitude)

	except Exception:
		print(etree.tostring(elem))
		raise


if __name__ == '__main__':
	main()
