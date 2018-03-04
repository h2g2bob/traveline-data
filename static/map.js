window.addEventListener("load", function () {
	var mymap = L.map('mapid')

	/* map layers */

	var geo_layers = L.layerGroup().addTo(mymap);
	L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token={accessToken}', {
	    attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery &copy; <a href="http://mapbox.com">Mapbox</a>, Contains public sector information licensed under the Open Government Licence v3.0 from <a href="http://www.travelinedata.org.uk/">Traveline National Dataset (TNDS)</a> and Naptan',
	    maxZoom: 18,
	    id: 'mapbox.light',
	    accessToken: 'pk.eyJ1IjoiaDJnMmJvYiIsImEiOiJjamUydDB1b3oxb3loMnFxbGdnbWZucmxlIn0.amXanuYenMfuUQxJb4ITKQ'
	}).addTo(mymap);


	/* controls */

	var controls_ui = $("#display").accordion({
		activate: function( event, ui ) {
			on_change();
		}
	});

	$("#postcode").autocomplete({
		source: function(request, response) {
			$.ajax({
				"method": "GET",
				"url": "/postcode/autocomplete/?prefix=" + request.term,
				"dataType": "json"
			}).done(function (body) {
				response(body["results"]);
			});
		},
		select: function(event, ui) {
			$.ajax({
				"method": "GET",
				"url": "/postcode/location/" + ui.item.label,
				"dataType": "json"
			}).done(function (body) {
				if (body["lat"] !== undefined) {
					mymap.setView([body["lat"], body["lng"]], 15);
				}
			});
		}
	});


	var show_frequency_drilldown = function () {
		$("#frequency-human").hide();
		$("#frequency-drilldown").show();
		$("#display").accordion("refresh");
	}
	$("#show-frequency-drilldown").on("click", show_frequency_drilldown);

	if ($("#freq-time").val() != "12"
	 || $("#freq-weekday").val() != "M"
	 || $("input[name='freq-services']:checked").val() != "all") {
		/* refreshing the page keeps old values in a form */
		/* so detect when this happens */
		show_frequency_drilldown();
	}

	var show_opportunities_drilldown = function () {
		$("#opportunities-human").hide();
		$("#opportunities-drilldown").show();
		$("#display").accordion("refresh");
	}
	$("#show-opportunities-drilldown").on("click", show_opportunities_drilldown);

	if ($("#oppy-speed").val() != "10"
	 || $("#oppy-distance").val() != "200") {
		/* refreshing the page keeps old values in a form */
		/* so detect when this happens */
		show_opportunities_drilldown();
	}


	/* data */

	var fetch_and_refresh_display = function(weekday, json_display_args) {
		var bound = mymap.getBounds();

		$.ajax({
			"method": "GET",
			"url": "/geojson/v3/links/",
			"datatype": "json",
			"data": {
				"minlat": bound.getSouth(),
				"maxlat": bound.getNorth(),
				"minlng": bound.getWest(),
				"maxlng": bound.getEast(),
				"weekday": weekday
			}
		}).done(function (data) {
			var geo_layer = L.geoJSON(data, json_display_args);
			geo_layers.clearLayers();
			geo_layers.addLayer(geo_layer);
		});
	};

	var color_freq = function (frequencies, hour) {
		var freq = frequencies[hour];
		if (freq >= 12) {
			return "#ff0000"
		} else if (freq >=8) {
			return "#ff7700"
		} else if (freq >=4) {
			return "#ffaa44"
		} else if (freq >=2) {
			return "#ffddbb"
		} else if (freq >0) {
			return "#ffeedd"
		} else {
			return undefined;
		}
	};

	var on_change_frequencies = function() {
		var hour = parseInt($("#freq-time").val());
		var weekday = $("#freq-weekday").val();
		var frequency_type = $("input[name='freq-services']:checked").val() == "all" ? "all_services" : "single_service";

		fetch_and_refresh_display(weekday, {
			style: function (feature) {
				return {
					"color": color_freq(feature.properties.frequencies[weekday][frequency_type], hour),
					"weight": feature.properties.length > 0.01 ? 1.0 : 3.0
				};
			},
			filter: function (feature, layer) {
				if (feature.properties.length > 0.2) {
					return false;  /* hide obviously flase long paths */
				}
				return color_freq(feature.properties.frequencies[weekday][frequency_type], hour) !== undefined;
			}
		});
	};

	function color_last_bus(frequencies) {
		if (frequencies[23] > 0) {
			return "#0000ff"
		} else if (frequencies[22] > 0) {
			return "#0077ff"
		} else if (frequencies[21] > 0) {
			return "#77ccff"
		} else if (frequencies[20] > 0) {
			return "#bbddff"
		} else if (frequencies[19] > 0) {
			return "#ddeeff"
		} else {
			/* not worth showing */
			/* also, array could be completetely full of zeros */
			return undefined;
		}
	}

	var on_change_lastbus = function() {
		var DOW = 'M';
		fetch_and_refresh_display(DOW, {
			style: function (feature) {
				var color = color_last_bus(feature.properties.frequencies[DOW].all_services);
				return {
					"weight": feature.properties.length > 0.01 ? 1.0 : 3.0,
					"color": color
				};
			},
			filter: function (feature, layer) {
				if (feature.properties.length > 0.2) {
					return false;  /* hide obviously flase long paths */
				}
				var color = color_last_bus(feature.properties.frequencies[DOW].all_services);
				return color !== undefined;
			}
		});
	};

	var deg2rad = function (deg) {
		/* https://stackoverflow.com/questions/27928/calculate-distance-between-two-latitude-longitude-points-haversine-formula */
		return deg * (Math.PI/180)
	}
	var distance_in_km = function (lat1, lon1, lat2, lon2) {
		/* https://stackoverflow.com/questions/27928/calculate-distance-between-two-latitude-longitude-points-haversine-formula */
		var R = 6371; // Radius of the earth in km
		var dLat = deg2rad(lat2-lat1);  // deg2rad below
		var dLon = deg2rad(lon2-lon1);
		var a =
			Math.sin(dLat/2) * Math.sin(dLat/2) +
			Math.cos(deg2rad(lat1)) * Math.cos(deg2rad(lat2)) *
			Math.sin(dLon/2) * Math.sin(dLon/2);
		var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
		var d = R * c; // Distance in km
		return d;
	}

	function color_congestion(frequencies, journey_time, geometry) {
		if ($(frequencies).filter(function (x) { return x != 0; }).length == 0) {
			/* no buses all day! */
			return undefined;
		}

		var journey_length = distance_in_km(
			geometry.coordinates[0][1],
			geometry.coordinates[0][0],
			geometry.coordinates[1][1],
			geometry.coordinates[1][0]);

		if (journey_time === undefined) {
			return undefined;
		} else if (journey_time < 1) {
			/* infinite speed, but still show it so that route can be followed */
			return "#cccccc";
		}

		/* speed in: mph */
		var mph_per_kmph = 0.6213712;
		var speed = mph_per_kmph * 3600 * journey_length / journey_time;

		if (speed > 12) {
			return "#ddccbb"
		} else if (speed > 8) {
			return "#cc9988"
		} else if (speed > 4) {
			return "#aa6666"
		} else if (speed > 2) {
			return "#884433"
		} else {
			return "#663300"
		}
	}

	var on_change_congestion = function() {
		var DOW = 'M'
		fetch_and_refresh_display(DOW, {
			style: function (feature) {
				var color = color_congestion(
					feature.properties.frequencies[DOW].all_services,
					feature.properties.runtime.max,
					feature.geometry);
				return {
					"weight": feature.properties.length > 0.01 ? 1.0 : 3.0,
					"color": color
				};
			},
			filter: function (feature, layer) {
				if (feature.properties.length > 0.2) {
					return false;  /* hide obviously flase long paths */
				}
				var color = color_congestion(
					feature.properties.frequencies[DOW].all_services,
					feature.properties.runtime.max,
					feature.geometry);
				return color !== undefined;
			}
		});
	};

	var passenger_time_saved_per_day = function (journey_length, journey_time, frequencies, assumptions) {
		var mph_per_kmph = 0.6213712;

		var ideal_speed_mph = assumptions.ideal_speed_mph;
		var ideal_speed_kmps = (ideal_speed_mph / mph_per_kmph) / 3600;

		var actual_speed_kmps = journey_length / journey_time;

		var distance_km = assumptions.distance_m / 1000;
		var travel_takes = distance_km / actual_speed_kmps;
		var ideal_travel_takes = distance_km / ideal_speed_kmps;

		var seconds_saved_per_passenger = travel_takes - ideal_travel_takes;

		var number_of_buses = 0;
		for (var i = 0; i < frequencies.length; ++i) {
			number_of_buses += frequencies[i];
		}
		var passengers_per_bus = 10;
		var number_of_passengers = passengers_per_bus * number_of_buses;

		return seconds_saved_per_passenger * number_of_passengers;
	};

	function color_opportunities(frequencies, journey_time, geometry, assumptions) {
		if ($(frequencies).filter(function (x) { return x != 0; }).length == 0) {
			/* no buses all day! */
			return undefined;
		}

		var journey_length = distance_in_km(
			geometry.coordinates[0][1],
			geometry.coordinates[0][0],
			geometry.coordinates[1][1],
			geometry.coordinates[1][0]);

		if (journey_time === undefined) {
			return undefined;
		} else if (journey_time < 1) {
			return undefined;
		}

		var time_saved = passenger_time_saved_per_day(journey_length, journey_time, frequencies, assumptions)
		var time_saved_hours = time_saved / 3600;
		var value_of_time = 10; /* average wage is 10 gbp/hour */
		var time_saved_cost = value_of_time * time_saved_hours;
		var time_saved_cost_per_year = time_saved_cost * 365;

		if (time_saved_cost_per_year < 10000) {
			return "#ddffee"
		} else if (time_saved_cost_per_year < 50000) {
			return "#99ffcc"
		} else if (time_saved_cost_per_year < 100000) {
			return "#55ffaa"
		} else if (time_saved_cost_per_year < 150000) {
			return "#33ff66"
		} else {
			return "#00ff00"
		}
	}

	var on_change_opportunities = function() {
		var DOW = 'M';
		var assumptions = {
			ideal_speed_mph: parseInt($("#oppy-speed").val()),
			distance_m: parseInt($("#oppy-distance").val())
		}
		fetch_and_refresh_display(DOW, {
			style: function (feature) {
				var color = color_opportunities(
					feature.properties.frequencies[DOW].all_services,
					feature.properties.runtime.max,
					feature.geometry,
					assumptions);
				return {
					"weight": feature.properties.length > 0.01 ? 1.0 : 3.0,
					"color": color
				};
			},
			filter: function (feature, layer) {
				if (feature.properties.length > 0.2) {
					return false;  /* hide obviously flase long paths */
				}
				var color = color_opportunities(
					feature.properties.frequencies[DOW].all_services,
					feature.properties.runtime.max,
					feature.geometry,
					assumptions);
				return color !== undefined;
			}
		});
	};

	var on_change = function() {
		if (mymap.getZoom() <= 10) {
			/* most web browsers will cry if you do this */
			return;
		}

		/* refetch and redraw */
		var active_tab = controls_ui.accordion("option", "active");
		if (active_tab == 0) {
			on_change_frequencies();
		} else if (active_tab == 1) {
			on_change_lastbus();
		} else if (active_tab == 2) {
			on_change_congestion();
		} else if (active_tab == 3) {
			on_change_opportunities();
		} else {
			/* no controls section selected? */
		}
	};

	mymap.on('moveend', on_change);
	mymap.on('viewreset', on_change);
	mymap.on('load', on_change);
	mymap.setView([51.539691790887, 0.71413324224317], 15);

	$("#freq-time").on("change", on_change);
	$("#freq-weekday").on("change", on_change);
	$("input[name='freq-services']").on("change", on_change);
	$("#oppy-speed").on("change", on_change);
	$("#oppy-distance").on("change", on_change);

});
