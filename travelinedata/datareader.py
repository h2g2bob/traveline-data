#!/usr/bin/python3
from lxml import etree
import zipfile
import logging

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

NAMESPACES = {
	"tx": "http://www.transxchange.org.uk/",
}

class JPSection():
	def __init__(self, jpsection_id):
		self.jpsection_id = jpsection_id
		self.departures = []

class FileData():
	def __init__(self):
		self.jpsections = {}
		self.jp_to_jps = {}
		self.line_name = None
		self.description_name = None

	def add_service(self, elem):
		[lineelem] = elem.xpath(".//tx:Lines/tx:Line/tx:LineName", namespaces=NAMESPACES)
		self.line_name = str(lineelem.text)

		[descriptionelem] = elem.xpath(".//tx:Description", namespaces=NAMESPACES)
		self.description_name = str(descriptionelem.text)


		for jpelem in elem.xpath(".//tx:JourneyPattern", namespaces=NAMESPACES):
			jpref = jpelem.get("id")

			for jpsectionelem in jpelem.xpath("./tx:JourneyPatternSectionRefs", namespaces=NAMESPACES):
				jpsectionref = str(jpsectionelem.text)
				self.jp_to_jps.setdefault(jpref, []).append(jpsectionref)

	def add_journeypatternsection(self, elem):
		jpsection_id = str(elem.get("id"))
		jpsection = JPSection(jpsection_id)
		self.jpsections[jpsection.jpsection_id] = jpsection

	def add_vehiclejourney(self, elem):
		[journeypatternrefelem] = elem.xpath(".//tx:JourneyPatternRef", namespaces=NAMESPACES)
		jpref = str(journeypatternrefelem.text)

		[departuretimeelem] = elem.xpath(".//tx:DepartureTime", namespaces=NAMESPACES)
		dtime = str(departuretimeelem.text)

		for jpsectionref in self.jp_to_jps[jpref]:
			jpsection = self.jpsections[jpsectionref]
			jpsection.departures.append(dtime)



def main():
	for contentname, f in iter_files():
		process_file(contentname, f)

def process_file(contentname, f):
	filedata = FileData()

	for tagname, elem in iter_elements(f):
		try:
			if tagname == 'Service':
				filedata.add_service(elem)
			elif tagname == 'VehicleJourney':
				filedata.add_vehiclejourney(elem)
			elif tagname == 'JourneyPatternSection':
				filedata.add_journeypatternsection(elem)
			else:
				pass
		except Exception:
			logging.info("got element: %r %r", contentname, tagname)
			logging.info("detail: %s", etree.tostring(elem))
			raise

	logging.info("name=%r description=%r", filedata.line_name, filedata.description_name)
	logging.info("sections=%r", [(jps, len(jps.departures)) for jps in filedata.jpsections.values()])

	raise Exception("END")

def iter_files():
	with zipfile.ZipFile("EA.zip") as container:
		for contentname in container.namelist():
			with container.open(contentname) as f:
				yield contentname, f

def iter_elements(f):
	parser = etree.XMLPullParser(events=("end",), no_network=True)
	while True:
		data = f.read(1024)
		if not data:
			break
		parser.feed(data)
		for action, elem in parser.read_events():
			tagname = elem.tag.split("}")[-1]
			if tagname in {"AnnotatedStopPointRef", "RouteSection", "Route", "JourneyPatternSection", "Operator", "Service", "VehicleJourney"}:
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
