"""代词多候选、“版/张”裁定与术语修订后全面重判的测试。"""
import unittest
from pathlib import Path

from materials import load_corpus
from woodcut.model import ReviewState
from woodcut.repository import Repository
from woodcut.workspace import Workspace


class TermAndPronounTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repository.load()
        self.ws = Workspace(self.repo, state=Workspace._empty_state(),
                            state_path=Path("/tmp/unused-state.json"))

    def test_hall_sentence_it_keeps_two_candidates(self):
        m = self.repo.mention_by_id["m:h0:it"]
        values = {c["value"] for c in m["candidates"]}
        self.assertIn("block:c12", values)
        self.assertIn("entity:c12:sheet-prev", values)
        self.assertGreaterEqual(len(m["candidates"]), 2)
        # 旧链接是为顺畅而做的单一固定
        self.assertEqual(m["v1_link"]["chosen"], "block:c12")
        self.assertTrue(m["v1_link"].get("smoothness_driven"))
        self.assertIn("时序", m["conflict"])

    def test_q2_pronoun_he_is_not_automatically_hukun(self):
        m = self.repo.mention_by_id["m:q2:ta"]
        values = {c["value"] for c in m["candidates"]}
        self.assertIn("entity:unnamed:ta-q2", values)
        self.assertIn("person:hekun", values)

        review = self.ws.review_mention(
            "m:q2:ta", ReviewState.OPEN_CANDIDATES,
            chosen=["entity:unnamed:ta-q2", "person:hekun"],
        )
        self.assertEqual(review["state"], ReviewState.OPEN_CANDIDATES)
        self.assertEqual(len(review["chosen"]), 2)
        # 候选数据本身没有被复核动作删改
        self.assertEqual(len(self.repo.mention_by_id["m:q2:ta"]["candidates"]), 2)

    def test_adopt_revision_marks_all_links_pending(self):
        self.assertEqual(self.ws.current_term_version(), 1)
        self.ws.adopt_term_revision("term:ban", reviewer="t")
        self.assertEqual(self.ws.current_term_version(), 2)
        self.assertEqual(len(self.ws.pending_mentions()), len(self.repo.mentions))
        self.assertEqual(len(self.ws.pending_descriptions()), len(self.repo.descriptions))

    def test_affected_includes_q2_even_without_character_ban(self):
        q2 = self.repo.statement_by_id["stmt:q2"]["verbatim"]
        self.assertNotIn("版", q2)  # q2 全句无“版”字
        self.ws.adopt_term_revision("term:ban")
        ids = self.ws.affected_statement_ids("term:ban")
        self.assertIn("stmt:q1", ids)
        self.assertIn("stmt:q2", ids)       # 经事件实体链接召回
        self.assertIn("stmt:h0", ids)
        self.assertIn("stmt:g1", ids)
        self.assertIn("stmt:c1", ids)

        overview = self.ws.affected_overview("term:ban")
        self.assertIn("stmt:l1", overview["downstream_teaching_ids"])

    def test_term_revision_does_not_rewrite_raw_corpus(self):
        before = load_corpus()
        self.ws.adopt_term_revision("term:ban")
        after = load_corpus()
        self.assertEqual(before, after)
        q1_raw = self.repo.raw_body("q1")
        self.assertIn("最后一版的时候，版已经用完了", q1_raw)

    def test_readjudication_can_change_links_rather_than_replace_text(self):
        self.ws.adopt_term_revision("term:ban")
        r = self.ws.review_mention(
            "m:q1:last-ban", ReviewState.CHANGED, chosen=["sense:ban:state"], note="语境裁定"
        )
        self.assertEqual(r["state"], ReviewState.CHANGED)
        # 未复核的仍在队列；已复核的离开队列
        pending_ids = {m["id"] for m in self.ws.pending_mentions()}
        self.assertNotIn("m:q1:last-ban", pending_ids)
        self.assertIn("m:h0:it", pending_ids)

    def test_description_review_queue_after_term_change(self):
        self.ws.adopt_term_revision("term:ban")
        self.assertEqual(
            {d["id"] for d in self.ws.pending_descriptions()},
            {"desc:c12:card", "desc:c12:technique", "desc:c12:hall"},
        )
        self.ws.review_description("desc:c12:card", ReviewState.CONFIRMED, note="ok")
        self.ws.review_description("desc:c12:technique", ReviewState.CONFIRMED, note="ok")
        self.assertEqual(
            [d["id"] for d in self.ws.pending_descriptions()],
            ["desc:c12:hall"],
        )

    def test_adjudicate_last_ban_uses_nearby_context(self):
        result = self.ws.adjudicate_quantity(
            "最后一版", nearby_statement_ids=["stmt:q1", "stmt:c1"]
        )
        self.assertEqual(result["decision"], "sense:ban:state")

        bare = self.ws.adjudicate_quantity("最后一版", nearby_statement_ids=[])
        self.assertEqual(bare["decision"], ReviewState.OPEN_CANDIDATES)

    def test_adjudicate_one_sheet_is_count_not_edition(self):
        r = self.ws.adjudicate_quantity("一张", nearby_statement_ids=[])
        self.assertEqual(r["decision"], "sense:ban:sheet_count")
        self.assertEqual(r["count_status"], "张数不可考")
        self.assertFalse(r["sheet_numbering"])

        numbered = self.ws.adjudicate_quantity("一张", has_sheet_number=True)
        self.assertIn("numbered", numbered["decision"])


if __name__ == "__main__":
    unittest.main()
