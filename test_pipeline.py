import unittest

from llm import extract_json
from pipeline import heuristic_score, run
from sources import Item, is_ai_related, parse_reddit_atom


class FakeLLM:
    enabled = True

    def chat(self, system, user, temperature=0.7):
        if "curate" in system:
            return '```json\n[{"id": 0, "score": 9, "angle": "国内可复现"}, {"id": 1, "score": 2, "angle": "融资新闻"}]\n```'
        return '{"title": "测试标题✨", "body": "正文", "tags": ["#AI"], "cover_text": "封面"}'


class T(unittest.TestCase):
    def test_keywords(self):
        self.assertTrue(is_ai_related("New LLM agent framework"))
        self.assertFalse(is_ai_related("Things to know when you get cancer"))

    def test_extract_json(self):
        self.assertEqual(extract_json('ok ```json\n{"a":1}\n```')["a"], 1)

    def test_heuristic(self):
        a = Item("HN", "Free open-source prompt tool", "u", points=300)
        b = Item("HN", "AI startup raises $1B", "u", points=300)
        self.assertGreater(heuristic_score(a), heuristic_score(b))

    def test_run_with_llm(self):
        items = [Item("HN", "Prompt trick", "u1"), Item("HN", "AI raises", "u2")]
        drafts = run(items, FakeLLM(), FakeLLM(), top_k=1)
        self.assertEqual(drafts[0].item.url, "u1")
        self.assertIn("测试标题", drafts[0].to_markdown())

    def test_reddit_atom(self):
        xml = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Llama trick</title>
        <link href="https://reddit.com/x"/><content>&lt;p&gt;hello&lt;/p&gt;</content></entry></feed>'''
        it = parse_reddit_atom(xml, "LocalLLaMA")[0]
        self.assertEqual((it.title, it.url, it.summary), ("Llama trick", "https://reddit.com/x", "hello"))


if __name__ == "__main__":
    unittest.main()
