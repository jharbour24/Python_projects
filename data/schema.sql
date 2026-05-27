-- ============================================================
-- Critics Impact Analysis — SQLite Schema
-- ============================================================
-- Design: normalized, incremental-friendly, causal-analysis ready
-- Week 0 = BroadwayWorld week containing official opening night
-- Negative week numbers = preview period
-- Positive week numbers = post-opening
-- ============================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ============================================================
-- SHOWS
-- ============================================================
CREATE TABLE IF NOT EXISTS shows (
    show_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    title               TEXT NOT NULL,
    normalized_title    TEXT NOT NULL,          -- lowercase, stripped for matching
    dtli_slug           TEXT UNIQUE,            -- e.g. "the-lost-boys"
    ibdb_id             INTEGER,
    show_type           TEXT CHECK(show_type IN ('M','P','S','O','U')),  -- Musical/Play/Specialty/Other/Unknown
    is_revival          INTEGER DEFAULT 0,      -- 0/1
    opening_date        DATE,                   -- official opening night
    closing_date        DATE,
    theater             TEXT,
    capitalization      REAL,                   -- production budget in $ (nullable, from public reporting)
    source_dtli         INTEGER DEFAULT 0,
    source_ibdb         INTEGER DEFAULT 0,
    source_bww          INTEGER DEFAULT 0,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_shows_normalized ON shows(normalized_title);
CREATE INDEX IF NOT EXISTS idx_shows_opening_date ON shows(opening_date);
CREATE INDEX IF NOT EXISTS idx_shows_dtli_slug ON shows(dtli_slug);

-- ============================================================
-- PUBLICATIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS publications (
    publication_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,
    normalized_name     TEXT NOT NULL UNIQUE,   -- lowercase, stripped
    first_review_date   DATE,
    last_review_date    DATE,
    total_reviews       INTEGER DEFAULT 0,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pubs_normalized ON publications(normalized_name);

-- ============================================================
-- CRITICS
-- ============================================================
CREATE TABLE IF NOT EXISTS critics (
    critic_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name                    TEXT NOT NULL,
    normalized_name         TEXT NOT NULL,
    primary_publication_id  INTEGER REFERENCES publications(publication_id),
    first_review_date       DATE,
    last_review_date        DATE,
    total_reviews           INTEGER DEFAULT 0,
    created_at              DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(normalized_name, primary_publication_id)
);

CREATE INDEX IF NOT EXISTS idx_critics_normalized ON critics(normalized_name);

-- ============================================================
-- REVIEWS
-- Individual review per critic per show from DTLI, enriched with NYT Critics Pick flag
-- ============================================================
CREATE TABLE IF NOT EXISTS reviews (
    review_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    show_id                 INTEGER NOT NULL REFERENCES shows(show_id),
    critic_id               INTEGER NOT NULL REFERENCES critics(critic_id),
    publication_id          INTEGER NOT NULL REFERENCES publications(publication_id),
    sentiment               TEXT NOT NULL CHECK(sentiment IN ('up','meh','down')),
    review_date             DATE NOT NULL,
    excerpt                 TEXT,
    is_opening_window       INTEGER DEFAULT 0,  -- 1 if within OPENING_WINDOW_DAYS of opening night
    days_from_opening       INTEGER,            -- negative = before opening, 0 = opening day
    is_nyt_critics_pick     INTEGER,            -- 1/0/NULL (NULL = not a NYT review)
    source                  TEXT CHECK(source IN ('dtli','nyt','manual')),
    created_at              DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(show_id, critic_id, review_date)    -- prevent duplicate imports
);

CREATE INDEX IF NOT EXISTS idx_reviews_show ON reviews(show_id);
CREATE INDEX IF NOT EXISTS idx_reviews_publication ON reviews(publication_id);
CREATE INDEX IF NOT EXISTS idx_reviews_opening_window ON reviews(show_id, is_opening_window);
CREATE INDEX IF NOT EXISTS idx_reviews_sentiment ON reviews(sentiment);

-- ============================================================
-- SHOW WEEK PERFORMANCES
-- One row per show per weekly reporting period.
-- week_number is relative to opening night (0=opening week, negative=previews)
-- ============================================================
CREATE TABLE IF NOT EXISTS show_week_performances (
    swp_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    show_id             INTEGER NOT NULL REFERENCES shows(show_id),
    week_ending         DATE NOT NULL,          -- Sunday date (BroadwayWorld reporting date)
    week_number         INTEGER,                -- NULL until opening_date is known for the show
    is_preview          INTEGER DEFAULT 0,      -- 1 if week is before official opening
    gross               REAL,
    gross_prev_week     REAL,
    gross_diff          REAL,
    gross_diff_pct      REAL,
    avg_ticket          REAL,
    top_ticket          REAL,
    attendance          INTEGER,
    seating_capacity    INTEGER,
    performances        INTEGER,
    capacity_pct        REAL,
    theater             TEXT,
    show_type           TEXT,                   -- M/P from BroadwayWorld
    UNIQUE(show_id, week_ending)
);

CREATE INDEX IF NOT EXISTS idx_swp_show ON show_week_performances(show_id);
CREATE INDEX IF NOT EXISTS idx_swp_week ON show_week_performances(week_ending);
CREATE INDEX IF NOT EXISTS idx_swp_week_number ON show_week_performances(show_id, week_number);

-- ============================================================
-- TONY OUTCOMES
-- ============================================================
CREATE TABLE IF NOT EXISTS tony_outcomes (
    tony_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    show_id             INTEGER REFERENCES shows(show_id),
    show_title          TEXT NOT NULL,          -- raw title (for shows not yet matched)
    ceremony_year       INTEGER NOT NULL,
    category            TEXT NOT NULL,
    nominated           INTEGER DEFAULT 0,
    won                 INTEGER DEFAULT 0,
    UNIQUE(show_title, ceremony_year, category)
);

CREATE INDEX IF NOT EXISTS idx_tony_show ON tony_outcomes(show_id);
CREATE INDEX IF NOT EXISTS idx_tony_year ON tony_outcomes(ceremony_year);

-- ============================================================
-- SCRAPE RUNS — observability & incremental checkpoint tracking
-- ============================================================
CREATE TABLE IF NOT EXISTS scrape_runs (
    run_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source              TEXT NOT NULL,          -- 'dtli_archive', 'dtli_show', 'nyt', 'grosses'
    started_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at         DATETIME,
    shows_processed     INTEGER DEFAULT 0,
    records_added       INTEGER DEFAULT 0,
    records_updated     INTEGER DEFAULT 0,
    errors              INTEGER DEFAULT 0,
    notes               TEXT
);

-- ============================================================
-- VIEWS — precomputed joins for analysis convenience
-- ============================================================

-- Opening-window review consensus per show × publication
CREATE VIEW IF NOT EXISTS v_opening_consensus AS
SELECT
    r.show_id,
    p.name                              AS publication,
    p.publication_id,
    c.name                              AS critic,
    r.sentiment,
    r.review_date,
    r.days_from_opening,
    r.is_nyt_critics_pick,
    s.title                             AS show_title,
    s.opening_date,
    s.show_type,
    s.is_revival
FROM reviews r
JOIN publications p  ON p.publication_id = r.publication_id
JOIN critics c       ON c.critic_id = r.critic_id
JOIN shows s         ON s.show_id = r.show_id
WHERE r.is_opening_window = 1;

-- Week-relative gross performance joined with opening consensus
-- (Use for: does a thumbs-up in [publication] predict gross in week +1, +2, +N?)
CREATE VIEW IF NOT EXISTS v_weekly_gross_with_reviews AS
SELECT
    swp.show_id,
    s.title                             AS show_title,
    s.opening_date,
    s.show_type,
    s.is_revival,
    swp.week_ending,
    swp.week_number,
    swp.is_preview,
    swp.gross,
    swp.gross_diff_pct,
    swp.capacity_pct,
    swp.attendance,
    swp.avg_ticket
FROM show_week_performances swp
JOIN shows s ON s.show_id = swp.show_id
WHERE swp.week_number IS NOT NULL;
