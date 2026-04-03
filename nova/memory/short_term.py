"""短期记忆 — 当前对话的上下文窗口"""

from __future__ import annotations

from collections import deque
from typing import Optional

from .models import ConversationMessage


class ShortTermMemory:
    """
    短期记忆

    维护当前会话的对话历史,
    自动截断过旧的消息以控制 token 开销。
    """

    def __init__(self, max_rounds: int = 20):
        self.max_rounds = max_rounds
        self._messages: deque[ConversationMessage] = deque()
        self._session_id: str = ""

    @property
    def session_id(self) -> str:
        return self._session_id

    @session_id.setter
    def session_id(self, value: str):
        self._session_id = value

    def add(self, message: ConversationMessage):
        """添加一条消息"""
        message.session_id = self._session_id
        self._messages.append(message)
        self._trim()

    def _trim(self):
        """保留最近 max_rounds 轮对话"""
        max_messages = self.max_rounds * 2
        while len(self._messages) > max_messages:
            self._messages.popleft()

    def get_history(self) -> list[ConversationMessage]:
        return list(self._messages)

    def get_llm_messages(self) -> list[dict]:
        return [m.to_llm_format() for m in self._messages]

    def get_recent_text(self, n: int = 5) -> str:
        """获取最近 n 轮对话的纯文本"""
        recent = list(self._messages)[-n * 2:]
        lines = []
        for msg in recent:
            role = "用户" if msg.role == "user" else "Nova"
            lines.append(f"{role}: {msg.content}")
        return "\n".join(lines)

    def get_last_user_message(self) -> Optional[str]:
        for msg in reversed(self._messages):
            if msg.role == "user":
                return msg.content
        return None

    def clear(self):
        self._messages.clear()

    def __len__(self) -> int:
        return len(self._messages)
