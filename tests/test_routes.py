import pytest
import app 

@pytest.fixture
def client(tmp_path, monkeypatch):
    """give each test a fresh app with its own seeded database"""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return app.create_app().test_client()

def test_home_page_reports_the_app_is_up(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"

def test_unknown_url_returns_json_not_html(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.get_json() == {"error": "not found"}

def test_adding_an_invalid_game_returns_400_with_the_reason(client):
    response = client.post("/games", json={"title": "Dune"})
    assert response.status_code == 400
    assert "missing field" in response.get_json()["error"]

def test_unknown_night_returns_404_with_the_reason(client):
    response = client.get("/nights/999")
    assert response.status_code == 404
    assert response.get_json() == {"error": "no night with id 999"}

def test_planning_a_night_through_the_api(client):
    jinin = client.post("/members", json={"name": "Jinin"}).get_json()
    nikita = client.post("/members", json={"name": "Nikita"}).get_json()
    night = client.post(
        "/nights",
        json={
            "night_date": "2026-10-12",
            "available_minutes": 60,
            "attendee_ids": [jinin["id"], nikita["id"]],
        },
    ).get_json()
    response = client.get(f"/nights/{night['id']}/plan")
    assert response.status_code == 200
    assert response.get_json()["player_count"] == 2
    assert len(response.get_json()["games"]) > 0