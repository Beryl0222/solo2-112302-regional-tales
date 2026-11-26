"""馆员命令行：复查人物/事件、追踪来源、修订术语、签发两类文稿。

示例：
    python -m woodcut summary
    python -m woodcut trace l1
    python -m woodcut affected
    python -m woodcut queue
    python -m woodcut adopt-revision term:ban --reviewer 馆员甲
    python -m woodcut review-mention m:h0:it --state open_candidates \\
        --choose block:c12 --choose entity:c12:sheet-prev --note "两候选并存"
    python -m woodcut issue hall_sound --issuer 馆员甲
    python -m woodcut issue classroom --issuer 馆员甲
    python -m woodcut export
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

from .model import Audience, ReviewState
from .repository import ROOT
from .workspace import Workspace


# ---------- 输出辅助 ----------

def _print_json(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _load(args: argparse.Namespace) -> Workspace:
    state_path = Path(args.state) if args.state else None
    return Workspace.load(state_path=state_path)


def _print_trace_text(t: dict[str, Any]) -> None:
    print(f"追踪起点 {t['ref']}（{t['root_kind']} / {t['root_label']}）")
    print("\n[追溯路径]")
    for p in t["paths"]:
        print("  " + p)

    print("\n[录音]")
    if not t["recording"]:
        print("  （无直接录音）")
    for r in t["recording"]:
        print(f"  {r['timestamp']} {r['speaker']} [{r['statement_id']}] “{r['verbatim']}”")
        if r.get("interview_note"):
            print(f"      目录：{r['interview_note']}")

    print("\n[作品卡 / 卡片]")
    for d in t["cards"]:
        print(f"  - {d['id']}（{d['kind']}）{d['label']}")
        print(f"      {d['current_text']}")
        if d.get("scope_warning"):
            print(f"      范围警告：{d['scope_warning']}")

    print("\n[作品]")
    for w in t["works"]:
        c = w["creation"]
        print(f"  - {w['id']} 编号 {w['inventory_no']}；创作者 {c['creator_id']}；导师 {w.get('mentor_ids')}")

    print("\n[事件]")
    for e in t["events"]:
        print(f"  - {e['id']}【{e['type_label']}】{e['label']}")

    if t["claims"]:
        print("\n[对立归属主张]")
        for c in t["claims"]:
            print(f"  - {c['id']} ({c['status']})：{c['text']} —— {c['handling']}")

    print("\n[原始 corpus 记录] " + ", ".join(t["raw_record_ids"]))


# ---------- 子命令 ----------

def cmd_summary(ws: Workspace, args: argparse.Namespace) -> int:
    repo = ws.repo
    print(f"项目：{repo.corpus['project']}（{repo.corpus.get('material_nature')}）")
    print(f"corpus 记录 {len(repo.records)} 条；人物 {len(repo.people)}；作品 {len(repo.works)}；"
          f"事件 {len(repo.events)}；语句 {len(repo.statements)}；提及 {len(repo.mentions)}")
    print(f"术语“版”当前版本 v{ws.current_term_version('term:ban')}")
    q = ws.review_queue()
    print(f"待重判提及 {len(q['pending_mentions'])}；等待复核作品说明 {len(q['pending_descriptions'])}")
    rels = ws.list_releases()
    if rels:
        print("已签发：")
        for r in rels:
            flag = "（有术语更新待决定）" if ws.is_stale(r) and r["status"] == "issued" else ""
            dec = ws.release_update_decision(r["id"])
            if dec and dec.get("action") == "keep_current":
                flag = "（受众决定暂不更新，已记理由）"
            print(f"  - {r['id']} v{r['version']} [{r['status']}] {r['audience']} "
                  f"签发人 {r['issuer']} {r['issued_at']}{flag}")
    return 0


def cmd_people(ws: Workspace, args: argparse.Namespace) -> int:
    if args.json:
        _print_json({"people": ws.repo.people, "works": ws.repo.works, "card_views": ws.repo.card_views})
        return 0
    for p in ws.repo.people:
        print(f"{p['id']} {p['name']}：{ '、'.join(p['roles']) }（来源 {','.join(p['source_ids'])}）")
        print(f"    {p['review_note']}")
    for w in ws.repo.works:
        print(f"\n{w['id']}（编号 {w['inventory_no']}）")
        print(f"  创作：{w['creation']['creator_id']}（{w['creation']['status']}，依据 {w['creation']['basis_ids']}）")
        print(f"  导师：{w['mentor_ids']}")
        for lin in w.get("lineage", []):
            print(f"  沿袭：{lin['from_person_id']} -> {lin['to_person_id']} / {lin['technique']}")
            print(f"        规则：{lin['rule']}")
        for c in w.get("attribution_claims", []):
            print(f"  对立主张：{c['id']} [{c['status']}] {c['text']}（来源 {c['source_id']}）")
    return 0


def cmd_events(ws: Workspace, args: argparse.Namespace) -> int:
    events = ws.repo.events
    if args.work:
        no = args.work
        wid = no if no in ws.repo.work_by_id else ws.repo.work_by_inventory.get(no, {}).get("id")
        events = [e for e in events if e.get("work_id") == wid]
    if args.type:
        events = [e for e in events if e["type"] == args.type]
    if args.json:
        _print_json({"events": events, "coverage_gaps": ws.repo.coverage_gaps})
        return 0
    for e in events:
        actors = ", ".join(f"{a['person_id']}:{a['role']}" for a in e.get("actors", [])) or "未登记"
        print(f"{e['id']} 【{e['type_label']}/{e['type']}】 {e['label']}")
        print(f"    参与：{actors}；证据：{e.get('evidence_ids', [])}；术语链接：{e.get('term_ids', [])}")
        if e.get("note"):
            print(f"    注：{e['note']}")
    for g in ws.repo.coverage_gaps:
        if not args.type or g["type"] == args.type:
            print(f"{g['work_id']} 【缺口/{g['type']}】{g['note']}")
    return 0


def cmd_trace(ws: Workspace, args: argparse.Namespace) -> int:
    t = ws.trace(args.ref)
    if args.json:
        _print_json(t)
    else:
        _print_trace_text(t)
    return 0


def cmd_affected(ws: Workspace, args: argparse.Namespace) -> int:
    stmts = ws.affected_statements(args.term)
    if args.json:
        _print_json({"term_id": args.term, "statement_ids": [s["id"] for s in stmts], "statements": stmts})
        return 0
    print(f"术语 {args.term} 修订后需要回看的语句（{len(stmts)} 条；按链接召回，非全文替换）：")
    for s in stmts:
        ts = f" {s['timestamp']}" if s.get("timestamp") else ""
        print(f"  - {s['id']} [{s['kind']}]{ts}：{s['verbatim'][:60]}")
    return 0


def cmd_queue(ws: Workspace, args: argparse.Namespace) -> int:
    q = ws.review_queue(args.term)
    if args.descriptions_only:
        if args.json:
            _print_json(q["pending_descriptions"])
        else:
            print("等待复核的作品说明：")
            for d in q["pending_descriptions"]:
                print(f"  - {d['id']}（{d['kind']}）{d['label']}")
            if not q["pending_descriptions"]:
                print("  （无）")
        return 0
    if args.json:
        _print_json(q)
        return 0
    print(f"术语 v{q['term_version']} 复核队列")
    print("提及/代词链接：")
    for m in q["pending_mentions"]:
        print(f"  - {m['id']} “{m['anchor']}” @ {m['statement_id']}")
    if not q["pending_mentions"]:
        print("  （无）")
    print("作品说明：")
    for d in q["pending_descriptions"]:
        print(f"  - {d['id']}（{d['kind']}）{d['label']}")
    if not q["pending_descriptions"]:
        print("  （无）")
    return 0


def cmd_adopt_revision(ws: Workspace, args: argparse.Namespace) -> int:
    payload = ws.adopt_term_revision(args.term_id, reviewer=args.reviewer)
    ws.save()
    print(f"已采用 {args.term_id} v{payload['version']}：{payload['label']}")
    print(f"当前待重判提及 {len(ws.pending_mentions(args.term_id))}；"
          f"待复核作品说明 {len(ws.pending_descriptions(args.term_id))}")
    return 0


def cmd_review_mention(ws: Workspace, args: argparse.Namespace) -> int:
    review = ws.review_mention(
        args.mention_id, args.review_state, chosen=args.choose, note=args.note or "", reviewer=args.reviewer
    )
    ws.save()
    _print_json({"mention_id": args.mention_id, "review": review})
    return 0


def cmd_review_description(ws: Workspace, args: argparse.Namespace) -> int:
    review = ws.review_description(
        args.description_id, args.review_state, note=args.note or "", reviewer=args.reviewer
    )
    ws.save()
    _print_json({"description_id": args.description_id, "review": review})
    return 0


def cmd_byline(ws: Workspace, args: argparse.Namespace) -> int:
    view = ws.apply_student_byline(args.view_id, reviewer=args.reviewer)
    ws.save()
    _print_json(view)
    return 0


def cmd_draft(ws: Workspace, args: argparse.Namespace) -> int:
    from .documents import build_draft
    md, title = build_draft(ws, args.audience, args.target)
    print(md)
    return 0


def _write_issued_file(ws: Workspace, rel: dict[str, Any], out_dir: Optional[str]) -> Path:
    from .documents import render_issued_file
    out = Path(out_dir) if out_dir else ROOT / "outputs"
    d = out / "issued"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{rel['id']}.md"
    p.write_text(render_issued_file(rel), encoding="utf-8")
    return p


def cmd_issue(ws: Workspace, args: argparse.Namespace) -> int:
    body = None
    if args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8")
    rel = ws.issue(
        audience=args.audience,
        issuer=args.issuer,
        target_id=args.target,
        body_markdown=body,
        supersedes=args.supersedes,
    )
    ws.save()
    p = _write_issued_file(ws, rel.to_dict(), args.out_dir)
    print(f"已签发 {rel.id}（{Audience.LABELS[rel.audience]}），术语版本 v{rel.term_version}")
    print(f"写入 {p}")
    print(f"保留录音时间点 {[t['timestamp'] for t in rel.source_timestamps]}")
    return 0


def cmd_release(ws: Workspace, args: argparse.Namespace) -> int:
    if args.release_action == "list":
        rels = ws.list_releases(args.audience)
        if args.json:
            _print_json(rels)
            return 0
        for r in rels:
            stale = " [术语已更新-待决定]" if ws.is_stale(r) and r["status"] == "issued" else ""
            print(f"{r['id']} v{r['version']} [{r['status']}] {r['audience']} "
                  f"{r['issuer']} {r['issued_at']}{stale}")
        return 0

    if args.release_action == "show":
        r = ws.get_release(args.release_id)
        if not r:
            print(f"找不到 {args.release_id}", file=sys.stderr)
            return 2
        if args.json:
            _print_json(r)
        else:
            print(r["body_markdown"])
        return 0

    if args.release_action == "keep":
        d = ws.keep_release(args.release_id, reason=args.reason, reviewer=args.reviewer)
        ws.save()
        _print_json({"release_id": args.release_id, "decision": d})
        return 0

    if args.release_action == "decide-revision":
        # 仅登记“决定出新版”，真正新版用 issue --supersedes 签发
        r = ws.get_release(args.release_id)
        if not r:
            print(f"找不到 {args.release_id}", file=sys.stderr)
            return 2
        ws.state["update_decisions"][args.release_id] = {
            "action": "issue_revision_pending",
            "reason": args.reason or "",
            "reviewer": args.reviewer,
        }
        ws.save()
        print(f"已登记 {args.release_id} 将按本受众安排修订；请随后用 issue --supersedes {args.release_id} 签发新版。")
        return 0

    return 1


def cmd_export(ws: Workspace, args: argparse.Namespace) -> int:
    from .exporting import export_all
    paths = export_all(ws, args.out)
    for k, p in paths.items():
        print(f"{k}: {p}")
    return 0


# ---------- 参数解析 ----------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="woodcut", description="木刻口述史人物/事件复核与文稿签发")
    p.add_argument("--state", help="馆员状态 JSON（默认 data/state.json；测试可指向临时文件）")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("summary", help="总览")
    sp.set_defaults(func=cmd_summary)

    sp = sub.add_parser("people", help="人物、作品与师承/归属主张")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_people)

    sp = sub.add_parser("events", help="按类型列出木刻制作事件")
    sp.add_argument("--work", help="作品编号或 id，如 C12")
    sp.add_argument("--type", choices=list(__import__("woodcut.model", fromlist=["EventType"]).EventType.ALL))
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_events)

    sp = sub.add_parser("trace", help="从教学稿/语句/签发稿追到录音与作品卡")
    sp.add_argument("ref")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_trace)

    sp = sub.add_parser("affected", help="术语修订后受影响、需重判的语句")
    sp.add_argument("--term", default="term:ban")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_affected)

    sp = sub.add_parser("queue", help="复核队列")
    sp.add_argument("--term", default="term:ban")
    sp.add_argument("--descriptions-only", action="store_true")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_queue)

    sp = sub.add_parser("adopt-revision", help="采用预备的术语修订版")
    sp.add_argument("term_id", nargs="?", default="term:ban")
    sp.add_argument("--reviewer", default="当值班员")
    sp.set_defaults(func=cmd_adopt_revision)

    sp = sub.add_parser("review-mention", help="重判一个代词/术语/行为人链接")
    sp.add_argument("mention_id")
    # 注意：dest 必须区别于全局 --state（状态文件路径）
    sp.add_argument("--state", "--review-state", dest="review_state", required=True, choices=[
        ReviewState.CONFIRMED, ReviewState.CHANGED, ReviewState.OPEN_CANDIDATES, ReviewState.DISPUTED
    ])
    sp.add_argument("--choose", action="append", help="裁定链接值；可重复；多候选并存时全部传入")
    sp.add_argument("--note")
    sp.add_argument("--reviewer", default="当值班员")
    sp.set_defaults(func=cmd_review_mention)

    sp = sub.add_parser("review-description", help="复核一条作品说明")
    sp.add_argument("description_id")
    sp.add_argument("--state", "--review-state", dest="review_state", required=True, choices=[
        ReviewState.CONFIRMED, ReviewState.CHANGED, ReviewState.DISPUTED
    ])
    sp.add_argument("--note")
    sp.add_argument("--reviewer", default="当值班员")
    sp.set_defaults(func=cmd_review_description)

    sp = sub.add_parser("byline", help="在作品卡上应用学员署名（保留师承）")
    sp.add_argument("view_id", nargs="?", default="view:c12:current")
    sp.add_argument("--reviewer", default="当值班员")
    sp.set_defaults(func=cmd_byline)

    sp = sub.add_parser("draft", help="打印按受众生成的草稿（不签发）")
    sp.add_argument("audience", choices=[Audience.HALL_SOUND, Audience.CLASSROOM])
    sp.add_argument("--target", default="stmt:h0")
    sp.set_defaults(func=cmd_draft)

    sp = sub.add_parser("issue", help="签发声音说明或课堂文字")
    sp.add_argument("audience", choices=[Audience.HALL_SOUND, Audience.CLASSROOM])
    sp.add_argument("--issuer", required=True)
    sp.add_argument("--target", default="stmt:h0")
    sp.add_argument("--body-file", help="使用馆员改定的 Markdown 正文；缺省由系统按复核状态生成")
    sp.add_argument("--supersedes", help="被本版替代的旧签发稿 id")
    sp.add_argument("--out-dir", help="签发 Markdown 输出目录，默认 outputs/")
    sp.set_defaults(func=cmd_issue)

    rel = sub.add_parser("release", help="签发稿管理")
    rel_sub = rel.add_subparsers(dest="release_action", required=True)
    rl = rel_sub.add_parser("list")
    rl.add_argument("--audience", choices=[Audience.HALL_SOUND, Audience.CLASSROOM])
    rl.add_argument("--json", action="store_true")
    rl.set_defaults(func=cmd_release)
    rs = rel_sub.add_parser("show")
    rs.add_argument("release_id")
    rs.add_argument("--json", action="store_true")
    rs.set_defaults(func=cmd_release)
    rk = rel_sub.add_parser("keep", help="该受众决定暂不更新已签发稿，必须写理由")
    rk.add_argument("release_id")
    rk.add_argument("--reason", required=True)
    rk.add_argument("--reviewer", default="当值班员")
    rk.set_defaults(func=cmd_release)
    rd = rel_sub.add_parser("decide-revision", help="登记将出修订版的受众决定")
    rd.add_argument("release_id")
    rd.add_argument("--reason")
    rd.add_argument("--reviewer", default="当值班员")
    rd.set_defaults(func=cmd_release)

    sp = sub.add_parser("export", help="导出自包含复查 JSON 与全部签发 Markdown")
    sp.add_argument("--out", help="输出目录，默认 outputs/")
    sp.set_defaults(func=cmd_export)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        ws = _load(args)
    except (ValueError, FileNotFoundError) as exc:
        print(f"载入失败：{exc}", file=sys.stderr)
        return 2
    return args.func(ws, args)


if __name__ == "__main__":
    raise SystemExit(main())
