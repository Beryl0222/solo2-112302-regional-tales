"""已提交的示范馆员作业状态与签发产物必须持续满足关键业务约束。"""
import json
import unittest
from pathlib import Path

from woodcut.repository import ROOT
from woodcut.workspace import Workspace


class CommittedDemoArtifactsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state_path = ROOT / "data" / "state.json"
        if not cls.state_path.exists():
            raise unittest.SkipTest("尚未运行 scripts/build_demo.py 生成 data/state.json")
        cls.ws = Workspace.load(state_path=cls.state_path)
        cls.state = cls.ws.state

    def test_four_releases_with_version_chain(self):
        ids = {r["id"] for r in self.ws.list_releases()}
        # 基准四稿必须存在；馆员按 README 继续演练追加的 v3 等不影响回归
        self.assertTrue({
            "REL-HALL-C12-v1", "REL-HALL-C12-v2",
            "REL-CLASS-C12-v1", "REL-CLASS-C12-v2",
        }.issubset(ids))
        v2 = self.ws.get_release("REL-HALL-C12-v2")
        self.assertEqual(v2["term_version"], 2)
        self.assertEqual(v2["supersedes"], "REL-HALL-C12-v1")
        self.assertEqual(self.ws.get_release("REL-HALL-C12-v1")["status"], "superseded")

    def test_issued_v2_docs_retain_both_timestamps(self):
        for rid in ("REL-HALL-C12-v2", "REL-CLASS-C12-v2"):
            rel = self.ws.get_release(rid)
            stamps = {t["timestamp"] for t in rel["source_timestamps"]}
            self.assertEqual(stamps, {"00:43", "01:12"})
            self.assertIn("口述者原意", rel["body_markdown"])
            self.assertIn("馆方", rel["body_markdown"])

    def test_ambiguous_it_kept_both_candidates_in_committed_review(self):
        review = self.ws.mention_review("m:h0:it")
        self.assertEqual(review["state"], "open_candidates")
        self.assertIn("block:c12", review["chosen"])
        self.assertIn("entity:c12:sheet-prev", review["chosen"])

    def test_hall_description_remains_in_review_queue(self):
        pending = {d["id"] for d in self.ws.pending_descriptions()}
        self.assertEqual(pending, {"desc:c12:hall"})

    def test_output_markdown_files_exist(self):
        out = ROOT / "outputs" / "issued"
        for rid in ("REL-HALL-C12-v1", "REL-HALL-C12-v2",
                    "REL-CLASS-C12-v1", "REL-CLASS-C12-v2"):
            self.assertTrue((out / f"{rid}.md").exists())
        registry = ROOT / "outputs" / "registry.json"
        self.assertTrue(registry.exists())
        bundle = json.loads(registry.read_text(encoding="utf-8"))
        self.assertIn("review_queue", bundle)


if __name__ == "__main__":
    unittest.main()
