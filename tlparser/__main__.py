#!/usr/bin/python3
import argparse
import psycopg2
import logging

from .table_definitions import create_tables, drop_materialized_views, create_materialized_views, refresh_materialized_views, update_all_journeypattern_boundingbox
from . import naptan_file_parser
from . import traveline_file_parser
from . import codepoint_parser

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
		with psycopg2.connect(args.database) as conn:
			drop_materialized_views(conn)
			create_tables(conn)
			create_materialized_views(conn)

	if args.naptan:
		with psycopg2.connect(args.database) as conn:
			naptan_file_parser.process_all_files(conn)

	if args.codepoint:
		with psycopg2.connect(args.database) as conn:
			codepoint_parser.process_all(conn)

	if args.process:
		conn = psycopg2.connect(args.database)
		traveline_file_parser.process_all_files(conn, args=args)
	elif args.process_test_data:
		conn = psycopg2.connect(args.database)
		traveline_file_parser.process_all_files(conn, test_data_only=True, args=args)

	if args.generate:
		with psycopg2.connect(args.database) as conn:
			update_all_journeypattern_boundingbox(conn)

	if args.matview:
		with psycopg2.connect(args.database) as conn:
			refresh_materialized_views(conn)



def parse_args():
	parser = argparse.ArgumentParser(prog='Process traveline data')
	parser.add_argument('--destroy_create_tables', help='Drop and re-create all the travelinedata tables', action="store_true", default=False)
	parser.add_argument('--naptan', help='import the data from naptan', action="store_true", default=False)
	parser.add_argument('--codepoint', help='import codepoint (postcode) data', action="store_true", default=False)
	parser.add_argument('--process', help='import the data from the given zip file', action="store_true", default=False)
	parser.add_argument('--process-test-data', help='import a small subset of travelinedata', action="store_true", dest="process_test_data", default=False)
	parser.add_argument('--generate', help='generate a table used as an index', action="store_true", default=False)
	parser.add_argument('--matview', help='refresh materialized views', action="store_true", default=False)
	parser.add_argument('--database', help='databse location', default="dbname=travelinedata")
	parser.add_argument('--target-week', dest="monday_of_desired_week", help='the dataset includes data for many weeks, but you should pick one. This value should be a monday', required=False)

	return parser.parse_args()



if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	main()
