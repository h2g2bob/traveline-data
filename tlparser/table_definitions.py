#!/usr/bin/python3
# encoding: utf8

import logging

TABLE_COMMANDS = [
	("""
		DROP TABLE IF EXISTS source;
		""", """
		CREATE TABLE source(
			source_id SERIAL PRIMARY KEY,
			source TEXT UNIQUE)
		"""),
	("""
		DROP TABLE IF EXISTS journeypattern_intern;
		""", """
		CREATE TABLE IF NOT EXISTS journeypattern_intern (
			journeypattern_id SERIAL PRIMARY KEY,
			source_id INTEGER NOT NULL REFERENCES source(source_id),
			journeypattern TEXT NOT NULL,
			UNIQUE (source_id, journeypattern));
		"""),
	("""
		DROP TABLE IF EXISTS jpsection_intern;
		""", """
		CREATE TABLE IF NOT EXISTS jpsection_intern (
			jpsection_id SERIAL PRIMARY KEY,
			source_id INTEGER NOT NULL REFERENCES source(source_id),
			jpsection TEXT NOT NULL,
			UNIQUE (source_id, jpsection));
		"""),

	("""
		DROP TABLE IF EXISTS jptiminglink;
		""", """
		CREATE TABLE jptiminglink(
			source_id INT REFERENCES source(source_id),
			jptiminglink TEXT PRIMARY KEY,
			jpsection_id INT REFERENCES jpsection_intern(jpsection_id),
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
			other_vjcode TEXT,
			journeypattern_id INT REFERENCES journeypattern_intern(journeypattern_id),
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
			journeypattern_id INT PRIMARY KEY REFERENCES journeypattern_intern(journeypattern_id),
			servicecode TEXT,
			route TEXT,
			direction TEXT);
		"""),
	("""
		DROP TABLE IF EXISTS journeypattern_service_section;
		""", """
		CREATE TABLE journeypattern_service_section(
			source_id INT REFERENCES source(source_id),
			journeypattern_id INT REFERENCES journeypattern_intern(journeypattern_id),
			jpsection_id INT REFERENCES jpsection_intern(jpsection_id),
			PRIMARY KEY (journeypattern_id, jpsection_id));
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
		cur.execute("""
			CREATE INDEX idx_timing_section ON jptiminglink(jpsection_id);
		""")

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

		# https://www.postgresql.org/docs/current/static/functions-geometry.html
		# This query works along the lines of:
		# travelinedata=> select * from naptan where point(latitude, longitude) <@ box(point(51.48, -2.51), point(51.49, -2.50));
		cur.execute("""
			CREATE INDEX idx_naptan_point
			ON naptan
			USING gist (point(latitude, longitude));
		""")


def drop_materialized_views(conn):
	with conn.cursor() as cur:
		cur.execute("""
			DROP MATERIALIZED VIEW IF EXISTS mv_journeypattern_bounding_box;
			""")
		cur.execute("""
			DROP MATERIALIZED VIEW IF EXISTS mv_vehiclejourney_per_hour;
			""")

def refresh_materialized_views(conn):
	with conn.cursor() as cur:
		cur.execute("""
			REFRESH MATERIALIZED VIEW mv_vehiclejourney_per_hour;
			""")
		cur.execute("""
			REFRESH MATERIALIZED VIEW mv_journeypattern_bounding_box;
			""")

def create_materialized_views(conn):
	with conn.cursor() as cur:
		logging.info("Generating mv_vehiclejourney_per_hour...")
		cur.execute("""
			CREATE MATERIALIZED VIEW mv_vehiclejourney_per_hour AS
			SELECT
				coalesce(vj.journeypattern_id, other.journeypattern_id),
				vj.line_id,
				vj.days_mask,
				sum(case when vj.deptime_seconds / 3600 = 0 then 1 else 0 end) as hour_0,
				sum(case when vj.deptime_seconds / 3600 = 1 then 1 else 0 end) as hour_1,
				sum(case when vj.deptime_seconds / 3600 = 2 then 1 else 0 end) as hour_2,
				sum(case when vj.deptime_seconds / 3600 = 3 then 1 else 0 end) as hour_3,
				sum(case when vj.deptime_seconds / 3600 = 4 then 1 else 0 end) as hour_4,
				sum(case when vj.deptime_seconds / 3600 = 5 then 1 else 0 end) as hour_5,
				sum(case when vj.deptime_seconds / 3600 = 6 then 1 else 0 end) as hour_6,
				sum(case when vj.deptime_seconds / 3600 = 7 then 1 else 0 end) as hour_7,
				sum(case when vj.deptime_seconds / 3600 = 8 then 1 else 0 end) as hour_8,
				sum(case when vj.deptime_seconds / 3600 = 9 then 1 else 0 end) as hour_9,
				sum(case when vj.deptime_seconds / 3600 = 10 then 1 else 0 end) as hour_10,
				sum(case when vj.deptime_seconds / 3600 = 11 then 1 else 0 end) as hour_11,
				sum(case when vj.deptime_seconds / 3600 = 12 then 1 else 0 end) as hour_12,
				sum(case when vj.deptime_seconds / 3600 = 13 then 1 else 0 end) as hour_13,
				sum(case when vj.deptime_seconds / 3600 = 14 then 1 else 0 end) as hour_14,
				sum(case when vj.deptime_seconds / 3600 = 15 then 1 else 0 end) as hour_15,
				sum(case when vj.deptime_seconds / 3600 = 16 then 1 else 0 end) as hour_16,
				sum(case when vj.deptime_seconds / 3600 = 17 then 1 else 0 end) as hour_17,
				sum(case when vj.deptime_seconds / 3600 = 18 then 1 else 0 end) as hour_18,
				sum(case when vj.deptime_seconds / 3600 = 19 then 1 else 0 end) as hour_19,
				sum(case when vj.deptime_seconds / 3600 = 20 then 1 else 0 end) as hour_20,
				sum(case when vj.deptime_seconds / 3600 = 21 then 1 else 0 end) as hour_21,
				sum(case when vj.deptime_seconds / 3600 = 22 then 1 else 0 end) as hour_22,
				sum(case when vj.deptime_seconds / 3600 = 23 then 1 else 0 end) as hour_23
			FROM vehiclejourney vj
			LEFT JOIN vehiclejourney other ON vj.other_vjcode = other.vjcode
			GROUP BY 1,2,3;
		""")

		logging.info("Generating mv_journeypattern_bounding_box...")
		# Doing this the normal way will make you run out of disk space
		# So we force this to be a loop over each service
		cur.execute("""
			CREATE OR REPLACE FUNCTION fn_journeypattern_bounding_box()
			RETURNS TABLE (journeypattern_id int, bounding_box box)
			AS $$
				DECLARE service record;
				BEGIN
				    FOR service IN SELECT * FROM journeypattern_service
				    LOOP

					RETURN QUERY SELECT
						section.journeypattern_id,
						box(
							point(
								(select min(minlat) from (select min(n_from.latitude) as minlat union select min(n_to.latitude) as minlat) as tminlat),
								(select min(minlong) from (select min(n_from.longitude) as minlong union select min(n_to.longitude) as minlong) as tinlong)),
							point(
								(select max(maxlat) from (select max(n_from.latitude) as maxlat union select max(n_to.latitude) as maxlat) as tmaxlat),
								(select max(maxlong) from (select max(n_from.longitude) as maxlong union select max(n_to.longitude) as maxlong) as tmaxling))) AS bounding_box
					FROM jptiminglink timing
					JOIN journeypattern_service_section section USING (jpsection_id)
					JOIN naptan n_from ON n_from.atcocode = timing.from_stoppoint
					JOIN naptan n_to ON n_to.atcocode = timing.to_stoppoint
					WHERE section.journeypattern_id = service.journeypattern_id
					GROUP BY 1;

				    END LOOP;
				END$$
			LANGUAGE plpgsql;
		""")
		cur.execute("""
			CREATE MATERIALIZED VIEW mv_journeypattern_bounding_box
			AS SELECT * FROM fn_journeypattern_bounding_box();
		""")
		cur.execute("""
			CREATE INDEX idx_journeypattern_bounding_box
			ON mv_journeypattern_bounding_box
			USING gist (bounding_box);
		""")


def interned_journeypattern(conn, source_id, journeypattern):
	with conn.cursor() as cur:
		cur.execute("""
			SELECT journeypattern_id
			FROM journeypattern_intern
			WHERE source_id = %s
			AND journeypattern = %s
		""", (source_id, journeypattern,))
		rows = list(cur)
		if len(rows) == 0:
			cur.execute("""
				INSERT INTO journeypattern_intern(source_id, journeypattern)
				VALUES (%s, %s)
				RETURNING journeypattern_id
			""", (source_id, journeypattern,))
			rows = list(cur)
		[[jp_id]] = rows
		return jp_id

def interned_jpsection(conn, source_id, jpsection):
	with conn.cursor() as cur:
		cur.execute("""
			SELECT jpsection_id
			FROM jpsection_intern
			WHERE source_id = %s
			AND jpsection = %s
		""", (source_id, jpsection,))
		rows = list(cur)
		if len(rows) == 0:
			cur.execute("""
				INSERT INTO jpsection_intern(source_id, jpsection)
				VALUES (%s, %s)
				RETURNING jpsection_id
			""", (source_id, jpsection,))
			rows = list(cur)
		[[jps_id]] = rows
		return jps_id
