function Box(minslng, maxslng, minslat, maxslat) {
	this.minslng = minslng;
	this.maxslng = maxslng;
	this.minslat = minslat;
	this.maxslat = maxslat;
}
Box.prototype = {
	width: function () {
		return this.maxslng - this.minslng;
	},

	height: function () {
		return this.maxslat - this.minslat;
	},

	toString: function () {
		return "Box(" + this.minslng + ", " + this.maxslng + ", " + this.minslat + ", " + this.maxslat + ")";
	}
}

function TravelineDataMap(container, paint, slng, slat) {
	this.container = container;
	this.paint = paint;

	/* current top-left position, call pan() after changing this */
	this.slat = slat;
	this.slng = slng;

	/* set this.data_already_requested */
	this.zero_requested_data();
}
TravelineDataMap.prototype = {
	zero_requested_data: function () {
		/* currently we "requested" just a single point -- but we can build from this one point */
		this.paint.clear();
		this.data_already_requested = new Box(this.slng, this.slng, this.slat, this.slat);
	},

	current_viewport: function () {
		return new Box(
			this.slng,
			this.slng + this.paint.descale(this.container.offsetWidth),
			this.slat,
			this.slat + this.paint.descale(this.container.offsetHeight)
		);
	},

	fetch_more_data: function () {
		function min_freq_from_zoom(zoom) {
			if (zoom > 2000) {
				return "1";
			} else if (zoom > 500) {
				return "2";
			} else {
				return "4";
			}
		}


		this.paint.debug_show_requested_data("requested", this.data_already_requested);

		var next_download = this.calculate_region_to_dowload_next();

		if (next_download !== null) {
			var debug_name = "next_" + Math.random()
			var currently_downloading = this.paint.show_downloading_indication(next_download);

			console.log("should download " + next_download);

			/* show less accuracy at wider zoom levels */
			var min_freq = min_freq_from_zoom(this.paint.zoom);
			var url = "/json/?lat=" + slat2lat(next_download.minslat) + "&lng=" + slng2lng(next_download.minslng) + "&width=" + next_download.width() + "&height=" + next_download.height() + "&min_freq=" + min_freq;
			var that = this;
			var callback = function () {
				if (xmlhttpreq.readyState == 4) {
					that.paint.add_data(JSON.parse(xmlhttpreq.responseText));

					if (currently_downloading.parentNode !== null) {
						currently_downloading.parentNode.removeChild(currently_downloading);
					}
				}
			};

			var xmlhttpreq = new XMLHttpRequest();
			xmlhttpreq.addEventListener("load", callback);
			xmlhttpreq.open("GET", url);
			xmlhttpreq.send();
		}
	},

	pan: function() {
		this.paint.svg.setAttribute("transform", "translate(" + this.paint.scale(-this.slng) + "," + this.paint.scale(-this.slat) + ")");
	},

	calculate_region_to_dowload_next: function () {
		var max_single_request_size = 0.1;
		var min_single_request_size = 0.05;

		function increase_from(current, desired) {
			return Math.max(
				Math.min(desired, current + max_single_request_size),
				current + min_single_request_size);
		}
		function decrease_from(current, desired) {
			return Math.min(
				Math.max(desired, current - max_single_request_size),
				current - min_single_request_size);
		}

		var desired = this.current_viewport();
		this.paint.debug_show_requested_data("viewport", desired);

		if (desired.maxslat > this.data_already_requested.maxslat) {
			/* expand down */
			var old_maxslat = this.data_already_requested.maxslat;
			this.data_already_requested.maxslat = increase_from(this.data_already_requested.maxslat, desired.maxslat);
			return new Box(
				this.data_already_requested.minslng,
				this.data_already_requested.maxslng,
				old_maxslat,
				this.data_already_requested.maxslat
			);
		} else if (desired.minslat < this.data_already_requested.minslat) {
			/* expand up */
			var old_minslat = this.data_already_requested.minslat;
			this.data_already_requested.minslat = decrease_from(this.data_already_requested.minslat, desired.minslat);
			return new Box(
				this.data_already_requested.minslng,
				this.data_already_requested.maxslng,
				this.data_already_requested.minslat,
				old_minslat
			);
		} else if (desired.maxslng > this.data_already_requested.maxslng) {
			/* expand right */
			var old_maxslng = this.data_already_requested.maxslng;
			this.data_already_requested.maxslng = increase_from(this.data_already_requested.maxslng, desired.maxslng);
			return new Box(
				old_maxslng,
				this.data_already_requested.maxslng,
				this.data_already_requested.minslat,
				this.data_already_requested.maxslat
			);
		} else if (desired.minslng < this.data_already_requested.minslng) {
			/* expand left */
			var old_minslng = this.data_already_requested.minslng;
			this.data_already_requested.minslng = decrease_from(this.data_already_requested.minslng, desired.minslng);
			return new Box(
				this.data_already_requested.minslng,
				old_minslng,
				this.data_already_requested.minslat,
				this.data_already_requested.maxslat
			);
		} else {
			return null;
		}
	},

	run: function () {
		this.pan();
		window.setInterval(this.fetch_more_data.bind(this), 100);
	}
}

function TLDataPaint(svg) {
	this.zoom = 5000;
	this.svg = svg;
}
TLDataPaint.prototype = {
	scale: function (value) {
		/*
		you might think this is possible from transform=scale(1000) and
		stroke-width: 0.001px, but this only makes either invisible or
		thick lines
		*/
		return value * this.zoom;
	},

	descale: function (value) {
		return value / this.zoom;
	},

	add_data: function (data) {
		var paint = this;
		data["pairs"].forEach(function (pair) {
			var path_id = "path_" + pair["from"] + "_" + pair["to"];
			if (document.getElementById(path_id) === null) {
				var path_desc = paint.path_description(data, pair);
				if (path_desc !== null) {
					var path = document.createElementNS("http://www.w3.org/2000/svg", "path");
					path.setAttribute("id", path_id);
					path.setAttribute("d", path_desc);
					path.setAttribute("frequency", paint.frequency_label(pair["frequency"]));
					paint.svg.appendChild(path);
				}
			}
		});
		for (var key in data["stops"]) {
			if (!data["stops"].hasOwnProperty(key)) {
				continue;
			}
			var stop_id = "stop_" + key;
			var stop = data["stops"][key];
			if (document.getElementById(stop_id) === null) {
				var circ = document.createElementNS("http://www.w3.org/2000/svg", "circle");
				circ.setAttribute("id", stop_id);
				circ.setAttribute("cx", this.scale(lng2slng(stop["lng"])));
				circ.setAttribute("cy", this.scale(lat2slat(stop["lat"])));
				circ.setAttribute("r", 5);
				circ.setAttribute("class", "stop");
				circ.setAttribute("data-stop-id", key);
				circ.setAttribute("data-stop-name", stop["name"]);
				paint.svg.appendChild(circ);
			}
		};
	},

	clear: function() {
		for (var child = this.svg.firstChild; child !== null; child = this.svg.firstChild) {
			this.svg.removeChild(child);
		}
	},

	clear: function() {
		for (var child = this.svg.firstChild; child !== null; child = this.svg.firstChild) {
			this.svg.removeChild(child);
		}
	},

	show_downloading_indication: function (box) {
		var path = document.createElementNS("http://www.w3.org/2000/svg", "rect");
		path.setAttribute("y", this.scale(box.minslat));
		path.setAttribute("x", this.scale(box.minslng));
		path.setAttribute("height", this.scale(box.maxslat - box.minslat));
		path.setAttribute("width", this.scale(box.maxslng - box.minslng));
		path.setAttribute("class", "being-downloaded");
		this.svg.appendChild(path);
		return path;
	},

	debug_show_requested_data: function (name, box) {
		var path = document.getElementById(name);
		if (path == undefined) {
			var path = document.createElementNS("http://www.w3.org/2000/svg", "rect");
			path.setAttribute("id", name);
			path.setAttribute("class", "debug-marker");

			// add this at the top of the element list, so that it gets rendered first
			// ie: underneath the stops, which have user interaction
			// this is ugly because most browsers ignore z-index in svg:
			// https://developer.mozilla.org/en-US/docs/Web/SVG/SVG_2_support_in_Mozilla#Painting
			// oh, and insertChild cannot have a null option, fuck you w3c
			if (this.svg.firstChild !== undefined) {
				this.svg.insertBefore(path, this.svg.firstChild);
			} else {
				this.svg.appendChild(path);
			}
		}
		path.setAttribute("y", this.scale(box.minslat));
		path.setAttribute("x", this.scale(box.minslng));
		path.setAttribute("height", this.scale(box.maxslat - box.minslat));
		path.setAttribute("width", this.scale(box.maxslng - box.minslng));
	},

	path_description: function (data, pair) {
		var from_stop = data["stops"][pair["from"]];
		var to_stop = data["stops"][pair["to"]];
		if (from_stop === undefined || to_stop === undefined) {
			return null;
		}
		return "M " + this.scale(lng2slng(from_stop["lng"])) + " " + this.scale(lat2slat(from_stop["lat"])) + " L " + this.scale(lng2slng(to_stop["lng"])) + " " + this.scale(lat2slat(to_stop["lat"]));
	},

	frequency_label: function(buses_per_hour) {
		if (buses_per_hour >= 4) {
			return "high";
		} else if (buses_per_hour >= 2) {
			return "medium";
		} else {
			return "low";
		}
	}
};

window.addEventListener("load", function () {
	function number_from_url(key, dfault) {
		var match = RegExp(key + "=([0-9-\.]+)").exec(window.location.href);
		return match !== null ? parseFloat(match[1]) : dfault;
	}

	var paint = new TLDataPaint(document.getElementById("map_paint_area"));
	window.travelinedatamap = new TravelineDataMap(
		document.getElementById("map_paint_container"),
		paint,
		lng2slng(number_from_url("lng", 0.698)),
		lat2slat(number_from_url("lat", 51.566)));
	window.travelinedatamap.run();

	var step_size = 100

	function do_zoom(scale) {
		paint.zoom *= scale;

		/* positions of lines on the canvas change when zoom changes */
		window.travelinedatamap.zero_requested_data();

		/* which also means the pan position changes */
		window.travelinedatamap.pan();
	}

	window.addEventListener("keyup", function (event) {
		switch (event.key) {
			case "q":
				do_zoom(1.5);
				break;
			case "e":
				do_zoom(1/1.5);
				break;
			case "w":
				window.travelinedatamap.slat -= step_size/window.travelinedatamap.paint.zoom;
				window.travelinedatamap.pan();
				break;
			case "s":
				window.travelinedatamap.slat += step_size/window.travelinedatamap.paint.zoom;
				window.travelinedatamap.pan();
				break;
			case "a":
				window.travelinedatamap.slng -= step_size/window.travelinedatamap.paint.zoom;
				window.travelinedatamap.pan();
				break;
			case "d":
				window.travelinedatamap.slng += step_size/window.travelinedatamap.paint.zoom;
				window.travelinedatamap.pan();
				break;
		}
	});

	var drag_elem = document.getElementById("map_paint_container");
	var drag_start_x = undefined;
	var drag_start_y = undefined;
	drag_elem.addEventListener("mousedown", function (event) {
		drag_start_x = event.screenX;
		drag_start_y = event.screenY;
	}, false);
	drag_elem.addEventListener("mouseup", function (event) {
		drag_start_x = undefined;
		drag_start_y = undefined;
	}, false);
	drag_elem.addEventListener("mousemove", function (event) {
		if (drag_start_x !== undefined && drag_start_y !== undefined) {
			var change_x = event.screenX - drag_start_x;
			var change_y = event.screenY - drag_start_y;
			drag_start_x = event.screenX;
			drag_start_y = event.screenY;
			window.travelinedatamap.slat -= change_y/window.travelinedatamap.paint.zoom;
			window.travelinedatamap.slng -= change_x/window.travelinedatamap.paint.zoom;
			window.travelinedatamap.pan();
		}
	}, false);

	function add_control(label, action) {
		var btn = document.createElement("button");
		btn.textContent = label;
		btn.addEventListener("click", action, false);
		document.getElementById("controls").appendChild(btn);
	}
	add_control("+", function () { do_zoom(1.5); });
	add_control("-", function () { do_zoom(1/1.5); });
	add_control("N", function () {
		window.travelinedatamap.slat -= step_size/window.travelinedatamap.paint.zoom;
		window.travelinedatamap.pan();
	});
	add_control("S", function () {
		window.travelinedatamap.slat += step_size/window.travelinedatamap.paint.zoom;
		window.travelinedatamap.pan();
	});
	add_control("W", function () {
		window.travelinedatamap.slng -= step_size/window.travelinedatamap.paint.zoom;
		window.travelinedatamap.pan();
	});
	add_control("E", function () {
		window.travelinedatamap.slng += step_size/window.travelinedatamap.paint.zoom;
		window.travelinedatamap.pan();
	});

	window.addEventListener("mouseover", function (event) {
		if (event.target) {
			var stop_id = event.target.getAttribute("data-stop-id");
			var stop_name = event.target.getAttribute("data-stop-name");
			if (stop_name) {
				document.getElementById("stop_name").textContent = stop_id + ": " + stop_name;
			}
		}
	});

});

/*
longitude increases as the screen gets nearer the top of the screen, which is
the opposite of x/y in a web browser.
it's convenient to pretend that doesn't happen, and deal with "screen latitude"
instead.

probably this should be combined with "scale", but some actions (pressing "w"
to go up a certain number of pixels) would also need to be changed, which might
make this even more confusing.
*/
function lat2slat(lat) {
	return -lat;
}
function lng2slng(lng) {
	return lng;
}
function slat2lat(slat) {
	return -slat;
}
function slng2lng(slng) {
	return slng;
}


