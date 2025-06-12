# Multi‑AI Code Review Playbook

**Goal :** Add a Gemini‑powered automated reviewer *alongside* your existing OpenAI GPT‑4o‑mini reviewer so every pull request (PR) gets two fully independent sets of AI feedback.

---

## 1 ▸ Select a Gemini reviewer action

| GitHub Action | Comment style | Trigger options | Repo URL |
|---------------|---------------|-----------------|---------|
| **`truongnh1992/gemini-ai-code-reviewer`** | Inline PR comments **plus** a summary block | • Automatic on each push<br>• Or manual by typing `/gemini-review` | <https://github.com/truongnh1992/gemini-ai-code-reviewer> |
| **`rubensflinco/gemini-code-review-action`** | Single summary comment (Markdown) | Automatic on each push | <https://github.com/rubensflinco/gemini-code-review-action> |

> *This playbook assumes the first action because its inline comments mirror the OpenAI reviewer you already use. Substitute freely if you prefer the second.*

---

## 2 ▸ One‑time setup

1. **Generate a Gemini API key** in Google AI Studio (or the Google Cloud console) with model access you need (e.g. `gemini-1.5-pro-latest`).  
2. **Add repository secrets**  
   * `OPENAI_API_KEY` – already present for GPT‑4o‑mini.  
   * `GEMINI_API_KEY` – new.  
3. **Decide event scope** (see §4 for public‑fork security):  
   ```yaml
   on:
     pull_request:
       types: [opened, reopened, synchronize, ready_for_review]
   ```

---

## 3 ▸ Add a parallel Gemini job to your workflow

Create (or extend) `.github/workflows/ai-reviewers.yml`:

```yaml
name: AI code reviewers

on:
  pull_request:
    types: [opened, reopened, synchronize, ready_for_review]

permissions:
  contents: read
  pull-requests: write

jobs:
  # ── 1 · OpenAI reviewer (existing) ────────────────────────────────
  openai_review:
    name: GPT‑4o‑mini review
    runs-on: ubuntu-latest
    concurrency: openai-${{ github.event.pull_request.number }}
    steps:
      - uses: AleksandrFurmenkovOfficial/ai-code-review@v0.8
        with:
          token:          ${{ secrets.GITHUB_TOKEN }}
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
          ai_provider:    openai
          openai_model:   gpt-4o-mini
          exclude_paths:  "*.md,*.yml,*.yaml"

  # ── 2 · Gemini reviewer (new) ─────────────────────────────────────
  gemini_review:
    name: Gemini‑1.5‑Pro review
    runs-on: ubuntu-latest
    concurrency: gemini-${{ github.event.pull_request.number }}
    steps:
      - uses: truongnh1992/gemini-ai-code-reviewer@v6.5.0
        with:
          GITHUB_TOKEN:   ${{ secrets.GITHUB_TOKEN }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          GEMINI_MODEL:   gemini-1.5-pro-latest   # or gemini-1.5-flash for cost/speed
          EXCLUDE:        "*.md,*.yml,*.yaml"
          COMMENT_HEADER: "### 💎 Gemini review\n"
```

**Why this layout?** Two separate jobs run in parallel; `concurrency:` prevents duplicate runs on force‑pushes; shared trigger keeps CI status clean (two checkmarks ✔︎).

---

## 4 ▸ Public‑fork security (secrets on `pull_request_target`)

For public repos that accept PRs from forks:

1. **Move only the AI jobs** to the `pull_request_target` event so secrets are still injected.  
2. **Checkout the PR code by SHA** to avoid running workflow code from the fork:  
   ```yaml
   - uses: actions/checkout@v4
     with:
       ref: ${{ github.event.pull_request.head.sha }}
       token: ${{ github.token }}
       fetch-depth: 0
   ```

---

## 5 ▸ Cost & quota hygiene

| Lever | OpenAI reviewer | Gemini reviewer |
|-------|-----------------|-----------------|
| **Model** | `gpt‑4o‑mini` (cheap, 128k context) | `gemini‑1.5‑pro` (25k context) or `gemini‑1.5‑flash` |
| **Size caps** | `MAX_PATCH_BYTES` or `pull_request_chunk_size` | `PATCH_CHUNK_SIZE` |
| **Exclude paths** | `"*.md,*.yml,*.yaml"` | identical |

Dial models or chunk sizes down if you have very large diffs.

---

## 6 ▸ Operational tips

* **Prefix Gemini comments** (`COMMENT_HEADER`) so reviewers are visually distinct.  
* **Ignore each other’s comments** by default (`exclude_paths` already avoids workflow files).  
* **Optional aggregator job**: post a single summary comment combining both reviewers if PR threads get noisy.

---

## 7 ▸ Maintenance

* Pin action versions (`@v6.5.0`) to avoid surprises; bump quarterly.  
* Rotate API keys and monitor usage dashboards for cost spikes.  
* Periodically sample reviews to ensure each AI still meets quality standards.

---

### References

* Gemini action docs – <https://github.com/truongnh1992/gemini-ai-code-reviewer>
* Gemini action docs (alt) – <https://github.com/rubensflinco/gemini-code-review-action>
* OpenAI reviewer action – <https://github.com/AleksandrFurmenkovOfficial/ai-code-review>
