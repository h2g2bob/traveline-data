  window.addEventListener("load", function () {
	var mymap = L.map('mapid').setView([51.566, 0.698], 13);

	var handle_updated_viewport = function (){
		var pattern = "/json/?lat={lat}&lng={lng}&width={width}&height={height}&min_freq=1"

		var se = mymap.getBounds().getSouthEast();
		var nw = mymap.getBounds().getNorthWest();
		var url = pattern.
			replace("{lat}", nw.lat).
			replace("{lng}", nw.lng).
			replace("{height}", nw.lat - se.lat).
			replace("{width}", se.lng - nw.lng);

		var xhr = new XMLHttpRequest();
		xhr.open("GET", url, true);
		xhr.onreadystatechange = function () {
			if(xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
				apply_update(JSON.parse(xhr.responseText));
			}
		};
		xhr.send();
	}

	var cache = {
		points: {},
		lines: {}};
	var apply_update = function (data) {
		Object.entries(data["stops"]).forEach(function (keyvalue){
			cache["points"][keyvalue[0]] = keyvalue[1];
		});
		data["pairs"].forEach(function (pair){
			var key = "pair_" + pair["from"] + "_" + pair["to"];
			if (cache["lines"][key] === undefined) {
				cache["lines"][key] = pair;
				var from_point = cache["points"][pair["from"]];
				var to_point = cache["points"][pair["to"]];
				var polygon = L.polyline([
				    [from_point["lat"], from_point["lng"]],
				    [to_point["lat"], to_point["lng"]]
				], {
					color: color_freq(pair["frequency"])
				}).addTo(mymap);
			}
		});
	}

	var color_freq = function (freq) {
		if (freq >= 8) {
			return "#ff0000"
		} else if (freq >=4) {
			return "#ff7700"
		} else if (freq >=2) {
			return "#ffcc77"
		} else {
			return "#ffeedd"
		}
	};

	mymap.on('moveend', handle_updated_viewport)
	mymap.on('load', handle_updated_viewport)

	L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token={accessToken}', {
	    attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="http://mapbox.com">Mapbox</a>',
	    maxZoom: 18,
	    id: 'mapbox.light',
	    accessToken: 'pk.eyJ1IjoiaDJnMmJvYiIsImEiOiJjamUydDB1b3oxb3loMnFxbGdnbWZucmxlIn0.amXanuYenMfuUQxJb4ITKQ'
	}).addTo(mymap);

  });
