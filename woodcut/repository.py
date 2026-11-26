"""读取并校验原始语料与复核知识层。

Repository 是无状态的只读层：
- data/corpus.json 原样保留，不修改任何一个字；
- data/knowledge.json 中的 source_ids / 证据号必须能回链到 corpus 记录；
- 提供人物、作品、事件、语句、提及、术语、说明稿的索引。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from .model import EventType

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

TIMESTAMP_RE = re.compile(r"(\d{1,2}:\d{2}(?::\d{2})?)")


def split_corpus_text(text: str) -> tuple[Optional[str], str]:
    """corpus 记录形如 ``标签|正文``，拆出标签与正文；无竖线时标签为 None。"""
    if "|" in text:
        label, body = text.split("|", 1)
        return label.strip(), body.strip()
    return None, text.strip()


def find_timestamps(text: str) -> list[str]:
    return TIMESTAMP_RE.findall(text)


class Repository:
    def __init__(self, corpus: dict[str, Any], knowledge: dict[str, Any]):
        self.corpus = corpus
        self.knowledge = knowledge
        self.records: list[dict[str, Any]] = corpus["records"]
        self.record_by_id: dict[str, dict[str, Any]] = {r["id"]: r for r in self.records}

        self.people = knowledge["people"]
        self.works = knowledge["works"]
        self.blocks = knowledge.get("blocks", [])
        self.candidate_entities = knowledge.get("candidate_entities", [])
        self.block_states = knowledge.get("block_states", [])
        self.events = knowledge["events"]
        self.coverage_gaps = knowledge.get("coverage_gaps", [])
        self.interviews = knowledge.get("interviews", [])
        self.statements = knowledge["statements"]
        self.mentions = knowledge["mentions"]
        self.rules = knowledge.get("quantity_expression_rules", [])
        self.terms = knowledge["terms"]
        self.descriptions = knowledge["descriptions"]
        self.card_views = knowledge.get("card_views", [])

        self.person_by_id = {p["id"]: p for p in self.people}
        self.work_by_id = {w["id"]: w for w in self.works}
        self.event_by_id = {e["id"]: e for e in self.events}
        self.statement_by_id = {s["id"]: s for s in self.statements}
        self.mention_by_id = {m["id"]: m for m in self.mentions}
        self.term_by_id = {t["id"]: t for t in self.terms}
        self.description_by_id = {d["id"]: d for d in self.descriptions}
        self.card_view_by_id = {v["id"]: v for v in self.card_views}
        self.interview_by_id = {i["id"]: i for i in self.interviews}
        self.block_by_id = {b["id"]: b for b in self.blocks}
        self.state_by_id = {s["id"]: s for s in self.block_states}
        self.candidate_entity_by_id = {c["id"]: c for c in self.candidate_entities}

        # 作品编号（C12）-> 作品
        self.work_by_inventory = {
            w.get("inventory_no"): w for w in self.works if w.get("inventory_no")
        }

    # ---------- 装载 ----------

    @classmethod
    def load(cls, data_dir: Optional[Path] = None) -> "Repository":
        d = Path(data_dir) if data_dir else DATA_DIR
        corpus = json.loads((d / "corpus.json").read_text(encoding="utf-8"))
        knowledge = json.loads((d / "knowledge.json").read_text(encoding="utf-8"))
        repo = cls(corpus, knowledge)
        errors = repo.validate()
        if errors:
            raise ValueError("知识层校验失败：\n- " + "\n- ".join(errors))
        return repo

    # ---------- 原始记录 ----------

    def raw_record(self, record_id: str) -> Optional[dict[str, Any]]:
        return self.record_by_id.get(record_id)

    def raw_body(self, record_id: str) -> Optional[str]:
        rec = self.record_by_id.get(record_id)
        return split_corpus_text(rec["text"])[1] if rec else None

    # ---------- 校验 / 覆盖 ----------

    def _iter_source_id_lists(self) -> list[tuple[str, list[str]]]:
        pairs: list[tuple[str, list[str]]] = []

        def walk(node: Any, path: str) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    if key in ("source_ids", "support_ids", "basis_ids", "evidence_ids") and isinstance(value, list):
                        pairs.append((f"{path}.{key}", [v for v in value if isinstance(v, str)]))
                    elif key in ("source_id", "raw_source_id", "catalog_ref") and isinstance(value, str):
                        pairs.append((f"{path}.{key}", [value]))
                    else:
                        walk(value, f"{path}.{key}")
            elif isinstance(node, list):
                for i, item in enumerate(node):
                    walk(item, f"{path}[{i}]")

        walk(self.knowledge, "knowledge")
        return pairs

    def validate(self) -> list[str]:
        errors: list[str] = []

        # 语料 id 唯一（既有测试也覆盖，这里再保证索引可用）
        ids = [r["id"] for r in self.records]
        if len(ids) != len(set(ids)):
            errors.append("corpus 记录 id 不唯一")

        # 所有 source_ids / support_ids 必须是真实 corpus 记录
        for path, refs in self._iter_source_id_lists():
            for ref in refs:
                if ref not in self.record_by_id:
                    errors.append(f"{path} 引用了不存在的 corpus 记录：{ref}")

        # 每条 corpus 记录至少被知识层使用一次（可复查覆盖）
        referenced: set[str] = set()
        for _, refs in self._iter_source_id_lists():
            referenced.update(refs)
        for rid in self.record_by_id:
            if rid not in referenced:
                errors.append(f"corpus 记录 {rid} 未被知识层任何来源/证据引用")

        # 提及必须挂在已登记语句上
        for m in self.mentions:
            if m["statement_id"] not in self.statement_by_id:
                errors.append(f"mention {m['id']} 指向不存在的语句 {m['statement_id']}")

        # 事件类型必须是允许的五类加刻毁端点
        for e in self.events:
            if e["type"] not in EventType.ALL:
                errors.append(f"event {e['id']} 使用未知类型 {e['type']}")

        # 每个作品至少有创作事件与展览/缺口登记；收藏可以是缺口但类型必须存在
        for w in self.works:
            typed = {e["type"] for e in self.events if e.get("work_id") == w["id"]}
            if EventType.CREATION not in typed:
                errors.append(f"{w['id']} 缺少创作事件")
            if EventType.EXHIBITION not in typed:
                errors.append(f"{w['id']} 缺少展览事件")
            has_collection_gap = any(
                g.get("work_id") == w["id"] and g.get("type") == EventType.COLLECTION
                for g in self.coverage_gaps
            )
            if EventType.COLLECTION not in typed and not has_collection_gap:
                errors.append(f"{w['id']} 既无收藏事件也无收藏材料缺口说明")

        return errors

    # ---------- 便捷查询 ----------

    def statements_for_record(self, record_id: str) -> list[dict[str, Any]]:
        return [s for s in self.statements if s.get("source_id") == record_id]

    def mentions_for_statement(self, statement_id: str) -> list[dict[str, Any]]:
        return [m for m in self.mentions if m["statement_id"] == statement_id]

    def descriptions_for_work(self, work_id: str) -> list[dict[str, Any]]:
        return [d for d in self.descriptions if d["work_id"] == work_id]

    def events_for_work(self, work_id: str) -> list[dict[str, Any]]:
        return [e for e in self.events if e.get("work_id") == work_id]

    def resolve_person_name(self, person_id: str) -> str:
        p = self.person_by_id.get(person_id)
        if p:
            return p["name"]
        c = self.candidate_entity_by_id.get(person_id)
        if c:
            return c["label"]
        return person_id
