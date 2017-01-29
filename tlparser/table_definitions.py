#!/usr/bin/python3
# encoding: utf8

TABLE_COMMANDS = [
	("""
		DROP TABLE IF EXISTS source;
		""", """
		CREATE TABLE source(
			source_id SERIAL PRIMARY KEY,
			source TEXT UNIQUE)
		"""),
	("""
		DROP TABLE IF EXISTS jptiminglink;
		""", """
		CREATE TABLE jptiminglink(
			source_id INT REFERENCES source(source_id),
			jptiminglink TEXT PRIMARY KEY,
			jpsection TEXT,
			routelink TEXT,
			runtime TEXT,
			from_sequence INT,
			from_stoppoint TEXT,
			to_sequence INT,
			to_stoppoint TEXT);
		"""),
	("""
		DROP TABLE IF EXISTS vehiclejourney;
		""", """
		CREATE TABLE vehiclejourney(
			source_id INT REFERENCES source(source_id),
			vjcode TEXT PRIMARY KEY,
			journeypattern TEXT,
			line_id TEXT,
			privatecode TEXT,
			days_mask INT,
			deptime TEXT,
			deptime_seconds INT);
		"""),
	("""
		DROP TABLE IF EXISTS service;
		""", """
		CREATE TABLE service(
			source_id INT REFERENCES source(source_id),
			servicecode TEXT PRIMARY KEY,
			privatecode TEXT,
			mode TEXT,
			operator_id TEXT,
			description TEXT);
		"""),
	("""
		DROP TABLE IF EXISTS line;
		""", """
		CREATE TABLE line(
			source_id INT REFERENCES source(source_id),
			line_id TEXT PRIMARY KEY,
			servicecode TEXT,
			line_name TEXT);
		"""),
	("""
		DROP TABLE IF EXISTS journeypattern_service;
		""", """
		CREATE TABLE journeypattern_service(
			source_id INT REFERENCES source(source_id),
			journeypattern TEXT PRIMARY KEY,
			servicecode TEXT,
			route TEXT,
			direction TEXT);
		"""),
	("""
		DROP TABLE IF EXISTS journeypattern_service_section;
		""", """
		CREATE TABLE journeypattern_service_section(
			source_id INT REFERENCES source(source_id),
			journeypattern TEXT,
			jpsection TEXT,
			PRIMARY KEY (journeypattern, jpsection));
		"""),
	("""
		DROP TABLE IF EXISTS operator;
		""", """
		CREATE TABLE operator(
			source_id INT REFERENCES source(source_id),
			operator_id TEXT PRIMARY KEY,
			shortname TEXT);
		"""),
	("""
		DROP TABLE IF EXISTS route;
		""", """
		CREATE TABLE route(
			source_id INT REFERENCES source(source_id),
			route_id TEXT PRIMARY KEY,
			privatecode TEXT,
			routesection TEXT,
			description TEXT);
		"""),
	("""
		DROP TABLE IF EXISTS routelink;
		""", """
		CREATE TABLE routelink(
			source_id INT REFERENCES source(source_id),
			routelink TEXT PRIMARY KEY,
			routesection TEXT,
			from_stoppoint TEXT,
			to_stoppoint TEXT,
			direction TEXT);
		"""),
	("""
		DROP TABLE IF EXISTS stoppoint;
		""", """
		CREATE TABLE stoppoint(
			source_id INT REFERENCES source(source_id),
			stoppoint TEXT PRIMARY KEY,
			name TEXT,
			indicator TEXT,
			locality_name TEXT,
			locality_qualifier TEXT);
		""")]

def create_tables(conn):
	with conn.cursor() as cur:
		for drop, _ in reversed(TABLE_COMMANDS):
			cur.execute(drop)
		for _, create in TABLE_COMMANDS:
			cur.execute(create)

def create_naptan_tables(conn):
	with conn.cursor() as cur:
		cur.execute("""
			DROP TABLE IF EXISTS naptan;
		""")
		cur.execute("""
			CREATE TABLE naptan (
				atcocode TEXT PRIMARY KEY,
				code TEXT UNIQUE,
				name TEXT,
				latitude REAL,
				longitude REAL)
		""")

def drop_materialized_views(conn):
	with conn.cursor() as cur:
		cur.execute("""
			DROP MATERIALIZED VIEW IF EXISTS mv_vehiclejourney_per_hour;
			""")

def refresh_materialized_views(conn):
	with conn.cursor() as cur:
		cur.execute("""
			REFRESH MATERIALIZED VIEW mv_vehiclejourney_per_hour;
			""")

def create_materialized_views(conn):
	with conn.cursor() as cur:
		cur.execute("""
			CREATE MATERIALIZED VIEW mv_vehiclejourney_per_hour AS
			SELECT
				journeypattern,
				line_id,
				days_mask,
				sum(case when deptime_seconds / 3600 = 0 then 1 else 0 end) as hour_0,
				sum(case when deptime_seconds / 3600 = 1 then 1 else 0 end) as hour_1,
				sum(case when deptime_seconds / 3600 = 2 then 1 else 0 end) as hour_2,
				sum(case when deptime_seconds / 3600 = 3 then 1 else 0 end) as hour_3,
				sum(case when deptime_seconds / 3600 = 4 then 1 else 0 end) as hour_4,
				sum(case when deptime_seconds / 3600 = 5 then 1 else 0 end) as hour_5,
				sum(case when deptime_seconds / 3600 = 6 then 1 else 0 end) as hour_6,
				sum(case when deptime_seconds / 3600 = 7 then 1 else 0 end) as hour_7,
				sum(case when deptime_seconds / 3600 = 8 then 1 else 0 end) as hour_8,
				sum(case when deptime_seconds / 3600 = 9 then 1 else 0 end) as hour_9,
				sum(case when deptime_seconds / 3600 = 10 then 1 else 0 end) as hour_10,
				sum(case when deptime_seconds / 3600 = 11 then 1 else 0 end) as hour_11,
				sum(case when deptime_seconds / 3600 = 12 then 1 else 0 end) as hour_12,
				sum(case when deptime_seconds / 3600 = 13 then 1 else 0 end) as hour_13,
				sum(case when deptime_seconds / 3600 = 14 then 1 else 0 end) as hour_14,
				sum(case when deptime_seconds / 3600 = 15 then 1 else 0 end) as hour_15,
				sum(case when deptime_seconds / 3600 = 16 then 1 else 0 end) as hour_16,
				sum(case when deptime_seconds / 3600 = 17 then 1 else 0 end) as hour_17,
				sum(case when deptime_seconds / 3600 = 18 then 1 else 0 end) as hour_18,
				sum(case when deptime_seconds / 3600 = 19 then 1 else 0 end) as hour_19,
				sum(case when deptime_seconds / 3600 = 20 then 1 else 0 end) as hour_20,
				sum(case when deptime_seconds / 3600 = 21 then 1 else 0 end) as hour_21,
				sum(case when deptime_seconds / 3600 = 22 then 1 else 0 end) as hour_22,
				sum(case when deptime_seconds / 3600 = 23 then 1 else 0 end) as hour_23
			FROM vehiclejourney
			GROUP BY 1,2,3;
		""")
