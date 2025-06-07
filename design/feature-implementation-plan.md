# Feature Implementation Plan: SQLite Database Schema & Logging Configuration

## Overview
This document outlines the implementation plan for the SQLite database schema and logging configuration for the daily intelligence report system, corresponding to Phase 1 tasks in the development plan.

## 1. SQLite Database Schema Implementation

### 1.1 Database Schema Design
**File: `infra/schema.sql`**

Core tables to implement:
- **`sources`**: Store RSS feeds, X accounts, email addresses, podcasts, YouTube channels
  - `id`, `type`, `url`, `name`, `config_json`, `created_at`, `updated_at`, `active`
- **`posts`**: Raw ingested content with metadata
  - `id`, `source_id`, `title`, `content`, `url`, `published_at`, `ingested_at`, `content_hash`
- **`embeddings`**: Vector embeddings for semantic search
  - `id`, `post_id`, `embedding_blob`, `model_name`, `created_at`
- **`clusters`**: Topic clusters with labels
  - `id`, `label`, `description`, `created_at`, `post_count`
- **`posts_fts`**: FTS5 virtual table for full-text search
  - Mirror of posts table with FTS5 indexing on title and content

### 1.2 Database Initialization Utility
**File: `src/intel/init_db.py`**
- CLI utility: `python -m intel.init_db`
- Read sqlite_path from configuration
- Create parent directories if needed
- Execute schema.sql idempotently using `PRAGMA user_version`
- Handle migrations strategy

### 1.3 Database Models
**Directory: `src/models/`**
- Create Pydantic models for type-safe database operations
- Models for: Source, Post, Embedding, Cluster
- Include validation and serialization logic

### 1.4 Configuration
- Database location: `./data/dev/intel.db` (configurable via config.yaml)
- Configuration entry: `storage.sqlite_path`

## 2. Logging Configuration Implementation

### 2.1 Dependencies
**File: `pyproject.toml`**
- Add `rich` dependency for enhanced console formatting

### 2.2 Logging Configuration
**File: `src/intel/logging_config.py`**
- dictConfig setup with:
  - Console handler with rich formatting (INFO level)
  - File handler with rotation (DEBUG level)
  - Structured formatters
  - External library noise suppression

### 2.3 Logging Bootstrap
**File: `src/intel/__init__.py`**
- Import-time logging configuration
- Call `logging.config.dictConfig(LOG_CONFIG)`

### 2.4 Logging Utilities
**File: `src/intel/utils/log.py`**
- Helper function: `get_logger(__name__)`
- Structured logging patterns for traceability

### 2.5 Configuration
- Log directory: `./logs/` (configurable via config.yaml)
- Configuration entry: `logging.log_dir`

## 3. Project Structure Updates

### 3.1 New Package Structure
```
src/
├── intel/
│   ├── __init__.py          # Logging bootstrap
│   ├── init_db.py           # Database initialization utility
│   ├── logging_config.py    # Logging configuration
│   └── utils/
│       └── log.py           # Logging utilities
├── models/
│   ├── __init__.py
│   ├── source.py            # Source model
│   ├── post.py              # Post model
│   ├── embedding.py         # Embedding model
│   └── cluster.py           # Cluster model
└── [existing directories...]

infra/
└── schema.sql               # Database DDL script
```

### 3.2 Configuration Management
- Ensure config.yaml structure supports new paths
- Default configurations for development environment

## 4. Implementation Order

1. **Create infra directory and schema.sql**
2. **Add rich dependency to pyproject.toml**
3. **Create src/intel package with logging configuration**
4. **Implement database initialization utility**
5. **Create Pydantic models for database entities**
6. **Add logging utilities and bootstrap**
7. **Test database initialization and logging setup**

## 5. Key Design Principles

- **Maintainability**: Clear separation of concerns, well-documented code
- **Type Safety**: Full mypy compliance with proper type hints
- **Configuration**: Everything configurable via config.yaml
- **Migrations**: Lightweight strategy using `PRAGMA user_version`
- **Testing**: Unit tests for all components
- **Human Understanding**: Clear naming, documentation, and structure

## 6. Testing Strategy

- Unit tests for database schema creation
- Integration tests for logging configuration
- CI automation to verify schema integrity
- Manual testing of CLI utilities

## 7. Migration Strategy

- Use `PRAGMA user_version` for schema versioning
- Future migrations in `infra/migrations/NNN_*.sql` format
- Document migration process in `docs/migrations.md`