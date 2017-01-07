
#
# Daytime frequency of bus services between bus stop pairs:
#
# sqlite> select jptl.from_stoppoint, jptl.to_stoppoint, sum(hour_12) as daytime_busses_per_hour, count(distinct vjph.line_id) as different_lines  from jptiminglink jptl join journeypattern_service jps on jps.jpsectionref = jptl.jpsection join vehiclejourney_per_hour vjph on vjph.jpref = jps.jpref group by 1, 2;
#

