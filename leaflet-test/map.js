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

	$("#display").accordion();

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

	var on_change = function() {
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
						{color: color_freq(feature.properties.frequencies[HOUR])};
				},
				filter: function (feature, layer) {
					return feature.properties &&
						feature.properties.frequencies &&
						(feature.properties.frequencies[HOUR] >= 1)
				}
			});
			geo_layers.clearLayers();
			geo_layers.addLayer(geo_layer);
		});
	};
	mymap.on('moveend', on_change);
	mymap.on('viewreset', on_change);
	mymap.on('load', on_change);
	mymap.setView([51.539691790887, 0.71413324224317], 15);
});
