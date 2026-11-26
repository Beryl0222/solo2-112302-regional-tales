"""按受众生成展厅声音说明与课堂讲义草稿。

铁律：
1. 口述者原话、说话人、录音时间、访谈归属放在“口述原意”区，逐字引用；
2. 馆方考订、候选代词、术语解释放在“馆方说明”区，绝不混入口述原话；
3. 术语修订后不静默改写任何已签发 Release，只在新草稿中反映新复核结论；
4. 候选所指必须原样列出，未裁定就标“多候选保留”，不为文从字顺而固定。
"""
from __future__ import annotations

from typing import Any, Optional

from .model import Audience, ReviewState


def _candidate_label(ws: "Workspace", value: str) -> str:  # noqa: F821
    v = value
    if v in ws.repo.person_by_id:
        return ws.repo.person_by_id[v]["name"] + f"（{v}）"
    if v in ws.repo.block_by_id:
        return ws.repo.block_by_id[v]["label"]
    if v in ws.repo.state_by_id:
        return ws.repo.state_by_id[v]["label"]
    if v in ws.repo.candidate_entity_by_id:
        return ws.repo.candidate_entity_by_id[v]["label"]
    term = ws.repo.term_by_id.get("term:ban")
    if term:
        for ver in ws.term_versions("term:ban"):
            for sense in ver.get("senses", []):
                if sense["id"] == v:
                    return sense["label"]
    return v


def _original_section(ws: "Workspace", trace: dict[str, Any]) -> list[str]:
    lines = ["## 一、口述者原意（逐字保留，含录音时间）", ""]
    recs = trace["recording"]
    if not recs:
        lines.append("_本件没有直接录音语句。_")
        lines.append("")
    for r in recs:
        lines.append(
            f"- **{r['speaker']}**｜录音时间 **{r['timestamp']}**"
            f"（语句 `{r['statement_id']}`，访谈 `{r.get('interview_id') or '未登记'}`）"
        )
        lines.append(f"  > “{r['verbatim']}”")
        if r.get("interview_note"):
            lines.append(f"  >")
            lines.append(f"  > 录音目录说明：{r['interview_note']}")
    lines.append("")
    lines.append("> 00:43、01:12 是**录音时间轴位置**，不是创作或刻版发生的历史日期；两段录音不属同一次访谈。")
    lines.append("")
    return lines


def _mention_table(ws: "Workspace", statement_ids: list[str]) -> list[str]:
    lines = ["### 代词与术语链接复核（候选不得因顺句删除）", ""]
    any_row = False
    for sid in statement_ids:
        for m in ws.repo.mentions_for_statement(sid):
            any_row = True
            review = ws.mention_review(m["id"])
            lines.append(f"- `{m['id']}` 锚文字 **“{m['anchor']}”**（{sid}）")
            for c in m.get("candidates", []):
                lines.append(f"  - 候选：{c['label']}｜支持度：{c.get('strength', 'n/a')}")
            old = m.get("v1_link")
            if old:
                lines.append(f"  - 术语修订前旧链接：`{old['chosen']}`"
                             + ("（为顺畅叙事而固定，需重判）" if old.get("smoothness_driven") else ""))
            if review:
                chosen = "、".join(review.get("chosen", [])) or "（不单选）"
                lines.append(f"  - 本次复核：**{review['state']}**；结论链接：{chosen}")
                if review.get("note"):
                    lines.append(f"    - 复核说明：{review['note']}")
            else:
                lines.append(f"  - 本次复核：**{ReviewState.PENDING}（等待逐条重判，不做全文替换）**")
            if m.get("conflict"):
                lines.append(f"  - 冲突记录：{m['conflict']}")
    if not any_row:
        lines.append("_目标语句没有登记中的提及。_")
    lines.append("")
    return lines


def _evidence_line(ws: "Workspace", trace: dict[str, Any]) -> list[str]:
    ids = trace["raw_record_ids"]
    return [
        "## 证据与追溯",
        "",
        f"- 回链 corpus 原始记录：{', '.join(f'`{i}`' for i in ids) if ids else '无'}",
        f"- 追踪入口：`{trace['ref']}`（{trace['root_kind']}）",
        "- 追踪路径：",
    ] + [f"  - {p}" for p in trace["paths"]] + [""]


def build_hall_sound(ws: "Workspace", target_id: str, trace: dict[str, Any]) -> str:
    ver = ws.current_term_version()
    title = "C12 展厅声音说明（听障字幕同文）" + ("·修订稿" if ver >= 2 else "·初版")
    L = [f"# {title}", ""]
    L += _original_section(ws, trace)

    L += ["## 二、馆方说明（馆方解释，不是口述者原话）", ""]
    if ver <= 1:
        td = ws.term_definition("term:ban", 1)
        L += [
            f"**术语口径（v{td['version']} {td['label']}）**：{td['definition']}",
            "",
            "**声音稿（初版，沿用展厅初稿 g1 与现行句 h0 的顺叙）**：",
            "",
            "> 最后一版印完，母版便毁了，贺昆在它上面刻出红土。",
            "",
            "_初版按旧术语把“最后一版”解作最后一块/一版，并把“它”顺指为母版、把行为人固定为贺昆。"
            "该处理仅为语句顺畅，术语修订后必须重新判断。_",
            "",
        ]
    else:
        td = ws.term_definition("term:ban", 2)
        L += [
            f"**术语口径（v{td['version']} {td['label']}）**：{td['definition']}",
            "",
            "“一张”按张数理解，指印出的纸张/成品；C12 没有登记张号，不能把“一张”进位成“一版”。",
            "",
            "**可录制声音稿（修订版；无证据的链接不坐实）**：",
            "",
            "> 这件 C12 是周敏创作并署名的套色木刻，贺昆是她的版画教师和作品导师。"
            "绝版木刻用同一块母版，边刻边印、逐版递减：每一套色是一个版次，刻去一层，就不能回头补版。"
            "周敏记得，“最后一版的时候，版已经用完了”。贺昆在另一次访谈里讲到“他把它刻毁了”，"
            "还讲到“红土”色层出来的刀痕没法再补。技术卡记载，全部套色之后母版刻毁，不能重复印制。",
            ">",
            "> 展厅旧句说“贺昆在它上面刻出红土”。句中的“它”，可能指母版，也可能指上一张印纸；"
            "而且旧句先说母版毁了、再说在“它”上面刻，顺序互相冲突。"
            "所以我们不把这句有矛盾的话当成制作顺序播讲：可以确定的是母版在最后阶段刻尽而毁；"
            "红土处在哪一个版次、贺昆话里的“他”是谁，目前没有张号或完整语境可以坐实，"
            "我们把不同说法一并保留。",
            "",
            "**受众处理**：听障字幕与配音同文；时间轴保留 00:43、01:12 两个录音点，"
            "字幕在两处分别标注说话人，不把两段不同访谈剪成同一现场对话。",
            "",
        ]

    L += _mention_table(ws, trace["statement_ids"])
    L += _evidence_line(ws, trace)
    return "\n".join(L)


def build_classroom(ws: "Workspace", target_id: str, trace: dict[str, Any]) -> str:
    ver = ws.current_term_version()
    title = "C12 课堂讲义（教师用）" + ("·术语修订版" if ver >= 2 else "·初版")
    L = [f"# {title}", ""]
    L += _original_section(ws, trace)

    L += ["## 二、馆方考订与教学说明（馆方解释，可与原话对照讲授）", ""]
    if ver >= 2:
        td = ws.term_definition("term:ban", 2)
        L += [
            f"### 1. 术语“版”的修订解释（v{td['version']}）",
            td["definition"],
            "",
            "- **版次/刻印状态**：绝版木刻同一母版逐版递减中的一个套色阶段，不是另一块板、另一作品。",
            "- **张数**：“一张”指印出的纸张；C12 只有作品编号、没有张号，张数不可考。",
            "- **版本（出版物意义）**：本批口述无证据采用。",
            "- 教学提醒：修订术语后不能只做全文替换；q2 全句没有“版”字，但因“刻毁/红土”链接到母版与版次事件，仍须重判。",
            "",
            "### 2. 人物与创作归属",
            "- 作品卡 w1 与 p2：**周敏创作、署个人名；贺昆为导师/版画教师**。",
            "- 师生共展与技艺沿袭把贺昆、周敏双方连到同一条绝版木刻技艺脉络，但**不把 C12 归为贺昆所有**。",
            "- l1 提出“教师示范后共同制作”，这是课程改写稿中的**对立主张（claim:l1-joint）**，"
            "在没有示范记录或共同制作证据前，不覆盖作品卡；可作为课堂史料对读问题。",
            "",
            "### 3. 事件不能折叠",
            "创作、刻版、套印、收藏、展览是不同事件；母版刻毁是刻版的终点，也单独登记。"
            "“最后版次状态”和此前各刻印状态属于同一块母版的不同阶段，不能折叠成“一张作品”的先后版本，"
            "也不能把红土色层擅自排到毁版之前或之后。收藏事件在现有语料中是材料缺口，不要替学生补造收藏故事。",
            "",
            "### 4. 课堂讨论：这个“它”指什么？",
            "展示 h0 原句与两个候选（母版 / 上一张印纸），让学生分别检验搭配与时序：",
            "若“它”是母版，则“母版便毁了”之后无法再刻；若“它”是印纸，则与“刻”和“刀痕”不合。"
            "结论应是：**句子本身需要拆分改写，候选可以并存，不能为了通顺替古人/口述者定指。**",
            "",
            "### 5. 从教学稿一键追溯",
            "对 `l1` 运行 `python -m woodcut trace l1`，可从“同文引用 q2”追到：",
            "- 贺昆 01:12 录音（访谈 int:he）；",
            "- a1 录音目录：q1 为周敏 00:43，两段不是同一次访谈；",
            "- C12 作品卡 w1/p2 与技术卡 c1（c1 未标 C12 编号，只作技术语境）。",
            "",
        ]
    else:
        L += [
            "### 初版口径",
            ws.term_definition("term:ban", 1)["definition"],
            "",
            "初版讲义沿用 l1 的“共同制作”表述与展厅句的固定代词链接；"
            "术语修订后需按本讲义新版对学生说明旧稿问题。",
            "",
        ]

    # 主张与事件清单，方便老师备课时复查
    if trace["claims"]:
        L += ["### 6. 归属主张对照", ""]
        for c in trace["claims"]:
            L.append(f"- `{c['id']}`（来源 `{c['source_id']}`，状态 **{c['status']}**）：{c['text']}")
            L.append(f"  - 处理：{c['handling']}")
        L.append("")

    L += ["### 7. 相关事件年表（逻辑顺序，非确切日期）", ""]
    for e in trace["events"]:
        L.append(f"- `{e['id']}`【{e['type_label']}】{e['label']}（证据：{', '.join(e.get('evidence_ids', [])) or '无'}）")
    L.append("")

    L += _mention_table(ws, trace["statement_ids"])
    L += _evidence_line(ws, trace)
    return "\n".join(L)


def build_draft(
    ws: "Workspace",
    audience: str,
    target_id: str = "stmt:h0",
) -> tuple[str, str]:
    trace = ws.trace(target_id)
    if audience == Audience.HALL_SOUND:
        md = build_hall_sound(ws, target_id, trace)
        return md, "C12 展厅声音说明"
    if audience == Audience.CLASSROOM:
        md = build_classroom(ws, target_id, trace)
        return md, "C12 课堂讲义"
    raise ValueError(f"未知受众：{audience}")


def render_issued_file(release: dict[str, Any]) -> str:
    """给已签发正文加签发元数据头（正文本身不再改动）。"""
    lines = [
        "---",
        f"release_id: {release['id']}",
        f"audience: {release['audience']}",
        f"version: {release['version']}",
        f"status: {release['status']}",
        f"issuer: {release['issuer']}",
        f"issued_at: {release['issued_at']}",
        f"term_version_at_issue: {release['term_version']}",
        f"target: {release['target_id']}",
        f"supersedes: {release.get('supersedes') or ''}",
        "recording_timestamps:",
    ]
    for t in release.get("source_timestamps", []):
        lines.append(
            f"  - statement: {t['statement_id']}; speaker: {t['speaker']}; "
            f"timestamp: {t['timestamp']}; interview: {t.get('interview_id') or ''}"
        )
    lines += ["---", ""]
    lines.append(release["body_markdown"])
    lines.append("")
    return "\n".join(lines)
