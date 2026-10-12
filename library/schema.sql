-- owner is plain text because members belong to the group domain (ADR-2)
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    owner TEXT NOT NULL,
    min_players INTEGER NOT NULL CHECK (min_players >= 1),
    max_players INTEGER NOT NULL CHECK (max_players >= min_players),
    playtime_minutes INTEGER NOT NULL CHECK (playtime_minutes > 0)
);
