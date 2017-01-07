#!/usr/bin/python3
from collections import defaultdict
from lxml import etree
import datetime
import logging
import sqlite3



def main():
	with sqlite3.connect("data.sqlite3", isolation_level="DEFERRED") as conn:
		create_tables(conn)
		analyze_data(conn)


def create_tables(conn):
	conn.execute("""
		DROP TABLE IF EXISTS vehiclejourney_per_hour;
	""")
	conn.execute("""
		CREATE TABLE vehiclejourney_per_hour(
			source TEXT,
			jpref TEXT,
			lineref TEXT,
			days_mask INT,
			hour_0 INT,
			hour_1 INT,
			hour_2 INT,
			hour_3 INT,
			hour_4 INT,
			hour_5 INT,
			hour_6 INT,
			hour_7 INT,
			hour_8 INT,
			hour_9 INT,
			hour_10 INT,
			hour_11 INT,
			hour_12 INT,
			hour_13 INT,
			hour_14 INT,
			hour_15 INT,
			hour_16 INT,
			hour_17 INT,
			hour_18 INT,
			hour_19 INT,
			hour_20 INT,
			hour_21 INT,
			hour_22 INT,
			hour_23 INT
		);
	""")

def analyze_data(conn):
	conn.execute("""
		INSERT INTO vehiclejourney_per_hour SELECT
			source,
			jpref,
			lineref,
			days_mask,
			sum(case when deptime_seconds / 3600 == 0 then 1 else 0 end) as hour_0,
			sum(case when deptime_seconds / 3600 == 1 then 1 else 0 end) as hour_1,
			sum(case when deptime_seconds / 3600 == 2 then 1 else 0 end) as hour_2,
			sum(case when deptime_seconds / 3600 == 3 then 1 else 0 end) as hour_3,
			sum(case when deptime_seconds / 3600 == 4 then 1 else 0 end) as hour_4,
			sum(case when deptime_seconds / 3600 == 5 then 1 else 0 end) as hour_5,
			sum(case when deptime_seconds / 3600 == 6 then 1 else 0 end) as hour_6,
			sum(case when deptime_seconds / 3600 == 7 then 1 else 0 end) as hour_7,
			sum(case when deptime_seconds / 3600 == 8 then 1 else 0 end) as hour_8,
			sum(case when deptime_seconds / 3600 == 9 then 1 else 0 end) as hour_9,
			sum(case when deptime_seconds / 3600 == 10 then 1 else 0 end) as hour_10,
			sum(case when deptime_seconds / 3600 == 11 then 1 else 0 end) as hour_11,
			sum(case when deptime_seconds / 3600 == 12 then 1 else 0 end) as hour_12,
			sum(case when deptime_seconds / 3600 == 13 then 1 else 0 end) as hour_13,
			sum(case when deptime_seconds / 3600 == 14 then 1 else 0 end) as hour_14,
			sum(case when deptime_seconds / 3600 == 15 then 1 else 0 end) as hour_15,
			sum(case when deptime_seconds / 3600 == 16 then 1 else 0 end) as hour_16,
			sum(case when deptime_seconds / 3600 == 17 then 1 else 0 end) as hour_17,
			sum(case when deptime_seconds / 3600 == 18 then 1 else 0 end) as hour_18,
			sum(case when deptime_seconds / 3600 == 19 then 1 else 0 end) as hour_19,
			sum(case when deptime_seconds / 3600 == 20 then 1 else 0 end) as hour_20,
			sum(case when deptime_seconds / 3600 == 21 then 1 else 0 end) as hour_21,
			sum(case when deptime_seconds / 3600 == 22 then 1 else 0 end) as hour_22,
			sum(case when deptime_seconds / 3600 == 23 then 1 else 0 end) as hour_23
		FROM vehiclejourney
		GROUP BY 1,2,3,4;
	""")



if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	main()
