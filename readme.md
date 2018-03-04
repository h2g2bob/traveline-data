Traveline Data Viewer
=====================

Set up the server
-----------------

```sh
apt-get install \
	git \
	apache2 libapache2-mod-wsgi-py3 dehydrated \
	postgresql \
	python3 python3-psycopg2 python3-flask python3-lxml
```

```sh
adduser --system --shell=/bin/bash --disabled-password travelinedata
```

Make an apache config, see `example_apache.conf`

Set up Lets Encrypt: `vim /etc/dehydrated/domains.txt` and `dehydrated -c`

Make a new database:
```sh
sudo -u postgres createuser "travelinedata"
sudo -u postgres createdb travelinedata -O "travelinedata"
sudo -u postgres psql travelinedata -c 'CREATE SCHEMA travelinedata;'
sudo -u postgres psql travelinedata -c "GRANT ALL ON SCHEMA travelinedata TO travelinedata;"
sudo -u postgres psql travelinedata -c "ALTER USER travelinedata SET search_path TO 'travelinedata';"
```


Importing data from fresh
-------------------------

Delete all old data and create a new schema
```sh
python3 -m tlparser --destroy_create_tables
```

Add location of bus stops, by adding files to `naptandata/` and
```sh
python3 -m tlparser --naptan
```

Add location about postcodes, see `postcodes/readme.md`.

Add timetable data, by adding files to `travelinedata/` and
```sh
python3 -m tlparser --process
```

Transactions are committed after every xml file, so killing `--process` with
`Ctrl+C` is fine.

Calculate or re-calculate data tabes which are calculated from these values by
```sh
python3 -m tlparser --generate --matview
```

Run the server (which uses flask, so you should probably deploy that properly
like a normal flask site):
```sh
python3 server.py
```
