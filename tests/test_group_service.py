import sqlite3

import pytest

from group import repository, service
from library import repository as library_repository


def add_library_game(title: str, min_players: int, max_players: int, playtime_minutes: int) -> int:
    """put a game straight into the library and return its id"""
    return library_repository.add_game(
        {
            "title": title,
            "owner": "Jinin",
            "min_players": min_players,
            "max_players": max_players,
            "playtime_minutes": playtime_minutes,
        }
    )


@pytest.fixture(autouse=True)
def empty_database(tmp_path, monkeypatch):
    """give every test its own empty database with both domains' tables"""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    library_repository.create_tables()
    repository.create_tables()


# rating rules


def test_rating_is_10_when_the_group_never_played_the_game():
    assert service.rating_for_member(own_score=None, group_has_played=False) == 10


def test_rating_is_10_for_a_never_played_game_even_if_the_member_rated_it():
    assert service.rating_for_member(own_score=3, group_has_played=False) == 10


def test_rating_is_5_when_the_game_was_played_but_the_member_never_rated_it():
    assert service.rating_for_member(own_score=None, group_has_played=True) == 5


def test_rating_is_the_members_own_score_once_played_and_rated():
    assert service.rating_for_member(own_score=8, group_has_played=True) == 8


# recency points


def test_recency_points_are_the_maximum_for_a_game_never_played():
    assert service.recency_points(last_played_date=None, night_date="2026-10-12") == 5


def test_recency_points_are_zero_for_a_game_played_less_than_a_week_ago():
    assert service.recency_points("2026-10-06", "2026-10-12") == 0


def test_recency_points_give_one_point_per_full_week():
    assert service.recency_points("2026-10-05", "2026-10-12") == 1
    assert service.recency_points("2026-09-22", "2026-10-12") == 2


def test_recency_points_are_capped_at_5():
    assert service.recency_points("2026-01-01", "2026-10-12") == 5


def test_recency_points_are_zero_when_last_play_is_after_the_night():
    assert service.recency_points("2026-10-20", "2026-10-12") == 0


# score


def test_game_score_is_the_average_rating_plus_recency_points():
    assert service.game_score(member_ratings=[10, 5], points=2) == 9.5


# filling the night


def test_fill_available_time_takes_the_highest_scores_first_and_skips_games_that_no_longer_fit():
    scored_games = [
        {"game_id": 1, "title": "Short", "playtime_minutes": 30, "score": 6},
        {"game_id": 2, "title": "Best", "playtime_minutes": 60, "score": 12},
        {"game_id": 3, "title": "Long", "playtime_minutes": 50, "score": 9},
    ]

    planned_games = service.fill_available_time(scored_games, available_minutes=90)

    planned_titles = []
    for game in planned_games:
        planned_titles.append(game["title"])
    assert planned_titles == ["Best", "Short"]


def test_fill_available_time_breaks_score_ties_by_title():
    scored_games = [
        {"game_id": 1, "title": "Zombies", "playtime_minutes": 30, "score": 7},
        {"game_id": 2, "title": "Azul", "playtime_minutes": 30, "score": 7},
    ]

    planned_games = service.fill_available_time(scored_games, available_minutes=30)

    assert planned_games[0]["title"] == "Azul"


# members


def test_add_member_trims_the_name_and_starts_active():
    member = service.add_member("  Sara  ")

    assert member == {"id": 1, "name": "Sara", "is_active": 1}


def test_add_member_rejects_a_blank_name():
    with pytest.raises(ValueError, match="name"):
        service.add_member("   ")


def test_add_member_rejects_a_duplicate_name():
    service.add_member("Sara")

    with pytest.raises(ValueError, match="already"):
        service.add_member("Sara")


def test_archive_and_reactivate_member_flip_is_active():
    member = service.add_member("Omar")

    assert service.archive_member(member["id"])["is_active"] == 0
    assert service.reactivate_member(member["id"])["is_active"] == 1


def test_archive_member_raises_not_found_for_an_unknown_id():
    with pytest.raises(service.NotFoundError):
        service.archive_member(999)


def test_reactivate_member_raises_not_found_for_an_unknown_id():
    with pytest.raises(service.NotFoundError):
        service.reactivate_member(999)


# nights


def test_create_night_saves_attendees_and_guests():
    sara = service.add_member("Sara")

    night = service.create_night("2026-10-12", 120, [sara["id"]], [" Nadia "])

    assert night["night_date"] == "2026-10-12"
    assert night["attendees"] == [{"id": sara["id"], "name": "Sara"}]
    assert night["guests"] == ["Nadia"]
    assert service.list_members()[0]["name"] == "Sara"


def test_create_night_rejects_a_date_that_is_not_a_real_date():
    sara = service.add_member("Sara")

    with pytest.raises(ValueError, match="night_date"):
        service.create_night("2026-02-30", 120, [sara["id"]], [])


def test_create_night_rejects_zero_minutes():
    sara = service.add_member("Sara")

    with pytest.raises(ValueError, match="available_minutes"):
        service.create_night("2026-10-12", 0, [sara["id"]], [])


def test_create_night_needs_at_least_one_member():
    with pytest.raises(ValueError, match="attendee_ids"):
        service.create_night("2026-10-12", 120, [], ["Nadia"])


def test_create_night_rejects_an_archived_member():
    sara = service.add_member("Sara")
    service.archive_member(sara["id"])

    with pytest.raises(ValueError, match="active member"):
        service.create_night("2026-10-12", 120, [sara["id"]], [])


def test_create_night_rejects_the_same_member_twice():
    sara = service.add_member("Sara")

    with pytest.raises(ValueError, match="more than once"):
        service.create_night("2026-10-12", 120, [sara["id"], sara["id"]], [])


def test_create_night_rejects_the_same_guest_twice():
    sara = service.add_member("Sara")

    with pytest.raises(ValueError, match="more than once"):
        service.create_night("2026-10-12", 120, [sara["id"]], ["Nadia", "Nadia"])


def test_create_night_rejects_guest_names_that_are_not_a_list():
    sara = service.add_member("Sara")

    with pytest.raises(ValueError, match="guest_names"):
        service.create_night("2026-10-12", 120, [sara["id"]], "Nadia")


def test_create_night_rolls_back_everything_when_one_insert_fails():
    sara_id = repository.add_member("Sara")

    # member 999 breaks the foreign key on the second insert, after the night row was written
    with pytest.raises(sqlite3.IntegrityError):
        repository.create_night("2026-10-12", 120, [sara_id, 999], [])

    assert repository.get_night(1) is None


def test_get_night_raises_not_found_for_an_unknown_id():
    with pytest.raises(service.NotFoundError):
        service.get_night(999)


# ratings


def test_save_rating_then_update_it():
    sara = service.add_member("Sara")
    azul_id = add_library_game("Azul", 2, 4, 45)

    service.save_rating(sara["id"], azul_id, 6)
    service.save_rating(sara["id"], azul_id, 9)

    assert repository.get_ratings_by_member(sara["id"]) == {azul_id: 9}


def test_save_rating_rejects_a_score_above_10():
    sara = service.add_member("Sara")
    azul_id = add_library_game("Azul", 2, 4, 45)

    with pytest.raises(ValueError, match="score"):
        service.save_rating(sara["id"], azul_id, 11)


def test_save_rating_rejects_a_game_the_library_does_not_have():
    sara = service.add_member("Sara")

    with pytest.raises(service.NotFoundError, match="game"):
        service.save_rating(sara["id"], 999, 7)


def test_save_rating_rejects_an_archived_member():
    sara = service.add_member("Sara")
    azul_id = add_library_game("Azul", 2, 4, 45)
    service.archive_member(sara["id"])

    with pytest.raises(ValueError, match="active member"):
        service.save_rating(sara["id"], azul_id, 7)


# plays and last played dates


def test_log_play_updates_the_last_played_date_to_the_latest_night():
    sara = service.add_member("Sara")
    azul_id = add_library_game("Azul", 2, 4, 45)
    first_night = service.create_night("2026-09-01", 120, [sara["id"]], [])
    second_night = service.create_night("2026-10-01", 120, [sara["id"]], [])

    service.log_play(second_night["id"], azul_id)
    service.log_play(first_night["id"], azul_id)

    assert repository.get_last_played_dates() == {azul_id: "2026-10-01"}


def test_log_play_rejects_an_unknown_night():
    azul_id = add_library_game("Azul", 2, 4, 45)

    with pytest.raises(service.NotFoundError, match="night"):
        service.log_play(999, azul_id)


def test_log_play_rejects_a_game_the_library_does_not_have():
    sara = service.add_member("Sara")
    night = service.create_night("2026-10-12", 120, [sara["id"]], [])

    with pytest.raises(service.NotFoundError, match="game"):
        service.log_play(night["id"], 999)


# night plan


def test_build_night_plan_puts_the_highest_scoring_games_first():
    sara = service.add_member("Sara")
    omar = service.add_member("Omar")
    azul_id = add_library_game("Azul", 2, 4, 45)
    pandemic_id = add_library_game("Pandemic", 2, 4, 45)
    add_library_game("Wingspan", 1, 5, 70)

    # azul was played last week and loved, pandemic was played last week and disliked
    last_week = service.create_night("2026-10-05", 120, [sara["id"], omar["id"]], [])
    service.log_play(last_week["id"], azul_id)
    service.log_play(last_week["id"], pandemic_id)
    service.save_rating(sara["id"], azul_id, 9)
    service.save_rating(omar["id"], azul_id, 7)
    service.save_rating(sara["id"], pandemic_id, 2)

    tonight = service.create_night("2026-10-12", 120, [sara["id"], omar["id"]], [])
    plan = service.build_night_plan(tonight["id"])

    # wingspan was never played: 10 + 5, azul: 8 + 1, pandemic: (2 + 5) / 2 + 1
    planned_titles = []
    for game in plan["games"]:
        planned_titles.append(game["title"])
    assert planned_titles == ["Wingspan", "Azul"]
    assert plan["games"][0]["score"] == 15
    assert plan["games"][1]["score"] == 9
    assert plan["minutes_left"] == 5


def test_build_night_plan_counts_guests_as_players():
    sara = service.add_member("Sara")
    add_library_game("Codenames", 4, 8, 15)

    without_guests = service.create_night("2026-10-12", 60, [sara["id"]], [])
    with_guests = service.create_night("2026-10-12", 60, [sara["id"]], ["Nadia", "Lina", "Rami"])

    assert service.build_night_plan(without_guests["id"])["games"] == []
    assert service.build_night_plan(with_guests["id"])["player_count"] == 4
    assert len(service.build_night_plan(with_guests["id"])["games"]) == 1


def test_build_night_plan_raises_not_found_for_an_unknown_night():
    with pytest.raises(service.NotFoundError):
        service.build_night_plan(999)


# rating reminders


def test_rating_reminders_list_games_a_member_played_but_never_rated():
    sara = service.add_member("Sara")
    omar = service.add_member("Omar")
    service.add_member("Lina")
    azul_id = add_library_game("Azul", 2, 4, 45)
    night = service.create_night("2026-10-12", 120, [sara["id"], omar["id"]], [])
    service.log_play(night["id"], azul_id)
    service.save_rating(omar["id"], azul_id, 8)

    reminders = service.rating_reminders()

    # omar already rated it and lina was not there, so only sara is reminded
    assert reminders == [
        {"member_id": sara["id"], "member_name": "Sara", "game_id": azul_id, "title": "Azul"}
    ]


def test_rating_reminders_skip_archived_members():
    sara = service.add_member("Sara")
    azul_id = add_library_game("Azul", 2, 4, 45)
    night = service.create_night("2026-10-12", 120, [sara["id"]], [])
    service.log_play(night["id"], azul_id)
    service.archive_member(sara["id"])

    assert service.rating_reminders() == []
