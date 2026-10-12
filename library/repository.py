import json
import os
import sqlite3
from contextlib import closing

import database

LIBRARY_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_FILE_PATH = os.path.join(LIBRARY_DIR, "schema.sql")
SEED_FILE_PATH = os.path.join(LIBRARY_DIR, "seed.json")

GAME_COLUMNS = "id, title, owner, min_players, max_players, playtime_minutes"


def create_tables() -> None:
    """create the library tables if they do not exist yet, keeping existing data"""
    with closing(database.get_connection()) as connection:
        database.run_sql_file(connection, SCHEMA_FILE_PATH)


def seed_games() -> int:
    """load the seed games into an empty games table and return how many were added"""
    with closing(database.get_connection()) as connection:
        game_count = connection.execute("SELECT COUNT(*) FROM games").fetchone()[0]
        # only seed a fresh database so restarts never duplicate or overwrite games
        if game_count > 0:
            return 0

        try:
            with open(SEED_FILE_PATH, encoding="utf-8") as seed_file:
                seed_data = json.load(seed_file)
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Could not read seed file {SEED_FILE_PATH}: {error}") from error

        for game in seed_data:
            _insert_game(connection, game)
        # one commit at the end so a broken seed file never leaves half the games behind
        connection.commit()
        return len(seed_data)


def add_game(game: dict) -> int:
    """save a game that has already been validated and return its new id"""
    with closing(database.get_connection()) as connection:
        game_id = _insert_game(connection, game)
        connection.commit()
        return game_id


def list_games() -> list[dict]:
    """return every game in the library, sorted by title"""
    with closing(database.get_connection()) as connection:
        rows = connection.execute(
            f"SELECT {GAME_COLUMNS} FROM games ORDER BY title"
        ).fetchall()
    return _rows_to_dicts(rows)


def find_games_that_fit(players: int, minutes: int) -> list[dict]:
    """return the games that support this many players and fit in this many minutes"""
    with closing(database.get_connection()) as connection:
        rows = connection.execute(
            f"SELECT {GAME_COLUMNS} FROM games"
            " WHERE min_players <= ? AND max_players >= ? AND playtime_minutes <= ?"
            " ORDER BY title",
            (players, players, minutes),
        ).fetchall()
    return _rows_to_dicts(rows)


def get_game_title(game_id: int) -> str | None:
    """return the title of a game, or None if no game has that id"""
    with closing(database.get_connection()) as connection:
        row = connection.execute(
            "SELECT title FROM games WHERE id = ?", (game_id,)
        ).fetchone()
    if row is None:
        return None
    return row["title"]


def _insert_game(connection: sqlite3.Connection, game: dict) -> int:
    """insert one game without committing and return its new id"""
    cursor = connection.execute(
        "INSERT INTO games (title, owner, min_players, max_players, playtime_minutes)"
        " VALUES (?, ?, ?, ?, ?)",
        (
            game["title"],
            game["owner"],
            game["min_players"],
            game["max_players"],
            game["playtime_minutes"],
        ),
    )
    return cursor.lastrowid


def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    """turn sqlite rows into plain dicts so they can be returned as json"""
    games = []
    for row in rows:
        games.append(dict(row))
    return games
