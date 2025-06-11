## Proposed code layout
daily‑intel/
├── README.md
├── pyproject.toml
├── config.yaml            # secrets via env vars / macOS keychain
├── cronjob.sh             # `$ python -m pipeline.daily_report`
├── src/
│   ├── connectors/
│   │   ├── rss.py
│   │   ├── x_api.py
│   │   └── email.py
│   │   └── podcast.py
│   │   └── youtube.py
│   ├── intel/
│	│   ├── utils/
│   │   ├── config_loader.py
│   │   ├── init_db.py
│   │   └── logging_config.py
│   ├── models/
│   │   ├── embeddings.py
│   │   ├── cluster.py
│   │   ├── post.py
│   │   ├── source.py
│   │   └── summaries.py
│   ├── pipeline/
│   │   └── daily_report.py
│   ├── render/
│   │   ├── template.md.jinja
│   │   └── render.py
│   └── api/
│       └── service.py      # optional FastAPI
└── tests/
