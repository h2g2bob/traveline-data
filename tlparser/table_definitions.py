#!/usr/bin/python3
# encoding: utf8

import logging

def _table_command_intern(tablename):
	return ("""
		DROP TABLE IF EXISTS %(tablename)s_intern;
		""" % dict(tablename=tablename), """
		CREATE TABLE IF NOT EXISTS %(tablename)s_intern (
			%(tablename)s_id SERIAL PRIMARY KEY,
			source_id INTEGER NOT NULL REFERENCES source(source_id),
			%(tablename)s TEXT NOT NULL,
			UNIQUE (source_id, %(tablename)s));
		""" % dict(tablename=tablename))

TABLE_COMMANDS = [
	("""
		DROP TABLE IF EXISTS source;
		""", """
		CREATE TABLE source(
			source_id SERIAL PRIMARY KEY,
			source TEXT UNIQUE)
		"""),

	_table_command_intern("journeypattern"),
	_table_command_intern("jpsection"),
	_table_command_intern("jptiminglink"),
	_table_command_intern("vjcode"),
	_table_command_intern("line"),
	_table_command_intern("service"),
	_table_command_intern("route"),
	_table_command_intern("routelink"),

	("""
		DROP TABLE IF EXISTS naptan;
		""", """
		CREATE TABLE naptan (
			atcocode_id SERIAL PRIMARY KEY,
			atcocode TEXT UNIQUE,
			code TEXT UNIQUE,
			name TEXT,
			latitude REAL,
			longitude REAL)
		"""),
	("""
		DROP TABLE IF EXISTS routelink CASCADE;
		""", """
		CREATE TABLE routelink(
			source_id INT REFERENCES source(source_id),
			routelink_id INT PRIMARY KEY REFERENCES routelink_intern(routelink_id),
			routesection TEXT,
			from_stoppoint INT REFERENCES stoppoint(atcocode_id),
			to_stoppoint INT REFERENCES stoppoint(atcocode_id),
			direction TEXT);
		"""),
	("""
		DROP TABLE IF EXISTS service CASCADE;
		""", """
		CREATE TABLE service(
			source_id INT REFERENCES source(source_id),
			service_id INT PRIMARY KEY REFERENCES service_intern(service_id),
			privatecode TEXT,
			mode TEXT,
			operator_id TEXT,
			description TEXT);
		"""),
	("""
		DROP TABLE IF EXISTS route CASCADE;
		""", """
		CREATE TABLE route(
			source_id INT REFERENCES source(source_id),
			route_id INT PRIMARY KEY REFERENCES route_intern(route_id),
			privatecode TEXT,
			routesection TEXT,
			description TEXT);
		"""),
	("""
		DROP TABLE IF EXISTS journeypattern_service CASCADE;
		""", """
		CREATE TABLE journeypattern_service(
			source_id INT REFERENCES source(source_id),
			journeypattern_id INT PRIMARY KEY REFERENCES journeypattern_intern(journeypattern_id),
			service_id INT NOT NULL REFERENCES service(service_id) DEFERRABLE,
			route_id INT REFERENCES route(route_id) DEFERRABLE,
			direction TEXT);
		"""),
	("""
		DROP TABLE IF EXISTS journeypattern_service_section CASCADE;
		""", """
		CREATE TABLE journeypattern_service_section(
			source_id INT REFERENCES source(source_id),
			jpsection_id INT PRIMARY KEY REFERENCES jpsection_intern(jpsection_id),
			journeypattern_id INT REFERENCES journeypattern_service(journeypattern_id) DEFERRABLE)
		"""),
	("""
		DROP TABLE IF EXISTS jptiminglink CASCADE;
		""", """
		CREATE TABLE jptiminglink(
			source_id INT REFERENCES source(source_id),
			jptiminglink_id INT PRIMARY KEY REFERENCES jptiminglink_intern(jptiminglink_id),
			jpsection_id INT REFERENCES journeypattern_service_section(jpsection_id) DEFERRABLE,
			routelink_id INT REFERENCES routelink(routelink_id) DEFERRABLE,
			runtime TEXT,
			from_sequence INT,
			from_stoppoint INT REFERENCES stoppoint(atcocode_id),
			to_sequence INT,
			to_stoppoint INT REFERENCES stoppoint(atcocode_id));
		"""),
	("""
		DROP TABLE IF EXISTS line CASCADE;
		""", """
		CREATE TABLE line(
			source_id INT REFERENCES source(source_id),
			line_id INT PRIMARY KEY REFERENCES line_intern(line_id),
			servicecode TEXT,
			line_name TEXT);
		"""),
	("""
		DROP TABLE IF EXISTS vehiclejourney CASCADE;
		""", """
		CREATE TABLE vehiclejourney(
			source_id INT NOT NULL REFERENCES source(source_id),
			vjcode_id INT PRIMARY KEY REFERENCES vjcode_intern(vjcode_id),
			other_vjcode_id INT REFERENCES vehiclejourney(vjcode_id) DEFERRABLE,
			journeypattern_id INT REFERENCES journeypattern_service(journeypattern_id) DEFERRABLE,
			line_id INT NOT NULL REFERENCES line(line_id) DEFERRABLE,
			privatecode TEXT,
			days_mask INT,
			deptime TEXT,
			deptime_seconds INT);
		"""),
	("""
		DROP TABLE IF EXISTS operator CASCADE;
		""", """
		CREATE TABLE operator(
			source_id INT REFERENCES source(source_id),
			operator_id TEXT PRIMARY KEY,
			shortname TEXT);
		"""),
	("""
		DROP TABLE IF EXISTS stoppoint CASCADE;
		""", """
		CREATE TABLE stoppoint(
			source_id INT REFERENCES source(source_id),
			atcocode_id INT REFERENCES naptan(atcocode_id),
			name TEXT,
			indicator TEXT,
			locality_name TEXT,
			locality_qualifier TEXT);
		"""),
	("""
		DROP TABLE IF EXISTS journeypattern_bounding_box;
		""", """
		CREATE TABLE journeypattern_bounding_box (
			journeypattern_id INT REFERENCES journeypattern_service(journeypattern_id),
			bounding_box box);
		""")]


def create_tables(conn):
	with conn.cursor() as cur:
		for drop, _ in reversed(TABLE_COMMANDS):
			cur.execute(drop)
		for _, create in TABLE_COMMANDS:
			cur.execute(create)

		# https://www.postgresql.org/docs/current/static/functions-geometry.html
		# This query works along the lines of:
		# travelinedata=> select * from naptan where point(latitude, longitude) <@ box(point(51.48, -2.51), point(51.49, -2.50));
		cur.execute("""
			CREATE INDEX idx_naptan_point
			ON naptan
			USING gist (point(latitude, longitude));
		""")

		cur.execute("""
			CREATE INDEX idx_timing_section ON jptiminglink(jpsection_id);
		""")
		cur.execute("""
			CREATE INDEX idx_journeypattern_bounding_box
			ON journeypattern_bounding_box
			USING gist (bounding_box);
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
		logging.info("Generating mv_vehiclejourney_per_hour...")
		cur.execute("""
			CREATE MATERIALIZED VIEW mv_vehiclejourney_per_hour AS
			SELECT
				coalesce(vj.journeypattern_id, other.journeypattern_id) AS journeypattern_id,
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
			LEFT JOIN vehiclejourney other ON vj.other_vjcode_id = other.vjcode_id
			GROUP BY 1,2,3;
		""")
		cur.execute("""
			CREATE INDEX idx_vehiclejourney_per_hour_id
			ON mv_vehiclejourney_per_hour
			USING btree (journeypattern_id);
		""")

def update_all_journeypattern_boundingbox(conn):
	with conn as transaction_conn:
		with transaction_conn.cursor() as cur:
			cur.execute("""
				SELECT journeypattern_id
				FROM journeypattern_service
				LEFT JOIN journeypattern_bounding_box USING (journeypattern_id)
				WHERE journeypattern_bounding_box.journeypattern_id IS NULL;
				""")
			journeypattern_id_list = [journeypattern_id for [journeypattern_id] in cur]

	logging.info("%d bounding boxes to calculate", len(journeypattern_id_list))

	for journeypattern_id in journeypattern_id_list:
		update_journeypattern_boundingbox(conn, journeypattern_id)

def update_journeypattern_boundingbox(conn, journeypattern_id):
	with conn as transaction_conn:
		with transaction_conn.cursor() as cur:
			cur.execute("""
				INSERT INTO journeypattern_bounding_box (journeypattern_id, bounding_box)
				SELECT
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
				JOIN naptan n_from ON n_from.atcocode_id = timing.from_stoppoint
				JOIN naptan n_to ON n_to.atcocode_id = timing.to_stoppoint
				WHERE section.journeypattern_id = %s
				GROUP BY section.journeypattern_id;
				""", (journeypattern_id,))

def id_from_actocode(conn, atcocode):
	with cur as conn.cursor():
		cur.execute("""
			SELECT atcocode_id
			FROM naptan
			WHERE atcocode = %s;
			""", (atcocode,))
		[[atcocode_id]] = cur
		return atcocode_id

def _interned(tablename, conn, source_id, longname):
	with conn.cursor() as cur:
		sql = """
			SELECT %(tablename)s_id
			FROM %(tablename)s_intern
			WHERE source_id = %%s
			AND %(tablename)s = %%s
		""" % dict(tablename=tablename)
		cur.execute(sql, (source_id, longname,))
		rows = list(cur)
		if len(rows) == 0:
			sql = """
				INSERT INTO %(tablename)s_intern(source_id, %(tablename)s)
				VALUES (%%s, %%s)
				RETURNING %(tablename)s_id
			""" % dict(tablename=tablename)
			cur.execute(sql, (source_id, longname,))
			rows = list(cur)
		[[short_id]] = rows
		return short_id

def interned_journeypattern(conn, source_id, journeypattern):
	return _interned('journeypattern', conn, source_id, journeypattern)

def interned_jpsection(conn, source_id, jpsection):
	return _interned('jpsection', conn, source_id, jpsection)

def interned_jptiminglink(conn, source_id, jptiminglink):
	return _interned('jptiminglink', conn, source_id, jptiminglink)

def interned_vjcode(conn, source_id, vjcode):
	return _interned('vjcode', conn, source_id, vjcode)

def interned_service(conn, source_id, service):
	return _interned('service', conn, source_id, service)

def interned_line(conn, source_id, line):
	return _interned('line', conn, source_id, line)

def interned_route(conn, source_id, route):
	return _interned('route', conn, source_id, route)

def interned_routelink(conn, source_id, routelink):
	return _interned('routelink', conn, source_id, routelink)
