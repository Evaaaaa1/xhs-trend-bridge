# XHS Trend Bridge 🌉

Turn today's overseas AI trends into **original, reviewed Xiaohongshu (小红书) drafts** for Chinese-speaking users who can't easily reach ChatGPT, Claude or X.

把海外每天的 AI 热点，筛选成国内用户真正用得上的内容，并生成小红书风格的中文原创草稿，人工审核后再发布。

## How it works

```
Hacker News / Reddit  ──►  collect + AI keyword filter + dedupe
                              │
                              ▼
                 scorer LLM (cheap classifier, e.g. SubQ Snap)
                 "is this useful & reproducible for CN users?"  0-10
                              │  top-k
                              ▼
                 writer LLM (e.g. Meta Muse via Meta Model API)
                 original Chinese post + domestic-tool recreation
                 (Doubao / Kimi / DeepSeek) + source link + tags
                              │
                              ▼
          drafts/YYYY-MM-DD/*.md  ──►  human review checklist  ──►  post
```

- **Two-model design**: a cheap classifier does the high-volume filtering, a stronger model only writes the few picks, which keeps cost low.
- **Any OpenAI-compatible API**: Meta Model API, DeepSeek, Kimi, Qwen, SubQ. Configure via env vars.
- **Works without a key**: falls back to an engagement + keyword heuristic so the pipeline always runs.
- **Responsible by design**: no verbatim translation of paywalled articles, always cites the source, never teaches VPN use, and every draft ships with a fact-check / real-test checklist.
- **Zero dependencies**: Python 3.10+ stdlib only. Run it daily with cron or GitHub Actions (`python main.py`).

## Quick start

```bash
cp env.example .env   # fill in keys (optional)
set -a; source .env; set +a
python main.py --top 3
python -m unittest test_pipeline
```

Drafts land in `drafts/<date>/`, with `candidates.json` holding every collected item.

## Roadmap (hackathon)

- [ ] Meta Muse as the writer model; Muse Image for cover images
- [ ] More sources: X lists, GitHub Trending, Product Hunt
- [ ] Review dashboard: approve / edit / reject, then export image-text cards
- [ ] Feedback loop: learn scoring from which drafts get approved and how posts perform

## License

MIT
