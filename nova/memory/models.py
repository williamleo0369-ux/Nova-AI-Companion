"""记忆系统的数据模型"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class MemoryItem:
    """一条长期记忆"""

    content: str
    memory_type: str = "fact"          # fact / event / emotion / preference
    keywords: list[str] = field(default_factory=list)
    importance: float = 0.5            # 0.0 ~ 1.0
    created_at: str = ""
    last_accessed: str = ""
    access_count: int = 0
    id: Optional[int] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_accessed:
            self.last_accessed = self.created_at

    @property
    def keywords_str(self) -> str:
        return ",".join(self.keywords)

    @classmethod
    def from_db_row(cls, row: dict) -> MemoryItem:
        keywords = row.get("keywords", "") or ""
        return cls(
            id=row["id"],
            content=row["content"],
            memory_type=row["memory_type"],
            keywords=keywords.split(",") if keywords else [],
            importance=row.get("importance", 0.5),
            created_at=row.get("created_at", ""),
            last_accessed=row.get("last_accessed", ""),
            access_count=row.get("access_count", 0),
        )


@dataclass
class UserProfile:
    """用户档案 — 关于用户的所有已知信息"""

    data: dict[str, str] = field(default_factory=dict)

    def set(self, key: str, value: str):
        self.data[key] = value

    def get(self, key: str, default: str = "") -> str:
        return self.data.get(key, default)

    def to_prompt(self) -> str:
        """转换为系统提示词中的用户描述"""
        if not self.data:
            return "（还不太了解这个人，刚开始聊天）"

        lines = []
        label_map = {
            "name": "名字", "nickname": "昵称",
            "age": "年龄", "gender": "性别",
            "city": "所在城市", "job": "职业",
            "pet": "宠物", "pet_name": "宠物名字",
            "hobby": "爱好", "relationship": "感情状态",
            "partner": "伴侣", "food": "喜欢的食物",
            "music": "喜欢的音乐",
            "mood_pattern": "情绪特征",
            "sleep_pattern": "作息特征",
        }
        for key, value in self.data.items():
            label = label_map.get(key, key)
            lines.append(f"- {label}: {value}")

        return "\n".join(lines)

    def summary(self) -> str:
        name = self.data.get("name", "用户")
        parts = [f"用户: {name}"]
        for k in ["city", "job", "pet_name"]:
            if k in self.data:
                parts.append(self.data[k])
        return " | ".join(parts)


@dataclass
class ConversationMessage:
    """一条对话消息"""

    role: str               # user / assistant
    content: str
    emotion: str = ""
    timestamp: str = ""
    session_id: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_llm_format(self) -> dict:
        return {"role": self.role, "content": self.content}
