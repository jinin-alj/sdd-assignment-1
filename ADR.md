# Architecture Decision Records

## 1. Backend language and framework
Date: 2026-10-11
Status: Decided
Context: The app lets my boardgame obsessed friendgroup track the games we own between us and plan game nights better. 
Decision: Python 3.12 with Flask, talking to SQLite through the standard library `sqlite3` module instead of using object relational mapping (ORM). 
Alternatives considered: I considered Django, but I rejected it because its ORM. Admin, auth and migration systems are far more than two small domains need and would add many files I wouldn't use. I also considered FastAPI, but I also rejected it because I would have to find a way to learn about / implement async handlers and Pydantic models which I don't currently need for this project.
Consequences: Flask allows me to have only one runtime dependency and very explicit code. The cost is that I write input validation and SQL by hand, but it's fine because it also keeps the schema visible for ADR-3.

## 2. The domains
Date: 2026-10-11
Status: Decided
Context: To bring the idea to life, the app would have to do two different jobs. The first is knowing which games the group owns and the other part would be planning nights and logging what was played. We plan nights for our friendgroup based on who is coming, how much time we have, and what we like.
Decision: I created two main packages. The first is called `library/`, which contains the games (title, owner, player range, and playtime). The second is called `group/`, which has the members of the friendgroup (members), the guests we invite (guests), nights, how much we rate each game (rating), plays, and suggestions. Group reads from Library, the first function would be "games that fit N players in M minutes" and the other is "titles of game X". A note, I decided that group stores the game ids, instead of the game details (which are in library). 
Alternatives considered: I considered putting the ratings in the library instead of in group, next to the games, but sincfe they're unofficial ratings / opinions (and each person will gave their rating seperately) I thought it made more sense to keep it in group. From a software perspective, library would have to know about the members, so the two domains would depend on each other which isnt recommended. 
Consequences: Splitting library and group later instead of now means that I replace the two Python function calls I wrote above with two HTTP calls. The downside is that group only stores the games by ids instead of the names, so every time it shows a game's name it has to ask library for it, which will just be a bit slower once its a network call instead.

