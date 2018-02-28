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


	/* data */

	var color_freq = function (freq) {
		if (freq >= 12) {
			return "#ff0000"
		} else if (freq >=8) {
			return "#ff7700"
		} else if (freq >=4) {
			return "#ffcc77"
		} else if (freq >=2) {
			return "#ffddbb"
		} else {
			return "#ffeedd"
		}
	};

	var on_change_frequencies = function() {
		var bound = mymap.getBounds();
		var HOUR = 12;
		var DAY = "M";

		$.ajax({
			"method": "GET",
			"url": "/geojson/",
			"datatype": "json",
			"data": {
				"minlat": bound.getSouth(),
				"maxlat": bound.getNorth(),
				"minlng": bound.getWest(),
				"maxlng": bound.getEast(),
				"dow": DAY
			}
		}).done(function (data) {
			var geo_layer = L.geoJSON(data, {
				style: function (feature) {
					return feature.properties &&
						feature.properties.frequencies &&
						{
							"color": color_freq(feature.properties.frequencies[HOUR]),
							"weight": feature.properties.length > 0.01 ? 1.0 : 3.0
						};
				},
				filter: function (feature, layer) {
					if (feature.properties.length > 0.2) {
						return false;  /* hide obviously flase long paths */
					}
					return feature.properties &&
						feature.properties.frequencies &&
						(feature.properties.frequencies[HOUR] >= 1)
				}
			});
			geo_layers.clearLayers();
			geo_layers.addLayer(geo_layer);
		});
	};

	function color_last_bus(properties) {
		if (!properties || !properties.frequencies) {
			return undefined
		}
		if (properties.frequencies[23] > 0) {
			return "#0000ff"
		} else if (properties.frequencies[22] > 0) {
			return "#0077ff"
		} else if (properties.frequencies[21] > 0) {
			return "#77ccff"
		} else if (properties.frequencies[20] > 0) {
			return "#bbddff"
		} else if (properties.frequencies[19] > 0) {
			return "#ddeeff"
		} else {
			/* not worth showing */
			/* also, array could be completetely full of zeros */
			return undefined;
		}
	}

	var on_change_lastbus = function() {
		var bound = mymap.getBounds();
		var DAY = "M";

		$.ajax({
			"method": "GET",
			"url": "/geojson/",
			"datatype": "json",
			"data": {
				"minlat": bound.getSouth(),
				"maxlat": bound.getNorth(),
				"minlng": bound.getWest(),
				"maxlng": bound.getEast(),
				"dow": DAY
			}
		}).done(function (data) {
			var geo_layer = L.geoJSON(data, {
				style: function (feature) {
					var color = color_last_bus(feature.properties);
					return {
						"weight": feature.properties.length > 0.01 ? 1.0 : 3.0,
						"color": color
					};
				},
				filter: function (feature, layer) {
					if (feature.properties.length > 0.2) {
						return false;  /* hide obviously flase long paths */
					}
					var color = color_last_bus(feature.properties);
					return color !== undefined;
				}
			});
			geo_layers.clearLayers();
			geo_layers.addLayer(geo_layer);
		});
	};

	function color_congestion(properties) {
		if (!properties || !properties.frequencies || !properties.length) {
			return undefined;
		}
		if ($(properties.frequencies).filter(function (x) { return x != 0; }).length == 0) {
			/* no buses all day! */
			return undefined;
		}

		var journey_time = properties.max_runtime;
		if (journey_time === undefined) {
			return undefined;
		} else if (journey_time < 1) {
			/* infinite speed, but still show it so that route can be followed */
			return "#ffffff";
		}

		/* speed in: micro arc-degrees per sec */
		var speed = 1000000 * properties.length / journey_time;

		if (speed >= 100) {
			return "#ffffff"
		} else if (speed >= 80) {
			return "#dddddd"
		} else if (speed >= 60) {
			return "#aaaaaa"
		} else if (speed >= 40) {
			return "#777777"
		} else if (speed >= 20) {
			return "#444444"
		} else {
			return "#000000"
		}
	}

	var on_change_congestion = function() {
		var bound = mymap.getBounds();
		var DAY = "M";

		$.ajax({
			"method": "GET",
			"url": "/geojson/",
			"datatype": "json",
			"data": {
				"minlat": bound.getSouth(),
				"maxlat": bound.getNorth(),
				"minlng": bound.getWest(),
				"maxlng": bound.getEast(),
				"dow": DAY
			}
		}).done(function (data) {
			var geo_layer = L.geoJSON(data, {
				style: function (feature) {
					var color = color_congestion(feature.properties);
					return {
						"weight": feature.properties.length > 0.01 ? 1.0 : 3.0,
						"color": color
					};
				},
				filter: function (feature, layer) {
					if (feature.properties.length > 0.2) {
						return false;  /* hide obviously flase long paths */
					}
					var color = color_congestion(feature.properties);
					return color !== undefined;
				}
			});
			geo_layers.clearLayers();
			geo_layers.addLayer(geo_layer);
		});
	};

	var on_change = function() {
		/* refetch and redraw */
		var active_tab = controls_ui.accordion("option", "active");
		if (active_tab == 2) {
			on_change_congestion();
		} else if (active_tab == 1) {
			on_change_lastbus();
		} else {
			on_change_frequencies();
		}
	};

	mymap.on('moveend', on_change);
	mymap.on('viewreset', on_change);
	mymap.on('load', on_change);
	mymap.setView([51.539691790887, 0.71413324224317], 15);

});
