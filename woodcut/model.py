"""领域常量与签发文档模型。"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


class EventType:
    """木刻作品生命周期中必须分开登记的事件类型。"""

    CREATION = "creation"            # 创作
    CARVING = "carving"              # 刻版
    OVERPRINTING = "overprinting"    # 套印
    COLLECTION = "collection"        # 收藏
    EXHIBITION = "exhibition"        # 展览
    DESTRUCTION = "block_destruction"  # 母版刻毁（刻版终点，单独登记）

    ALL = (
        CREATION,
        CARVING,
        OVERPRINTING,
        COLLECTION,
        EXHIBITION,
        DESTRUCTION,
    )
    LABELS = {
        CREATION: "创作",
        CARVING: "刻版",
        OVERPRINTING: "套印",
        COLLECTION: "收藏",
        EXHIBITION: "展览",
        DESTRUCTION: "母版刻毁",
    }


class Audience:
    HALL_SOUND = "hall_sound"    # 展厅声音说明 / 听障字幕
    CLASSROOM = "classroom"      # 课堂讲义（教师用）

    LABELS = {
        HALL_SOUND: "展厅声音说明（含听障字幕）",
        CLASSROOM: "课堂讲义（教师用）",
    }
    PREFIX = {
        HALL_SOUND: "HALL",
        CLASSROOM: "CLASS",
    }


class ReviewState:
    PENDING = "pending_rereview"          # 术语已修订，等待重新判断
    CONFIRMED = "confirmed"               # 重判后维持链接
    CHANGED = "link_changed"              # 重判后改变实体链接
    OPEN_CANDIDATES = "open_candidates"   # 证据不足，多个候选同时保留
    DISPUTED = "disputed_claim"           # 主张对立，不能坐实


class UpdateAction:
    ISSUE_REVISION = "issue_revision"
    KEEP_CURRENT = "keep_current"


@dataclass
class Release:
    """一次签发的声音说明或课堂文字。

    签发后的正文不可被术语修订静默改写：修订只会把 release 标为 stale，
    是否出新版由该受众对应的馆员决定。
    """

    id: str
    audience: str
    target_id: str
    title: str
    body_markdown: str
    issuer: str
    issued_at: str
    version: int
    term_version: int
    source_timestamps: list[dict[str, Any]] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    supersedes: Optional[str] = None
    status: str = "issued"  # issued | superseded

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Release":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})
