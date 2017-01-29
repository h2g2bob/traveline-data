#!/usr/bin/python3
import argparse
import logging

from .table_definitions import database, create_tables, drop_materialized_views, create_materialized_views, refresh_materialized_views
from .traveline_file_parser import process_all_files

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
# sqlite> select lineref, journeypattern, deptime_seconds/3600 as hour, count(1) from vehiclejourney where days_mask & 1 group by 1,2,3 order by 4;


def main():
	args = parse_args()

	if args.destroy_create_tables:
		with database() as conn:
			drop_materialized_views(conn)
			create_tables(conn)
			create_materialized_views(conn)

	if args.process:
		process_all_files()

	if args.matview:
		with database() as conn:
			refresh_materialized_views(conn)





def parse_args():
	parser = argparse.ArgumentParser(prog='Process traveline data')
	parser.add_argument('--destroy_create_tables', help='Drop and re-create all the travelinedata tables', action="store_true", default=False)
	parser.add_argument('--process', help='import the data from the given zip file', action="store_true", default=False)
	parser.add_argument('--matview', help='refresh materialized views', action="store_true", default=False)

	return parser.parse_args()



if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	main()
