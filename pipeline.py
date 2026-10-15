"""Score -> pick -> rewrite into Xiaohongshu drafts for human review."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

from llm import LLM, extract_json
from sources import Item

SCORE_SYSTEM = """You curate overseas AI news for Chinese-speaking Xiaohongshu users in mainland China.
They usually cannot use ChatGPT, Claude or X directly, so value = practical tricks, prompts or tool ideas
they can reproduce with domestic apps (Doubao, Kimi, DeepSeek, Qwen), or genuinely big news.
Low value: pure business/funding news, US politics, niche infra, anything requiring a VPN to try.
Return ONLY JSON: [{"id": <int>, "score": <0-10>, "angle": "<one-line Chinese angle>"}]"""

WRITE_SYSTEM = """你是小红书 AI 博主。把一条海外 AI 热点改写成一篇原创中文笔记：
- 不要逐句翻译原文，要用自己的话讲清楚"是什么、为什么火、对普通人有什么用"
- 如果是玩法/提示词，给出用豆包、Kimi 或 DeepSeek 复现的具体步骤和可复制的提示词
- 不教翻墙，不夸大，不确定的地方说"据原帖称"
- 标题 20 字以内，带 1 个 emoji；正文 300-500 字，分段+少量 emoji；结尾抛一个互动问题
- 末尾附"来源：<原链接>"和 4-6 个话题标签
只返回 JSON：{"title": "...", "body": "...", "tags": ["#..."], "cover_text": "封面大字，10字以内"}"""


@dataclass
class Draft:
    item: Item
    score: float
    angle: str
    title: str = ""
    body: str = ""
    tags: list | None = None
    cover_text: str = ""

    def to_markdown(self) -> str:
        tags = " ".join(self.tags or [])
        return (
            f"# {self.title or self.item.title}\n\n"
            f"> 封面字：{self.cover_text}  \n> 评分：{self.score:.1f}  ·  角度：{self.angle}  \n"
            f"> 原文：[{self.item.title}]({self.item.url})（{self.item.source}）\n\n"
            f"{self.body}\n\n{tags}\n\n---\n- [ ] 已人工核对事实\n- [ ] 已在国内工具实测并截图\n"
        )


def heuristic_score(item: Item) -> float:
    """No-API fallback: engagement + 'tryable by normal people' keywords."""
    s = math.log10(1 + item.points + 2 * item.comments) * 2
    t = item.title.lower()
    if re.search(r"prompt|how to|guide|trick|free|open[- ]source|release|launch|tool", t):
        s += 2
    if re.search(r"funding|raises|lawsuit|valuation|ipo|layoff", t):
        s -= 2
    return max(0.0, min(10.0, s))


def score_items(items: list[Item], llm: LLM, batch: int = 20) -> list[tuple[Item, float, str]]:
    if not llm.enabled:
        return [(it, heuristic_score(it), "（未配置模型，按热度排序）") for it in items]
    out = []
    for start in range(0, len(items), batch):
        chunk = items[start:start + batch]
        listing = "\n".join(f"{i}. [{it.source}] {it.title} | {it.summary[:200]}" for i, it in enumerate(chunk))
        try:
            res = extract_json(llm.chat(SCORE_SYSTEM, listing, temperature=0))
            by_id = {int(r["id"]): r for r in res}
        except Exception as exc:
            print(f"[warn] scoring failed, using heuristic: {exc}")
            by_id = {}
        for i, it in enumerate(chunk):
            r = by_id.get(i)
            if r:
                out.append((it, float(r.get("score", 0)), r.get("angle", "")))
            else:
                out.append((it, heuristic_score(it), "（启发式）"))
    return out


def write_draft(item: Item, score: float, angle: str, llm: LLM) -> Draft:
    d = Draft(item=item, score=score, angle=angle)
    if not llm.enabled:
        d.title = item.title
        d.body = "（未配置模型：这里会生成中文笔记正文）"
        return d
    prompt = f"热点标题：{item.title}\n来源：{item.source}\n链接：{item.url}\n摘要：{item.summary}\n建议角度：{angle}"
    try:
        res = extract_json(llm.chat(WRITE_SYSTEM, prompt))
        d.title, d.body = res.get("title", ""), res.get("body", "")
        d.tags, d.cover_text = res.get("tags", []), res.get("cover_text", "")
    except Exception as exc:
        d.body = f"（生成失败：{exc}）"
    return d


def run(items: list[Item], scorer: LLM, writer: LLM, top_k: int = 3, min_score: float = 6.0) -> list[Draft]:
    scored = sorted(score_items(items, scorer), key=lambda x: x[1], reverse=True)
    # Items above the bar first; if fewer than top_k clear it, the next best still go to review.
    picks = scored[:top_k] if len([s for s in scored if s[1] >= min_score]) < top_k else \
        [s for s in scored if s[1] >= min_score][:top_k]
    return [write_draft(it, sc, ang, writer) for it, sc, ang in picks]
