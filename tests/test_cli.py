"""CLI 端到端测试，特别防止全局 --state 与复核 --state 的 dest 冲突复发。"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from woodcut.cli import main


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.state = self.tmp / "state.json"
        self.out = self.tmp / "outputs"

    def run_cli(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["--state", str(self.state), *argv])
        return code, buf.getvalue()

    def test_summary_and_trace(self):
        code, out = self.run_cli(["summary"])
        self.assertEqual(code, 0)
        self.assertIn("木刻", out)

        code, out = self.run_cli(["trace", "l1"])
        self.assertEqual(code, 0)
        self.assertIn("01:12", out)
        self.assertIn("作品卡", out)

    def test_review_state_option_does_not_overwrite_state_path(self):
        # 回归：review-mention 的 --state 曾覆盖全局状态文件路径
        self.run_cli(["adopt-revision", "term:ban", "--reviewer", "t"])
        code, out = self.run_cli([
            "review-mention", "m:h0:it",
            "--state", "open_candidates",
            "--choose", "block:c12",
            "--choose", "entity:c12:sheet-prev",
            "--note", "两候选并存",
        ])
        self.assertEqual(code, 0)
        saved = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertIn("m:h0:it", saved["mention_reviews"])
        # 不得在当前工作目录写出以复核状态命名的垃圾文件
        self.assertFalse(Path("open_candidates").exists())

    def test_full_issue_flow_via_cli(self):
        code, out = self.run_cli([
            "issue", "hall_sound", "--issuer", "CLI馆员", "--out-dir", str(self.out)
        ])
        self.assertEqual(code, 0)
        self.assertIn("REL-HALL-C12-v1", out)
        md_files = list((self.out / "issued").glob("*.md"))
        self.assertEqual(len(md_files), 1)

        code, out = self.run_cli(["release", "list", "--json"])
        self.assertEqual(code, 0)
        releases = json.loads(out)
        self.assertEqual(releases[0]["issuer"], "CLI馆员")

    def test_queue_descriptions_only_json(self):
        self.run_cli(["adopt-revision", "term:ban"])
        code, out = self.run_cli(["queue", "--descriptions-only", "--json"])
        self.assertEqual(code, 0)
        pending = json.loads(out)
        self.assertEqual(len(pending), 3)


if __name__ == "__main__":
    unittest.main()
