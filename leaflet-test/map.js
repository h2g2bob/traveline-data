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
	mymap.setView([51.566, 0.698], 13);



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
					mymap.setView([body["lat"], body["lng"]], 13);
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

	mymap.on('moveend', function() {
		var bound = mymap.getBounds()

		$.ajax({
			"method": "GET",
			"url": "/geojson/",
			"datatype": "json",
			"data": {
				"minlat": bound.getSouth(),
				"maxlat": bound.getNorth(),
				"minlng": bound.getWest(),
				"maxlng": bound.getEast(),
			}
		}).done(function (data) {
			var geo_layer = L.geojson(data, {
				style: function (feature) {
					return feature.properties &&
						feature.properties.frequeny &&
						{color: color_freq(feature.properties.frequeny)};
				}
			});
			geo_layers.clearLayers();
			geo_layers.addLayer(geo_layer);
		});
	});


  });
