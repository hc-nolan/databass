Instructions for how to migrate from <v0.6 (Postgres) to v0.7 (Neo4j)

# Export from postgres

```shell
sudo docker exec -it databass-postgres-1 /bin/sh
psql -U postgres -d databass
COPY (SELECT * FROM artist) TO '/tmp/artist.csv' WITH CSV header;
COPY (SELECT * FROM genre) TO '/tmp/genre.csv' WITH CSV header;
COPY (SELECT * FROM goal) TO '/tmp/goal.csv' WITH CSV header;
COPY (SELECT * FROM label) TO '/tmp/label.csv' WITH CSV header;
COPY (SELECT * FROM release) TO '/tmp/release.csv' WITH CSV header;
COPY (SELECT * FROM review) TO '/tmp/review.csv' WITH CSV header;
\q
mkdir /db_export
mv /tmp/*.csv /db_export/
exit

sudo docker cp databass-postgres-1:/db_export .
```

# Import to Neo4j container

```shell
sudo docker cp db_export databass-neo4j-1:/
sudo docker exec databass-neo4j-1 sh -c 'cd /db_csv && mv * /var/lib/neo4j/import/'
```

# Migrate

Open `migrate-0.6-to-0.7.py`, make sure connection values are correct, then run it

# TODO: populate genres and countries with MBID/other values i.e. country code

