This is a document that provides details on implementing the next steps in our development plan.


1. Initialize SQLite database schema
| Sub-task | Purpose & Notes | Rough Deliverable |
| --- | --- | --- |
| **Decide file location & naming** | Keep the DB file in `./data/dev/intel.db` for local dev; allow overrides via **config.yaml** (e.g., `~/intel/intel.db`). | Path entry in `config.yaml`: `storage.sqlite_path` |
| **Outline logical entities** | Plan core tables: `sources`, `posts`, `embeddings`, `clusters`, optional `errors`. | Signed-off ERD diagram or Markdown table |
| **Write the DDL script** | Author `infra/schema.sql`; include tables, FTS5 virtual table, and triggers to sync FTS. | `schema.sql` committed to `infra/` |
| **Provide an init utility** | CLI/Script that ① reads `sqlite_path`, ② creates parent dirs, ③ executes `schema.sql` idempotently (`PRAGMA user_version`). | `python -m intel.init_db` (or entry point) |
| **Automate in CI** | Add GitHub Actions step that runs `pytest tests/db_schema_test.py` to assert expected tables exist. | CI green check |
| **Plan for migrations** | Choose lightweight strategy (`sqlite-migrate` or `infra/migrations/NNN_*.sql`) and document it. | `docs/migrations.md` |

2. Configure logging
| Sub-task | Purpose & Notes | Rough Deliverable |
| --- | --- | --- |
| **Choose logging backend** | Use std‑lib `logging`; add **rich** for pretty console output. Rotate files via `RotatingFileHandler`. | `pyproject.toml` dependency: `rich` |
| **Define log directory** | Default path `./logs/`; allow override via `config.yaml` → `logging.log_dir`. | Config entry |
| **Draft a dictConfig** | Place config dict in `intel/logging_config.py` (avoids YAML dep). | `logging_config.py` |
| **Bootstrap early** | In `intel/__init__.py` call `logging.config.dictConfig(LOG_CONFIG)` on import. | Working import side-effect |
| **Provide helper `get_logger`** | Wrapper that returns `logging.getLogger(__name__)`. | `intel/utils/log.py` |
| **Capture external noise** | Suppress chatty libs (e.g., `urllib3`) with `setLevel(logging.WARNING)`. | One-time call in bootstrap |
| **Add structured context (later)** | Include IDs in `extra=` for traceability, e.g., `logger.info("Fetched", extra={"feed": url})`. | Pattern documented |
| **Test it** | Unit test ensures log file is created; manual run (`python -m intel.init_db -vv`) prints INFO to console, DEBUG to file. | Test & manual demo |
