"""人物、作品归属与木刻制作事件的可复查图谱测试。"""
import unittest

from woodcut.model import EventType
from woodcut.repository import Repository
from woodcut.workspace import Workspace


class GraphTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = Repository.load()
        cls.ws = Workspace(cls.repo)

    def test_all_nine_corpus_records_are_accounted_for(self):
        # 校验在 load() 时已保证每条 corpus 记录被知识层引用
        self.assertEqual(len(self.repo.records), 9)
        self.assertEqual(self.repo.validate(), [])

    def test_people_built_from_interview_catalog_and_cards(self):
        he = self.repo.person_by_id["person:hekun"]
        zhou = self.repo.person_by_id["person:zhoumin"]
        self.assertEqual(he["name"], "贺昆")
        self.assertIn("版画教师", he["roles"])
        self.assertEqual(zhou["name"], "周敏")
        self.assertIn("参展学员", zhou["roles"])

        # a1 的说话人归属进入访谈登记
        self.assertEqual(self.repo.interview_by_id["int:zhou"]["speaker_id"], "person:zhoumin")
        self.assertEqual(self.repo.interview_by_id["int:he"]["speaker_id"], "person:hekun")

    def test_student_is_creator_teacher_is_mentor_not_owner(self):
        w = self.repo.work_by_id["work:c12"]
        self.assertEqual(w["creation"]["creator_id"], "person:zhoumin")
        self.assertIn("person:hekun", w["mentor_ids"])

        lineage = w["lineage"][0]
        self.assertEqual(lineage["from_person_id"], "person:hekun")
        self.assertEqual(lineage["to_person_id"], "person:zhoumin")
        self.assertIn("不把学员作品", lineage["rule"])

        # l1 的“共同制作”只是对立主张，不能覆盖作品卡
        claim = w["attribution_claims"][0]
        self.assertEqual(claim["source_id"], "l1")
        self.assertEqual(claim["status"], "conflicting_unverified")
        self.assertEqual(w["creation"]["creator_id"], "person:zhoumin")

    def test_creation_carving_overprint_collection_exhibition_are_distinct(self):
        types = {e["type"] for e in self.repo.events}
        for t in (EventType.CREATION, EventType.CARVING, EventType.OVERPRINTING,
                  EventType.EXHIBITION, EventType.COLLECTION):
            self.assertIn(t, EventType.ALL)
        self.assertIn(EventType.CREATION, types)
        self.assertIn(EventType.CARVING, types)
        self.assertIn(EventType.OVERPRINTING, types)
        self.assertIn(EventType.EXHIBITION, types)

        # 语料没有收藏材料：不得虚构收藏事件，只能登记材料缺口
        self.assertNotIn(EventType.COLLECTION, types)
        gaps = [g for g in self.repo.coverage_gaps if g["type"] == EventType.COLLECTION]
        self.assertTrue(gaps)
        self.assertEqual(gaps[0]["work_id"], "work:c12")

        creation = [e for e in self.repo.events if e["type"] == EventType.CREATION][0]
        exhibit = [e for e in self.repo.events if e["type"] == EventType.EXHIBITION][0]
        self.assertNotEqual(creation["id"], exhibit["id"])

    def test_reduction_states_are_not_folded_into_one_work(self):
        # 最后套印、红土刻版、母版刻毁是不同事件
        ids = {e["id"]: e for e in self.repo.events}
        self.assertNotEqual(ids["event:c12:overprint-last"]["type"],
                            ids["event:c12:block-destroyed"]["type"])
        self.assertEqual(ids["event:c12:carve-red-earth"]["type"], EventType.CARVING)

        # 最终状态、递减序列、红土层是不同 block_state
        state_ids = {s["id"] for s in self.repo.block_states}
        self.assertIn("state:c12:final", state_ids)
        self.assertIn("state:c12:sequence", state_ids)
        self.assertIn("state:c12:red-earth-layer", state_ids)
        red = self.repo.state_by_id["state:c12:red-earth-layer"]
        self.assertEqual(red["ordinal"], "unknown")

        # 全部状态都属于同一块母版，而不是被建模成多张作品
        work_ids = {w["id"] for w in self.repo.works}
        self.assertEqual(work_ids, {"work:c12"})
        for s in self.repo.block_states:
            self.assertEqual(s["block_id"], "block:c12")

    def test_teacher_student_co_exhibition_links_both_but_no_ownership_shift(self):
        exhibit = next(e for e in self.repo.events if e["type"] == EventType.EXHIBITION)
        actor_ids = {a["person_id"] for a in exhibit["actors"]}
        self.assertEqual(actor_ids, {"person:zhoumin", "person:hekun"})
        w = self.repo.work_by_id["work:c12"]
        self.assertEqual(w["creation"]["creator_id"], "person:zhoumin")

    def test_card_scope_warning_for_unnumbered_technique_card(self):
        desc = self.repo.description_by_id["desc:c12:technique"]
        self.assertEqual(desc["raw_source_id"], "c1")
        self.assertIn("未标 C12 编号", desc["scope_warning"])


if __name__ == "__main__":
    unittest.main()
