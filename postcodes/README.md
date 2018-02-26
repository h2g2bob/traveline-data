Go to https://data.gov.uk/dataset/nhs-postcode-directory-latest-centroids2

And:
```
wget 'http://geoportal1-ons.opendata.arcgis.com/datasets/675f07b52292428992709d0af98d86d9_0.csv' -O postcodepoints.csv
```

And:
```
xz -z postcodepoints.csv
```

And:
```
CREATE TABLE postcodes (
	postcode TEXT UNIQUE PRIMARY KEY,
	lat FLOAT NOT NULL,
	lng FLOAT NOT NULL);
```

And:
```
( echo "COPY postcodes (lat, lng, postcode) FROM stdin WITH (FORMAT csv);" && xzcat postcodepoints.csv.xz | tail -n +2 | cut -d , -f 1,2,4 | tr -d ' ' | grep -vE '^,,' ) | psql --single-transaction travelinedata
```
