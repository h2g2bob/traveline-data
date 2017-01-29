#!/usr/bin/python3
# encoding: utf8

import psycopg2

def database():
	return psycopg2.connect("dbname=travelinedata") # XXX should be in __main__ and passed around?


def create_tables(conn):
	with conn.cursor() as cur:
		cur.execute("""
			DROP TABLE IF EXISTS jptiminglink;
			""")
		cur.execute("""
			CREATE TABLE jptiminglink(
				source TEXT,
				jptiminglink TEXT PRIMARY KEY,
				jpsection TEXT,
				routelink TEXT,
				runtime TEXT,
				from_sequence INT,
				from_stoppoint TEXT,
				to_sequence INT,
				to_stoppoint TEXT);
			""")
		cur.execute("""
			DROP TABLE IF EXISTS vehiclejourney;
			""")
		cur.execute("""
			CREATE TABLE vehiclejourney(
				source TEXT,
				vjcode TEXT PRIMARY KEY,
				journeypattern TEXT,
				line_id TEXT,
				privatecode TEXT,
				days_mask INT,
				deptime TEXT,
				deptime_seconds INT);
			""")
		cur.execute("""
			DROP TABLE IF EXISTS service;
			""")
		cur.execute("""
			CREATE TABLE service(
				source TEXT,
				servicecode TEXT PRIMARY KEY,
				privatecode TEXT,
				mode TEXT,
				operator_id TEXT,
				description TEXT);
			""")
		cur.execute("""
			DROP TABLE IF EXISTS line;
			""")
		cur.execute("""
			CREATE TABLE line(
				source TEXT,
				line_id TEXT PRIMARY KEY,
				servicecode TEXT,
				line_name TEXT);
			""")
		cur.execute("""
			DROP TABLE IF EXISTS journeypattern_service;
			""")
		cur.execute("""
			CREATE TABLE journeypattern_service(
				source TEXT,
				journeypattern TEXT PRIMARY KEY,
				servicecode TEXT,
				route TEXT,
				direction TEXT);
			""")
		cur.execute("""
			DROP TABLE IF EXISTS journeypattern_service_section;
			""")
		cur.execute("""
			CREATE TABLE journeypattern_service_section(
				source TEXT,
				journeypattern TEXT,
				jpsection TEXT,
				PRIMARY KEY (journeypattern, jpsection));
			""")
		cur.execute("""
			DROP TABLE IF EXISTS operator;
			""")
		cur.execute("""
			CREATE TABLE operator(
				source TEXT,
				operator_id TEXT PRIMARY KEY,
				shortname TEXT);
			""")
		cur.execute("""
			DROP TABLE IF EXISTS route;
			""")
		cur.execute("""
			CREATE TABLE route(
				source TEXT,
				route_id TEXT PRIMARY KEY,
				privatecode TEXT,
				routesection TEXT,
				description TEXT);
			""")
		cur.execute("""
			DROP TABLE IF EXISTS routelink;
			""")
		cur.execute("""
			CREATE TABLE routelink(
				source TEXT,
				routelink TEXT PRIMARY KEY,
				routesection TEXT,
				from_stoppoint TEXT,
				to_stoppoint TEXT,
				direction TEXT);
			""")
		cur.execute("""
			DROP TABLE IF EXISTS stoppoint;
			""")
		cur.execute("""
			CREATE TABLE stoppoint(
				source TEXT,
				stoppoint TEXT PRIMARY KEY,
				name TEXT,
				indicator TEXT,
				locality_name TEXT,
				locality_qualifier TEXT);
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
