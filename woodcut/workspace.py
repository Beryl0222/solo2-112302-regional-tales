"""馆员工作台：术语修订、实体重判、来源追踪与文稿签发。

所有变更只写入 curator state（默认 data/state.json），
data/corpus.json 与 data/knowledge.json 保持只读。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .model import Audience, Release, ReviewState, UpdateAction
from .repository import DATA_DIR, Repository


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class Workspace:
    def __init__(
        self,
        repo: Repository,
        state: Optional[dict[str, Any]] = None,
        state_path: Optional[Path] = None,
    ):
        self.repo = repo
        self.state_path = Path(state_path) if state_path else DATA_DIR / "state.json"
        self.state = state or self._empty_state()

    # ---------- 装载 / 保存 ----------

    @staticmethod
    def _empty_state() -> dict[str, Any]:
        return {
            "schema": "woodcut-curator-state/1",
            "adopted_term_versions": {},   # term_id -> [追加采用的版本对象]
            "current_term_versions": {},   # term_id -> version（覆盖 knowledge 默认值）
            "mention_reviews": {},
            "description_reviews": {},
            "releases": [],
            "update_decisions": {},
            "card_view_overrides": {},
        }

    @classmethod
    def load(
        cls,
        data_dir: Optional[Path] = None,
        state_path: Optional[Path] = None,
    ) -> "Workspace":
        repo = Repository.load(data_dir)
        sp = Path(state_path) if state_path else DATA_DIR / "state.json"
        if sp.exists():
            raw = sp.read_text(encoding="utf-8").strip()
            if not raw:
                state = cls._empty_state()
            else:
                try:
                    loaded = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"馆员状态文件 {sp} 不是有效 JSON：{exc}") from exc
                base = cls._empty_state()
                base.update(loaded)
                state = base
        else:
            state = cls._empty_state()
        return cls(repo, state, sp)

    def save(self) -> Path:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return self.state_path

    # ---------- 术语版本 ----------

    def current_term_version(self, term_id: str = "term:ban") -> int:
        if term_id in self.state["current_term_versions"]:
            return int(self.state["current_term_versions"][term_id])
        return int(self.repo.term_by_id[term_id]["current_version"])

    def term_versions(self, term_id: str = "term:ban") -> list[dict[str, Any]]:
        term = self.repo.term_by_id[term_id]
        versions = [dict(v) for v in term["versions"]]
        versions.extend(self.state["adopted_term_versions"].get(term_id, []))
        versions.sort(key=lambda v: v["version"])
        return versions

    def term_definition(self, term_id: str = "term:ban", version: Optional[int] = None) -> dict[str, Any]:
        versions = self.term_versions(term_id)
        ver = version or self.current_term_version(term_id)
        for v in versions:
            if v["version"] == ver:
                return v
        raise KeyError(f"术语 {term_id} 没有版本 {ver}")

    def adopt_term_revision(
        self,
        term_id: str = "term:ban",
        reviewer: str = "当值班员",
        at: Optional[str] = None,
    ) -> dict[str, Any]:
        """采用 knowledge 中预备的修订版术语解释。

        采用后，所有通过‘术语提及 + 事件链接 + 说明稿链接’受影响的对象
        都要重新判断；本方法不做任何全文替换。
        """
        term = self.repo.term_by_id[term_id]
        revision = term.get("revision")
        if not revision:
            raise ValueError(f"术语 {term_id} 没有预备修订稿")
        new_version = int(revision["version"])
        adopted = self.state["adopted_term_versions"].setdefault(term_id, [])
        if any(v["version"] == new_version for v in adopted):
            self.state["current_term_versions"][term_id] = new_version
            return self.term_definition(term_id, new_version)
        payload = dict(revision)
        payload["adopted_by"] = reviewer
        payload["adopted_at"] = at or _now()
        adopted.append(payload)
        self.state["current_term_versions"][term_id] = new_version
        return payload

    # ---------- 受影响语句（不是字符串替换） ----------

    def affected_statement_ids(self, term_id: str = "term:ban") -> list[str]:
        ids: list[str] = []

        def add(sid: Optional[str]) -> None:
            if sid and sid in self.repo.statement_by_id and sid not in ids:
                ids.append(sid)

        # 1) 直接挂了该术语的提及
        for m in self.repo.mentions:
            if m.get("term_id") == term_id:
                add(m["statement_id"])

        # 2) 链接到带该术语的事件的语句（q2 全句无“版”字也会因此被召回）
        tagged_events = {
            e["id"] for e in self.repo.events if term_id in e.get("term_ids", [])
        }
        for s in self.repo.statements:
            if tagged_events.intersection(s.get("linked_event_ids", [])):
                add(s["id"])
            # 语句引用的原始 corpus 号恰好是事件证据
            src = s.get("source_id")
            if src and any(src in e.get("evidence_ids", []) for e in self.repo.events if e["id"] in tagged_events):
                add(s["id"])

        # 3) 术语说明稿本身（c1）以及用该术语写的展厅稿
        for d in self.repo.descriptions:
            if term_id in d.get("term_ids", []):
                add(self.repo.statements_for_record(d["raw_source_id"])[0]["id"]
                    if self.repo.statements_for_record(d["raw_source_id"]) else None)
        return ids

    def affected_statements(self, term_id: str = "term:ban") -> list[dict[str, Any]]:
        order = {s["id"]: i for i, s in enumerate(self.repo.statements)}
        return [self.repo.statement_by_id[i] for i in self.affected_statement_ids(term_id)
                if i in self.repo.statement_by_id]

    def affected_overview(self, term_id: str = "term:ban") -> dict[str, Any]:
        """区分需重判的口述/卡片/展厅句，以及引用了它们的下游教学改写稿。"""
        core = self.affected_statement_ids(term_id)
        downstream: list[str] = []
        for s in self.repo.statements:
            if s["id"] in core:
                continue
            if any(r in core for r in s.get("references", [])):
                downstream.append(s["id"])
        return {
            "term_id": term_id,
            "rejudge_ids": core,
            "rejudge": [self.repo.statement_by_id[i] for i in core],
            "downstream_teaching_ids": downstream,
            "downstream_teaching": [self.repo.statement_by_id[i] for i in downstream],
        }

    # ---------- 提及（代词 / 实体链接）复核 ----------

    def review_mention(
        self,
        mention_id: str,
        review_state: str,
        chosen: Optional[list[str] | str] = None,
        note: str = "",
        reviewer: str = "当值班员",
        at: Optional[str] = None,
    ) -> dict[str, Any]:
        if mention_id not in self.repo.mention_by_id:
            raise KeyError(mention_id)
        if isinstance(chosen, str):
            chosen = [chosen]
        review = {
            "state": review_state,
            "chosen": chosen or [],
            "note": note,
            "reviewer": reviewer,
            "reviewed_at": at or _now(),
            "term_version": self.current_term_version(
                self.repo.mention_by_id[mention_id].get("term_id", "term:ban")
            ),
        }
        self.state["mention_reviews"][mention_id] = review
        return review

    def mention_review(self, mention_id: str) -> Optional[dict[str, Any]]:
        return self.state["mention_reviews"].get(mention_id)

    def pending_mentions(self, term_id: str = "term:ban") -> list[dict[str, Any]]:
        ver = self.current_term_version(term_id)
        out = []
        for m in self.repo.mentions:
            if m.get("term_id") != term_id:
                continue
            r = self.state["mention_reviews"].get(m["id"])
            if not r or int(r.get("term_version", 0)) < ver:
                out.append(m)
        return out

    # ---------- 作品说明复核 ----------

    def review_description(
        self,
        description_id: str,
        review_state: str,
        note: str = "",
        reviewer: str = "当值班员",
        at: Optional[str] = None,
    ) -> dict[str, Any]:
        if description_id not in self.repo.description_by_id:
            raise KeyError(description_id)
        term_ids = self.repo.description_by_id[description_id].get("term_ids", [])
        review = {
            "state": review_state,
            "note": note,
            "reviewer": reviewer,
            "reviewed_at": at or _now(),
            "term_versions": {t: self.current_term_version(t) for t in term_ids},
        }
        self.state["description_reviews"][description_id] = review
        return review

    def description_review(self, description_id: str) -> Optional[dict[str, Any]]:
        return self.state["description_reviews"].get(description_id)

    def pending_descriptions(self, term_id: str = "term:ban") -> list[dict[str, Any]]:
        """术语修订后等待复核的作品说明。"""
        ver = self.current_term_version(term_id)
        out = []
        for d in self.repo.descriptions:
            if term_id not in d.get("term_ids", []):
                continue
            r = self.state["description_reviews"].get(d["id"])
            versions = (r or {}).get("term_versions", {})
            if not r or int(versions.get(term_id, 0)) < ver:
                out.append(d)
        return out

    def review_queue(self, term_id: str = "term:ban") -> dict[str, Any]:
        return {
            "term_id": term_id,
            "term_version": self.current_term_version(term_id),
            "pending_mentions": [
                {"id": m["id"], "anchor": m["anchor"], "statement_id": m["statement_id"]}
                for m in self.pending_mentions(term_id)
            ],
            "pending_descriptions": [
                {"id": d["id"], "label": d["label"], "kind": d["kind"]}
                for d in self.pending_descriptions(term_id)
            ],
        }

    # ---------- “最后一版 / 一张”裁定 ----------

    def adjudicate_quantity(
        self,
        anchor: str,
        nearby_statement_ids: Optional[list[str]] = None,
        has_sheet_number: bool = False,
    ) -> dict[str, Any]:
        """按附近完整语境与原件编号判定“版次 vs 张数”。

        返回候选与裁定建议；证据不足时建议保留多个候选，不强行归一。
        """
        rule = next((r for r in self.repo.rules if anchor in r["anchors"]), None)
        if not rule:
            return {"anchor": anchor, "decision": ReviewState.OPEN_CANDIDATES,
                    "reason": "没有登记该数量词的裁定规则，保留候选。"}

        nearby = nearby_statement_ids or []
        nearby_text = "\n".join(
            self.repo.statement_by_id[s]["verbatim"]
            for s in nearby if s in self.repo.statement_by_id
        )
        has_reduction_context = ("逐版递减" in nearby_text) or ("版已经用完" in nearby_text)
        result: dict[str, Any] = {
            "anchor": anchor,
            "rule": rule["rule"],
            "work_numbering": rule.get("numbering_available", []),
            "sheet_numbering": rule.get("sheet_numbering_available", []),
            "nearby_statement_ids": nearby,
        }

        if anchor == "一张":
            result["literal_sense"] = rule["literal_sense"]
            if has_sheet_number:
                result["decision"] = "sense:ban:sheet_count_numbered"
                result["reason"] = "有张号与邻近语境，可按张号核定具体印件。"
            else:
                result["decision"] = "sense:ban:sheet_count"
                result["count_status"] = "张数不可考"
                result["reason"] = "“一张”按张数读；C12 只有作品编号、没有张号，不能进位为版次。"
            return result

        if anchor == "最后一版":
            if has_reduction_context:
                result["decision"] = "sense:ban:state"
                result["reason"] = "邻近有 q1‘版已经用完了’与 c1‘逐版递减、母版刻毁’，裁定为同一母版最后套色版次。"
            else:
                result["decision"] = ReviewState.OPEN_CANDIDATES
                result["reason"] = "缺少逐版递减的完整语境时，版次/印次/张数候选应同时保留。"
            return result

        result["decision"] = ReviewState.OPEN_CANDIDATES
        return result

    # ---------- 来源追踪：教学稿句子 -> 录音 + 作品卡 ----------

    def trace(self, ref: str) -> dict[str, Any]:
        ref = ref.strip()
        paths: list[str] = []
        statement_ids: list[str] = []
        raw_ids: list[str] = []
        work_ids: list[str] = []
        event_ids: list[str] = []

        def add_statement(sid: Optional[str], via: str = "") -> Optional[dict[str, Any]]:
            if not sid or sid not in self.repo.statement_by_id:
                return None
            if sid not in statement_ids:
                statement_ids.append(sid)
                s = self.repo.statement_by_id[sid]
                if via:
                    paths.append(via)
                if s.get("source_id") and s["source_id"] not in raw_ids:
                    raw_ids.append(s["source_id"])
                for w in s.get("about_work_ids", []):
                    if w not in work_ids:
                        work_ids.append(w)
                for e in s.get("linked_event_ids", []):
                    if e not in event_ids:
                        event_ids.append(e)
                return s
            return self.repo.statement_by_id[sid]

        root_kind = "unknown"
        root_label = ref

        # Release
        release = self.get_release(ref) if ref.startswith("REL") else None
        if release:
            root_kind = "release"
            root_label = release.id
            paths.append(f"签发稿 {release.id}（{Audience.LABELS.get(release.audience, release.audience)}）")
            add_statement(release.target_id, f"{release.id} -> 对应语句 {release.target_id}")

        # Statement id
        elif ref in self.repo.statement_by_id:
            root_kind = "statement"
            s = add_statement(ref)
            root_label = ref
            paths.append(f"语句 {ref}（{s['kind']}）")  # type: ignore[index]

        # Mention id
        elif ref in self.repo.mention_by_id:
            root_kind = "mention"
            m = self.repo.mention_by_id[ref]
            root_label = ref
            paths.append(f"提及 {ref}（锚文字‘{m['anchor']}’）")
            add_statement(m["statement_id"], f"{ref} -> 所在语句 {m['statement_id']}")

        # Work / inventory number
        elif ref in self.repo.work_by_id or ref in self.repo.work_by_inventory:
            w = self.repo.work_by_id.get(ref) or self.repo.work_by_inventory[ref]
            root_kind = "work"
            root_label = w["id"]
            work_ids.append(w["id"])
            paths.append(f"作品 {w['inventory_no']}（{w['id']}）")

        else:
            # Corpus record id，允许 l1 或 l1#2 这种句子号
            rid = ref.split("#", 1)[0]
            rec = self.repo.raw_record(rid)
            if rec:
                root_kind = "corpus_record"
                root_label = rid
                raw_ids.append(rid)
                paths.append(f"原始记录 {rid}（{rec['kind']}）")
                for s in self.repo.statements_for_record(rid):
                    add_statement(s["id"], f"{rid} -> 语句 {s['id']}")
            else:
                raise KeyError(f"无法识别的追踪起点：{ref}")

        # 引用闭包（l1 -> q2；h0 -> q1/q2/g1）
        queue = list(statement_ids)
        seen: set[str] = set()
        while queue:
            sid = queue.pop(0)
            if sid in seen:
                continue
            seen.add(sid)
            s = self.repo.statement_by_id[sid]
            for r in s.get("references", []):
                before = set(statement_ids)
                add_statement(r, f"{sid} 引用 -> {r}")
                if r not in before:
                    queue.append(r)

        # 事件证据回填原始记录
        for eid in list(event_ids):
            e = self.repo.event_by_id.get(eid)
            if not e:
                continue
            for ev_ref in e.get("evidence_ids", []):
                if ev_ref in self.repo.record_by_id and ev_ref not in raw_ids:
                    raw_ids.append(ev_ref)
                for s in self.repo.statements_for_record(ev_ref):
                    if s["id"] not in statement_ids:
                        add_statement(s["id"], f"事件 {eid} 证据 {ev_ref} -> 语句 {s['id']}")
                        queue.append(s["id"])

        # 录音目录 a1
        recording_entries: list[dict[str, Any]] = []
        interview_ids: set[str] = set()
        for sid in statement_ids:
            s = self.repo.statement_by_id[sid]
            iid = s.get("interview_id")
            if iid:
                interview_ids.add(iid)
            if s.get("speaker_id") and s.get("timestamp"):
                recording_entries.append({
                    "statement_id": sid,
                    "speaker_id": s["speaker_id"],
                    "speaker": self.repo.resolve_person_name(s["speaker_id"]),
                    "timestamp": s["timestamp"],
                    "interview_id": iid,
                    "verbatim": s["verbatim"],
                })
        for iid in interview_ids:
            iv = self.repo.interview_by_id.get(iid)
            if iv and iv.get("catalog_ref") and iv["catalog_ref"] not in raw_ids:
                raw_ids.append(iv["catalog_ref"])

        works = [self.repo.work_by_id[w] for w in dict.fromkeys(work_ids) if w in self.repo.work_by_id]
        for w in works:
            pass  # descriptions/events 通过 id 直接收集
        desc_ids: list[str] = []
        for w in works:
            for d in self.repo.descriptions_for_work(w["id"]):
                if d["id"] not in desc_ids:
                    desc_ids.append(d["id"])
            for e in self.repo.events_for_work(w["id"]):
                if e["id"] not in event_ids:
                    event_ids.append(e["id"])
        # 事件再跑一轮证据回填（作品带出的事件）
        for eid in list(event_ids):
            e = self.repo.event_by_id.get(eid)
            if not e:
                continue
            for ev_ref in e.get("evidence_ids", []):
                if ev_ref in self.repo.record_by_id and ev_ref not in raw_ids:
                    raw_ids.append(ev_ref)

        raw_records = [self.repo.record_by_id[r] for r in dict.fromkeys(raw_ids) if r in self.repo.record_by_id]
        descriptions = [self.repo.description_by_id[d] for d in desc_ids]
        cards = [d for d in descriptions if d["kind"] in ("artwork_card", "technique_card")]
        events = [self.repo.event_by_id[e] for e in dict.fromkeys(event_ids) if e in self.repo.event_by_id]
        claims = [c for w in works for c in w.get("attribution_claims", [])]

        for r in recording_entries:
            iv = self.repo.interview_by_id.get(r["interview_id"] or "")
            if iv:
                r["interview_note"] = iv["note"]

        return {
            "ref": ref,
            "root_kind": root_kind,
            "root_label": root_label,
            "paths": paths,
            "statement_ids": statement_ids,
            "statements": [self.repo.statement_by_id[s] for s in statement_ids],
            "recording": recording_entries,
            "interviews": [self.repo.interview_by_id[i] for i in interview_ids if i in self.repo.interview_by_id],
            "raw_record_ids": list(dict.fromkeys(raw_ids)),
            "raw_records": raw_records,
            "works": works,
            "cards": cards,
            "descriptions": descriptions,
            "events": events,
            "claims": claims,
        }

    # ---------- 作品卡署名 / 师承 ----------

    @staticmethod
    def add_student_byline(view: dict[str, Any], student_name: str = "周敏") -> dict[str, Any]:
        """在作品卡展示上增加学员署名。

        这是纯变换：只改创作关系展示与 byline 标记，
        lineage_display / 师承字段原样保留。
        """
        updated = dict(view)
        updated["byline_present"] = True
        existing = updated.get("creation_display", "")
        if student_name not in existing:
            updated["creation_display"] = f"{student_name} 创作并署名（增加学员署名展示）；原展示：{existing}"
        updated["byline_change_note"] = (
            "增加学员署名只改变创作关系展示；已有师承说明与技艺沿袭不得消去。"
        )
        return updated

    def apply_student_byline(
        self,
        view_id: str,
        reviewer: str = "当值班员",
        at: Optional[str] = None,
    ) -> dict[str, Any]:
        base = self.state["card_view_overrides"].get(view_id) or self.repo.card_view_by_id[view_id]
        updated = self.add_student_byline(base)
        updated["byline_updated_by"] = reviewer
        updated["byline_updated_at"] = at or _now()
        self.state["card_view_overrides"][view_id] = updated
        return updated

    def card_view(self, view_id: str) -> dict[str, Any]:
        if view_id in self.state["card_view_overrides"]:
            return self.state["card_view_overrides"][view_id]
        return self.repo.card_view_by_id[view_id]

    # ---------- 签发 ----------

    def _next_release_id(self, audience: str, work_no: str, version: int) -> str:
        prefix = Audience.PREFIX.get(audience, "DOC")
        return f"REL-{prefix}-{work_no}-v{version}"

    def issue(
        self,
        audience: str,
        issuer: str,
        target_id: str = "stmt:h0",
        body_markdown: Optional[str] = None,
        title: Optional[str] = None,
        at: Optional[str] = None,
        supersedes: Optional[str] = None,
    ) -> Release:
        if audience not in (Audience.HALL_SOUND, Audience.CLASSROOM):
            raise ValueError(f"未知受众：{audience}")

        trace = self.trace(target_id)
        work_no = "ITEM"
        if trace["works"]:
            work_no = trace["works"][0].get("inventory_no") or trace["works"][0]["id"]

        family = [
            r for r in self.state["releases"]
            if r["audience"] == audience and work_no in r["id"]
        ]
        version = max([int(r["version"]) for r in family] + [0]) + 1
        rid = self._next_release_id(audience, work_no, version)

        if body_markdown is None:
            from .documents import build_draft
            body_markdown, auto_title = build_draft(self, audience, target_id)
            title = title or auto_title
        title = title or f"{Audience.LABELS[audience]} {work_no}"

        release = Release(
            id=rid,
            audience=audience,
            target_id=target_id,
            title=title,
            body_markdown=body_markdown,
            issuer=issuer,
            issued_at=at or _now(),
            version=version,
            term_version=self.current_term_version(),
            source_timestamps=trace["recording"],
            evidence_ids=trace["raw_record_ids"],
            supersedes=supersedes,
        )
        self.state["releases"].append(release.to_dict())
        if supersedes:
            old = self.get_release(supersedes)
            if old:
                old["status"] = "superseded"
                self.state["update_decisions"].setdefault(supersedes, {})
                self.state["update_decisions"][supersedes].update({
                    "action": UpdateAction.ISSUE_REVISION,
                    "new_release_id": rid,
                    "decided_by": issuer,
                    "decided_at": release.issued_at,
                })
        return release

    def get_release(self, release_id: str) -> Optional[dict[str, Any]]:
        for r in self.state["releases"]:
            if r["id"] == release_id:
                return r
        return None

    def list_releases(self, audience: Optional[str] = None) -> list[dict[str, Any]]:
        rels = self.state["releases"]
        if audience:
            rels = [r for r in rels if r["audience"] == audience]
        return rels

    def is_stale(self, release: dict[str, Any]) -> bool:
        return int(release.get("term_version", 1)) < self.current_term_version()

    def keep_release(
        self,
        release_id: str,
        reason: str,
        reviewer: str = "当值班员",
        at: Optional[str] = None,
    ) -> dict[str, Any]:
        """该受众决定本次不更新已签发稿（必须写理由），旧稿继续有效。"""
        if not self.get_release(release_id):
            raise KeyError(release_id)
        decision = {
            "action": UpdateAction.KEEP_CURRENT,
            "reason": reason,
            "reviewer": reviewer,
            "decided_at": at or _now(),
            "term_version": self.current_term_version(),
        }
        self.state["update_decisions"][release_id] = decision
        return decision

    def release_update_decision(self, release_id: str) -> Optional[dict[str, Any]]:
        return self.state["update_decisions"].get(release_id)

    def release_attention(self, release: dict[str, Any]) -> str:
        """current | update_decision_required | kept | revision_issued | superseded。"""
        if release.get("status") == "superseded":
            return "superseded"
        if not self.is_stale(release):
            return "current"
        decision = self.release_update_decision(release["id"])
        if not decision:
            return "update_decision_required"
        action = decision.get("action")
        if action == UpdateAction.KEEP_CURRENT:
            return "kept"
        if action == UpdateAction.ISSUE_REVISION:
            return "revision_issued"
        return "update_decision_required"
