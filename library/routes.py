from flask import Blueprint, jsonify, request

from library import service

library_blueprint = Blueprint("library", __name__)


@library_blueprint.get("/games")
def list_games():
    """return every game in the library as json"""
    return jsonify(service.list_games())


@library_blueprint.post("/games")
def add_game():
    """add the game in the request body and return it with its new id"""
    # silent=True gives None for a missing or broken body, which validate_game rejects
    game = request.get_json(silent=True)
    try:
        saved_game = service.add_game(game)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify(saved_game), 201


@library_blueprint.get("/games/fit")
def find_games_that_fit():
    """return the games that fit the players and minutes query parameters"""
    # type=int gives None for a missing or non-numeric value, which the service rejects
    players = request.args.get("players", type=int)
    minutes = request.args.get("minutes", type=int)
    try:
        fitting_games = service.find_games_that_fit(players, minutes)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify(fitting_games)
