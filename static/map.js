window.addEventListener("load", function () {
	var mymap = L.map('mapid')

	/* map layers */

	var geo_layers = L.layerGroup().addTo(mymap);
	L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token={accessToken}', {
	    attribution: "Map data &copy; <a href=\"http://openstreetmap.org\">OpenStreetMap</a> contributors, <a href=\"http://creativecommons.org/licenses/by-sa/2.0/\">CC-BY-SA</a>, Imagery &copy; <a href=\"http://mapbox.com\">Mapbox</a>, Contains public sector information licensed under the Open Government Licence v3.0 from <a href=\"http://www.travelinedata.org.uk/\">Traveline National Dataset (TNDS)</a>, <a href=\"https://data.gov.uk/dataset/ff93ffc1-6656-47d8-9155-85ea0b8f2251/national-public-transport-access-nodes-naptan\">Naptan</a> and <a href=\"https://data.gov.uk/dataset/7dc36b99-9b5e-4475-91ab-ab16e1cabb6d/nhs-postcode-directory-latest-centroids\">NHS Postcode Directory</a>",
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

	var postcode_box_change = function (postcode) {
		$.ajax({
			"method": "GET",
			"url": "https://api.buildmorebuslanes.com/postcode/location/" + postcode,
			"dataType": "json"
		}).done(function (body) {
			if (body["lat"] !== undefined) {
				mymap.setView([body["lat"], body["lng"]], 15);
			}
		});
	}

	$("#postcode").autocomplete({
		minLength: 0,
		source: function(request, response) {
			$.ajax({
				"method": "GET",
				"url": "https://api.buildmorebuslanes.com/postcode/autocomplete/?prefix=" + request.term,
				"dataType": "json"
			}).done(function (body) {
				response(body["results"]);
			});
		},
		select: function(event, ui) {
			postcode_box_change(ui.item.label);
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
			"url": "https://api.buildmorebuslanes.com/geojson/segments/v4/",
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

	var weight_by_distance = function (feature) {
		/*
		Show long-distance routes with thin lines. Showing all these routes makes
		the interface very cluttered. (Besides, limited-stop services are only
		useful around their bus stops - it's probably correct to show them less
		prominently.)
		*/
		return feature.properties.distance.km > 2.0 ? 1.0 : 3.0
	};

	var obviously_wrong = function (feature) {
		/*
		NAPTAN does have some errors, where some bus stops are in the wrong place.
		I don't trust routes with very long gaps beteen bus stops (although these
		are sometimes correct for long-distance coach or rail services!)
		*/
		return feature.properties.distance.km > 4.0
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
					"weight": weight_by_distance(feature)
				};
			},
			filter: function (feature, layer) {
				if (obviously_wrong(feature)) {
					return false;
				}
				return color_freq(feature.properties.frequencies[weekday][frequency_type], hour) !== undefined;
			}
		});
	};

	function color_last_bus(frequencies) {
		if (frequencies[2] > 0 || frequencies[3] > 0) {
			return "#0000ff"
		} else if (frequencies[0] > 0 || frequencies[1] > 0) {
			return "#0077ff"
		} else if (frequencies[22] > 0 || frequencies[23] > 0) {
			return "#77ccff"
		} else if (frequencies[20] > 0 || frequencies[21] > 0) {
			return "#bbddff"
		} else if (frequencies[18] > 0 || frequencies[19] > 0) {
			return "#ddeeff"
		} else {
			/* not worth showing */
			/* also, array could be completetely full of zeros */
			return undefined;
		}
	}

	var on_change_lastbus = function() {
		var DOW = 'T';
		fetch_and_refresh_display(DOW, {
			style: function (feature) {
				var color = color_last_bus(feature.properties.frequencies[DOW].all_services);
				return {
					"color": color,
					"weight": weight_by_distance(feature)
				};
			},
			filter: function (feature, layer) {
				if (obviously_wrong(feature)) {
					return false;
				}
				var color = color_last_bus(feature.properties.frequencies[DOW].all_services);
				return color !== undefined;
			}
		});
	};

	function color_congestion(frequencies, journey_time, journey_length, geometry) {
		if ($(frequencies).filter(function (x) { return x != 0; }).length == 0) {
			/* no buses all day! */
			return undefined;
		}

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
			return "#eeddcc"
		} else if (speed > 9) {
			return "#ddc6aa"
		} else if (speed > 6) {
			return "#bb8866"
		} else if (speed > 3) {
			return "#774411"
		} else {
			return "#441100"
		}
	}

	var on_change_congestion = function() {
		var DOW = 'M'
		fetch_and_refresh_display(DOW, {
			style: function (feature) {
				var color = color_congestion(
					feature.properties.frequencies[DOW].all_services,
					feature.properties.runtime.max.s,
					feature.properties.distance.km,
					feature.geometry);
				return {
					"color": color,
					"weight": weight_by_distance(feature)
				};
			},
			filter: function (feature, layer) {
				if (obviously_wrong(feature)) {
					return false;
				}
				var color = color_congestion(
					feature.properties.frequencies[DOW].all_services,
					feature.properties.runtime.max.s,
					feature.properties.distance.km,
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
		var passengers_per_bus = assumptions.passengers_per_bus;
		var number_of_passengers = passengers_per_bus * number_of_buses;

		return seconds_saved_per_passenger * number_of_passengers;
	};

	function color_opportunities(frequencies, journey_time, journey_length, geometry, assumptions) {
		if ($(frequencies).filter(function (x) { return x != 0; }).length == 0) {
			/* no buses all day! */
			return undefined;
		}

		if (journey_time === undefined) {
			return undefined;
		} else if (journey_time < 1) {
			return undefined;
		}

		var time_saved = passenger_time_saved_per_day(journey_length, journey_time, frequencies, assumptions)
		var time_saved_hours = time_saved / 3600;

		var working_days_per_year = 52 * 5 /* 52 weeks/year * 5 days/week */
		var median_wage_per_day = assumptions.median_wage_per_year / working_days_per_year;
		var value_of_time_per_hour = median_wage_per_day / assumptions.hours_worked_per_day;

		var time_saved_cost = value_of_time_per_hour * time_saved_hours;
		var time_saved_cost_per_year = time_saved_cost * working_days_per_year;

		if (time_saved_cost_per_year < 10000) {
			return "#ffddee"
		} else if (time_saved_cost_per_year < 50000) {
			return "#ffccdd"
		} else if (time_saved_cost_per_year < 100000) {
			return "#ff77bb"
		} else if (time_saved_cost_per_year < 150000) {
			return "#ee4499"
		} else {
			return "#cc0077"
		}
	}

	var on_change_opportunities = function() {
		var DOW = 'M';
		var assumptions = {
			ideal_speed_mph: parseInt($("#oppy-speed").val()),
			distance_m: parseInt($("#oppy-distance").val()),
			passengers_per_bus: 11.1, /* https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/11854/annual-bus-statistics-2011-12.pdf#page=7 */
			median_wage_per_year: 21000,
			hours_worked_per_day: 37 / 5
		}
		fetch_and_refresh_display(DOW, {
			style: function (feature) {
				var color = color_opportunities(
					feature.properties.frequencies[DOW].all_services,
					feature.properties.runtime.max.s,
					feature.properties.distance.km,
					feature.geometry,
					assumptions);
				return {
					"color": color,
					"weight": weight_by_distance(feature)
				};
			},
			filter: function (feature, layer) {
				if (obviously_wrong(feature)) {
					return false;
				}
				var color = color_opportunities(
					feature.properties.frequencies[DOW].all_services,
					feature.properties.runtime.max.s,
					feature.properties.distance.km,
					feature.geometry,
					assumptions);
				return color !== undefined;
			}
		});
	};

	var on_change = function() {
		if (mymap.getZoom() <= 11) {
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

	mymap.setView([54.00366, -2.547855], 6);

	mymap.on('moveend', on_change);
	mymap.on('viewreset', on_change);
	mymap.on('load', on_change);

	$("#freq-time").on("change", on_change);
	$("#freq-weekday").on("change", on_change);
	$("input[name='freq-services']").on("change", on_change);
	$("#oppy-speed").on("change", on_change);
	$("#oppy-distance").on("change", on_change);

	if (window.location.hash) {
		var postcode_from_url = window.location.hash.substring(1);
		$("#postcode").val(postcode_from_url);
		postcode_box_change(postcode_from_url);
	} else {
		/* force some random search suggestions to appear */
		$("#postcode").autocomplete("search", "");
	}
});
