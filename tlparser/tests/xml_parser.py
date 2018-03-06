from ..traveline_xml_parser import parse_single_vj_elem
from ..traveline_xml_parser import NAMESPACES
from lxml.etree import XML
import unittest
import logging
from os.path import dirname
import datetime

class SingleVJ(unittest.TestCase):
	def test_single_vj(self):
		monday_of_desired_week = datetime.date(2018, 3, 12)
		with open(dirname(__file__) + "/single_vj.xml", mode='rb') as f:
			root = XML(f.read())
		[vjelem] = root.xpath("//tx:VehicleJourney", namespaces=NAMESPACES)
		rtn = parse_single_vj_elem(vjelem, monday_of_desired_week)
		[privatecode, jpref_id, vjcode, other_vjcode, linecode, days_bitmask, departuretime] = rtn
		self.assertEqual(privatecode, "cen-33-6-W-y11-13-287-UU")
		self.assertEqual(jpref_id, "JP_33-6-W-y11-13-35-I-5")
		self.assertEqual(vjcode, "VJ_33-6-W-y11-13-287-UU")
		self.assertEqual(other_vjcode, None)
		self.assertEqual(linecode, "33-6-W-y11-13")
		self.assertEqual(days_bitmask, 1<<6)
		self.assertEqual(departuretime, "08:48:00")

	def test_single_vj_excluded_date(self):
		monday_of_desired_week = datetime.date(2018, 3, 5)
		with open(dirname(__file__) + "/single_vj.xml", mode='rb') as f:
			root = XML(f.read())
		[vjelem] = root.xpath("//tx:VehicleJourney", namespaces=NAMESPACES)
		rtn = parse_single_vj_elem(vjelem, monday_of_desired_week)
		[_privatecode, _jpref_id, _vjcode, _other_vjcode, _linecode, days_bitmask, _departuretime] = rtn
		self.assertEqual(days_bitmask, 0)


if __name__ == '__main__':
	logging.basicConfig(level=logging.DEBUG)
	unittest.main()
