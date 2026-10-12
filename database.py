import os
import sqlite3

import config

DATABASE_FILE_NAME = "game_nights.db"


def get_database_path() -> str:
    """return the full path of the sqlite file in the data directory"""
    return os.path.join(config.get_data_dir(), DATABASE_FILE_NAME)


def get_connection() -> sqlite3.Connection:
    """open a connection to the app database"""
    os.makedirs(config.get_data_dir(), exist_ok=True)
    connection = sqlite3.connect(get_database_path())
    # rows behave like dicts so routes can turn them into json easily
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def run_sql_file(connection: sqlite3.Connection, file_path: str) -> None:
    """run every statement in a .sql file"""
    with open(file_path, encoding="utf-8") as sql_file:
        connection.executescript(sql_file.read())
