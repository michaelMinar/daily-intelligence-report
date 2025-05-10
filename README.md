# Daily Intelligence Report

A personalized daily intelligence report system that collects information from various sources, processes it, and delivers a concise summary.

## Project Description

This system is designed to:

1. **Ingest** content from multiple sources:
   - RSS feeds
   - X/Twitter
   - Email newsletters
   - Podcast transcripts
   - YouTube videos

2. **Process** the content:
   - Normalize to a common format
   - Store in SQLite with full-text search
   - Generate embeddings
   - Cluster by topic
   - Summarize each cluster

3. **Deliver** a daily brief:
   - Generate a PDF report
   - Save locally and/or email

## Development Setup

### Prerequisites

- Python 3.11+
- Poetry (for dependency management)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/daily-intelligence-report.git
   cd daily-intelligence-report
   ```

2. Run the setup script:
   ```bash
   ./setup.sh
   ```
   
   This script will:
   - Install Poetry (if needed)
   - Set up the pyproject.toml (if needed)
   - Install all dependencies
   - Create the project structure
   - Configure Poetry to create virtual environment in the project directory

3. Activate the virtual environment:
   ```bash
   poetry shell
   ```

### Development Commands

- Run tests:
  ```bash
  poetry run pytest
  ```

- Code formatting:
  ```bash
  poetry run black src tests
  ```

- Linting:
  ```bash
  poetry run ruff src tests
  ```

- Type checking:
  ```bash
  poetry run mypy src
  ```

## Project Structure

```
daily‑intel/
├── README.md
├── pyproject.toml
├── config.yaml            # secrets via env vars / macOS keychain
├── cronjob.sh             # `$ python -m pipeline.daily_report`
├── src/
│   ├── connectors/        # RSS, X API, Email, Podcast, YouTube
│   ├── models/            # Embedding, clustering, summarization
│   ├── pipeline/          # Pipeline orchestration
│   ├── render/            # Report rendering
│   └── api/               # Optional FastAPI service
└── tests/
```