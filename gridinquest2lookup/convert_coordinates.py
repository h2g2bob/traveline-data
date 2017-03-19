# Grid InQuest II example calling GIQ dynamic library from Python.
#
# Copyright (C) 2016 Paul Michell, Michell Computing.
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Library General Public License as published by
# the Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Library General Public License
# for more details.

# This file is based on GridInQuestIIExample.py




# Setup required library imports.
import sys
import os
from math import degrees as rad2deg
from ctypes import *


# Download GridInQuestII from:
# https://www.ordnancesurvey.co.uk/business-and-government/help-and-support/navigation-technology/os-net/grid-inquest.html
# and put the directory containing the .so file here:
GRIDINQUEST_DIR=os.environ['GRIDINQUEST_DIR']
GRIDINQUEST_SO=os.path.join(GRIDINQUEST_DIR, "libgiq.so")

GIQLib = CDLL(GRIDINQUEST_SO)

# Define the library coordinate structure.
class coordinates(Structure):
	_fields_ = [
		("x", c_double),
		("y", c_double),
		("z", c_double)]


# Reference the library convert function.
Convert = GIQLib.ConvertCoordinates
Convert.argtypes = [
	c_int,
	c_int,
	c_int,
	c_int,
	POINTER(coordinates),
	POINTER(coordinates),
	POINTER(c_int)]
Convert.restype = bool


def convert_coordinates(easting, northing):

	# Code-Point Open has urn:ogc:def:crs:EPSG:27700
	# https://data.gov.uk/dataset/code-point-open1
	SRIDSource = c_int(27700)
	RevisionSource = c_int(0)

	# Convert to geodesic
	SRIDTarget = c_int(4937)
	RevisionTarget = c_int(0)

	Source = coordinates(easting, northing, 0) # Longitude, Latitude, Altitude.
	Target = coordinates(0, 0, 0)

	Datum = c_int(13) # Malin Head datum.

	# Call coordinate converter.
	CallOK = Convert(SRIDSource, SRIDTarget, RevisionSource, RevisionTarget, Source, Target, Datum)
	if not CallOK:
		raise Exception("Convert() failed!")

	lat = rad2deg(Target.y)
	lng = rad2deg(Target.x)
	return lat, lng


if __name__ == '__main__':
	print(convert_coordinates(588180, 186223))
