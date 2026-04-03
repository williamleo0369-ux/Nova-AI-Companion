"""长期记忆 — SQLite 持久化存储"""

from __future__ import annotations

import aiosqlite
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger

from .models import MemoryItem, UserProfile, ConversationMessage


class LongTermMemory:
    """
    长期记忆 — 使用 SQLite 存储:
    - 用户档案 (key-value)
    - 事实记忆 (用户提到的信息)
    - 情感记忆 (重要情感事件)
    - 对话历史 (所有历史对话)
    """

    def __init__(self, db_path: str = "data/nova_memory.db"):
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def initialize(self):
        """初始化数据库, 创建表结构"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row

        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS user_profile (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_type TEXT NOT NULL DEFAULT 'fact',
                content TEXT NOT NULL,
                keywords TEXT DEFAULT '',
                importance REAL DEFAULT 0.5,
                created_at TEXT NOT NULL,
                last_accessed TEXT NOT NULL,
                access_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                emotion TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_memories_type
                ON memories(memory_type);
            CREATE INDEX IF NOT EXISTS idx_memories_keywords
                ON memories(keywords);
            CREATE INDEX IF NOT EXISTS idx_conv_session
                ON conversations(session_id);
            CREATE INDEX IF NOT EXISTS idx_conv_time
                ON conversations(created_at);
        """)
        await self._db.commit()
        logger.info(f"📦 长期记忆已加载: {self.db_path}")

    async def close(self):
        if self._db:
            await self._db.close()

    # ============ 用户档案 ============

    async def get_user_profile(self) -> UserProfile:
        profile = UserProfile()
        async with self._db.execute(
            "SELECT key, value FROM user_profile"
        ) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                profile.set(row["key"], row["value"])
        return profile

    async def update_profile(self, key: str, value: str):
        now = datetime.now().isoformat()
        await self._db.execute("""
            INSERT INTO user_profile (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
        """, (key, value, now))
        await self._db.commit()

    async def update_profile_batch(self, data: dict[str, str]):
        now = datetime.now().isoformat()
        for key, value in data.items():
            if value and value.strip():
                await self._db.execute("""
                    INSERT INTO user_profile (key, value, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = excluded.updated_at
                """, (key, value.strip(), now))
        await self._db.commit()

    # ============ 记忆存取 ============

    async def store_memory(self, item: MemoryItem):
        # 简单去重
        async with self._db.execute(
            "SELECT id FROM memories WHERE content = ?",
            (item.content,),
        ) as cursor:
            if await cursor.fetchone():
                return

        await self._db.execute("""
            INSERT INTO memories
            (memory_type, content, keywords, importance,
             created_at, last_accessed, access_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            item.memory_type, item.content, item.keywords_str,
            item.importance, item.created_at,
            item.last_accessed, item.access_count,
        ))
        await self._db.commit()
        logger.debug(f"💾 新记忆: [{item.memory_type}] {item.content[:50]}")

    async def search_memories(
        self, query: str,
        memory_type: str = "", limit: int = 10,
    ) -> list[MemoryItem]:
        """搜索相关记忆 — 关键词匹配 + 全文搜索"""
        query_words = self._extract_keywords(query)
        results = []

        # 1. 关键词匹配
        for word in query_words:
            if len(word) < 2: continue
            sql = "SELECT * FROM memories WHERE keywords LIKE ?"
            params = [f"%{word}%"]
            if memory_type:
                sql += " AND memory_type = ?"
                params.append(memory_type)
            sql += " ORDER BY importance DESC, created_at DESC LIMIT ?"
            params.append(limit)

            async with self._db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    item = MemoryItem.from_db_row(dict(row))
                    if item.id not in [r.id for r in results]:
                        results.append(item)

        # 2. 内容全文搜索补充
        if len(results) < limit:
            for word in query_words:
                if len(word) < 2: continue
                remaining = limit - len(results)
                sql = "SELECT * FROM memories WHERE content LIKE ?"
                params = [f"%{word}%"]
                if memory_type:
                    sql += " AND memory_type = ?"
                    params.append(memory_type)
                sql += " ORDER BY importance DESC LIMIT ?"
                params.append(remaining)

                async with self._db.execute(sql, params) as cursor:
                    rows = await cursor.fetchall()
                    for row in rows:
                        item = MemoryItem.from_db_row(dict(row))
                        if item.id not in [r.id for r in results]:
                            results.append(item)

        # 更新访问计数
        now = datetime.now().isoformat()
        for item in results:
            if item.id:
                await self._db.execute(
                    "UPDATE memories SET last_accessed=?, access_count=access_count+1 WHERE id=?",
                    (now, item.id),
                )
        if results:
            await self._db.commit()

        return results[:limit]

    async def get_recent_memories(self, limit: int = 10) -> list[MemoryItem]:
        async with self._db.execute(
            "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?", (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [MemoryItem.from_db_row(dict(row)) for row in rows]

    async def get_important_memories(self, limit: int = 10) -> list[MemoryItem]:
        async with self._db.execute(
            "SELECT * FROM memories ORDER BY importance DESC, access_count DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [MemoryItem.from_db_row(dict(row)) for row in rows]

    # ============ 对话历史 ============

    async def save_conversation(self, msg: ConversationMessage):
        await self._db.execute("""
            INSERT INTO conversations
            (session_id, role, content, emotion, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (msg.session_id, msg.role, msg.content, msg.emotion, msg.timestamp))
        await self._db.commit()

    async def get_conversation_count(self) -> int:
        async with self._db.execute(
            "SELECT COUNT(*) as cnt FROM conversations"
        ) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    async def get_memory_count(self) -> int:
        async with self._db.execute(
            "SELECT COUNT(*) as cnt FROM memories"
        ) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    # ============ 工具方法 ============

    def _extract_keywords(self, text: str) -> list[str]:
        """简单的中文关键词提取"""
        stop_words = {
            "的", "了", "在", "是", "我", "有", "和",
            "就", "不", "人", "都", "一", "一个", "上",
            "也", "很", "到", "说", "要", "去", "你",
            "会", "着", "没有", "看", "好", "自己", "这",
            "他", "她", "它", "吗", "吧", "呢", "啊",
            "哦", "嗯", "呀", "哈", "嘿", "喂", "哎",
            "那", "什么", "怎么", "为什么", "可以",
            "但是", "因为", "所以", "如果", "虽然",
        }
        words = []
        segments = re.split(r'[，。！？、；：\s,\.!?\;\:\n]+', text)
        for seg in segments:
            seg = seg.strip()
            if len(seg) >= 2 and seg not in stop_words:
                words.append(seg)
            if len(seg) >= 4:
                for i in range(len(seg) - 1):
                    for j in range(2, min(5, len(seg) - i + 1)):
                        sub = seg[i:i+j]
                        if sub not in stop_words and len(sub) >= 2:
                            words.append(sub)
        seen = set()
        unique = []
        for w in words:
            if w not in seen:
                seen.add(w)
                unique.append(w)
        return unique[:15]
