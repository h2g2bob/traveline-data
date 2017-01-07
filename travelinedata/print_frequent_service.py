#!/usr/bin/python3
import logging
import sqlite3


def main():
	with sqlite3.connect("data.sqlite3", isolation_level="DEFERRED") as conn:
		print_marginal_services(conn)
		print_frequent_services(conn)

def print_marginal_services(conn):
	print("Sections which have a services which runs every 30 minutes between 9am and 5pm:")
	cur = conn.cursor()
	cur.execute("""
		SELECT * FROM vehiclejourney_per_hour
		WHERE days_mask & 1
		AND hour_9 >= 2
		AND hour_10 >= 2
		AND hour_11 >= 2
		AND hour_12 >= 2
		AND hour_13 >= 2
		AND hour_14 >= 2
		AND hour_15 >= 2
		AND hour_16 >= 2
	""")
	for row in cur:
		print(row)

def print_frequent_services(conn):
	print("Sections which have a service every 15 minutes between 8am and 6pm, and hourly between 7am and 9pm:")
	cur = conn.cursor()
	cur.execute("""
		SELECT * FROM vehiclejourney_per_hour
		WHERE days_mask & 1
		AND hour_7 >= 1
		AND hour_8 >= 4
		AND hour_9 >= 4
		AND hour_10 >= 4
		AND hour_11 >= 4
		AND hour_12 >= 4
		AND hour_13 >= 4
		AND hour_14 >= 4
		AND hour_15 >= 4
		AND hour_16 >= 4
		AND hour_17 >= 4
		AND hour_18 >= 1
		AND hour_19 >= 1
		AND hour_20 >= 1
	""")
	for row in cur:
		print(row)


if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	main()
