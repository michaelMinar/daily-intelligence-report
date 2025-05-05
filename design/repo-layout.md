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
│   ├── models/
│   │   ├── embed.py
│   │   ├── cluster.py
│   │   └── summarise.py
│   ├── pipeline/
│   │   └── daily_report.py
│   ├── render/
│   │   ├── template.md.jinja
│   │   └── render.py
│   └── api/
│       └── service.py      # optional FastAPI
└── tests/
