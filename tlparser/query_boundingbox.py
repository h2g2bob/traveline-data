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
				"lat": from_lat,
				"lng": from_lng},
			"to": {
				"id": to_id,
				"lat": to_lat,
				"lng": to_lng},
			"frequency": frequency,
			"line_names": line_names}
			for (from_id, from_lat, from_lng, to_id, to_lat, to_lng, frequency, line_names)
			in cur]
