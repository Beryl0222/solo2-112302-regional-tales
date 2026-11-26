"""教学稿 -> 录音/作品卡追踪，以及两类文稿签发与受众更新决定的测试。"""
import json
import tempfile
import unittest
from pathlib import Path

from woodcut.documents import build_draft
from woodcut.model import Audience, ReviewState, UpdateAction
from woodcut.workspace import Workspace


class TraceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws = Workspace.load(state_path=Path(tempfile.mkdtemp()) / "state.json")

    def test_trace_lesson_l1_reaches_recording_and_cards(self):
        t = self.ws.trace("l1")
        stamps = {(r["speaker"], r["timestamp"]) for r in t["recording"]}
        self.assertIn(("贺昆", "01:12"), stamps)
        # a1 的“不是同一次访谈”说明必须随追踪返回
        notes = " ".join(r.get("interview_note", "") for r in t["recording"])
        self.assertIn("不是同一次访谈", notes)

        card_kinds = {d["kind"] for d in t["cards"]}
        self.assertIn("artwork_card", card_kinds)
        self.assertIn("technique_card", card_kinds)

        raw = set(t["raw_record_ids"])
        self.assertIn("l1", raw)
        self.assertIn("q2", raw)
        self.assertIn("a1", raw)
        self.assertIn("w1", raw)

        # 对立归属主张也在追踪结果里
        self.assertTrue(any(c["id"] == "claim:l1-joint" for c in t["claims"]))

    def test_trace_h0_keeps_both_recording_timestamps(self):
        t = self.ws.trace("stmt:h0")
        stamps = {r["timestamp"] for r in t["recording"]}
        self.assertEqual(stamps, {"00:43", "01:12"})

    def test_trace_accepts_release_and_mention_ids(self):
        t1 = self.ws.trace("m:h0:it")
        self.assertIn("stmt:h0", t1["statement_ids"])
        t2 = self.ws.trace("C12")
        self.assertTrue(t2["works"])


class PublishingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.state_path = self.tmp / "state.json"
        self.ws = Workspace.load(state_path=self.state_path)

    def test_issue_separates_original_words_from_museum_interpretation(self):
        rel = self.ws.issue(Audience.HALL_SOUND, "测试馆员", at="2026-11-18T09:00:00+08:00")
        md = rel.body_markdown
        self.assertIn("口述者原意", md)
        self.assertIn("馆方说明", md)
        self.assertIn("00:43", md)
        self.assertIn("01:12", md)
        self.assertEqual({t["timestamp"] for t in rel.source_timestamps}, {"00:43", "01:12"})
        self.ws.save()

        # 状态可重载
        reloaded = Workspace.load(state_path=self.state_path)
        self.assertEqual(len(reloaded.list_releases()), 1)
        self.assertEqual(reloaded.get_release(rel.id)["issuer"], "测试馆员")

    def test_term_revision_marks_issued_docs_stale_but_never_rewrites_them(self):
        v1 = self.ws.issue(Audience.HALL_SOUND, "馆员", at="2026-11-18T09:00:00+08:00")
        original_body = v1.body_markdown
        self.ws.adopt_term_revision("term:ban")

        stored = self.ws.get_release(v1.id)
        self.assertTrue(self.ws.is_stale(stored))
        # 已签发正文原样保留
        self.assertEqual(stored["body_markdown"], original_body)
        self.assertIn("v1", original_body)

    def test_audience_can_keep_or_revise_independently(self):
        hall_v1 = self.ws.issue(Audience.HALL_SOUND, "馆员")
        class_v1 = self.ws.issue(Audience.CLASSROOM, "馆员")
        self.ws.adopt_term_revision("term:ban")

        # 展厅受众决定本次不更新，必须留理由
        decision = self.ws.keep_release(hall_v1.id, "本季录音已制作，先以现场口头补充", "馆员甲")
        self.assertEqual(decision["action"], UpdateAction.KEEP_CURRENT)
        kept = self.ws.get_release(hall_v1.id)
        self.assertEqual(kept["status"], "issued")  # 仍然有效
        # 术语虽旧，但已有“保留不更新”的受众决定，不再挂待处理
        self.assertEqual(self.ws.release_attention(kept), "kept")

        # 课堂受众决定出修订版
        v2 = self.ws.issue(Audience.CLASSROOM, "馆员乙", supersedes=class_v1.id)
        self.assertEqual(v2.version, 2)
        self.assertEqual(v2.supersedes, class_v1.id)
        self.assertEqual(self.ws.get_release(class_v1.id)["status"], "superseded")
        self.assertEqual(self.ws.get_release(v2.id)["status"], "issued")
        # 新版仍保留录音时间
        self.assertEqual({t["timestamp"] for t in v2.source_timestamps}, {"00:43", "01:12"})
        # 展厅稿没有被连带升版
        self.assertEqual(self.ws.get_release(hall_v1.id)["version"], 1)

    def test_revised_draft_preserves_timestamps_and_candidates(self):
        self.ws.adopt_term_revision("term:ban")
        self.ws.review_mention(
            "m:h0:it", ReviewState.OPEN_CANDIDATES,
            chosen=["block:c12", "entity:c12:sheet-prev"], note="并存",
        )
        md, _ = build_draft(self.ws, Audience.HALL_SOUND)
        self.assertIn("00:43", md)
        self.assertIn("01:12", md)
        self.assertIn("上一张印纸", md)
        self.assertIn("open_candidates", md)

    def test_student_byline_changes_display_but_keeps_lineage(self):
        base = {
            "id": "view:x",
            "creation_display": "师生共展（仅标导师）",
            "byline_present": False,
            "lineage_display": "贺昆 -> 周敏：绝版木刻技艺沿袭",
        }
        updated = Workspace.add_student_byline(base)
        self.assertTrue(updated["byline_present"])
        self.assertIn("周敏", updated["creation_display"])
        self.assertEqual(updated["lineage_display"], base["lineage_display"])
        # 不变更原对象
        self.assertFalse(base["byline_present"])

    def test_apply_byline_persists_override_without_touching_knowledge(self):
        view = self.ws.apply_student_byline("view:c12:current", reviewer="馆员")
        self.assertTrue(view["byline_present"])
        self.assertIn("贺昆", view["lineage_display"])
        again = self.ws.card_view("view:c12:current")
        self.assertIn("byline_updated_by", again)


if __name__ == "__main__":
    unittest.main()
