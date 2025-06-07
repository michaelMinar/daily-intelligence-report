-- Daily Intelligence Report Database Schema
-- SQLite with FTS5 for full-text search capabilities

-- Schema version for migration tracking
PRAGMA user_version = 1;

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- Sources table: RSS feeds, X accounts, email addresses, podcasts, YouTube channels
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK (type IN ('rss', 'twitter', 'email', 'podcast', 'youtube')),
    url TEXT NOT NULL,
    name TEXT NOT NULL,
    config_json TEXT, -- JSON configuration specific to source type
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT TRUE,
    UNIQUE(type, url)
);

-- Posts table: Raw ingested content with metadata
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    url TEXT,
    published_at DATETIME,
    ingested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    content_hash TEXT NOT NULL, -- SHA-256 hash for deduplication
    metadata_json TEXT, -- Additional metadata as JSON
    FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE,
    UNIQUE(content_hash)
);

-- Embeddings table: Vector embeddings for semantic search
CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    embedding_blob BLOB NOT NULL, -- Serialized vector embedding
    model_name TEXT NOT NULL, -- e.g., 'sentence-transformers/all-MiniLM-L6-v2'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    UNIQUE(post_id, model_name)
);

-- Clusters table: Topic clusters with labels
CREATE TABLE IF NOT EXISTS clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    post_count INTEGER DEFAULT 0,
    centroid_blob BLOB -- Serialized cluster centroid
);

-- Post-cluster relationship table
CREATE TABLE IF NOT EXISTS post_clusters (
    post_id INTEGER NOT NULL,
    cluster_id INTEGER NOT NULL,
    distance REAL, -- Distance from cluster centroid
    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (post_id, cluster_id),
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY (cluster_id) REFERENCES clusters(id) ON DELETE CASCADE
);

-- FTS5 virtual table for full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
    title,
    content,
    content=posts,
    content_rowid=id
);

-- Triggers to keep FTS5 table in sync with posts table
CREATE TRIGGER IF NOT EXISTS posts_fts_insert AFTER INSERT ON posts BEGIN
    INSERT INTO posts_fts(rowid, title, content) VALUES (new.id, new.title, new.content);
END;

CREATE TRIGGER IF NOT EXISTS posts_fts_delete AFTER DELETE ON posts BEGIN
    INSERT INTO posts_fts(posts_fts, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
END;

CREATE TRIGGER IF NOT EXISTS posts_fts_update AFTER UPDATE ON posts BEGIN
    INSERT INTO posts_fts(posts_fts, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
    INSERT INTO posts_fts(rowid, title, content) VALUES (new.id, new.title, new.content);
END;

-- Trigger to update sources.updated_at
CREATE TRIGGER IF NOT EXISTS sources_updated_at AFTER UPDATE ON sources BEGIN
    UPDATE sources SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Trigger to update cluster post_count
CREATE TRIGGER IF NOT EXISTS cluster_post_count_insert AFTER INSERT ON post_clusters BEGIN
    UPDATE clusters SET post_count = (
        SELECT COUNT(*) FROM post_clusters WHERE cluster_id = NEW.cluster_id
    ) WHERE id = NEW.cluster_id;
END;

CREATE TRIGGER IF NOT EXISTS cluster_post_count_delete AFTER DELETE ON post_clusters BEGIN
    UPDATE clusters SET post_count = (
        SELECT COUNT(*) FROM post_clusters WHERE cluster_id = OLD.cluster_id
    ) WHERE id = OLD.cluster_id;
END;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_posts_source_id ON posts(source_id);
CREATE INDEX IF NOT EXISTS idx_posts_published_at ON posts(published_at);
CREATE INDEX IF NOT EXISTS idx_posts_ingested_at ON posts(ingested_at);
CREATE INDEX IF NOT EXISTS idx_posts_content_hash ON posts(content_hash);
CREATE INDEX IF NOT EXISTS idx_embeddings_post_id ON embeddings(post_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_model_name ON embeddings(model_name);
CREATE INDEX IF NOT EXISTS idx_sources_type ON sources(type);
CREATE INDEX IF NOT EXISTS idx_sources_active ON sources(active);