import os
import sqlite3
from contextlib import closing

import database

GROUP_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_FILE_PATH = os.path.join(GROUP_DIR, "schema.sql")


def create_tables() -> None:
    """create the group tables if they do not exist yet, keeping existing data"""
    with closing(database.get_connection()) as connection:
        database.run_sql_file(connection, SCHEMA_FILE_PATH)


def add_member(name: str) -> int:
    """save a new active member and return their id"""
    with closing(database.get_connection()) as connection:
        cursor = connection.execute("INSERT INTO members (name) VALUES (?)", (name,))
        connection.commit()
        return cursor.lastrowid


def get_member(member_id: int) -> dict | None:
    """return one member, or None if no member has that id"""
    with closing(database.get_connection()) as connection:
        row = connection.execute(
            "SELECT id, name, is_active FROM members WHERE id = ?", (member_id,)
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def list_members() -> list[dict]:
    """return every member, active and archived, sorted by name"""
    with closing(database.get_connection()) as connection:
        rows = connection.execute(
            "SELECT id, name, is_active FROM members ORDER BY name"
        ).fetchall()
    return _rows_to_dicts(rows)


def archive_member(member_id: int) -> bool:
    """mark a member inactive and return False if no member has that id"""
    return _set_member_active(member_id, 0)


def reactivate_member(member_id: int) -> bool:
    """mark an archived member active again and return False if no member has that id"""
    return _set_member_active(member_id, 1)


def create_night(
    night_date: str, available_minutes: int, attendee_ids: list[int], guest_names: list[str]
) -> int:
    """save a night with its attendees and guests in one transaction and return its id"""
    with closing(database.get_connection()) as connection:
        # the inner with commits only if every insert works, otherwise it rolls all of them back
        with connection:
            cursor = connection.execute(
                "INSERT INTO nights (night_date, available_minutes) VALUES (?, ?)",
                (night_date, available_minutes),
            )
            night_id = cursor.lastrowid

            for member_id in attendee_ids:
                connection.execute(
                    "INSERT INTO night_attendees (night_id, member_id) VALUES (?, ?)",
                    (night_id, member_id),
                )
            for guest_name in guest_names:
                connection.execute(
                    "INSERT INTO night_guests (night_id, guest_name) VALUES (?, ?)",
                    (night_id, guest_name),
                )
        return night_id


def get_night(night_id: int) -> dict | None:
    """return a night with its attendees and guests, or None if it does not exist"""
    with closing(database.get_connection()) as connection:
        night_row = connection.execute(
            "SELECT id, night_date, available_minutes FROM nights WHERE id = ?", (night_id,)
        ).fetchone()
        if night_row is None:
            return None

        attendee_rows = connection.execute(
            "SELECT members.id, members.name FROM night_attendees"
            " JOIN members ON members.id = night_attendees.member_id"
            " WHERE night_attendees.night_id = ? ORDER BY members.name",
            (night_id,),
        ).fetchall()
        guest_rows = connection.execute(
            "SELECT guest_name FROM night_guests WHERE night_id = ? ORDER BY guest_name",
            (night_id,),
        ).fetchall()

    night = dict(night_row)
    night["attendees"] = _rows_to_dicts(attendee_rows)
    night["guests"] = []
    for guest_row in guest_rows:
        night["guests"].append(guest_row["guest_name"])
    return night


def save_rating(member_id: int, game_id: int, score: int) -> None:
    """save a member's score for a game, replacing their old score if they had one"""
    with closing(database.get_connection()) as connection:
        connection.execute(
            "INSERT INTO ratings (member_id, game_id, score) VALUES (?, ?, ?)"
            " ON CONFLICT (member_id, game_id) DO UPDATE SET score = excluded.score",
            (member_id, game_id, score),
        )
        connection.commit()


def get_ratings_by_member(member_id: int) -> dict[int, int]:
    """return a member's scores as a dict of game id to score"""
    with closing(database.get_connection()) as connection:
        rows = connection.execute(
            "SELECT game_id, score FROM ratings WHERE member_id = ?", (member_id,)
        ).fetchall()
    scores = {}
    for row in rows:
        scores[row["game_id"]] = row["score"]
    return scores


def log_play(night_id: int, game_id: int) -> int:
    """record that a game was played on a night and return the play's id"""
    with closing(database.get_connection()) as connection:
        cursor = connection.execute(
            "INSERT INTO plays (night_id, game_id) VALUES (?, ?)", (night_id, game_id)
        )
        connection.commit()
        return cursor.lastrowid


def get_last_played_dates() -> dict[int, str]:
    """return a dict of game id to the date of the most recent night it was played"""
    with closing(database.get_connection()) as connection:
        rows = connection.execute(
            "SELECT plays.game_id, MAX(nights.night_date) AS last_played FROM plays"
            " JOIN nights ON nights.id = plays.night_id GROUP BY plays.game_id"
        ).fetchall()
    last_played_dates = {}
    for row in rows:
        last_played_dates[row["game_id"]] = row["last_played"]
    return last_played_dates


def get_unrated_plays() -> list[dict]:
    """return each active member and game they played at a night but never rated"""
    with closing(database.get_connection()) as connection:
        rows = connection.execute(
            "SELECT DISTINCT members.id AS member_id, members.name AS member_name, plays.game_id"
            " FROM members"
            " JOIN night_attendees ON night_attendees.member_id = members.id"
            " JOIN plays ON plays.night_id = night_attendees.night_id"
            " LEFT JOIN ratings ON ratings.member_id = members.id"
            " AND ratings.game_id = plays.game_id"
            " WHERE members.is_active = 1 AND ratings.member_id IS NULL"
            " ORDER BY members.name, plays.game_id"
        ).fetchall()
    return _rows_to_dicts(rows)


def _set_member_active(member_id: int, is_active: int) -> bool:
    """set a member's is_active flag and return False if no member has that id"""
    with closing(database.get_connection()) as connection:
        cursor = connection.execute(
            "UPDATE members SET is_active = ? WHERE id = ?", (is_active, member_id)
        )
        connection.commit()
        return cursor.rowcount > 0


def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    """turn sqlite rows into plain dicts so they can be returned as json"""
    results = []
    for row in rows:
        results.append(dict(row))
    return results
