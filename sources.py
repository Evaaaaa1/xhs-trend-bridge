"""Collect trending AI items from public sources (stdlib only)."""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict

UA = "xhs-trend-bridge/0.1 (+https://github.com/)"

AI_KEYWORDS = [
    "ai", "llm", "gpt", "chatgpt", "claude", "gemini", "llama", "muse", "deepseek",
    "qwen", "kimi", "openai", "anthropic", "agent", "prompt", "model", "diffusion",
    "transformer", "rag", "copilot", "cursor", "sora", "midjourney", "mcp",
]
_KW_RE = re.compile(r"\b(" + "|".join(map(re.escape, AI_KEYWORDS)) + r")\b", re.I)


@dataclass
class Item:
    source: str
    title: str
    url: str
    points: int = 0
    comments: int = 0
    summary: str = ""
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _get(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def is_ai_related(text: str) -> bool:
    return bool(_KW_RE.search(text or ""))


def fetch_hackernews(hours: int = 24, min_points: int = 50, limit: int = 50) -> list[Item]:
    since = int(time.time()) - hours * 3600
    q = urllib.parse.urlencode({
        "tags": "story",
        "numericFilters": f"created_at_i>{since},points>{min_points}",
        "hitsPerPage": limit,
    })
    data = json.loads(_get(f"https://hn.algolia.com/api/v1/search?{q}"))
    items = []
    for h in data.get("hits", []):
        title = h.get("title") or ""
        if not is_ai_related(title):
            continue
        items.append(Item(
            source="Hacker News",
            title=title,
            url=h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
            points=h.get("points") or 0,
            comments=h.get("num_comments") or 0,
            extra={"discussion": f"https://news.ycombinator.com/item?id={h.get('objectID')}"},
        ))
    return items


_ATOM = {"a": "http://www.w3.org/2005/Atom"}


def parse_reddit_atom(xml_bytes: bytes, subreddit: str) -> list[Item]:
    root = ET.fromstring(xml_bytes)
    items = []
    for e in root.findall("a:entry", _ATOM):
        title = (e.findtext("a:title", default="", namespaces=_ATOM) or "").strip()
        link = e.find("a:link", _ATOM)
        url = link.get("href") if link is not None else ""
        content = e.findtext("a:content", default="", namespaces=_ATOM) or ""
        text = re.sub(r"<[^>]+>", " ", content)
        text = re.sub(r"\s+", " ", text).strip()[:500]
        items.append(Item(source=f"r/{subreddit}", title=title, url=url, summary=text))
    return items


def fetch_reddit(subreddit: str = "LocalLLaMA", limit: int = 15) -> list[Item]:
    raw = _get(f"https://www.reddit.com/r/{subreddit}/top/.rss?t=day&limit={limit}")
    return parse_reddit_atom(raw, subreddit)[:limit]


def collect(subreddits=("LocalLLaMA", "ChatGPT")) -> list[Item]:
    items: list[Item] = []
    for fn, args in [(fetch_hackernews, ())] + [(fetch_reddit, (s,)) for s in subreddits]:
        try:
            items.extend(fn(*args))
            time.sleep(2)  # be polite; Reddit rate-limits bursts
        except Exception as exc:  # one bad source shouldn't kill the run
            print(f"[warn] {fn.__name__}{args}: {exc}")
    seen, unique = set(), []
    for it in items:
        key = it.url.split("?")[0].rstrip("/")
        if key not in seen:
            seen.add(key)
            unique.append(it)
    return unique
