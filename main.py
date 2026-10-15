"""CLI: python main.py [--top 3] [--out drafts]"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re

from llm import LLM
from pipeline import run
from sources import collect


def slug(s: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", "-", s).strip("-")[:40] or "draft"


def main() -> None:
    ap = argparse.ArgumentParser(description="Overseas AI trends -> Xiaohongshu drafts")
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--min-score", type=float, default=6.0)
    ap.add_argument("--out", default="drafts")
    a = ap.parse_args()

    # Scorer can be a cheap classifier model (e.g. SubQ Snap); writer a stronger chat model (e.g. Meta Muse).
    writer = LLM()
    scorer = LLM(os.getenv("SCORER_BASE_URL") or None, os.getenv("SCORER_API_KEY") or None,
                 os.getenv("SCORER_MODEL") or None) if os.getenv("SCORER_MODEL") else writer

    items = collect()
    print(f"collected {len(items)} AI-related items")
    drafts = run(items, scorer, writer, top_k=a.top, min_score=a.min_score)

    day = pathlib.Path(a.out) / dt.date.today().isoformat()
    day.mkdir(parents=True, exist_ok=True)
    (day / "candidates.json").write_text(json.dumps([i.to_dict() for i in items], ensure_ascii=False, indent=2))
    for n, d in enumerate(drafts, 1):
        p = day / f"{n:02d}-{slug(d.title or d.item.title)}.md"
        p.write_text(d.to_markdown(), encoding="utf-8")
        print(f"[{d.score:.1f}] {d.item.title}\n   -> {p}")


if __name__ == "__main__":
    main()
