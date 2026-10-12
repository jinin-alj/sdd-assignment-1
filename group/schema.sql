CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS nights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    night_date TEXT NOT NULL,
    available_minutes INTEGER NOT NULL CHECK (available_minutes > 0)
);

CREATE TABLE IF NOT EXISTS night_attendees (
    night_id INTEGER NOT NULL REFERENCES nights(id) ON DELETE CASCADE,
    member_id INTEGER NOT NULL REFERENCES members(id),
    PRIMARY KEY (night_id, member_id)
);

CREATE TABLE IF NOT EXISTS night_guests (
    night_id INTEGER NOT NULL REFERENCES nights(id) ON DELETE CASCADE,
    guest_name TEXT NOT NULL,
    PRIMARY KEY (night_id, guest_name)
);

CREATE TABLE IF NOT EXISTS ratings (
    member_id INTEGER NOT NULL REFERENCES members(id),
    game_id INTEGER NOT NULL,
    score INTEGER NOT NULL CHECK (score BETWEEN 1 AND 10),
    PRIMARY KEY (member_id, game_id)
);

CREATE TABLE IF NOT EXISTS plays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    night_id INTEGER NOT NULL REFERENCES nights(id) ON DELETE CASCADE,
    game_id INTEGER NOT NULL
);