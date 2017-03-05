Traveline Data Viewer
=====================


Getting started
---------------

Make a blank database:
```sh
sudo apt-get install python3-pscopg2 python3-flask python3-lxml libapache2-mod-wsgi-py3
sudo -u postgres createdb travelinedata -O "$USER"
python3 -m tlparser --destroy_create_tables
```

Add location of bus stops, by adding files to `naptandata/` and
```sh
python3 -m tlparser --naptan
```

Add location about postcodes, by adding files to `oscodepointdata/` and
```sh
python3 -m tlparser --codepoint
```

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
