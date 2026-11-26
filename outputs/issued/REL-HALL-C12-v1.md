---
release_id: REL-HALL-C12-v1
audience: hall_sound
version: 1
status: superseded
issuer: 示范馆员
issued_at: 2026-11-18T09:30:00+08:00
term_version_at_issue: 1
target: stmt:h0
supersedes: 
recording_timestamps:
  - statement: stmt:q1; speaker: 周敏; timestamp: 00:43; interview: int:zhou
  - statement: stmt:q2; speaker: 贺昆; timestamp: 01:12; interview: int:he
---

# C12 展厅声音说明（听障字幕同文）·初版

## 一、口述者原意（逐字保留，含录音时间）

- **周敏**｜录音时间 **00:43**（语句 `stmt:q1`，访谈 `int:zhou`）
  > “边刻边印，最后一版的时候，版已经用完了。”
  >
  > 录音目录说明：据 a1：q1 说话人为周敏。
- **贺昆**｜录音时间 **01:12**（语句 `stmt:q2`，访谈 `int:he`）
  > “他把它刻毁了，这种红土出来的刀痕就不能再补。”
  >
  > 录音目录说明：据 a1：q2 为贺昆；q1、q2 两段不是同一次访谈，不能互相借用上下文或代词所指。

> 00:43、01:12 是**录音时间轴位置**，不是创作或刻版发生的历史日期；两段录音不属同一次访谈。

## 二、馆方说明（馆方解释，不是口述者原话）

**术语口径（v1 旧术语解释）**：‘版’指印版；‘最后一版’被解作最后刻出的一块板或一个完整版本，该版印完后母版被摧毁。

**声音稿（初版，沿用展厅初稿 g1 与现行句 h0 的顺叙）**：

> 最后一版印完，母版便毁了，贺昆在它上面刻出红土。

_初版按旧术语把“最后一版”解作最后一块/一版，并把“它”顺指为母版、把行为人固定为贺昆。该处理仅为语句顺畅，术语修订后必须重新判断。_

### 代词与术语链接复核（候选不得因顺句删除）

- `m:h0:last-ban` 锚文字 **“最后一版”**（stmt:h0）
  - 候选：套色版次：母版最后刻印状态｜支持度：strong
  - 候选：张数：最后一张印纸（若附近有张号才能裁定）｜支持度：weak
  - 术语修订前旧链接：`sense:ban:plate_or_version`
  - 本次复核：**pending_rereview（等待逐条重判，不做全文替换）**
- `m:h0:it` 锚文字 **“它”**（stmt:h0）
  - 候选：母版（紧邻前词；‘在板上刻’与刻版动作相容）｜支持度：medium
  - 候选：上一张印纸（若指印纸则应是套印关系，不能‘刻’纸；但原句本身时序矛盾，不能为此删除该候选）｜支持度：medium
  - 术语修订前旧链接：`block:c12`（为顺畅叙事而固定，需重判）
  - 本次复核：**pending_rereview（等待逐条重判，不做全文替换）**
  - 冲突记录：原句先言‘母版便毁了’，再言‘在它上面刻’：若‘它’=母版，则毁版之后不能再刻，时序自相矛盾；若‘它’=印纸，则与‘刻’的工具动作及 q2‘刀痕’不合。句子本身必须拆分重写，不能靠选定代词掩盖冲突。
- `m:h0:agent-hekun` 锚文字 **“贺昆”**（stmt:h0）
  - 候选：贺昆（展厅句断言的红土刻制行为人）｜支持度：museum_claim_only
  - 候选：q2 的未具名‘他’，不能自动等同于贺昆｜支持度：open
  - 术语修订前旧链接：`person:hekun`（为顺畅叙事而固定，需重判）
  - 本次复核：**pending_rereview（等待逐条重判，不做全文替换）**
- `m:q1:last-ban` 锚文字 **“最后一版”**（stmt:q1）
  - 候选：套色版次：同一母版最后刻印状态/色层｜支持度：strong
  - 候选：张数/印数：最后一张或最后一批印件｜支持度：weak
  - 候选：出版物版本/版次｜支持度：unsupported
  - 术语修订前旧链接：`sense:ban:plate_or_version`
  - 本次复核：**pending_rereview（等待逐条重判，不做全文替换）**
- `m:q1:ban-used-up` 锚文字 **“版已经用完了”**（stmt:q1）
  - 候选：逐版刻到终点，母版板面已被刻尽（‘用完’）｜支持度：strong
  - 候选：纸张/印数用完｜支持度：unsupported
  - 术语修订前旧链接：`entity:block:c12`
  - 本次复核：**pending_rereview（等待逐条重判，不做全文替换）**
- `m:q2:ta` 锚文字 **“他”**（stmt:q2）
  - 候选：未具名的男性刻者（语法上的第三人称，默认候选）｜支持度：strong
  - 候选：贺昆以‘他’自指或泛称刻者（推测，无直接证据）｜支持度：speculative
  - 术语修订前旧链接：`person:hekun`（为顺畅叙事而固定，需重判）
  - 本次复核：**pending_rereview（等待逐条重判，不做全文替换）**
- `m:q2:it` 锚文字 **“它”**（stmt:q2）
  - 候选：C12 母版（‘刻毁’与 c1‘母版刻毁’搭配一致）｜支持度：strong
  - 候选：最后版次的板面状态（与母版同一实体的状态描述）｜支持度：medium
  - 候选：印纸（‘刻毁纸张’搭配异常，仅保留为候选）｜支持度：weak
  - 术语修订前旧链接：`block:c12`
  - 本次复核：**pending_rereview（等待逐条重判，不做全文替换）**
- `m:q2:red-earth` 锚文字 **“红土”**（stmt:q2）
  - 候选：名为‘红土’的套色色层/颜料及其刀痕｜支持度：strong
  - 术语修订前旧链接：`state:c12:red-earth-layer`
  - 本次复核：**pending_rereview（等待逐条重判，不做全文替换）**
- `m:g1:last-ban` 锚文字 **“贺昆刻出的最后一版”**（stmt:g1）
  - 候选：最后套色版次（同一母版的最终刻印状态）｜支持度：strong
  - 候选：最后一块板/一个独立版本（旧解释，易导致把状态当成新实体）｜支持度：rejected_after_revision
  - 术语修订前旧链接：`sense:ban:plate_or_version`
  - 本次复核：**pending_rereview（等待逐条重判，不做全文替换）**
- `m:g1:agent-hekun` 锚文字 **“贺昆刻出 / 摧毁”**（stmt:g1）
  - 候选：贺昆（仅为 g1 的馆方断言；q2 原作‘他’，说话人虽为贺昆但不能直接划等号）｜支持度：museum_claim_only
  - 候选：q2 中未具名的‘他’｜支持度：open
  - 术语修订前旧链接：`person:hekun`（为顺畅叙事而固定，需重判）
  - 本次复核：**pending_rereview（等待逐条重判，不做全文替换）**

## 证据与追溯

- 回链 corpus 原始记录：`q1`, `q2`, `g1`, `c1`, `a1`, `w1`, `p2`
- 追踪入口：`stmt:h0`（statement）
- 追踪路径：
  - 语句 stmt:h0（hall_script_current）
  - stmt:h0 引用 -> stmt:q1
  - stmt:h0 引用 -> stmt:q2
  - stmt:h0 引用 -> stmt:g1
  - 事件 event:c12:block-destroyed 证据 c1 -> 语句 stmt:c1

