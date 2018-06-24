# Postcodes



## Get the data

Go to https://data.gov.uk/dataset/nhs-postcode-directory-latest-centroids2

And:
```
wget 'http://geoportal1-ons.opendata.arcgis.com/datasets/675f07b52292428992709d0af98d86d9_0.csv' -O postcodepoints.csv
```

And:
```
xz -z postcodepoints.csv
```


## Import the data

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


## Make short codes

We want to allow searching for "W1", not just "W11AA".

Fake up some entries to make that easier:
```
CREATE MATERIALIZED VIEW postcodes_short AS
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
select short AS postcode, lat, lng from best_rank;

create index idx_postcodes_short on postcodes_short using btree (postcode);
```


## Pre-generate search suggestions

Suggestions for "W" should be: "W1...", "W2...", "W3...", etc. (Really,
this means "W11AA", "W21AA", "W31AA", etc.)

To do this query for a given prefix takes 800ms, which is unacceptably slow.

So we can pre-calculate all of this. The query below takes 5 minutes to make
a 250MB table, but is totally worth it:

```
create materialized view postcode_prefix_lookup as
with all_postcodes as (
        select postcode, lat, lng from postcodes
        union
        select postcode, lat, lng from postcodes_short
), lengths as (
        select
                num
        from generate_series(1, 10) num
), next_character_suggestion as (
        select
                substring(postcode, 1, num) as prefix,
                substring(postcode, 1, num+1) as longer_prefix,
                min(postcode) as postcode_suggestion
        from all_postcodes
        cross join lengths
        group by prefix, longer_prefix
), ordered_suggestions as (
        select
                prefix,
                postcode_suggestion,
                rank() over (partition by prefix order by postcode_suggestion asc) as seq
        from next_character_suggestion
        order by prefix, seq)
select prefix, array_agg(postcode_suggestion) as suggestions
from ordered_suggestions where seq <= 10
group by prefix;

create index idx_postcode_prefix_lookup on postcode_prefix_lookup using btree (prefix);
```
