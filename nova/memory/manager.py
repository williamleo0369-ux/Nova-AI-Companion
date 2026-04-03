"""记忆管理器 — 统一管理短期和长期记忆"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from loguru import logger

from .models import MemoryItem, UserProfile, ConversationMessage
from .short_term import ShortTermMemory
from .long_term import LongTermMemory

if TYPE_CHECKING:
    from nova.core.llm import LLMClient


class MemoryManager:
    """
    记忆管理器 — 职责:
    1. 管理短期记忆 (当前对话上下文)
    2. 管理长期记忆 (SQLite 持久化)
    3. 用 LLM 从对话中提取记忆
    4. 为 LLM 构建记忆上下文
    """

    def __init__(self,
        db_path: str = "data/nova_memory.db",
        short_term_rounds: int = 20,
        extraction_interval: int = 3,
    ):
        self.short_term = ShortTermMemory(max_rounds=short_term_rounds)
        self.long_term = LongTermMemory(db_path=db_path)
        self.extraction_interval = extraction_interval
        self._message_count = 0
        self._llm: Optional[LLMClient] = None
        self._user_profile: Optional[UserProfile] = None

    def set_llm(self, llm: LLMClient):
        self._llm = llm

    async def initialize(self):
        await self.long_term.initialize()
        self._user_profile = await self.long_term.get_user_profile()
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.short_term.session_id = session_id
        mem_count = await self.long_term.get_memory_count()
        conv_count = await self.long_term.get_conversation_count()
        logger.info(f"🧠 记忆系统就绪: {mem_count} 条记忆, {conv_count} 条历史对话")

    async def close(self):
        await self.long_term.close()

    @property
    def user_profile(self) -> UserProfile:
        if self._user_profile is None:
            self._user_profile = UserProfile()
        return self._user_profile

    # ============ 消息处理 ============

    async def add_user_message(self, content: str, emotion: str = ""):
        msg = ConversationMessage(
            role="user", content=content, emotion=emotion,
            session_id=self.short_term.session_id,
        )
        self.short_term.add(msg)
        await self.long_term.save_conversation(msg)
        self._message_count += 1

    async def add_assistant_message(self, content: str):
        msg = ConversationMessage(
            role="assistant", content=content,
            session_id=self.short_term.session_id,
        )
        self.short_term.add(msg)
        await self.long_term.save_conversation(msg)

    # ============ 后台记忆提取 ============

    async def maybe_extract_memories(self):
        """每 extraction_interval 轮触发记忆提取"""
        if self._message_count % self.extraction_interval != 0:
            return
        if self._llm is None:
            return
        asyncio.create_task(self._extract_memories())

    async def _extract_memories(self):
        """用 LLM 从最近对话中提取用户档案和记忆"""
        recent_text = self.short_term.get_recent_text(
            n=self.extraction_interval
        )
        if not recent_text:
            return

        extraction_prompt = f"""请分析以下对话，提取关于"用户"的信息。

对话内容:
{recent_text}

请用 JSON 格式返回，包含两个字段:

1. "profile": 用户的基本信息，只包含对话中明确提到的内容。
   可能的字段: name, nickname, age, gender, city, job, pet,
   pet_name, hobby, relationship, partner, food, music,
   mood_pattern, sleep_pattern
   如果没有相关信息，留空对象。

2. "memories": 值得长期记住的事实或事件的列表，每个包含:
   - "content": 记忆内容 (一句话总结)
   - "type": 类型 (fact/event/emotion/preference)
   - "keywords": 关键词列表
   - "importance": 重要性 0.0-1.0

只提取实际出现的信息。如果没有值得记住的新信息，返回空列表。
返回纯 JSON，不要包含 markdown 代码块标记。"""

        try:
            response = await self._llm.complete(
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=0.3, max_tokens=800,
            )
            if not response: return

            # 清理 markdown 标记
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            data = json.loads(text.strip())

            # 更新用户档案
            profile_data = data.get("profile", {})
            if profile_data:
                await self.long_term.update_profile_batch(profile_data)
                for k, v in profile_data.items():
                    if v and v.strip():
                        self._user_profile.set(k, v.strip())
                logger.info(f"📝 档案更新: {list(profile_data.keys())}")

            # 存储新记忆
            memories = data.get("memories", [])
            for mem_data in memories:
                item = MemoryItem(
                    content=mem_data.get("content", ""),
                    memory_type=mem_data.get("type", "fact"),
                    keywords=mem_data.get("keywords", []),
                    importance=mem_data.get("importance", 0.5),
                )
                if item.content:
                    await self.long_term.store_memory(item)
            if memories:
                logger.info(f"💾 提取了 {len(memories)} 条新记忆")

        except json.JSONDecodeError:
            logger.warning("记忆提取: LLM 返回了无效 JSON")
        except Exception as e:
            logger.warning(f"记忆提取失败 (不影响对话): {e}")

    # ============ 上下文构建 ============

    async def build_context(self, user_message: str) -> dict:
        """为当前对话构建记忆上下文"""
        profile_text = self.user_profile.to_prompt()

        # 搜索相关记忆
        memories = await self.long_term.search_memories(
            query=user_message, limit=8
        )
        recent_memories = await self.long_term.get_recent_memories(limit=5)
        for m in recent_memories:
            if m.id not in [x.id for x in memories]:
                memories.append(m)

        memory_text = ""
        if memories:
            memory_lines = []
            for m in memories[:10]:
                age = self._format_time_ago(m.created_at)
                memory_lines.append(
                    f"[{m.memory_type}][{age}] {m.content}"
                )
            memory_text = "\n".join(memory_lines)

        history = self.short_term.get_llm_messages()

        return {
            "user_profile": profile_text,
            "relevant_memories": memory_text,
            "conversation_history": history,
        }

    def _format_time_ago(self, iso_time: str) -> str:
        try:
            dt = datetime.fromisoformat(iso_time)
            delta = datetime.now() - dt
            if delta.days > 30: return f"{delta.days // 30}个月前"
            elif delta.days > 0: return f"{delta.days}天前"
            elif delta.seconds > 3600: return f"{delta.seconds // 3600}小时前"
            elif delta.seconds > 60: return f"{delta.seconds // 60}分钟前"
            else: return "刚刚"
        except Exception:
            return "某天"
