from pathlib import Path
from dotenv import load_dotenv
from os import getenv
import neo4j
from neo4j.exceptions import ClientError

DOTENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(DOTENV_PATH)

NEO4J_USER = getenv("NEO4J_USER")
NEO4J_PASSWORD = getenv("NEO4J_PASSWORD")
NEO4J_HOST = getenv("NEO4J_HOST")

neo4j_driver = neo4j.GraphDatabase.driver(
    f"neo4j://{NEO4J_HOST}", auth=(NEO4J_USER, NEO4J_PASSWORD)
)
neo4j_driver.verify_connectivity()


def create_nodes(driver: neo4j.GraphDatabase.driver):
    # Create country nodes
    driver.execute_query(
        """
        LOAD CSV WITH HEADERS FROM 'file:///release.csv' as row
        WITH row
        WHERE row.country IS NOT NULL
        MERGE (c:Country {name: row.country})
        """
    )
    driver.execute_query(
        """
        LOAD CSV WITH HEADERS FROM 'file:///artist.csv' as row
        WITH row
        WHERE row.country IS NOT NULL
        MERGE (c:Country {name: row.country})
        """
    )
    driver.execute_query(
        """
        LOAD CSV WITH HEADERS FROM 'file:///label.csv' as row
        WITH row
        WHERE row.country IS NOT NULL
        MERGE (c:Country {name: row.country})
        """
    )

    # Release nodes
    driver.execute_query(
        """
        LOAD CSV WITH HEADERS FROM 'file:///release.csv' as row
        MERGE (r:Release {releaseID: row.id})
          ON CREATE SET r.artistID = row.artist_id, r.labelID = row.label_id, r.year = row.year, r.runtime = row.runtime, r.rating = row.rating, r.listenDate = row.listen_date, r.trackCount = row.track_count, r.mainGenreID = row.main_genre_id, r.mbid = row.mbid, r.name = row.name, r.image = row.image, r.dateAdded = row.date_added;
        """
    )

    # Artist nodes
    driver.execute_query(
        """
        LOAD CSV WITH HEADERS FROM 'file:///artist.csv' as row
        MERGE (a:Artist {artistID: row.id})
          ON CREATE SET a.kind = row.type, a.begin = row.begin, a.end = row.end, a.mbid = row.mbid, a.name = row.name, a.image = row.image, a.dateAdded = row.date_added;
        """
    )

    # Label nodes
    driver.execute_query(
        """
        LOAD CSV WITH HEADERS FROM 'file:///label.csv' as row
        MERGE (l:Label {labelID: row.id})
          ON CREATE SET l.kind = row.type, l.begin = row.begin, l.end = row.end, l.mbid = row.mbid, l.name = row.name, l.image = row.image, l.dateAdded = row.date_added;
        """
    )
    driver.execute_query(
        """
        LOAD CSV WITH HEADERS FROM 'file:///genre.csv' as row
        MERGE (g:Genre {genreID: row.id})
          ON CREATE SET g.name = row.name, g.dateAdded = row.date_added;
        """
    )
    driver.execute_query(
        """
        LOAD CSV WITH HEADERS FROM 'file:///goal.csv' as row
        MERGE (g:Goal {goalID: row.id})
          ON CREATE SET g.start = row.start, g.end = row.end, g.completed = row.completed, g.kind = row.type, g.amount = row.amount, g.dateAdded = row.date_added;
        """
    )
    driver.execute_query(
        """
        LOAD CSV WITH HEADERS FROM 'file:///review.csv' as row
        MERGE (r:Review {reviewID: row.id})
          ON CREATE SET r.timestamp = row.timestamp, r.content = row.text, r.releaseID = row.release_id, r.dateAdded = row.date_added;
        """
    )


def create_indexes(driver: neo4j.GraphDatabase.driver):
    try:
        driver.execute_query(
            """
            CREATE INDEX release_id for (r:Release) on (r.id);
            """
        )
    except ClientError as e:
        if "EquivalentSchemaRuleAlreadyExists" in e.code:
            pass
        else:
            raise (e)

    try:
        driver.execute_query(
            """
            CREATE INDEX artist_id for (a:Artist) on (a.id);
            """
        )
    except ClientError as e:
        if "EquivalentSchemaRuleAlreadyExists" in e.code:
            pass
        else:
            raise (e)

    try:
        driver.execute_query(
            """
            CREATE INDEX label_id for (l:Label) on (l.id);
            """
        )
    except ClientError as e:
        if "EquivalentSchemaRuleAlreadyExists" in e.code:
            pass
        else:
            raise (e)

    try:
        driver.execute_query(
            """
            CREATE INDEX genre_id for (g:Genre) on (g.id);
            """
        )
    except ClientError as e:
        if "EquivalentSchemaRuleAlreadyExists" in e.code:
            pass
        else:
            raise (e)

    try:
        driver.execute_query(
            """
            CREATE INDEX goal_id for (g:Goal) on (g.id);
            """
        )
    except ClientError as e:
        if "EquivalentSchemaRuleAlreadyExists" in e.code:
            pass
        else:
            raise (e)

    try:
        driver.execute_query(
            """
            CREATE INDEX review_id for (r:Review) on (r.id);
            """
        )
    except ClientError as e:
        if "EquivalentSchemaRuleAlreadyExists" in e.code:
            pass
        else:
            raise (e)

    try:
        driver.execute_query(
            """
            CREATE CONSTRAINT release_mbid FOR (r:Release) REQUIRE r.mbid IS UNIQUE;
            """
        )
    except ClientError as e:
        if "EquivalentSchemaRuleAlreadyExists" in e.code:
            pass
        else:
            raise (e)
    try:
        driver.execute_query(
            """
            CREATE CONSTRAINT artist_mbid FOR (a:Artist) REQUIRE a.mbid IS UNIQUE;
            """
        )
    except ClientError as e:
        if "EquivalentSchemaRuleAlreadyExists" in e.code:
            pass
        else:
            raise (e)
    try:
        driver.execute_query(
            """
            CREATE CONSTRAINT label_mbid FOR (l:Label) REQUIRE l.mbid IS UNIQUE;
            """
        )
    except ClientError as e:
        if "EquivalentSchemaRuleAlreadyExists" in e.code:
            pass
        else:
            raise (e)
    try:
        driver.execute_query(
            """
            CREATE CONSTRAINT country_mbid FOR (c:Country) REQUIRE c.mbid IS UNIQUE;
            """
        )
    except ClientError as e:
        if "EquivalentSchemaRuleAlreadyExists" in e.code:
            pass
        else:
            raise (e)
    try:
        driver.execute_query(
            """
            CREATE CONSTRAINT genre_mbid FOR (g:Genre) REQUIRE g.mbid IS UNIQUE;
            """
        )
    except ClientError as e:
        if "EquivalentSchemaRuleAlreadyExists" in e.code:
            pass
        else:
            raise (e)


def create_relationships(driver: neo4j.GraphDatabase.driver):
    driver.execute_query(
        """
        LOAD CSV WITH HEADERS FROM 'file:///release.csv' as row
        MATCH (r:Release {releaseID: row.id})
        MATCH (a:Artist {artistID: row.artist_id})
        MERGE (r)-[m:MADE_BY]->(a)
        """
    )

    driver.execute_query(
        """
        LOAD CSV WITH HEADERS FROM 'file:///release.csv' as row
        MATCH (r:Release {releaseID: row.id})
        MATCH (l:Label {labelID: row.label_id})
        MERGE (r)-[m:RELEASED_BY]->(l)
        """
    )

    driver.execute_query(
        """
        LOAD CSV WITH HEADERS FROM 'file:///release.csv' as row
        MATCH (r:Release {releaseID: row.id})
        MATCH (g:Genre {genreID: row.main_genre_id})
        MERGE (r)-[m:HAS_GENRE]->(g)
        """
    )

    driver.execute_query(
        """
        LOAD CSV WITH HEADERS FROM 'file:///review.csv' as row
        MATCH (rev:Review {reviewID: row.id})
        MATCH (rel:Release {releaseID: row.release_id})
        MERGE (rev)-[a:IS_ABOUT]->(rel)
        """
    )

    driver.execute_query(
        """
        LOAD CSV WITH HEADERS FROM 'file:///rg.csv' as row
        MATCH (r:Release {releaseID: row.release_id})
        MATCH (g:Genre {genreID: row.genre_id})
        MERGE (r)-[:HAS_GENRE]->(g)
        """
    )

    # Country relationships
    driver.execute_query(
        """
        LOAD CSV WITH HEADERS FROM 'file:///release.csv' as row
        MATCH (r:Release {releaseID: row.id})
        MATCH (c:Country {name: row.country})
        MERGE (r)-[:RELEASED_IN]-(c)
        """
    )
    driver.execute_query(
        """
        LOAD CSV WITH HEADERS FROM 'file:///label.csv' as row
        MATCH (l:Label {labelId: row.id})
        MATCH (c:Country {name: row.country})
        MERGE (l)-[:IS_FROM]-(c)
        """
    )
    driver.execute_query(
        """
        LOAD CSV WITH HEADERS FROM 'file:///artist.csv' as row
        MATCH (a:Artist {artistID: row.id})
        MATCH (c:Country {name: row.country})
        MERGE (a)-[:IS_FROM]-(c)
        """
    )


with neo4j_driver as driver:
    create_nodes(driver)
    create_indexes(driver)
    create_relationships(driver)
