Database schema
===============

`mv_link_frequency`
-------------------

How many buses an hour are there between two bus stops (`stoppoint`s), including the geolocations (`line`).

This is actually a view into `mv_link_frequency_*` tables, which each have a gist index on the geolocation data (line).


`vehiclejourney`
----------------

PK: `vjcode_id`

A bus which departs at `deptime` (for the days in `days_mask`) and goes on the path described by `journeypattern_id`.


`journeypattern_bounding_box`
-----------------------------

FK: `journeypattern_id`

Efficient queries


`journeypattern_service`
------------------------

PK: `journeypattern_id`

Links to `service_id` and `route_id`


`journeypattern_section`
------------------------

PK: `jpsection_id`

Links to `journeypattern_id`


`jptiminglink`
--------------

PK: `jptiminglink_id`

A line between two bus stops (`stoppoint`s) with timing (`runtime`) information for a given bus route (`routelink_id`).

The line belongs to a `jpsection_id` and `jptiminglink_id`.


`line`
------

PK: `line_id`

The number on the front of the bus.


`route`
-------

PK: `route_id`


`routelink`
-----------

PK: `routelink_id`

A line between two bus stops (`stoppoint`s).


`service`
---------

PK: `service_id`
