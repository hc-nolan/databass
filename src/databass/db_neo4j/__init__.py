from flask import g
from neo4j import Driver, GraphDatabase, Session
from dotenv import load_dotenv
from pathlib import Path
from os import getenv

DOTENV_PATH = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(DOTENV_PATH)
NEO4J_USER = getenv("NEO4J_USER")
NEO4J_PASSWORD = getenv("NEO4J_PASSWORD")
NEO4J_AUTH = (NEO4J_USER, NEO4J_PASSWORD)
NEO4J_HOST = getenv("NEO4J_HOST")
NEO4J_DB = getenv("NEO4J_DATABASE")


def database_driver() -> Driver:
    """
    Create and return a connection to the Neo4j database
    """
    driver = GraphDatabase.driver(f"neo4j://{NEO4J_HOST}", auth=NEO4J_AUTH)
    driver.verify_connectivity()
    return driver


def get_db_driver() -> Driver:
    """
    Get the Neo4j driver for the current request context.
    If it does not exist, create it.
    """
    if "neo4j_driver" not in g:
        g.neo4j_driver = database_driver()
    return g.neo4j_driver


def get_db_session() -> Session:
    """
    Return a Neo4j session using the driver from the Flask app context.
    """
    driver = g.get("neo4j_driver")
    if not driver:
        driver = get_db_driver()
        g.neo4j_driver = driver
    return driver.session(database=NEO4J_DB)
