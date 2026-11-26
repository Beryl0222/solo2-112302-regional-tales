"""木刻口述史复核与签发工作包。

模块划分：
- model: 常量、枚举与签发文档模型
- repository: 读取 corpus.json（原始记录）与 knowledge.json（复核层）
- workspace: 馆员复核/术语修订/签发/追踪的统一工作区
- documents: 按受众生成“口述原意 / 馆方解释”分离的文稿
- cli: 命令行入口
"""

from .model import Audience, EventType, ReviewState, Release
from .repository import Repository
from .workspace import Workspace

__all__ = [
    "Audience",
    "EventType",
    "ReviewState",
    "Release",
    "Repository",
    "Workspace",
]
