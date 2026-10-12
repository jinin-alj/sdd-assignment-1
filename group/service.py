import sqlite3
from datetime import date

from group import repository
from library import repository as library_repository

NEVER_PLAYED_RATING = 10
UNRATED_RATING = 5
MAX_RECENCY_POINTS = 5
DAYS_PER_WEEK = 7
MIN_SCORE = 1
MAX_SCORE = 10


class NotFoundError(Exception):
    """raised when a member, night or game id does not exist"""


def rating_for_member(own_score: int | None, group_has_played: bool) -> int:
    """return the rating a member gives a game when planning a night"""
    # unplayed games get top marks so new games in the library actually get tried
    if not group_has_played:
        return NEVER_PLAYED_RATING
    if own_score is None:
        return UNRATED_RATING
    return own_score


def recency_points(last_played_date: str | None, night_date: str) -> int:
    """return 1 point per full week since the game was last played, capped at 5"""
    if last_played_date is None:
        return MAX_RECENCY_POINTS

    days_since_played = (date.fromisoformat(night_date) - date.fromisoformat(last_played_date)).days
    weeks_since_played = days_since_played // DAYS_PER_WEEK
    if weeks_since_played < 0:
        return 0
    if weeks_since_played > MAX_RECENCY_POINTS:
        return MAX_RECENCY_POINTS
    return weeks_since_played


def game_score(member_ratings: list[int], points: int) -> float:
    """return the average of the attendees' ratings plus the recency points"""
    average_rating = sum(member_ratings) / len(member_ratings)
    return average_rating + points


def fill_available_time(scored_games: list[dict], available_minutes: int) -> list[dict]:
    """pick games from highest score down, skipping any that no longer fit the time left"""
    planned_games = []
    minutes_left = available_minutes
    for game in sorted(scored_games, key=_plan_order):
        if game["playtime_minutes"] <= minutes_left:
            planned_games.append(game)
            minutes_left = minutes_left - game["playtime_minutes"]
    return planned_games


def add_member(name: str) -> dict:
    """add a new active member and return them"""
    clean_name = _check_text(name, "name")
    try:
        member_id = repository.add_member(clean_name)
    except sqlite3.IntegrityError as error:
        raise ValueError(f"a member named {clean_name} already exists") from error
    return repository.get_member(member_id)


def list_members() -> list[dict]:
    """return every member, active and archived, sorted by name"""
    return repository.list_members()


def archive_member(member_id: int) -> dict:
    """archive a member so their history stays but they stop counting, and return them"""
    if not repository.archive_member(member_id):
        raise NotFoundError(f"no member with id {member_id}")
    return repository.get_member(member_id)


def reactivate_member(member_id: int) -> dict:
    """bring an archived member back and return them"""
    if not repository.reactivate_member(member_id):
        raise NotFoundError(f"no member with id {member_id}")
    return repository.get_member(member_id)


def create_night(
    night_date: str, available_minutes: int, attendee_ids: list[int], guest_names: list[str]
) -> dict:
    """check and save a new night with its attendees and guests, and return it"""
    clean_date = _check_date(night_date, "night_date")
    _check_positive_whole_number(available_minutes, "available_minutes")

    if not isinstance(attendee_ids, list) or len(attendee_ids) == 0:
        raise ValueError("attendee_ids must be a list with at least one member id")
    for member_id in attendee_ids:
        _check_active_member(member_id)
    if len(set(attendee_ids)) != len(attendee_ids):
        raise ValueError("attendee_ids lists the same member more than once")

    if not isinstance(guest_names, list):
        raise ValueError("guest_names must be a list of names")
    clean_guest_names = []
    for guest_name in guest_names:
        clean_guest_names.append(_check_text(guest_name, "guest_names"))
    if len(set(clean_guest_names)) != len(clean_guest_names):
        raise ValueError("guest_names lists the same guest more than once")

    night_id = repository.create_night(clean_date, available_minutes, attendee_ids, clean_guest_names)
    return repository.get_night(night_id)


def get_night(night_id: int) -> dict:
    """return a night with its attendees and guests"""
    night = repository.get_night(night_id)
    if night is None:
        raise NotFoundError(f"no night with id {night_id}")
    return night


def save_rating(member_id: int, game_id: int, score: int) -> dict:
    """save or update a member's score for a game and return the saved rating"""
    _check_active_member(member_id)
    _check_game_exists(game_id)
    _check_positive_whole_number(score, "score")
    if score < MIN_SCORE or score > MAX_SCORE:
        raise ValueError(f"score must be between {MIN_SCORE} and {MAX_SCORE}")

    repository.save_rating(member_id, game_id, score)
    return {"member_id": member_id, "game_id": game_id, "score": score}


def log_play(night_id: int, game_id: int) -> dict:
    """record that a game was played on a night and return the play"""
    get_night(night_id)
    _check_game_exists(game_id)

    play_id = repository.log_play(night_id, game_id)
    return {"id": play_id, "night_id": night_id, "game_id": game_id}


def build_night_plan(night_id: int) -> dict:
    """plan a night by filling its time with the highest-scoring games that fit the group"""
    night = get_night(night_id)
    player_count = len(night["attendees"]) + len(night["guests"])
    candidate_games = library_repository.find_games_that_fit(
        player_count, night["available_minutes"]
    )

    scored_games = _score_games(candidate_games, night)
    planned_games = fill_available_time(scored_games, night["available_minutes"])

    minutes_used = 0
    for game in planned_games:
        minutes_used = minutes_used + game["playtime_minutes"]

    return {
        "night_id": night["id"],
        "night_date": night["night_date"],
        "player_count": player_count,
        "available_minutes": night["available_minutes"],
        "minutes_left": night["available_minutes"] - minutes_used,
        "games": planned_games,
    }


def rating_reminders() -> list[dict]:
    """return the games each active member played but has not rated yet"""
    reminders = repository.get_unrated_plays()
    for reminder in reminders:
        reminder["title"] = library_repository.get_game_title(reminder["game_id"])
    return reminders


def _score_games(candidate_games: list[dict], night: dict) -> list[dict]:
    """give every candidate game a score for the members attending this night"""
    last_played_dates = repository.get_last_played_dates()

    # load each attendee's ratings once instead of once per game
    attendee_ratings = []
    for attendee in night["attendees"]:
        attendee_ratings.append(repository.get_ratings_by_member(attendee["id"]))

    scored_games = []
    for game in candidate_games:
        last_played_date = last_played_dates.get(game["id"])
        group_has_played = last_played_date is not None

        member_ratings = []
        for ratings in attendee_ratings:
            member_ratings.append(rating_for_member(ratings.get(game["id"]), group_has_played))

        scored_games.append(
            {
                "game_id": game["id"],
                "title": game["title"],
                "playtime_minutes": game["playtime_minutes"],
                "last_played": last_played_date,
                "score": game_score(member_ratings, recency_points(last_played_date, night["night_date"])),
            }
        )
    return scored_games


def _plan_order(game: dict) -> tuple:
    """sort key that puts the highest score first and breaks ties by title"""
    return (-game["score"], game["title"])


def _check_active_member(member_id: int) -> None:
    """raise ValueError unless member_id belongs to an active member"""
    _check_positive_whole_number(member_id, "member_id")
    member = repository.get_member(member_id)
    if member is None or member["is_active"] == 0:
        raise ValueError(f"{member_id} is not the id of an active member")


def _check_game_exists(game_id: int) -> None:
    """raise NotFoundError unless the library has a game with this id"""
    _check_positive_whole_number(game_id, "game_id")
    # ratings and plays have no foreign key to games (ADR-3), so library is asked instead
    if library_repository.get_game_title(game_id) is None:
        raise NotFoundError(f"no game with id {game_id} in the library")


def _check_text(value, field_name: str) -> str:
    """raise ValueError unless value is non-empty text, and return it trimmed"""
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError(f"{field_name} must be non-empty text")
    return value.strip()


def _check_date(value, field_name: str) -> str:
    """raise ValueError unless value is a real YYYY-MM-DD date, and return it in that form"""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a date like 2026-10-12")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as error:
        raise ValueError(f"{field_name} must be a date like 2026-10-12") from error


def _check_positive_whole_number(value, field_name: str) -> None:
    """raise ValueError unless value is a whole number of at least 1"""
    # a copy of library's check on purpose, so each domain can be lifted out on its own (ADR-2)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field_name} must be a whole number of at least 1")
