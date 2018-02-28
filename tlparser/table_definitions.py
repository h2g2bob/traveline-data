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
		DROP TABLE IF EXISTS journeypattern_bounding_box;
		""", """
		CREATE TABLE journeypattern_bounding_box (
			journeypattern_id INT REFERENCES journeypattern_service(journeypattern_id),
			bounding_box box);
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
		logging.info("Defining mv_vehiclejourney_per_hour...")
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
			GROUP BY 1,2,3
			WITH NO DATA;
		""")
		cur.execute("""
			CREATE INDEX idx_vehiclejourney_per_hour_id
			ON mv_vehiclejourney_per_hour
			USING btree (journeypattern_id);
		""")

		create_mv_link_frequency2(cur)

def create_mv_link_frequency2(cur):
	logging.info("Defining mv_link_frequency2...")
	SHARDS = ["ea", "em", "l", "ncsd", "nw", "s", "se", "sw", "w", "wm", "y"]

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
	for shard in SHARDS:
		cur.execute("""
		CREATE MATERIALIZED VIEW mv_link_frequency2_""" + shard + """ AS
		 WITH jptiminglink_subset AS (
			 SELECT jptiminglink.from_stoppoint,
			    jptiminglink.to_stoppoint,
			    jptiminglink.jpsection_id,
			    runtime_to_seconds(jptiminglink.runtime) as runtime_sec
			   FROM jptiminglink
			     JOIN source USING (source_id)
			  WHERE source.source ~~ '""" + shard.upper() + """.zip/%'::text
			), stops_and_frequency AS (
			 SELECT timing.from_stoppoint,
			    timing.to_stoppoint,
			    vjph.days_mask,
			    sum(vjph.hour_0) AS hour_0,
			    sum(vjph.hour_1) AS hour_1,
			    sum(vjph.hour_2) AS hour_2,
			    sum(vjph.hour_3) AS hour_3,
			    sum(vjph.hour_4) AS hour_4,
			    sum(vjph.hour_5) AS hour_5,
			    sum(vjph.hour_6) AS hour_6,
			    sum(vjph.hour_7) AS hour_7,
			    sum(vjph.hour_8) AS hour_8,
			    sum(vjph.hour_9) AS hour_9,
			    sum(vjph.hour_10) AS hour_10,
			    sum(vjph.hour_11) AS hour_11,
			    sum(vjph.hour_12) AS hour_12,
			    sum(vjph.hour_13) AS hour_13,
			    sum(vjph.hour_14) AS hour_14,
			    sum(vjph.hour_15) AS hour_15,
			    sum(vjph.hour_16) AS hour_16,
			    sum(vjph.hour_17) AS hour_17,
			    sum(vjph.hour_18) AS hour_18,
			    sum(vjph.hour_19) AS hour_19,
			    sum(vjph.hour_20) AS hour_20,
			    sum(vjph.hour_21) AS hour_21,
			    sum(vjph.hour_22) AS hour_22,
			    sum(vjph.hour_23) AS hour_23,
			    sum(vjph.hour_0 + vjph.hour_1 + vjph.hour_2 + vjph.hour_3 + vjph.hour_4 + vjph.hour_5 + vjph.hour_6 + vjph.hour_7 + vjph.hour_8 + vjph.hour_9 + vjph.hour_10 + vjph.hour_11 + vjph.hour_12 + vjph.hour_13 + vjph.hour_14 + vjph.hour_15 + vjph.hour_16 + vjph.hour_17 + vjph.hour_18 + vjph.hour_19 + vjph.hour_20 + vjph.hour_21 + vjph.hour_22 + vjph.hour_23) * (((vjph.days_mask >> 0) & 1) + ((vjph.days_mask >> 1) & 1) + ((vjph.days_mask >> 2) & 1) + ((vjph.days_mask >> 3) & 1) + ((vjph.days_mask >> 4) & 1) + ((vjph.days_mask >> 5) & 1) + ((vjph.days_mask >> 6) & 1) + ((vjph.days_mask >> 7) & 1))::numeric AS bus_per_week,
			    array_agg(distinct timing.runtime_sec) as runtimes
			   FROM jptiminglink_subset timing
			     JOIN journeypattern_service_section section USING (jpsection_id)
			     JOIN mv_vehiclejourney_per_hour vjph USING (journeypattern_id)
			  GROUP BY timing.from_stoppoint, timing.to_stoppoint, vjph.days_mask
			)
		 SELECT
		    -- a line segment allows you to draw directly from a
		    -- query on this table, which is a massive speed improvement
		    lseg(point(from_point.latitude::double precision, from_point.longitude::double precision), point(to_point.latitude::double precision, to_point.longitude::double precision)) AS line_segment,

		    -- ... but you can only (easily) have a gist index on a box!
		    box(point(from_point.latitude::double precision, from_point.longitude::double precision), point(to_point.latitude::double precision, to_point.longitude::double precision)) AS lseg_bbox,

		    stops_and_frequency.from_stoppoint,
		    stops_and_frequency.to_stoppoint,
		    stops_and_frequency.days_mask,
		    stops_and_frequency.hour_0,
		    stops_and_frequency.hour_1,
		    stops_and_frequency.hour_2,
		    stops_and_frequency.hour_3,
		    stops_and_frequency.hour_4,
		    stops_and_frequency.hour_5,
		    stops_and_frequency.hour_6,
		    stops_and_frequency.hour_7,
		    stops_and_frequency.hour_8,
		    stops_and_frequency.hour_9,
		    stops_and_frequency.hour_10,
		    stops_and_frequency.hour_11,
		    stops_and_frequency.hour_12,
		    stops_and_frequency.hour_13,
		    stops_and_frequency.hour_14,
		    stops_and_frequency.hour_15,
		    stops_and_frequency.hour_16,
		    stops_and_frequency.hour_17,
		    stops_and_frequency.hour_18,
		    stops_and_frequency.hour_19,
		    stops_and_frequency.hour_20,
		    stops_and_frequency.hour_21,
		    stops_and_frequency.hour_22,
		    stops_and_frequency.hour_23,
		    stops_and_frequency.bus_per_week,
		    stops_and_frequency.runtimes
		   FROM stops_and_frequency
		     JOIN naptan from_point ON stops_and_frequency.from_stoppoint = from_point.atcocode_id
		     JOIN naptan to_point ON stops_and_frequency.to_stoppoint = to_point.atcocode_id

		   WITH NO DATA
		""")
		cur.execute("""
			CREATE INDEX idx_mv_link_frequency2_%(shard)s
			ON mv_link_frequency2_%(shard)s
			USING gist(lseg_bbox);
		""" % dict(shard=shard))

	cur.execute("""CREATE VIEW mv_link_frequency2 AS """ + 
	"""
		UNION ALL
	""".join("""
		 SELECT
		    mv_link_frequency2_%(shard)s.line_segment,
		    mv_link_frequency2_%(shard)s.lseg_bbox,
		    mv_link_frequency2_%(shard)s.from_stoppoint,
		    mv_link_frequency2_%(shard)s.to_stoppoint,
		    mv_link_frequency2_%(shard)s.days_mask,
		    mv_link_frequency2_%(shard)s.hour_0,
		    mv_link_frequency2_%(shard)s.hour_1,
		    mv_link_frequency2_%(shard)s.hour_2,
		    mv_link_frequency2_%(shard)s.hour_3,
		    mv_link_frequency2_%(shard)s.hour_4,
		    mv_link_frequency2_%(shard)s.hour_5,
		    mv_link_frequency2_%(shard)s.hour_6,
		    mv_link_frequency2_%(shard)s.hour_7,
		    mv_link_frequency2_%(shard)s.hour_8,
		    mv_link_frequency2_%(shard)s.hour_9,
		    mv_link_frequency2_%(shard)s.hour_10,
		    mv_link_frequency2_%(shard)s.hour_11,
		    mv_link_frequency2_%(shard)s.hour_12,
		    mv_link_frequency2_%(shard)s.hour_13,
		    mv_link_frequency2_%(shard)s.hour_14,
		    mv_link_frequency2_%(shard)s.hour_15,
		    mv_link_frequency2_%(shard)s.hour_16,
		    mv_link_frequency2_%(shard)s.hour_17,
		    mv_link_frequency2_%(shard)s.hour_18,
		    mv_link_frequency2_%(shard)s.hour_19,
		    mv_link_frequency2_%(shard)s.hour_20,
		    mv_link_frequency2_%(shard)s.hour_21,
		    mv_link_frequency2_%(shard)s.hour_22,
		    mv_link_frequency2_%(shard)s.hour_23,
		    mv_link_frequency2_%(shard)s.bus_per_week,
		    mv_link_frequency2_%(shard)s.runtimes
		   FROM mv_link_frequency2_%(shard)s
		""" % dict(shard=shard)
		for shard in SHARDS))

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
