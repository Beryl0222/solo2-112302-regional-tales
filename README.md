# 木刻作品口述稿中的创作者和版本沿袭

面向“访谈转写、作品卡、课程改写稿”的可复查 Python 项目：

1. 从 `data/corpus.json` 的 9 条原始记录建立**人物、作品、木刻制作事件、语句、代词候选**图谱；
2. 支持馆员**修订术语 → 回看全部受影响口述句 → 逐条重判实体链接 → 复核作品说明**；
3. 支持按受众**签发展厅声音说明（含听障字幕）与课堂讲义**，两栏分离“口述者原意 / 馆方解释”，
   永久保留说话人与录音时间；
4. 支持从任意一句教学稿（如 `l1`）一键追到录音时间、访谈目录、作品卡与技术卡。

仅依赖 Python 3.11 标准库。

## 业务底线（已固化为数据约束与测试）

- **五类事件不折叠**：创作、刻版、套印、收藏、展览分别登记；“母版刻毁”作为刻版终点单独登记。
  收藏没有语料时只登记“材料缺口”，不虚构收藏事件。
- **绝版木刻逐版递减**：“最后一版”裁定为同一母版的最后套色版次/刻印状态，不是另一块板、
  不是一个独立版本，也不是“一张作品”；最终状态与此前各版状态不折叠。
- **“版 / 一张”按语境与编号裁定**：附近有 c1“逐版递减”与 q1“版已经用完了”时，
  “最后一版”取版次义；“一张”按张数义。C12 只有作品编号、没有张号，张数不可考。
- **代词允许多候选并存**：展厅句 h0“贺昆在它上面刻出红土”的“它”同时保留
  `block:c12`（母版）与 `entity:c12:sheet-prev`（上一张印纸），并记录时序冲突，
  不为释文顺畅而固定为母版。q2 的“他”不直接等同于说话人贺昆。
- **师生沿袭不转移所有权**：C12 作品卡（w1/p2）记周敏创作并署个人名、贺昆导师；
  技艺沿袭连接师生双方，但 C12 不是贺昆的作品。l1“教师示范后共同制作”作为
  `conflicting_unverified` 对立主张原样保留并可追溯，不覆盖作品卡，也不被删除。
- **术语修订不是全文替换**：采用“版”v2 解释后，所有含“版”或经事件链接受影响的语句
  （包括全句无“版”字的 q2）全部回到待重判队列；`corpus.json` 原文一个字不改。
- **已签发稿件不被静默改写**：术语修订只把旧稿标为 stale；展厅与课堂两个受众分别决定
  “出修订版”或“本期保留（必须写理由）”。新版保留 00:43 / 01:12 录音时间并以
  `supersedes` 保留版本链。
- **学员署名与师承并存**：增加学员署名只改创作关系展示，`lineage_display` 必须原样保留。

## 目录

```
materials.py              # 原有语料读取入口（保持兼容）
data/corpus.json          # 9 条合成原始记录（只读，测试保证不被改写）
data/context.json
data/knowledge.json       # 人工复核层：人物/事件/语句/候选/术语版本/说明稿/卡片视图
data/state.json           # 馆员作业状态：术语采用、复核结论、签发稿（可重建）
woodcut/
  model.py                # 事件类型、受众、复核状态、Release
  repository.py           # 读取并校验 corpus + knowledge 的回链完整性
  workspace.py            # 术语修订、复核队列、来源追踪、签发与受众更新决定
  documents.py            # 两类受众文稿生成（原意/馆方解释分栏）+ 签发文件头
  exporting.py            # outputs/registry.json 与 Markdown 导出
  cli.py                  # python -m woodcut ...
scripts/build_demo.py     # 一键重建示范复核结论、4 份签发稿与 outputs/
tests/                    # 37 个 unittest（原有 3 个 + 新增 34 个）
outputs/                  # 自包含复查 JSON 与已签发 Markdown
```

## 运行检查

```bash
python3 -m unittest discover -s tests -v
```

## 重建示范馆员作业状态

```bash
python3 scripts/build_demo.py
```

该脚本会：签发 v1 两稿 → 采用“版”v2 → 重判全部 10 个提及链接 →
复核作品卡与技术卡（展厅说明稿刻意留在待复核队列）→ 应用学员署名 →
签发 v2 两稿 → 导出 `outputs/`。

## 馆员常用命令

> 下面的复核/签发命令默认改写 `data/state.json`。想在不影响示范状态的情况下练手，
> 请在 `woodcut` 后加全局参数，例如 `python3 -m woodcut --state /tmp/drill.json issue ...`。

```bash
# 总览（术语版本、队列、签发稿状态）
python3 -m woodcut summary

# 人物 / 师承 / 对立主张；事件（可按作品与类型过滤）
python3 -m woodcut people
python3 -m woodcut events --work C12
python3 -m woodcut events --work C12 --type creation

# 从教学稿 l1 追到：q2 贺昆 01:12 录音、a1“非同一访谈”、w1 作品卡、c1 技术卡
python3 -m woodcut trace l1
python3 -m woodcut trace stmt:h0          # 同时拿到 00:43 周敏 与 01:12 贺昆
python3 -m woodcut trace m:h0:it --json   # 也可从某个代词链接出发

# 术语修订后受影响的语句（按实体链接召回，不是 grep 替换）
python3 -m woodcut affected

# 哪些作品说明等待复核
python3 -m woodcut queue --descriptions-only
python3 -m woodcut queue --json

# 采用 knowledge.json 中预备的“版”v2 修订解释
python3 -m woodcut adopt-revision term:ban --reviewer 馆员甲

# 重判代词/术语/行为人（--choose 可重复，多候选就全部保留）
python3 -m woodcut review-mention m:h0:it --state open_candidates \
  --choose block:c12 --choose entity:c12:sheet-prev \
  --note "母版与上一张印纸并存，原句时序矛盾，需拆分改写"
python3 -m woodcut review-description desc:c12:card --state confirmed --note "归属无误"

# 学员署名（师承说明保留）
python3 -m woodcut byline view:c12:current

# 预览/签发两类文稿
python3 -m woodcut draft hall_sound
python3 -m woodcut issue hall_sound --issuer 馆员甲
python3 -m woodcut issue classroom  --issuer 馆员乙

# 术语更新后，各受众独立决定
python3 -m woodcut release list
python3 -m woodcut release keep REL-HALL-C12-v1 --reason "本季展期不重录，现场口头补充"
python3 -m woodcut issue hall_sound --issuer 馆员甲 --supersedes REL-HALL-C12-v1

# 导出复查包（registry.json + outputs/issued/*.md）
python3 -m woodcut export
```

全局选项 `--state /path/to/state.json` 可让测试或不同馆员使用独立状态文件，
默认读写 `data/state.json`。

## 从 Python API 使用

```python
from pathlib import Path
from woodcut import Workspace, Audience
from woodcut.model import ReviewState

ws = Workspace.load(state_path=Path("/tmp/curator.json"))

t = ws.trace("l1")
print([(r["speaker"], r["timestamp"]) for r in t["recording"]])  # [('贺昆', '01:12')]
print([d["id"] for d in t["cards"]])

ws.adopt_term_revision("term:ban", reviewer="馆员甲")
ws.review_mention(
    "m:h0:it", ReviewState.OPEN_CANDIDATES,
    chosen=["block:c12", "entity:c12:sheet-prev"],
    note="两候选并存",
)
print(ws.pending_descriptions())   # 术语改动后等待复核的作品说明

rel = ws.issue(Audience.HALL_SOUND, issuer="馆员甲")
ws.save()
```

## 需求到测试的对应

| 业务要求 | 守护测试 |
| --- | --- |
| 人物/事件可复查、9 条语料全部被引用 | `test_graph.py::test_all_nine_corpus_records_are_accounted_for` |
| 学员创作、教师导师、沿袭不转移所有权 | `test_graph.py::test_student_is_creator_teacher_is_mentor_not_owner`、`test_teacher_student_co_exhibition_links_both_but_no_ownership_shift` |
| 五类事件分开、收藏只能是缺口 | `test_graph.py::test_creation_carving_overprint_collection_exhibition_are_distinct` |
| 逐版递减状态不折叠 | `test_graph.py::test_reduction_states_are_not_folded_into_one_work` |
| “它”两候选并存、“他”不等同贺昆 | `test_terms_pronouns.py::test_hall_sentence_it_keeps_two_candidates`、`test_q2_pronoun_he_is_not_automatically_hukun` |
| 术语修订召回 q2（无“版”字）且不改原文 | `test_terms_pronouns.py::test_affected_includes_q2_even_without_character_ban`、`test_term_revision_does_not_rewrite_raw_corpus` |
| “最后一版 / 一张”按语境与编号裁定 | `test_adjudicate_last_ban_uses_nearby_context`、`test_adjudicate_one_sheet_is_count_not_edition` |
| 作品说明复核队列 | `test_description_review_queue_after_term_change` |
| l1 → 01:12 录音 + 作品卡/c1 | `test_publishing.py::test_trace_lesson_l1_reaches_recording_and_cards` |
| 原意/馆方分栏、时间保留、旧稿不被改写 | `test_publishing.py::test_issue_separates_...`、`test_term_revision_marks_issued_docs_stale_...` |
| 两受众分别 keep / revise | `test_audience_can_keep_or_revise_independently` |
| 学员署名保留师承 | `test_student_byline_changes_display_but_keeps_lineage` |
| CLI 参数冲突回归 | `test_cli.py::test_review_state_option_does_not_overwrite_state_path` |
| 已签发示范产物一致性 | `test_committed_demo.py` |

## 资料性质

`data/corpus.json` 与 `data/knowledge.json` 中的人物、机构、录音与事件均为本地合成演练资料，
不含真实个人或机构处理记录。`h0`（“最后一版印完……刻出红土”）是馆方提供、未单列为
corpus 记录的现行展厅句，在 `knowledge.json` 中以 `stmt:h0` 原样登记并注明来源，不改字。
