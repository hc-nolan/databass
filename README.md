# Overview

Databass is a music diary app. It's similar to RateYourMusic but meant for one user only. Data about releases, artists, and labels is retrieved mainly from MusicBrainz, but also from Discogs.

The app is still in early stages, so expect breaking changes in new releases. Currently development is focused solely on the desktop browser experience.

The intention for the app is to help you uncover your listening habits, and to that end there will eventually be more sophisticated statistics and charts. Currently, there are some basic statistics:
- Most frequent artist/label (by number of releases logged)
- Artists/labels with highest rating (simple average of all logged release ratings for that entity)
- Favourite label/artist
  - Uses [Bayesian average](https://en.wikipedia.org/wiki/Bayesian_average) to calculate a weighted average. This helps even out the ratings a bit so that the number of releases logged doesn't matter as much.
  - For instance, an artist with five releases each rated 80% has a higher Bayesian average than an artist with only two releases rated 80%

There are a few things to note before you use it:
- Rating is percentage based
- Album art is currently best-effort; an attempt will be made to grab it from CoverArtArchive and Discogs, but you have no control over what art is picked unless you edit the release after the fact

# Usage
Clone the repository, or just download the `docker-compose.yml` and `.env.example` files:
```shell
wget https://raw.githubusercontent.com/chunned/databass/main/docker-compose.yml
wget https://raw.githubusercontent.com/chunned/databass/main/.env.example
```

Rename `.env.example` to `.env` and fill out the required values:
- Set TIMEZONE to your local timezone for accurate listen date information
- If you want to use an external database you can change `PG_USER` and `PG_PASSWORD` (and `PG_PORT`, if needed)
- DISCOGS_KEY and DISCOGS_SECRET
  - Create an account at [Discogs.com](https://discogs.com)
  - Create a [new application](https://www.discogs.com/applications/edit)
  - Copy and paste`Consumer Key` -> `DISCOGS_KEY`
  - Copy and paste`Consumer Secret` -> `DISCOGS_SECRET`

Then, run `docker compose up --build -d` and visit the application at `localhost:<port>`



# Backup and restore
Backup:
```shell
# Note: change '-U postgres' if you change your databass user
sudo docker exec -it databass-postgres-1 pg_dump -U postgres databass > ./backup.sql
```
Restore:
```shell
sudo docker cp ./backup.yml databass-postgres-1:/backup.sql
sudo docker exec --user postgres -it databass-postgres-1 /bin/sh -c "psql databass < backup.sql"
```

Migrating the database (seldom required in new releases):

**Make sure you take a backup before doing this**
```shell
sudo docker exec -it databass-databass-1 sh -c "flask db init && flask db migrate && flask db upgrade"
```
