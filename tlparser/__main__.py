#!/usr/bin/python3
import argparse
import psycopg2
import logging

from .table_definitions import create_tables, create_naptan_tables, drop_materialized_views, create_materialized_views, refresh_materialized_views
from . import naptan_file_parser
from . import traveline_file_parser

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

	if args.naptan:
		with psycopg2.connect(args.database) as conn:
			create_naptan_tables(conn)
			naptan_file_parser.process_all_files(conn)

	if args.destroy_create_tables:
		with psycopg2.connect(args.database) as conn:
			drop_materialized_views(conn)
			create_tables(conn)
			create_materialized_views(conn)

	if args.process:
		conn = psycopg2.connect(args.database)
		traveline_file_parser.process_all_files(conn)

	if args.matview:
		with psycopg2.connect(args.database) as conn:
			refresh_materialized_views(conn)



def parse_args():
	parser = argparse.ArgumentParser(prog='Process traveline data')
	parser.add_argument('--naptan', help='import the data from naptan', action="store_true", default=False)
	parser.add_argument('--destroy_create_tables', help='Drop and re-create all the travelinedata tables', action="store_true", default=False)
	parser.add_argument('--process', help='import the data from the given zip file', action="store_true", default=False)
	parser.add_argument('--matview', help='refresh materialized views', action="store_true", default=False)
	parser.add_argument('--database', help='databse location', default="dbname=travelinedata")

	return parser.parse_args()



if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	main()
