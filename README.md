# daily-intelligence-report
Our goal here is to build an feed ingest and document processing pipeline that will produce a short summary of yesterday's events/news for our daily consumption. 

## 1  Problem Analysis

| Requirement | Design implications |
|-------------|--------------------|
| Pull **heterogeneous real-time feeds** (RSS, X/Twitter, IMAP, audio/video transcripts) | Five independent collectors with retry/back-off, plus a thin normalization layer so every item becomes a common “Post” object. |
| Run **locally on a MacBook Air _or_ a small cloud VM** | Lightweight footprint: SQLite + FTS5, cron/ruffus scheduler, on-device embeddings. |
| Produce a **3-10 page daily brief** | Pipeline must deduplicate, cluster, summarise, and render to PDF/Markdown. |
| Respect **API limits / costs** | Use X **Basic** tier (10 k reads/mo) or Nitter scraping fallback; configurable rate caps. |
| Keep **private data local** | Optional offline LLM via Ollama; secrets stored in macOS Keychain or env-vars. |

---

## 2  Proposed Solution Overview

The system is a modular Python pipeline scheduled daily (via `cron` or `systemd`) that

1. **Ingests** items from RSS, X/Twitter API, and IMAP newsletters, podcast and youtube transcripts.  
2. **Normalises** them into a common `Post` schema and persists to SQLite + FTS5.  
3. **Embeds & clusters** the last 24 h of posts (MiniLM → k-means).  
4. **Summarises** each cluster with an on-device LLM (default: Ollama `llama3:8b`).  
5. **Renders** a Markdown template to `YYYY-MM-DD.pdf`.  
6. **Delivers** the brief to `~/DailyBriefs/` and optionally emails it.
