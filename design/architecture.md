## Architecture Specification
flowchart LR
    subgraph Ingestion
        RSS[RSS Collector] --> N1
        X[X API Collector] --> N1
        EMAIL[IMAP Collector\nGmail / iCloud] --> N1
		POD[Podcast] --> N1
		VID[Youtube] --> N1
    end
    subgraph Normalise & Store
        N1[Normaliser\nJSON to Post] --> DB[(SQLite + FTS5)]
    end
    DB --> EMBEDDING[Embed &\nVector-store]
    EMBEDDING --> CLUSTER[Topic clustering\nBERT k-means]
    CLUSTER --> SUMMARISE[LLM Summariser\nchunk to tl;dr]
    SUMMARISE --> RENDER[Markdown to PDF\nPandoc / Reportlab]
    RENDER --> DELIVER[Save to ~/DailyBriefs\n+ optional email]

Ingestion --> Normalise --> SQLite --> Embed --> Cluster --> Summarise --> Render --> Deliver
   |            |             ^                                         |
   |            |             +-----------------------------------------+
   +-- RSS      +-- JSON      (FTS & vectors)
   +-- X API
   +-- IMAP

## Key Components
| Layer / Function      | Primary libraries & tools (local-first)                                    |
|-----------------------|-----------------------------------------------------------------------------|
| **RSS**               | `feedparser`, `httpx`, `tenacity`                                           |
| **X API**             | `requests` / `httpx`; bearer-token in Keychain; Basic tier (10 k reads/mo)   |
| **Email**             | `imaplib`, `mailparser`                                                     |
| **YouTube Ingest**    | `google-api-python-client` **or** channel RSS, `yt-dlp`, `youtube-transcript-api` |
| **Podcast Ingest**    | `feedparser`, built-in `xml.etree` for OPML, `podcastindex-python` (optional) |
| **Transcription / ASR** | `whisper` (local CPU/GPU) **or** `openai.Audio.transcriptions`, `assemblyai` |
| **Storage**           | `sqlite3` + FTS5 index                                                      |
| **Embeddings**        | `sentence-transformers/all-MiniLM-L6-v2`                                    |
| **Clustering**        | `scikit-learn` `KMeans`                                                     |
| **Summarisation**     | Ollama (`llama3:8b`) *or* cloud adapters (`openai`, `anthropic`, `gemini`)  |
| **Rendering**         | Markdown + Jinja template; `pandoc` → PDF *or* `reportlab`                  |
