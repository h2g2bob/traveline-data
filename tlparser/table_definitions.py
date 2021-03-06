#!/usr/bin/python3
# encoding: utf8

import logging


def _table_command_intern(tablename):
	"""
	What's with the intern tables?

	Well, it solves the following problems:

	- If the data is in the xml file in the "wrong" order? We won't
	  have a routelink_id to use.

	- While the inserts are slower, the table we *want to query a lot*
	  gets a lot bigger

	- if we re-upload a file, we can no longer delete the old data but
	  keep all the old ids (which might be useful, maybe? eg: for
	  comparing old and new datasets)

	- it's especially needed for naptan and travelinedata, because it's
	  100% certain that not all items refered to by one dataset are in
	  the other dataset.
	"""

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
		DROP TABLE IF EXISTS atcocode_intern;
		""", """
		CREATE TABLE atcocode_intern(
			atcocode_id SERIAL PRIMARY KEY,
			atcocode TEXT UNIQUE)
		"""),
	("""
		DROP TABLE IF EXISTS naptan;
		""", """
		CREATE TABLE naptan (
			atcocode_id INT PRIMARY KEY REFERENCES atcocode_intern(atcocode_id),
			code TEXT UNIQUE,
			name TEXT,
			latitude REAL,
			longitude REAL)
		"""),
	("""
		DROP TABLE IF EXISTS stoppoint CASCADE;
		""", """
		CREATE TABLE stoppoint(
			-- may exist in multiple files, but we assume it's the
			-- same in all the files, so we miss out source_id
			atcocode_id INT PRIMARY KEY REFERENCES atcocode_intern(atcocode_id),
			name TEXT,
			indicator TEXT,
			locality_name TEXT,
			locality_qualifier TEXT);
		"""),
	("""
		DROP TABLE IF EXISTS routelink CASCADE;
		""", """
		CREATE TABLE routelink(
			source_id INT REFERENCES source(source_id),
			routelink_id INT PRIMARY KEY REFERENCES routelink_intern(routelink_id),
			routesection TEXT,
			from_stoppoint INT REFERENCES stoppoint(atcocode_id) DEFERRABLE,
			to_stoppoint INT REFERENCES stoppoint(atcocode_id) DEFERRABLE,
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
		DROP TABLE IF EXISTS oscodepointdata;
		""", """
		CREATE TABLE oscodepointdata(
			postcode TEXT PRIMARY KEY,
			display TEXT NOT NULL,
			location point NOT NULL);
		""")]


def create_tables(conn):
	with conn.cursor() as cur:
		for drop, _ in reversed(TABLE_COMMANDS):
			logging.info("sql %s", drop)
			cur.execute(drop)
		for _, create in TABLE_COMMANDS:
			logging.info("sql %s", create)
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
			CREATE INDEX idx_oscodepointdata_point
			ON oscodepointdata
			USING gist (location);
		""")

		cur.execute("""
			CREATE INDEX idx_timing_section ON jptiminglink(jpsection_id);
		""")

def drop_materialized_views(conn):
	with conn.cursor() as cur:
		cur.execute("""
			DROP MATERIALIZED VIEW IF EXISTS mv_vehiclejourney_per_hour;
			""")
		drop_mv_link_frequency3(cur)

def refresh_materialized_views(conn):
	with conn.cursor() as cur:
		cur.execute("""
			REFRESH MATERIALIZED VIEW mv_vehiclejourney_per_hour;
			""")
		refresh_mv_link_frequency3(cur)

def create_materialized_views(conn):
	with conn.cursor() as cur:
		logging.info("Defining mv_vehiclejourney_per_hour...")
		cur.execute("""
			CREATE MATERIALIZED VIEW mv_vehiclejourney_per_hour AS
			WITH vehiclejourney_fix_jpid AS (
				SELECT
					vj.source_id,
					vj.vjcode_id,
					vj.other_vjcode_id,
					coalesce(vj.journeypattern_id, other.journeypattern_id) AS journeypattern_id,
					vj.line_id,
					vj.days_mask,
					vj.deptime_seconds
				FROM vehiclejourney vj
				LEFT JOIN vehiclejourney other ON vj.other_vjcode_id = other.vjcode_id
			),
			vehiclejourney_dedup AS (
				-- So, um, some buses leave at exactly the same time, and go on
				-- exactly the same route?
				-- But don't worry, someone adds DaysOfNonOperation each time,
				-- a couple of days before departure.
				-- I wouldn't trust that, so let's get rid of the obvious nonsense.

				SELECT DISTINCT source_id, vjcode_id, other_vjcode_id, journeypattern_id, line_id, days_mask, deptime_seconds
				FROM vehiclejourney_fix_jpid
			)
			SELECT
				vj.journeypattern_id,
				vj.line_id,
				vj.days_mask,
				sum(case when vj.deptime_seconds / 3600 = 0 then 1 else 0 end)::int as hour_0,
				sum(case when vj.deptime_seconds / 3600 = 1 then 1 else 0 end)::int as hour_1,
				sum(case when vj.deptime_seconds / 3600 = 2 then 1 else 0 end)::int as hour_2,
				sum(case when vj.deptime_seconds / 3600 = 3 then 1 else 0 end)::int as hour_3,
				sum(case when vj.deptime_seconds / 3600 = 4 then 1 else 0 end)::int as hour_4,
				sum(case when vj.deptime_seconds / 3600 = 5 then 1 else 0 end)::int as hour_5,
				sum(case when vj.deptime_seconds / 3600 = 6 then 1 else 0 end)::int as hour_6,
				sum(case when vj.deptime_seconds / 3600 = 7 then 1 else 0 end)::int as hour_7,
				sum(case when vj.deptime_seconds / 3600 = 8 then 1 else 0 end)::int as hour_8,
				sum(case when vj.deptime_seconds / 3600 = 9 then 1 else 0 end)::int as hour_9,
				sum(case when vj.deptime_seconds / 3600 = 10 then 1 else 0 end)::int as hour_10,
				sum(case when vj.deptime_seconds / 3600 = 11 then 1 else 0 end)::int as hour_11,
				sum(case when vj.deptime_seconds / 3600 = 12 then 1 else 0 end)::int as hour_12,
				sum(case when vj.deptime_seconds / 3600 = 13 then 1 else 0 end)::int as hour_13,
				sum(case when vj.deptime_seconds / 3600 = 14 then 1 else 0 end)::int as hour_14,
				sum(case when vj.deptime_seconds / 3600 = 15 then 1 else 0 end)::int as hour_15,
				sum(case when vj.deptime_seconds / 3600 = 16 then 1 else 0 end)::int as hour_16,
				sum(case when vj.deptime_seconds / 3600 = 17 then 1 else 0 end)::int as hour_17,
				sum(case when vj.deptime_seconds / 3600 = 18 then 1 else 0 end)::int as hour_18,
				sum(case when vj.deptime_seconds / 3600 = 19 then 1 else 0 end)::int as hour_19,
				sum(case when vj.deptime_seconds / 3600 = 20 then 1 else 0 end)::int as hour_20,
				sum(case when vj.deptime_seconds / 3600 = 21 then 1 else 0 end)::int as hour_21,
				sum(case when vj.deptime_seconds / 3600 = 22 then 1 else 0 end)::int as hour_22,
				sum(case when vj.deptime_seconds / 3600 = 23 then 1 else 0 end)::int as hour_23
			FROM vehiclejourney_dedup vj
			GROUP BY 1,2,3
			WITH NO DATA;
		""")
		cur.execute("""
			CREATE INDEX idx_vehiclejourney_per_hour_id
			ON mv_vehiclejourney_per_hour
			USING btree (journeypattern_id);
		""")

		create_mv_link_frequency3(cur)

def create_mv_link_frequency3(cur):
	logging.info("Defining mv_link_frequency3...")

	cur.execute("""
	CREATE TABLE mask_to_weekday (mask INT UNIQUE, weekday CHAR UNIQUE);
	""")
	cur.execute("""
	INSERT INTO mask_to_weekday (mask, weekday)
	VALUES (1, 'M'), (2, 'T'), (4, 'W'), (8, 'H'), (16, 'F'), (32, 'S'), (64, 'N');
	""")


	cur.execute("""
	CREATE FUNCTION hourarray_add(INT[24], INT[24]) RETURNS INT[24]
        AS $$
                SELECT ARRAY[
                        $1[1] + $2[1],
                        $1[2] + $2[2],
                        $1[3] + $2[3],
                        $1[4] + $2[4],
                        $1[5] + $2[5],
                        $1[6] + $2[6],
                        $1[7] + $2[7],
                        $1[8] + $2[8],
                        $1[9] + $2[9],
                        $1[10] + $2[10],
                        $1[11] + $2[11],
                        $1[12] + $2[12],
                        $1[13] + $2[13],
                        $1[14] + $2[14],
                        $1[15] + $2[15],
                        $1[16] + $2[16],
                        $1[17] + $2[17],
                        $1[18] + $2[18],
                        $1[19] + $2[19],
                        $1[20] + $2[20],
                        $1[21] + $2[21],
                        $1[22] + $2[22],
                        $1[23] + $2[23],
                        $1[24] + $2[24]
                ];
        $$ LANGUAGE SQL
        IMMUTABLE
        RETURNS NULL ON NULL INPUT;
	""")
	cur.execute("""
	CREATE AGGREGATE hourarray_sum (int[24])
	(
	    sfunc = hourarray_add,
	    stype = int[24],
	    initcond = '{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0}'
	);
	""")

	cur.execute("""
	CREATE FUNCTION runtime_to_seconds(TEXT) RETURNS integer
	AS $$
		SELECT (coalesce(x.match[1]::int, 0)*60) + coalesce(x.match[2]::int, 0)
		FROM (
			SELECT regexp_matches($1, '^PT(?:([0-9]+)M)?(?:([0-9]+)S)?$') as match
		) AS x;
	$$ LANGUAGE SQL
	IMMUTABLE
	RETURNS NULL ON NULL INPUT;
	""")

	cur.execute("""
	CREATE MATERIALIZED VIEW mv_link_frequency3 AS
		WITH stops_and_frequency_per_line AS (
			SELECT
				timing.from_stoppoint,
				timing.to_stoppoint,
				jp_service.service_id,
				weekday.weekday,
				ARRAY [
					sum(vjph.hour_0),
					sum(vjph.hour_1),
					sum(vjph.hour_2),
					sum(vjph.hour_3),
					sum(vjph.hour_4),
					sum(vjph.hour_5),
					sum(vjph.hour_6),
					sum(vjph.hour_7),
					sum(vjph.hour_8),
					sum(vjph.hour_9),
					sum(vjph.hour_10),
					sum(vjph.hour_11),
					sum(vjph.hour_12),
					sum(vjph.hour_13),
					sum(vjph.hour_14),
					sum(vjph.hour_15),
					sum(vjph.hour_16),
					sum(vjph.hour_17),
					sum(vjph.hour_18),
					sum(vjph.hour_19),
					sum(vjph.hour_20),
					sum(vjph.hour_21),
					sum(vjph.hour_22),
					sum(vjph.hour_23)
				]::int[24] AS hour_array,
				min(distinct runtime_to_seconds(timing.runtime)) as min_runtime,
				max(distinct runtime_to_seconds(timing.runtime)) as max_runtime
			FROM jptiminglink timing
			JOIN journeypattern_service_section section USING (jpsection_id)
			JOIN mv_vehiclejourney_per_hour vjph USING (journeypattern_id)
			LEFT JOIN journeypattern_service jp_service USING (journeypattern_id)
			JOIN mask_to_weekday weekday ON weekday.mask & vjph.days_mask > 0
			GROUP BY
				timing.from_stoppoint,
				timing.to_stoppoint,
				jp_service.service_id,
				weekday.weekday
		),
		stops_and_frequency AS (
			
			SELECT
				from_stoppoint,
				to_stoppoint,
				weekday,

				ARRAY [
					sum(hour_array[1]),
					sum(hour_array[2]),
					sum(hour_array[3]),
					sum(hour_array[4]),
					sum(hour_array[5]),
					sum(hour_array[6]),
					sum(hour_array[7]),
					sum(hour_array[8]),
					sum(hour_array[9]),
					sum(hour_array[10]),
					sum(hour_array[11]),
					sum(hour_array[12]),
					sum(hour_array[13]),
					sum(hour_array[14]),
					sum(hour_array[15]),
					sum(hour_array[16]),
					sum(hour_array[17]),
					sum(hour_array[18]),
					sum(hour_array[19]),
					sum(hour_array[20]),
					sum(hour_array[21]),
					sum(hour_array[22]),
					sum(hour_array[23]),
					sum(hour_array[24])
				] hour_array_total,

				ARRAY [
					max(hour_array[1]),
					max(hour_array[2]),
					max(hour_array[3]),
					max(hour_array[4]),
					max(hour_array[5]),
					max(hour_array[6]),
					max(hour_array[7]),
					max(hour_array[8]),
					max(hour_array[9]),
					max(hour_array[10]),
					max(hour_array[11]),
					max(hour_array[12]),
					max(hour_array[13]),
					max(hour_array[14]),
					max(hour_array[15]),
					max(hour_array[16]),
					max(hour_array[17]),
					max(hour_array[18]),
					max(hour_array[19]),
					max(hour_array[20]),
					max(hour_array[21]),
					max(hour_array[22]),
					max(hour_array[23]),
					max(hour_array[24])
				] hour_array_best_service,

				array_agg(DISTINCT service_id) AS service_ids,
				min(min_runtime) AS min_runtime,
				max(max_runtime) AS max_runtime

			FROM stops_and_frequency_per_line
			GROUP BY
				from_stoppoint,
				to_stoppoint,
				weekday
		)
		SELECT
			-- a line segment allows you to draw directly from a
			-- query on this table, which is a massive speed improvement
			lseg(point(from_point.latitude::double precision, from_point.longitude::double precision), point(to_point.latitude::double precision, to_point.longitude::double precision)) AS line_segment,

			-- ... but you can only (easily) have a gist index on a box!
			box(point(from_point.latitude::double precision, from_point.longitude::double precision), point(to_point.latitude::double precision, to_point.longitude::double precision)) AS lseg_bbox,

			stops_and_frequency.from_stoppoint,
			stops_and_frequency.to_stoppoint,
			stops_and_frequency.weekday,

			stops_and_frequency.hour_array_total,
			stops_and_frequency.hour_array_best_service,
			stops_and_frequency.service_ids,
			stops_and_frequency.min_runtime,
			stops_and_frequency.max_runtime

		FROM stops_and_frequency
		JOIN naptan from_point ON stops_and_frequency.from_stoppoint = from_point.atcocode_id
		JOIN naptan to_point ON stops_and_frequency.to_stoppoint = to_point.atcocode_id

	WITH NO DATA;
	""")
	cur.execute("""
		CREATE INDEX idx_mv_link_frequency3
		ON mv_link_frequency3
		USING gist(lseg_bbox);
	""")


def drop_mv_link_frequency3(cur):
	cur.execute("""
		DROP MATERIALIZED VIEW mv_link_frequency3
		""")
	cur.execute("""
		DROP TABLE mask_to_weekday
		""")
	cur.execute("""
		DROP FUNCTION hourarray_add(INT[24], INT[24])
		""")
	cur.execute("""
		DROP AGGREGATE hourarray_sum (int[24])
		""")
	cur.execute("""
		DROP FUNCTION runtime_to_seconds(TEXT)
		""")

def refresh_mv_link_frequency3(cur):
	cur.execute("""
		REFRESH MATERIALIZED VIEW mv_link_frequency3
		""")

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

def interned_atcocode(conn, atcocode):
	"No source_id for this one"
	with conn.cursor() as cur:
		sql = """
			SELECT atcocode_id
			FROM atcocode_intern
			WHERE atcocode = %s
		"""
		cur.execute(sql, (atcocode,))
		rows = list(cur)
		if len(rows) == 0:
			sql = """
				INSERT INTO atcocode_intern(atcocode)
				VALUES (%s)
				RETURNING atcocode_id
			"""
			cur.execute(sql, (atcocode,))
			rows = list(cur)
		[[short_id]] = rows
		return short_id
