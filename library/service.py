from library import repository

TEXT_FIELDS = ["title", "owner"]
NUMBER_FIELDS = ["min_players", "max_players", "playtime_minutes"]


def validate_game(game: dict) -> None:
    """raise ValueError if a new game is missing a field or has impossible values"""
    if not isinstance(game, dict):
        raise ValueError("game must be a JSON object")

    for field_name in TEXT_FIELDS + NUMBER_FIELDS:
        if field_name not in game:
            raise ValueError(f"missing field: {field_name}")

    for field_name in TEXT_FIELDS:
        value = game[field_name]
        if not isinstance(value, str) or value.strip() == "":
            raise ValueError(f"{field_name} must be non-empty text")

    for field_name in NUMBER_FIELDS:
        _check_positive_whole_number(game[field_name], field_name)

    if game["max_players"] < game["min_players"]:
        raise ValueError("max_players must be at least min_players")


def add_game(game: dict) -> dict:
    """validate a new game, save it, and return it with its new id"""
    validate_game(game)

    # copy only the known fields so extra keys in the request never reach the database
    new_game = {
        "title": game["title"].strip(),
        "owner": game["owner"].strip(),
        "min_players": game["min_players"],
        "max_players": game["max_players"],
        "playtime_minutes": game["playtime_minutes"],
    }
    game_id = repository.add_game(new_game)

    saved_game = {"id": game_id}
    saved_game.update(new_game)
    return saved_game


def list_games() -> list[dict]:
    """return every game in the library, sorted by title"""
    return repository.list_games()


def find_games_that_fit(players: int, minutes: int) -> list[dict]:
    """return the games that suit this group size and time, after checking both values"""
    _check_positive_whole_number(players, "players")
    _check_positive_whole_number(minutes, "minutes")
    return repository.find_games_that_fit(players, minutes)


def _check_positive_whole_number(value, field_name: str) -> None:
    """raise ValueError unless value is a whole number of at least 1"""
    # bool is a subclass of int, so True and False have to be rejected on their own
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field_name} must be a whole number of at least 1")
