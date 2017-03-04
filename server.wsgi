#!/usr/bin/python3

import sys
import os
HERE = os.path.dirname(__file__)

os.chdir(HERE)

# Make sure library code is in the path
sys.path.append(HERE)

# magic required for wsgi
from server import app as application

# Set up logging
import logging
from logging.handlers import RotatingFileHandler
file_handler = RotatingFileHandler(HERE + '/server.log', maxBytes=20 * 1024 * 1024, backupCount=3)
file_handler.setLevel(logging.WARNING)
application.logger.addHandler(file_handler)
