# Game Night Planner

I created a small web API that my board game friend group uses to keep track of the games we own between us and to plan our game nights. It suggests what to play based on who's coming, how much time we have, what we like, and what we haven't played in a while.

> **IMPORTANT:** the app needs Python 3.12. The database is created automatically on first start no need for setup. The starter games are loaded from `library/seed.json`.

## What it does

The app has two domains:

- **Library** (`library/`): the games we own, who owns it, player range and play time.
- **Group** (`group/`): members of the group, guests we invite, game nights, everyone's ratings of the game (on a scale of 1 to 10), what was played on each night, and the night planner.

### How a night plan is built

1. How many players? Players = members coming + guests. Then we filter out the games and we keep the ones that can fit that amount of players.
2. Every game gets a score: the average rating of the members coming + recency points (when's the last time we played this game?).
   - A member's rating is their own score. If nobody in the group has played the game yet it counts as 10, and if it was played but they haven't rated it, it counts as 5 (keeping it neutral).
   - Recency points: 1 point per full week since the game was last played, maximum 5. A game that was never played gets 5.
3. The planner fills the available time starting from the highest score, skipping games that don't fit in the time that's left.

Guests count as players, but their opinions don't count in the ratings.

## Run it directly

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The app starts on http://localhost:8000.

## Run it with Docker

```bash
docker build -t game-night-planner .
docker run -p 8000:8000 -v game-night-data:/data game-night-planner
```

On a different port:

```bash
docker run -e PORT=9000 -p 9000:9000 -v game-night-data:/data game-night-planner
```

## Configuration

| Variable | Default | What it does |
|---|---|---|
| `PORT` | `8000` | The port the app listens on. A value that isn't a number between 1 and 65535 falls back to 8000. |
| `DATA_DIR` | `./data` (in Docker: `/data`) | The folder where the SQLite file is stored. Created if it doesn't exist. |

**SQLite file:** `$DATA_DIR/game_nights.db` (in Docker: `/data/game_nights.db`).

On every start the app creates any missing tables (`CREATE TABLE IF NOT EXISTS`) and loads `library/seed.json` only if the games table is empty. It never drops tables or re-seeds, so restarting keeps all data.

## API

All requests and responses are JSON.

| Method | Path | What it does |
|---|---|---|
| GET | `/` | Status check |
| GET | `/games` | List all games |
| POST | `/games` | Add a game (`title`, `owner`, `min_players`, `max_players`, `playtime_minutes`) |
| GET | `/games/fit?players=4&minutes=120` | Games that fit 4 players in 120 minutes |
| GET | `/members` | List members, active and archived |
| POST | `/members` | Add a member (`name`) |
| POST | `/members/<id>/archive` | Archive a member who left (their history stays) |
| POST | `/members/<id>/reactivate` | Bring an archived member back |
| POST | `/nights` | Create a night (`night_date`, `available_minutes`, `attendee_ids`, optional `guest_names`) |
| GET | `/nights/<id>` | A night with its attendees and guests |
| POST | `/nights/<id>/plays` | Log a game played that night (`game_id`) |
| GET | `/nights/<id>/plan` | Suggested games for the night, best first |
| PUT | `/ratings` | Save or update a rating (`member_id`, `game_id`, `score` 1-10) |
| GET | `/reminders` | Games members played but haven't rated yet |

Example of planning a night:

```bash
curl -X POST localhost:8000/members -H "Content-Type: application/json" -d '{"name": "Jinin"}'
curl -X POST localhost:8000/members -H "Content-Type: application/json" -d '{"name": "Ameed"}'
curl -X POST localhost:8000/nights -H "Content-Type: application/json" \
  -d '{"night_date": "2026-10-16", "available_minutes": 180, "attendee_ids": [1, 2], "guest_names": ["Omar"]}'
curl localhost:8000/nights/1/plan
```

### Errors

| Status | When |
|---|---|
| 400 | Invalid input, e.g. a score of 11, a date that doesn't exist, or a missing field. The response says what's wrong. |
| 404 | Unknown member, night, game or URL |
| 500 | Unexpected error. The real error is printed in the server log. |

## Project structure

```
app.py               creates the app, the tables and registers both domains
config.py            reads PORT and DATA_DIR
database.py          opens SQLite connections (foreign keys on)
library/             games: schema.sql, seed.json, repository (SQL), service (validation), routes
group/               members, nights, ratings, plays: schema.sql, repository, service (planner), routes
tests/               pytest tests for both services and the routes
pytest.ini           tells pytest where the tests are and adds the project root to the import path
Dockerfile           the provided template with its four TODOs filled in
ADR.md               my 5 architecture decisions
AI_USAGE.md          log of how I used AI
```

## Tests

```bash
pytest --cov=library --cov=group --cov-report=term-missing
```

```
================================ test session starts =================================
platform darwin -- Python 3.12.12, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/jininaljayyousi/sdd-assignment-1
configfile: pytest.ini
testpaths: tests
plugins: cov-7.1.0
collected 75 items

tests/test_group_service.py ........................................           [ 53%]
tests/test_library_service.py ..............................                   [ 93%]
tests/test_routes.py .....                                                     [100%]

=================================== tests coverage ===================================
_________________ coverage: platform darwin, python 3.12.12-final-0 __________________

Name                    Stmts   Miss  Cover   Missing
-----------------------------------------------------
group/__init__.py           0      0   100%
group/repository.py        88      1    99%   32
group/routes.py            50     11    78%   11, 23, 36, 42, 67-68, 80-82, 88, 96
group/service.py          145      1    99%   238
library/__init__.py         0      0   100%
library/repository.py      53      2    96%   32-33
library/routes.py          23      9    61%   11, 23, 30-36
library/service.py         33      0   100%
-----------------------------------------------------
TOTAL                     392     24    94%
================================= 75 passed in 0.45s =================================
```

Total coverage is 94% (75 tests). The business logic is almost fully covered: `library/service.py` is at 100% and `group/service.py` at 99%. The repositories are at 96-99%, and the routes are lower (61-78%) on purpose, since ADR-4 focuses the tests on the logic and only a few route tests check status codes, JSON errors and one full night plan. The only lines left in the logic and repositories are rare error paths, like a broken seed file for example.

## Container check

```bash
./container/run.sh .
```

```
=== SDD Assignment 1 contract check ===
Repository: /Users/jininaljayyousi/sdd-assignment-1

==> Repository shape
  PASS  one Dockerfile, one manifest (requirements.txt)

==> Build from a clean context, no build args
  PASS  image built
  PASS  image size 245 MB

==> Start on PORT=8000 and reach it from the host
  PASS  HTTP 200 from http://localhost:8000/

==> SQLite file under DATA_DIR
  PASS  found in /data: game_nights.db

==> Data persists, and a second boot does not re-seed
  PASS  volume at /data persists
  PASS  row counts unchanged across restart: games=8 members=0 night_attendees=0 night_guests=0 nights=0 plays=0 ratings=0

==> PORT override is honoured (not hardcoded)
  PASS  HTTP 200 from http://localhost:9123/

=== ALL CHECKS PASSED ===
```

## Known limitations

- There's no login. Anyone who can reach the app can change data, so it's meant to run locally for our group. Might add that later.
- There's no UI yet, it's a JSON API. I plan to design the proper UI by the end of this week because I want to take my time designing it myself. 
- Winners aren't tracked yet, but I plan to add that later (see ADR-5).
- Two games can have the same title on purpose, since two people in the group can each own a copy.
- The test dependencies (pytest, pytest-cov) are in the same `requirements.txt` as Flask, because the assignment allows only one manifest. That means they're also installed in the Docker image.

## Maintenance

- To reset everything, stop the app and delete `$DATA_DIR/game_nights.db`. It's recreated with the starter games on the next start.
- Errors are printed to the terminal, or to `docker logs` in the container.

## Author

Jinin AlJayyousi, IE University, October 2026