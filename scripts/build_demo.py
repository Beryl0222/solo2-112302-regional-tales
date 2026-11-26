#!/usr/bin/env python3
"""可复现的馆员作业脚本：重建 data/state.json 与 outputs/。

流程：
1. 在旧术语 v1 下签发展厅声音说明 v1 与课堂讲义 v1；
2. 采用修订后的“版”术语 v2（触发全部相关口述句/说明稿待重判）；
3. 逐条重判 10 个提及链接（多候选保留、对立主张不坐实）；
4. 复核作品卡与技术卡；展厅说明稿保留为“等待复核”，供复查队列演示；
5. 应用学员署名（保留师承）；
6. 两个受众分别决定出修订版 v2（保留录音时间点与被替代的 v1）；
7. 导出自包含 registry.json 与签发 Markdown。

直接运行：python3 scripts/build_demo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from woodcut.exporting import export_all  # noqa: E402
from woodcut.model import Audience, ReviewState  # noqa: E402
from woodcut.workspace import Workspace  # noqa: E402

STATE = ROOT / "data" / "state.json"
ISSUER = "示范馆员"

V1_AT = "2026-11-18T09:30:00+08:00"
V1_CLASS_AT = "2026-11-18T10:05:00+08:00"
REVISE_AT = "2026-11-25T09:00:00+08:00"
REVIEW_AT = "2026-11-25T10:30:00+08:00"
V2_HALL_AT = "2026-11-25T15:00:00+08:00"
V2_CLASS_AT = "2026-11-25T15:20:00+08:00"


def main() -> int:
    if STATE.exists():
        STATE.unlink()
    ws = Workspace.load(state_path=STATE)

    # 1) 旧口径下的 v1 签发稿（历史状态，随后会被替代但不删除）
    hall_v1 = ws.issue(Audience.HALL_SOUND, ISSUER, at=V1_AT)
    class_v1 = ws.issue(Audience.CLASSROOM, ISSUER, at=V1_CLASS_AT)
    print("issued", hall_v1.id, class_v1.id)

    # 2) 术语修订
    ws.adopt_term_revision("term:ban", reviewer=ISSUER, at=REVISE_AT)

    # 3) 逐条实体重判。关键：候选不删除，不搞全文替换。
    R = ReviewState
    decisions = [
        ("m:q1:last-ban", R.CHANGED, ["sense:ban:state"],
         "附近有 c1 逐版递减与 q1‘版已经用完了’，旧链接 plate_or_version 改为同一母版最后套色版次。"),
        ("m:q1:ban-used-up", R.CONFIRMED, ["sense:ban:state_exhausted", "block:c12"],
         "‘用完’指母版板面被逐版刻尽；母版链接成立，但细化为终点状态而非纸张用完。"),
        ("m:q2:ta", R.OPEN_CANDIDATES, ["entity:unnamed:ta-q2", "person:hekun"],
         "q2 说话人是贺昆，但引句用第三人称‘他’；不能因 g1 顺畅叙事就把‘他’固定为贺昆，两候选并存。"),
        ("m:q2:it", R.CONFIRMED, ["block:c12", "state:c12:final"],
         "‘刻毁’与 c1‘母版刻毁’搭配一致，母版/最终状态为主链接；印纸候选搭配异常，留档不采。"),
        ("m:q2:red-earth", R.CONFIRMED, ["state:c12:red-earth-layer"],
         "红土作为色层/刀痕链接成立；处于哪一版次无完整语境与张号，ordinal 保持 unknown。"),
        ("m:g1:last-ban", R.CHANGED, ["sense:ban:state"],
         "停止把‘最后一版’实体化为贺昆刻出的另一块板或独立版本。"),
        ("m:g1:agent-hekun", R.DISPUTED, ["person:hekun", "entity:unnamed:ta-q2"],
         "贺昆只是 g1 的馆方断言；q2 的‘他’未坐实，行为人链接标争议，不覆盖口述原文。"),
        ("m:h0:last-ban", R.CHANGED, ["sense:ban:state"],
         "版次读法有 q1/c1 支持；‘张数’候选因无张号仅作弱候选保留。"),
        ("m:h0:it", R.OPEN_CANDIDATES, ["block:c12", "entity:c12:sheet-prev"],
         "母版与上一张印纸两个候选同时保留：原句先言毁版再言在‘它’上刻，时序冲突，"
         "不能为让释文顺畅而固定为母版；句子应拆分重写。"),
        ("m:h0:agent-hekun", R.DISPUTED, ["person:hekun", "entity:unnamed:ta-q2"],
         "‘贺昆刻出红土’是展厅句的主语安排，属馆方稿断言；与 q2 未具名‘他’一并展示。"),
    ]
    for mid, state, chosen, note in decisions:
        ws.review_mention(mid, state, chosen=chosen, note=note, reviewer=ISSUER, at=REVIEW_AT)

    # 4) 作品说明复核：卡与技术卡通过；展厅说明稿故意保留待复核
    ws.review_description(
        "desc:c12:card", R.CONFIRMED,
        "w1/p2 互证周敏创作并署名、贺昆导师；术语细化不改变创作关系。",
        reviewer=ISSUER, at=REVIEW_AT,
    )
    ws.review_description(
        "desc:c12:technique", R.CONFIRMED,
        "c1 内容与 v2‘逐版递减、母版刻毁’一致；继续保留‘c1 未标 C12 编号’的范围警告。",
        reviewer=ISSUER, at=REVIEW_AT,
    )
    # 注意：desc:c12:hall 不写复核结论 -> 它会出现在‘等待复核的作品说明’队列，
    # 因为 g1/h0 的改写需展陈责任岗另行签发，声音说明 v2 不替代说明牌定稿。

    # 5) 学员署名展示（师承必须保留）
    ws.apply_student_byline("view:c12:current", reviewer=ISSUER, at=REVIEW_AT)

    # 6) 两个受众各自决定出修订版；supersedes 保留版本链与录音时间
    hall_v2 = ws.issue(
        Audience.HALL_SOUND, ISSUER, at=V2_HALL_AT, supersedes=hall_v1.id
    )
    class_v2 = ws.issue(
        Audience.CLASSROOM, ISSUER, at=V2_CLASS_AT, supersedes=class_v1.id
    )
    ws.save()

    paths = export_all(ws, ROOT / "outputs")
    print("issued", hall_v2.id, class_v2.id)
    q = ws.review_queue()
    print("pending descriptions:", [d["id"] for d in q["pending_descriptions"]])
    print("pending mentions:", len(q["pending_mentions"]))
    for key, p in paths.items():
        print("exported", key, p.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
