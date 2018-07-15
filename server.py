#!/usr/bin/python3
# encoding: utf8
import logging
from math import atan2
from math import cos
from math import pi
from math import sin
from math import sqrt

import psycopg2
from flask import Flask
from flask import jsonify
from flask import request

app = Flask(__name__, static_url_path='')

DEC2FLOAT = psycopg2.extensions.new_type(
    psycopg2.extensions.DECIMAL.values,
    'DEC2FLOAT',
    lambda value, curs: float(value) if value is not None else None)
psycopg2.extensions.register_type(DEC2FLOAT)

BASIC_INFO = {
    "about": {
        "description": "This is the API for buildmorebuslanes.com",
        "url": "https://github.com/h2g2bob/traveline-data",
        "copyright":
            "Contains public sector information licensed under the Open Government Licence v3.0 from <a href=\"http://www.travelinedata.org.uk/\">Traveline National Dataset (TNDS)</a>, <a href=\"https://data.gov.uk/dataset/ff93ffc1-6656-47d8-9155-85ea0b8f2251/national-public-transport-access-nodes-naptan\">Naptan</a> and <a href=\"https://data.gov.uk/dataset/7dc36b99-9b5e-4475-91ab-ab16e1cabb6d/nhs-postcode-directory-latest-centroids\">NHS Postcode Directory</a>. Data provided by <a href=\"https://github.com/h2g2bob/traveline-data\">traveline-data</a>.",
    }
}

EARTH_RADIUS_KM = 6371
MILES_PER_KM = 0.6213712


def database():
    return psycopg2.connect("dbname=travelinedata")


def statement_timeout(conn, seconds):
    millis = int(seconds * 1000)
    with conn.cursor() as cur:
        cur.execute("SET statement_timeout TO %s;", (millis,))


def json_response(data):
    data.update(BASIC_INFO)
    return jsonify(data)


@app.route('/')
def index():
    return json_response({})


@app.route('/postcode/location/<code>/')
def postcode_location(code):
    code = code.upper().replace(" ", "")
    with database() as conn:
        statement_timeout(conn, 10)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT lat, lng
                    FROM postcodes_short
                    WHERE postcode = %(postcode)s
                UNION ALL
                SELECT lat, lng
                    FROM postcodes
                    WHERE postcode = %(postcode)s
                """, {"postcode": code})
            [[lat, lng]] = cur.fetchall()
            return json_response({"lat": lat, "lng": lng})


@app.route('/postcode/autocomplete/')
def postcode_complete():
    prefix = request.args.get("prefix", "")
    prefix = prefix.upper().replace(" ", "")
    if prefix == "":
        return json_response({"results": [
            "DE12FD",  # Derby bus station
            "EX1",  # Exeter
            "L18JX",  # Liverpool bus station
            "NR1",  # Norwich
            "OX41AA",  # Oxford
            "SS1",  # Southend-on-sea
            "W1",  # Central London
        ]})

    with database() as conn:
        statement_timeout(conn, 10)
        with conn.cursor() as cur:
            cur.execute("""
                select unnest(suggestions)
                from postcode_prefix_lookup
                where prefix = %(prefix)s
                """, {'prefix': prefix})
            data = [suggestion for [suggestion] in cur.fetchall()]
            return json_response({"results": data})


def _one_feature_v3(
    from_id,
     to_id,
     from_lat,
     from_lng,
     to_lat,
     to_lng,
     weekday,
     length,
     min_runtime,
     max_runtime,
     all_services_array,
     one_service_array):
    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [from_lng, from_lat],
                [to_lng, to_lat],
            ]
        },
        "properties": {
            "length": length,
            "frequencies": {
                weekday: {
                    "single_service": one_service_array,
                    "all_services": all_services_array,
                },
            },
            "runtime": {
                "min": min_runtime,
                "max": max_runtime,
            }
        },
        "id": 1
    }


@app.route('/geojson/v3/links/')
def geojson_frequency_v3():
    return geojson_frequency_v34(_one_feature_v3)


def _deg2rad(deg):
    return deg * (pi / 180)


def _calc_distance_km(lon1, lat1, lon2, lat2):
    # https://stackoverflow.com/questions/27928/calculate-distance-between-two-latitude-longitude-points-haversine-formula
    dLat = _deg2rad(lat2 - lat1)
    dLon = _deg2rad(lon2 - lon1)
    a = (
        sin(dLat / 2) * sin(dLat / 2) +
        cos(_deg2rad(lat1)) * cos(_deg2rad(lat2)) * sin(dLon / 2) * sin(dLon / 2))
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    d = EARTH_RADIUS_KM * c
    return d


def _distance(distance_km):
    return {
        "km": distance_km,
        "mi": distance_km * MILES_PER_KM,
    }


def _runtime(runtime_sec):
    if runtime_sec is None:
        return None
    return {
        "s": runtime_sec,
        "h": float(runtime_sec) / 3600,
    }


def _speed(distance_km, runtime_sec):
    if runtime_sec is None:
        return None
    runtime_hour = float(runtime_sec) / 3600
    if runtime_hour == 0:
        # bus stops have same time scheduled which suggests infinite speed!
        return None
    return {
        "kph": distance_km / runtime_hour,
        "mph": MILES_PER_KM * distance_km / runtime_hour,
    }


def _one_feature_v4(
        from_id,
        to_id,
        from_lat,
        from_lng,
        to_lat,
        to_lng,
        weekday,
        _length,
        min_runtime_sec,
        max_runtime_sec,
        all_services_array,
        one_service_array):

    distance_km = _calc_distance_km(from_lng, from_lat, to_lng, to_lat)
    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [from_lng, from_lat],
                [to_lng, to_lat],
            ]
        },
        "properties": {
            "frequencies": {
                weekday: {
                    "single_service": one_service_array,
                    "all_services": all_services_array,
                },
            },
            "runtime": {
                "min": _runtime(min_runtime_sec),
                "max": _runtime(max_runtime_sec),
            },
            "distance": _distance(distance_km),
            "speed": _speed(distance_km, max_runtime_sec),
        },
        "id": 1
    }


@app.route('/geojson/segments/v4/')
def geojson_frequency_v4():
    return geojson_frequency_v34(_one_feature_v4)


def geojson_frequency_v34(format_function):
    with database() as conn:
        statement_timeout(conn, 10)
        with conn.cursor() as cur:
            cur.execute("""
                with
                links_with_deduplication_applied as (
                    select
                        coalesce(dedup_from.canonical, link.from_stoppoint) as from_stoppoint,
                        coalesce(dedup_to.canonical, link.to_stoppoint) as to_stoppoint,

                        -- correct lseg if we deduplicated bus stops
                        -- (we calculate this each time, as there might not be any lseg using
                        -- both canonical bus stops!)
                        case
                            when dedup_from.canonical is null and dedup_to.canonical is null
                            then line_segment
                            else lseg(
                                coalesce(dedup_from.location, link.line_segment[0]),
                                coalesce(dedup_to.location, link.line_segment[1]))
                            end as line_segment,

                        weekday,
                        hour_array_total,
                        hour_array_best_service,
                        max_runtime,
                        min_runtime

                    from mv_link_frequency3 link

                    left join mv_stop_deduplication dedup_from on dedup_from.mapping = link.from_stoppoint
                    left join mv_stop_deduplication dedup_to on dedup_to.mapping = link.to_stoppoint

                    where lseg_bbox && box(point(%(minlat)s, %(minlng)s), point(%(maxlat)s, %(maxlng)s))
                    and weekday = %(weekday)s
                ),
                bus_per_hour_for_day as (
                    select
                        -- implicit group by on these columns
                        weekday,
                        from_stoppoint,
                        to_stoppoint,

                        -- this value could be null if canonical location is off map
                        first_value(line_segment) over (partition by weekday, from_stoppoint, to_stoppoint) as line_segment,

                        -- aggregates
                        min(min_runtime) over (partition by from_stoppoint, to_stoppoint) as min_runtime,
                        max(max_runtime) over (partition by from_stoppoint, to_stoppoint) as max_runtime,
                        hourarray_sum(hour_array_total::int[24]) over (partition by from_stoppoint, to_stoppoint) as hour_array_total,
                        hourarray_sum(hour_array_best_service::int[24]) over (partition by from_stoppoint, to_stoppoint) as hour_array_best_service

                    from links_with_deduplication_applied
                )
                select
                    from_stoppoint,
                    to_stoppoint,
                    (line_segment[0]::point)[0],
                    (line_segment[0]::point)[1],
                    (line_segment[1]::point)[0],
                    (line_segment[1]::point)[1],
                    weekday as weekday,
                    length(line_segment),
                    min_runtime,
                    max_runtime,
                    hour_array_total,
                    hour_array_best_service

                from bus_per_hour_for_day
                where line_segment is not null
                order by
                        (select sum(num) from unnest(hour_array_total) as per_hour(num)) desc
                limit %(limit)s;
                """, dict(
                    limit=request.args.get('limit', 10000),
                    minlat=request.args.get('minlat'),
                    minlng=request.args.get('minlng'),
                    maxlat=request.args.get('maxlat'),
                    maxlng=request.args.get('maxlng'),
                    weekday=request.args.get('weekday', 'M')))

            return json_response({
                "type": "FeatureCollection",
                "features": [
                    format_function(*row)
                    for row in cur
                ]
            })


"""
travelinedata=> CREATE MATERIALIZED VIEW mv_stop_deduplication AS
        with

        -- find bus stops located in roughly the same area and have buses
        -- going in the same direction (grouping by to_stoppoint)
        group_by_from as (
                select
                        ((line_segment[0]::point)[0])::numeric(8, 4) as grouped_lat,
                        ((line_segment[0]::point)[1])::numeric(8, 4) as grouped_lng,
                        to_stoppoint,
                        array_agg(distinct from_stoppoint) as array_from_stoppoint,
                        array_agg(line_segment[0]::point) as array_from_stoppoint_locations
                from mv_link_frequency3
                group by 1, 2, 3
        ),
        group_by_to as (
                select
                        ((line_segment[1]::point)[0])::numeric(8, 4) as grouped_lat,
                        ((line_segment[1]::point)[1])::numeric(8, 4) as grouped_lng,
                        from_stoppoint,
                        array_agg(distinct to_stoppoint) as array_to_stoppoint,
                        array_agg(line_segment[1]::point) as array_to_stoppoint_locations
                from mv_link_frequency3
                group by 1, 2, 3
        ),

        -- combine both queries. This isn't _quite_ the correct way to do this,
        -- as min(id) may not be the same
        all_mappings(canonical, location, mapping) as (
                select
                        -- unique identifier for this array of stoppoints
                        (select min(id) from unnest(array_from_stoppoint) as x(id)),

                        -- a location for this array of stoppoints
                        (select @@box(
                                point(
                                        min(location[0]),
                                        max(location[0])),
                                point(
                                        min(location[1]),
                                        max(location[1])))
                                from unnest(array_from_stoppoint_locations) as y(location)),

                        -- for each stoppoint in the array
                        unnest(array_from_stoppoint)

                        from group_by_from
                        where array_length(array_from_stoppoint, 1) > 1
                union all
                select
                        -- unique identifier for this array of stoppoints
                        (select min(id) from unnest(array_to_stoppoint) as x(id)),

                        -- a location for this array of stoppoints
                        (select @@box(
                                point(
                                        min(location[0]),
                                        max(location[0])),
                                point(
                                        min(location[1]),
                                        max(location[1])))
                                from unnest(array_to_stoppoint_locations) as y(location)),

                        -- for each stoppoint in the array
                        unnest(array_to_stoppoint)

                        from group_by_to
                        where array_length(array_to_stoppoint, 1) > 1
        ),

        -- all_mappings can have duplicate entries (one from array_from_stoppoint and
        -- one from array_to_stoppoint
        unique_mappings as (
                select
                        mapping,
                        array_agg(location) as location_array,
                        min(canonical) as canonical
                from all_mappings
                group by mapping
        )

        select
                mapping,
                canonical,
                location_array[1] as location
        from unique_mappings
WITH NO DATA;
REFRESH MATERIALIZED VIEW mv_stop_deduplication;
CREATE INDEX idx_stop_deduplication ON mv_stop_deduplication USING btree (mapping);
"""


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run()
