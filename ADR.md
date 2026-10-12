# Architecture Decision Records

## 1. Backend language and framework
Date: 2026-10-11
Status: Decided
Context: The app lets my boardgame obsessed friendgroup track the games we own between us and plan game nights better. 
Decision: Python 3.12 with Flask, talking to SQLite through the standard library `sqlite3` module instead of using object relational mapping (ORM). 
Alternatives considered: I considered Django, but I rejected it because its ORM, admin, auth and migration systems are far more than two small domains need and would add many files I wouldn't use. I also considered FastAPI, but I also rejected it because I would have to find a way to learn about / implement async handlers and Pydantic models which I don't currently need for this project.
Consequences: Flask allows me to have only one runtime dependency and very explicit code. The cost is that I write input validation and SQL by hand, but it's fine because it also keeps the schema visible for ADR-3.

## 2. The domains
Date: 2026-10-11
Status: Decided
Context: To bring the idea to life, the app would have to do two different jobs. The first is knowing which games the group owns and the other part would be planning nights and logging what was played. We plan nights for our friendgroup based on who is coming, how much time we have, and what we like.
Decision: I created two main packages. The first is called `library/`, which contains the games (title, owner, player range, and playtime). The second is called `group/`, which has the members of the friendgroup (members), the guests we invite (guests), nights, how much we rate each game (rating), plays, and suggestions. Group reads from Library, the first function would be "games that fit N players in M minutes" and the other is "titles of game X". A note, I decided that group stores the game ids, instead of the game details (which are in library). 
Alternatives considered: I considered putting the ratings in the library instead of in group, next to the games, but since they're unofficial ratings / opinions (and each person will have their rating separately) I thought it made more sense to keep it in group. From a software perspective, library would have to know about the members, so the two domains would depend on each other which isnt recommended. 
Consequences: Splitting library and group later instead of now means that I replace the two Python function calls I wrote above with two HTTP calls. The downside is that group only stores the games by ids instead of the names, so every time it shows a game's name it has to ask library for it, which will just be a bit slower once its a network call instead.

## 3. The database tables
Date: 2026-10-11
Status: Decided
Context: I had to design the tables for both of the domains so that each one only stores its own data. The tricky part was that group needs to refer to games (when someone rates a game or we log a play), even though games belong to library, and that friends sometimes leave the group while we still want to keep their history. 
Decision: I kept every table inside one domain. Ratings and plays have their own tables in the "Group" domain, and they store a game's ID as a plain number with no foreign key to games. Also, I decided that members who leave the group are never deleted, instead they are marked as inactive (is_active = 0) which archives them, keeps their history, and pauses their ratings. 
Alternatives considered: I considered using a foreign key from ratings and plays to games, but I rejected it because it would tie the domains together, and thinking long term, having them in the same database file would mean that it wouldn't exist anymore once they are split into separate services. I also considered deleting members when they leave, but it would delete the player history, which I'll need when I add win tracking later.
Consequences: Because there's no foreign key, a rating or a play can point at a game that doesn't exist, so group has to check with library before saving one (which is what I mentioned above). As for archived members, the consequence is that they stay in the database until someone deliberately deletes them, but on the bright side bringing someone back is as simple as setting "is_active" back to one.

## 4. Testing approach
Date: 2026-10-12 
Status: Decided
Context: In my project, the logic that I need to test the most is the night planner (the rating rules, recency points, scoring, and filling the available time), as well as the validation that stops wrong data from reaching the database. 
Decision: I tested the service functions of both of the domains with pytest against an SQLite file that each test gets in its own temporary folder. I tested the scoring functions with actual numbers. I also tested cases like archived members being rejected, what happens if seeding is done only once, and making sure that a failed night insert completely rolls back (to follow ACID principles). I also added a few route tests with Flask’s test client that check status codes, JSON errors, and one full night plan through the API.
Alternatives considered: I considered mocking the repositories so that the tests don't interact with SQLite, but I rejected it since I decided to write SQL by hand (ADR1), and the mock wouldve hidden mistakes in my queries. 
Consequences: Although the real queries catch the mistakes in my hand written sql, they remain slower than mocked tests and each one creates a database file. And when a test fails it could either be because of the logic or the query, so it takes even longer to identify the actual cause. Since I only have a handful of route tests, most error cases are only checked at the service level, so a route that passes the wrong field to the service could still slip through.

## 5. What I deliberately didn't build

Date: 2026-10-12
Status: Decided
Context: The two things that are missing are a UI, which is what would actually get my friends to use the app, and tracking who wins, which we always argue about (I even kept archived members' history for it in ADR-3). But neither is needed to prove the two domains, the night planner or the container contract, and I had limited time before the deadline. 
Decision: I deliberately built the app as a JSON API only, with no frontend, and plays only records which game was played on which night as of right now without who won. I'll add a proper UI and win tracking together after the deadline. I want to take my time with it. 
Alternatives considered: I considered serving simple HTML pages with Flask templates from the same process, but I rejected it because it would've meant more routes and pages to build and test, and I'd most likely redesign them later anyway. I also considered adding a winner column to the plays table, but I rejected it because one column doesn't work for every game, like Pandemic where everyone wins or loses together, or Codenames where a whole team wins. I'd need time to think through that logic more.
Consequences: All my time went into the logic, the tests and the container, and the JSON API is exactly what a future UI (or another service in assignment 2) will call. The downside is that right now only someone comfortable with curl or a tool like Postman can use it, and nights we play before I add win tracking won't have any winners recorded. 