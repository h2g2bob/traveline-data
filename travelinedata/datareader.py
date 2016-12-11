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



def main():
	for contentname, tagname, elem in iter_elements():
		logging.info("got element: %r %r", contentname, tagname)
		logging.debug("detail: %s", etree.tostring(elem))

def iter_elements():
	with zipfile.ZipFile("EA.zip") as container:
		for contentname in container.namelist():
			with container.open(contentname) as f:
				parser = etree.XMLPullParser(events=("end",), no_network=True)
				while True:
					data = f.read(1024)
					if not data:
						break
					parser.feed(data)
					for action, elem in parser.read_events():
						tagname = elem.tag.split("}")[-1]
						if tagname in {"AnnotatedStopPointRef", "RouteSection", "Route", "JourneyPatternSection", "Operator", "Service", "VehicleJourney"}:
							yield contentname, tagname, elem
							cleanup(elem)
				parser.close()

def cleanup(element):
	element.clear()                 # clean up children
	while element.getprevious() is not None:
		del element.getparent()[0]  # clean up preceding siblings

if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	main()
