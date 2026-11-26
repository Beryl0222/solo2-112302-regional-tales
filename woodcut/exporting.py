"""把可复查图谱与已签发文稿导出为普通文件。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .documents import render_issued_file
from .repository import ROOT
from .workspace import Workspace


def build_registry_bundle(ws: Workspace) -> dict[str, Any]:
    """生成一份自包含的复查 JSON：原始语料 + 知识层 + 当前复核/签发状态。"""
    return {
        "project": ws.repo.corpus.get("project"),
        "material_nature": ws.repo.corpus.get("material_nature"),
        "corpus": ws.repo.corpus,
        "knowledge": ws.repo.knowledge,
        "curator_state": ws.state,
        "review_queue": ws.review_queue(),
        "pending_descriptions": ws.review_queue()["pending_descriptions"],
        "releases_overview": [
            {
                "id": r["id"],
                "audience": r["audience"],
                "version": r["version"],
                "status": r["status"],
                "issuer": r["issuer"],
                "issued_at": r["issued_at"],
                "term_version": r["term_version"],
                "stale": ws.is_stale(r),
                "update_decision": ws.release_update_decision(r["id"]),
            }
            for r in ws.list_releases()
        ],
    }


def export_all(ws: Workspace, out_dir: Path | str | None = None) -> dict[str, Path]:
    out = Path(out_dir) if out_dir else ROOT / "outputs"
    issued_dir = out / "issued"
    issued_dir.mkdir(parents=True, exist_ok=True)

    registry_path = out / "registry.json"
    registry_path.write_text(
        json.dumps(build_registry_bundle(ws), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    written: dict[str, Path] = {"registry": registry_path}
    for rel in ws.list_releases():
        p = issued_dir / f"{rel['id']}.md"
        p.write_text(render_issued_file(rel), encoding="utf-8")
        written[rel["id"]] = p
    return written
