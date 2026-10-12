from flask import Blueprint, jsonify, request

from group import service

group_blueprint = Blueprint("group", __name__)


@group_blueprint.errorhandler(ValueError)
def bad_request(error):
    """turn a validation error from the service into a 400 response"""
    return jsonify({"error": str(error)}), 400


@group_blueprint.errorhandler(service.NotFoundError)
def not_found(error):
    """turn a missing member, night or game into a 404 response"""
    return jsonify({"error": str(error)}), 404


@group_blueprint.get("/members")
def list_members():
    """return every member, active and archived"""
    return jsonify(service.list_members())


@group_blueprint.post("/members")
def add_member():
    """add the member named in the request body"""
    body = _read_json_object()
    return jsonify(service.add_member(body.get("name"))), 201


@group_blueprint.post("/members/<int:member_id>/archive")
def archive_member(member_id):
    """archive a member who left the group"""
    return jsonify(service.archive_member(member_id))


@group_blueprint.post("/members/<int:member_id>/reactivate")
def reactivate_member(member_id):
    """bring an archived member back"""
    return jsonify(service.reactivate_member(member_id))


@group_blueprint.post("/nights")
def create_night():
    """create a night with its date, time, attendees and guests"""
    body = _read_json_object()
    night = service.create_night(
        body.get("night_date"),
        body.get("available_minutes"),
        body.get("attendee_ids"),
        body.get("guest_names", []),
    )
    return jsonify(night), 201


@group_blueprint.get("/nights/<int:night_id>")
def get_night(night_id):
    """return one night with its attendees and guests"""
    return jsonify(service.get_night(night_id))


@group_blueprint.post("/nights/<int:night_id>/plays")
def log_play(night_id):
    """record that the game in the request body was played on this night"""
    body = _read_json_object()
    return jsonify(service.log_play(night_id, body.get("game_id"))), 201


@group_blueprint.get("/nights/<int:night_id>/plan")
def build_night_plan(night_id):
    """return the suggested games for this night, best first"""
    return jsonify(service.build_night_plan(night_id))


@group_blueprint.put("/ratings")
def save_rating():
    """save or update a member's score for a game"""
    body = _read_json_object()
    rating = service.save_rating(body.get("member_id"), body.get("game_id"), body.get("score"))
    return jsonify(rating)


@group_blueprint.get("/reminders")
def rating_reminders():
    """return the games each active member still needs to rate"""
    return jsonify(service.rating_reminders())


def _read_json_object() -> dict:
    """return the request body, or raise ValueError if it is not a JSON object"""
    # silent=True gives None for a missing or broken body instead of an html error page
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValueError("request body must be a JSON object")
    return body
