-- Khiip v0 SQLite schema
-- Authority: ADR-0007 (custom SQLite graph layer), ADR-0008 (5+1 canonical edge vocabulary),
--            ADR-0005 (Option Δ hybrid edge typing — evidence_span + confidence + vocab_match + plain-English templates).
-- Storage location: ~/.local/share/khiip/index.db (per v0 spec — internal)
-- Vault content is filesystem-canonical; this DB is the index + graph layer + can be rebuilt from vault.

-- Pragmas — apply on every connection (set in storage/db.py)
-- PRAGMA journal_mode = WAL;       -- concurrent readers + single writer
-- PRAGMA foreign_keys = ON;        -- enforce FK constraints
-- PRAGMA synchronous = NORMAL;     -- balance durability + perf

-- ───────────────────────────────────────────────────────────────────────────
-- SCHEMA VERSIONING — single-row table; migration script reads + advances
-- ───────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER NOT NULL PRIMARY KEY,
    applied_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ───────────────────────────────────────────────────────────────────────────
-- CAPTURES — one row per captured URL/artifact
-- Filesystem markdown is canonical; this table is the index for fast queries.
-- ───────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS captures (
    -- Identity
    id              TEXT    NOT NULL PRIMARY KEY,  -- ULID (matches markdown filename prefix)
    url             TEXT    NOT NULL,              -- canonical source URL
    url_hash        TEXT    NOT NULL,              -- SHA-256 of normalized URL for dedup
    source          TEXT    NOT NULL,              -- 'x' | 'web' | 'pdf' | 'youtube' | ...

    -- Markdown filesystem location (vault-relative, e.g. 'captures/x/{ulid}-{slug}.md')
    vault_path      TEXT    NOT NULL,

    -- Bitemporal — REQUIRED per ADR-0005 D8
    recorded_at     TEXT    NOT NULL,              -- ISO 8601, when Khiip fetched
    valid_from      TEXT    NOT NULL,              -- ISO 8601, when data was true in world

    -- Content metadata (lightweight; full content in vault markdown)
    title           TEXT,
    description     TEXT,
    author          TEXT,
    content_sha256  TEXT,                          -- hash of markdown body for change-detection

    -- Status flags
    archived        INTEGER NOT NULL DEFAULT 0,    -- soft archive (capture preserved but hidden from default recall)
    superseded_by   TEXT,                          -- ULID of newer capture if this one superseded (chain)

    -- Audit
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),

    -- Self-reference for superseded chain
    FOREIGN KEY (superseded_by) REFERENCES captures(id)
);

CREATE INDEX IF NOT EXISTS idx_captures_url_hash    ON captures(url_hash);
CREATE INDEX IF NOT EXISTS idx_captures_source      ON captures(source);
CREATE INDEX IF NOT EXISTS idx_captures_recorded_at ON captures(recorded_at);
CREATE INDEX IF NOT EXISTS idx_captures_valid_from  ON captures(valid_from);

-- ───────────────────────────────────────────────────────────────────────────
-- EMBEDDINGS — per-capture (and later per-claim) vector embeddings
-- Stored as BLOB; embedding model + dimension recorded for migration safety.
-- ───────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS embeddings (
    capture_id      TEXT    NOT NULL PRIMARY KEY,
    model           TEXT    NOT NULL,              -- e.g. 'all-MiniLM-L6-v2'
    dimension       INTEGER NOT NULL,              -- 384 for MiniLM-L6, 1536 for ada-002, etc.
    vector          BLOB    NOT NULL,              -- raw float32 array, little-endian
    content_sha256  TEXT    NOT NULL,              -- input hash — re-embed when content changes
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (capture_id) REFERENCES captures(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_embeddings_model ON embeddings(model);

-- ───────────────────────────────────────────────────────────────────────────
-- GRAPH_EDGES — capture-to-capture typed edges per ADR-0008 (5+1 vocab) +
-- ADR-0005 (hybrid Option Δ: evidence_span + confidence + vocab_match) +
-- ADR-0007 (append-only with overrides:uuid chain; bitemporal valid_to).
-- ───────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS graph_edges (
    id                  INTEGER PRIMARY KEY,
    source_capture_id   TEXT    NOT NULL,
    target_capture_id   TEXT,                                -- nullable for self-edges or pending targets
    edge_type           TEXT    NOT NULL,                    -- one of 5+1 if vocab_match=1, else freeform
    vocab_match         INTEGER NOT NULL DEFAULT 1,          -- 1 = canonical (in enum), 0 = emergent (raw LLM label)

    -- Option Δ Promise #1 + #2 — REQUIRED
    evidence_span       TEXT    NOT NULL,                    -- exact source text justifying this edge
    confidence          REAL    NOT NULL,                    -- 0.0-1.0; ≥0.7 = primary, <0.7 = tentative

    -- Optional Option Δ metadata
    metadata            TEXT,                                -- JSON blob for extractor-specific extras

    -- Bitemporal per ADR-0005 D8 + ADR-0007
    recorded_at         TEXT    NOT NULL,
    valid_from          TEXT    NOT NULL,
    valid_to            TEXT,                                -- NULL = currently valid

    -- ADR-0007 append-only correction chain (overrides:uuid pattern)
    overrides           INTEGER,                             -- prior edge_id this one supersedes

    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),

    -- Constraints
    FOREIGN KEY (source_capture_id) REFERENCES captures(id) ON DELETE CASCADE,
    FOREIGN KEY (target_capture_id) REFERENCES captures(id) ON DELETE CASCADE,
    FOREIGN KEY (overrides)         REFERENCES graph_edges(id),

    -- Khiip canonical 5+1 vocabulary per ADR-0008
    -- If vocab_match=1, edge_type must be one of the canonical set.
    -- If vocab_match=0, any string is permitted (LLM-emergent label preserved verbatim).
    CHECK (
        vocab_match = 0
        OR edge_type IN ('SUPPORTS','CONTRADICTS','SUPERSEDES','ELABORATES','REFERENCES','RELATES')
    ),

    CHECK (confidence >= 0.0 AND confidence <= 1.0)
);

-- Recall + traversal indexes per ADR-0007 Probe 3 benchmark schema
-- (p99 = 0.024 ms at 50K-edge scale on synthetic data)
CREATE INDEX IF NOT EXISTS idx_graph_edges_src_type_vt
    ON graph_edges(source_capture_id, edge_type, valid_to);

CREATE INDEX IF NOT EXISTS idx_graph_edges_dst_type_vt
    ON graph_edges(target_capture_id, edge_type, valid_to);

CREATE INDEX IF NOT EXISTS idx_graph_edges_conf_vf
    ON graph_edges(confidence, valid_from);

CREATE INDEX IF NOT EXISTS idx_graph_edges_overrides
    ON graph_edges(overrides);

-- Partial index for canonical primary edges (vocab_match=1 AND confidence>=0.7)
-- — fast path for the default UI render per ADR-0005 Option Δ
CREATE INDEX IF NOT EXISTS idx_graph_edges_canonical_primary
    ON graph_edges(edge_type)
    WHERE vocab_match = 1 AND confidence >= 0.7;

-- ───────────────────────────────────────────────────────────────────────────
-- API_KEYS — auth per v0 spec D7 (auto-generated; ~/.config/khiip/auth.toml)
-- Stored hashed (SHA-256) — never plaintext.
-- ───────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS api_keys (
    id              INTEGER PRIMARY KEY,
    key_hash        TEXT    NOT NULL UNIQUE,        -- SHA-256 of raw key
    label           TEXT,                            -- optional user-friendly name
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    last_used_at    TEXT,
    revoked         INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(revoked, key_hash);

-- ───────────────────────────────────────────────────────────────────────────
-- SCHEMA INITIALIZATION — bootstrap version row on first create
-- ───────────────────────────────────────────────────────────────────────────

INSERT OR IGNORE INTO schema_version (version) VALUES (1);
