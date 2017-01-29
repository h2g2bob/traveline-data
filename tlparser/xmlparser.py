#!/usr/bin/python3
# encoding: utf8

from lxml import etree
import logging

def process_xml_file(xmlfile, parsers, args):
	for tagname, elem in iter_elements(xmlfile, parsers.keys()):
		try:
			parser_func = parsers[tagname]
			parser_func(elem, *args)
		except Exception:
			logging.exception("error parsing element: %r %r", args, tagname)
			logging.info("detail: %s", etree.tostring(elem))
			raise # or return to ignore exceptions

def iter_elements(xmlfile, interesting_tags):
	"""Parses a large xmlfile, yielding any listed tag.

	Removes tags from the tree after yielding: do not mark nested
	tags as interesting.
	"""
	parser = etree.XMLPullParser(events=("end",), no_network=True)
	while True:
		data = xmlfile.read(1024)
		if not data:
			break
		parser.feed(data)
		for action, elem in parser.read_events():
			tagname = elem.tag.split("}")[-1]
			if tagname in interesting_tags:
				yield tagname, elem
				cleanup(elem)
	parser.close()

def cleanup(element):
	"""Deletes element from the tree.

	This avoids using lots of memory when the file is very large
	(without this, all nodes reference all others, via .parent)
	"""
	element.clear()                 # clean up children
	while element.getprevious() is not None:
		del element.getparent()[0]  # clean up preceding siblings
