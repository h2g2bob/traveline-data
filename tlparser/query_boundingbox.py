#!/usr/bin/python3
# encoding: utf8


def line_segments_in_boundingbox(conn, minlat, minlong, maxlat, maxlong, day_of_week=0x01, hour=12):
	assert 0 <= hour < 24
	hour_column = 'hour_%d' % (hour,)
	with conn.cursor() as cur:
		cur.execute("""
			WITH desired_bounding_box_table AS (
				SELECT box(point(%s, %s), point(%s, %s)) AS desired_bounding_box
			)
			SELECT
				bus_stop_pair_frequencies.from_stoppoint,
				n_from.latitude,
				n_from.longitude,
				bus_stop_pair_frequencies.to_stoppoint,
				n_to.latitude,
				n_to.longitude,
				bus_stop_pair_frequencies.frequency,
				bus_stop_pair_frequencies.line_names

			FROM (
				SELECT
					timing.from_stoppoint,
					timing.to_stoppoint,
					sum(case when days_mask & %s != 0 then """ + hour_column + """ else 0 end) AS frequency,
					array_agg(distinct line.line_name) AS line_names

				FROM jptiminglink timing
				JOIN journeypattern_service_section section USING (jpsection_id)
				JOIN mv_vehiclejourney_per_hour vjph USING (journeypattern_id)
				JOIN mv_journeypattern_bounding_box jp_bbox USING (journeypattern_id)
				LEFT JOIN line line ON vjph.line_id = line.line_id
				WHERE jp_bbox.bounding_box && (select desired_bounding_box from desired_bounding_box_table)
				GROUP BY 1, 2
			) AS bus_stop_pair_frequencies
			JOIN naptan n_from ON n_from.atcocode = bus_stop_pair_frequencies.from_stoppoint
			JOIN naptan n_to ON n_to.atcocode = bus_stop_pair_frequencies.to_stoppoint

			-- if this was an "and" relation, it might speed things up by filtering out a large
			-- number of naptan points before joining... but currently it appears to make no
			-- difference to the query plan, so we can stick with an "or" here:
			WHERE point(n_from.latitude, n_from.longitude) <@ (select desired_bounding_box from desired_bounding_box_table)
			OR point(n_to.latitude, n_to.longitude) <@ (select desired_bounding_box from desired_bounding_box_table)

		""", (minlat, minlong, maxlat, maxlong, day_of_week,))
		return [{
			"from": {
				"id": from_id,
				"lat": float(from_lat),
				"lng": float(from_lng)},
			"to": {
				"id": to_id,
				"lat": float(to_lat),
				"lng": float(to_lng)},
			"frequency": int(frequency),
			"line_names": line_names}
			for (from_id, from_lat, from_lng, to_id, to_lat, to_lng, frequency, line_names)
			in cur]


def line_segments_and_stops_in_boundingbox(conn, minlat, minlong, maxlat, maxlong, day_of_week=0x01, hour=12):
	assert 0 <= hour < 24
	hour_column = 'hour_%d' % (hour,)
	with conn.cursor() as cur:

		# Efficiently find most of the bus stops using the geographic index:
		bus_stops = {}
		cur.execute("""
			SELECT
				atcocode,
				name,
				latitude,
				longitude
			FROM
				naptan

			WHERE point(latitude, longitude) <@ box(point(%s, %s), point(%s, %s))
		""", (
			minlat,
			minlong,
			maxlat,
			maxlong,))
		for stop_id, name, latitude, longitude in cur:
			bus_stops[stop_id] = {
				"name": name,
				"lat": latitude,
				"lng": longitude}

		cur.execute("""
			SELECT
				timing.from_stoppoint,
				timing.to_stoppoint,
				sum(case when days_mask & %s != 0 then """ + hour_column + """ else 0 end) AS frequency,
				array_agg(distinct line.line_name) AS line_names

			FROM jptiminglink timing
			JOIN journeypattern_service_section section USING (jpsection_id)
			JOIN mv_vehiclejourney_per_hour vjph USING (journeypattern_id)
			JOIN mv_journeypattern_bounding_box jp_bbox USING (journeypattern_id)
			LEFT JOIN line line ON vjph.line_id = line.line_id
			WHERE jp_bbox.bounding_box && box(point(%s, %s), point(%s, %s))
			GROUP BY 1, 2
			""", (day_of_week, minlat, minlong, maxlat, maxlong,))
		bus_stop_pairs = []
		atcocode_sets = set()
		for from_id, to_id, frequency, line_names in cur:

			if not (from_id in bus_stops or to_id in bus_stops):
				# jptiminglink is grouped by (stop1, stop2, journeypattern_id)
				# we want to make sure our sum() contains all the possible
				# journeypattern_ids for the bus stop pair ... which is only
				# true if at least one stop is inside the requested_bbox.
				continue

			bus_stop_pairs.append({
				"from": from_id,
				"to": to_id,
				"frequency": int(frequency),
				"line_names": line_names})

			atcocode_sets.add(from_id)
			atcocode_sets.add(to_id)

		# We want to draw lines whuch have a bus stop inside and a bus stop outside
		# the requested bounding box. We query the extra bus stops we need with this
		# inefficient query (which will probably do a loop over the index on atcocode)
		atcocode_list = tuple(atcocode_sets - set(bus_stops.keys())) or ('nothing',)
		cur.execute("""
			SELECT
				atcocode,
				name,
				latitude,
				longitude
			FROM
				naptan

			WHERE atcocode IN %s
		""", (atcocode_list,))
		for stop_id, name, latitude, longitude in cur:
			bus_stops[stop_id] = {
				"name": name,
				"lat": latitude,
				"lng": longitude}

	return {"pairs": bus_stop_pairs, "stops": bus_stops}
