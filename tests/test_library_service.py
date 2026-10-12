import pytest

from library import repository, service


def make_game(**changes) -> dict:
    """return a valid game, with any fields overridden by the test"""
    game = {
        "title": "Azul",
        "owner": "Omar",
        "min_players": 2,
        "max_players": 4,
        "playtime_minutes": 45,
    }
    game.update(changes)
    return game


@pytest.fixture(autouse=True)
def empty_library(tmp_path, monkeypatch):
    """give every test its own empty database file so tests never share data"""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    repository.create_tables()


def test_validate_game_accepts_a_valid_game():
    service.validate_game(make_game())


def test_validate_game_accepts_equal_min_and_max_players():
    service.validate_game(make_game(min_players=2, max_players=2))


def test_validate_game_rejects_data_that_is_not_a_dict():
    with pytest.raises(ValueError, match="JSON object"):
        service.validate_game(["Azul"])


@pytest.mark.parametrize(
    "missing_field", ["title", "owner", "min_players", "max_players", "playtime_minutes"]
)
def test_validate_game_rejects_a_missing_field(missing_field):
    game = make_game()
    del game[missing_field]
    with pytest.raises(ValueError, match=missing_field):
        service.validate_game(game)


def test_validate_game_rejects_a_blank_title():
    with pytest.raises(ValueError, match="title"):
        service.validate_game(make_game(title="   "))


def test_validate_game_rejects_an_owner_that_is_not_text():
    with pytest.raises(ValueError, match="owner"):
        service.validate_game(make_game(owner=42))


def test_validate_game_rejects_max_players_below_min_players():
    with pytest.raises(ValueError, match="max_players"):
        service.validate_game(make_game(min_players=4, max_players=2))


def test_validate_game_rejects_zero_min_players():
    with pytest.raises(ValueError, match="min_players"):
        service.validate_game(make_game(min_players=0))


def test_validate_game_rejects_zero_minutes():
    with pytest.raises(ValueError, match="playtime_minutes"):
        service.validate_game(make_game(playtime_minutes=0))


def test_validate_game_rejects_negative_minutes():
    with pytest.raises(ValueError, match="playtime_minutes"):
        service.validate_game(make_game(playtime_minutes=-30))


def test_validate_game_rejects_numbers_sent_as_text():
    with pytest.raises(ValueError, match="playtime_minutes"):
        service.validate_game(make_game(playtime_minutes="45"))


def test_validate_game_rejects_true_as_a_number():
    # bool is a subclass of int in python, so True would otherwise count as 1
    with pytest.raises(ValueError, match="min_players"):
        service.validate_game(make_game(min_players=True))


def test_add_game_saves_the_game_and_returns_it_with_an_id():
    saved_game = service.add_game(make_game(title="  Azul  "))

    assert saved_game["id"] == 1
    assert saved_game["title"] == "Azul"
    assert service.list_games() == [saved_game]


def test_add_game_ignores_unknown_fields():
    saved_game = service.add_game(make_game(rating=10))

    assert "rating" not in saved_game
    assert "rating" not in service.list_games()[0]


def test_add_game_does_not_save_an_invalid_game():
    with pytest.raises(ValueError):
        service.add_game(make_game(max_players=1))

    assert service.list_games() == []


def test_list_games_is_sorted_by_title():
    service.add_game(make_game(title="Wingspan"))
    service.add_game(make_game(title="Azul"))

    titles = []
    for game in service.list_games():
        titles.append(game["title"])
    assert titles == ["Azul", "Wingspan"]


def test_find_games_that_fit_includes_games_at_the_exact_limits():
    service.add_game(make_game(title="Azul", min_players=2, max_players=4, playtime_minutes=45))

    assert len(service.find_games_that_fit(players=2, minutes=45)) == 1
    assert len(service.find_games_that_fit(players=4, minutes=45)) == 1


def test_find_games_that_fit_leaves_out_games_that_do_not_fit():
    service.add_game(make_game(title="Azul", min_players=2, max_players=4, playtime_minutes=45))
    service.add_game(make_game(title="Codenames", min_players=4, max_players=8, playtime_minutes=15))
    service.add_game(make_game(title="Twilight Imperium", min_players=3, max_players=6, playtime_minutes=480))

    fitting_games = service.find_games_that_fit(players=3, minutes=60)

    assert len(fitting_games) == 1
    assert fitting_games[0]["title"] == "Azul"


def test_find_games_that_fit_rejects_zero_players():
    with pytest.raises(ValueError, match="players"):
        service.find_games_that_fit(players=0, minutes=60)


def test_find_games_that_fit_rejects_missing_minutes():
    # the route passes None when the minutes query parameter is missing or not a number
    with pytest.raises(ValueError, match="minutes"):
        service.find_games_that_fit(players=4, minutes=None)


def test_get_game_title_returns_the_title_for_a_known_id():
    saved_game = service.add_game(make_game(title="Pandemic"))

    assert repository.get_game_title(saved_game["id"]) == "Pandemic"


def test_get_game_title_returns_none_for_an_unknown_id():
    assert repository.get_game_title(999) is None


def test_seed_games_fills_an_empty_library():
    added_count = repository.seed_games()

    assert added_count > 0
    assert len(service.list_games()) == added_count


def test_seed_games_does_nothing_on_a_second_boot():
    first_count = repository.seed_games()

    assert repository.seed_games() == 0
    assert len(service.list_games()) == first_count


def test_seed_games_does_not_touch_a_library_that_already_has_games():
    service.add_game(make_game())

    assert repository.seed_games() == 0
    assert len(service.list_games()) == 1


def test_create_tables_keeps_existing_games():
    service.add_game(make_game())

    repository.create_tables()

    assert len(service.list_games()) == 1
