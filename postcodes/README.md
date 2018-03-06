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
( echo "COPY postcodes (lng, lat, postcode) FROM stdin WITH (FORMAT csv);" && xzcat postcodepoints.csv.xz | tail -n +2 | cut -d , -f 1,2,4 | tr -d ' ' | grep -vE '^,,' ) | psql --single-transaction travelinedata
```

Also want to allow searching for "W1", not just "W11AA", so fake up some entries to make that easier:
```
with add_short_code as (
	select
		(regexp_matches(postcode, '^([A-Z]+[0-9]+)[0-9][A-Z][A-Z]$'))[1] as short,
		postcode,
		lat,
		lng
	from postcodes
),
ranked_codes as (
	select
		*,
		rank() over (partition by short order by postcode) as rank
	from add_short_code
),
best_rank as (
	select
		short,
		lat,
		lng
	from ranked_codes
	where rank = 1
)
insert into postcodes (postcode, lat, lng)
select short, lat, lng from best_rank;
```
