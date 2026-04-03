"""Nova 核心引擎 — 整合所有模块的主控制器"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional
from loguru import logger

from ..memory import MemoryManager
from ..emotion import EmotionEngine, EmotionResult
from ..voice import VoiceManager
from ..tools import ToolRegistry, Tool
from .llm import LLMClient
from ..prompts import PromptBuilder


class Nova:
    """
    Nova AI 伴侣 — 核心引擎

    整合记忆系统、情感引擎、语音系统和工具系统，
    提供统一的对话交互接口。
    """

    def __init__(
        self,
        llm_client: LLMClient,
        memory_manager: MemoryManager,
        emotion_engine: EmotionEngine,
        voice_manager: VoiceManager,
        tool_registry: ToolRegistry,
        prompt_builder: PromptBuilder,
    ):
        self.llm = llm_client
        self.memory = memory_manager
        self.emotion = emotion_engine
        self.voice = voice_manager
        self.tools = tool_registry
        self.prompts = prompt_builder

        # 设置记忆系统对 LLM 的引用
        self.memory.set_llm(llm_client)

        # 标记是否仍在处理
        self._processing = False

    async def initialize(self):
        """初始化所有子系统"""
        await self.memory.initialize()
        await self.voice.initialize()
        logger.info("🌟 Nova 初始化完成!")

    async def close(self):
        """关闭所有子系统"""
        await self.memory.close()
        await self.voice.close()
        await self.llm.close()
        logger.info("👋 Nova 已关闭")

    async def chat(self, user_message: str) -> str:
        """
        处理用户消息并生成回复

        Args:
            user_message: 用户输入的文本

        Returns:
            Nova 的回复文本
        """
        if self._processing:
            return "我还在思考中，请稍等..."

        self._processing = True
        try:
            # 1. 检测用户情绪
            emotion_result = self.emotion.detect_user_emotion(user_message)
            logger.debug(f"用户情绪: {emotion_result}")

            # 2. 更新 Nova 的情感状态
            self.emotion.update_nova_emotion(emotion_result)

            # 3. 保存用户消息到记忆
            await self.memory.add_user_message(
                user_message,
                emotion=emotion_result.primary,
            )

            # 4. 构建上下文和系统提示
            context = await self.memory.build_context(user_message)
            system_prompt = self.prompts.build_system_prompt(
                user_profile=context["user_profile"],
                memories=context["relevant_memories"],
                emotion_context=self.emotion.get_emotional_context(),
            )

            # 检查安慰策略
            comfort_strategy = self.emotion.get_comfort_strategy(emotion_result)
            if comfort_strategy:
                system_prompt += f"\n\n{comfort_strategy}"

            # 5. 构建消息历史
            messages = [
                {"role": "system", "content": system_prompt},
                *context["conversation_history"],
            ]

            # 6. 获取工具定义
            tool_schemas = self.tools.get_tool_schemas()

            # 7. 调用 LLM
            if tool_schemas:
                text_reply, func_data = await self.llm.complete_with_functions(
                    messages=messages,
                    tools=tool_schemas,
                )

                # 处理函数调用
                if func_data and "tool_calls" in func_data:
                    for tool_call in func_data["tool_calls"]:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["arguments"]

                        # 执行工具
                        tool_result = await self.tools.execute(tool_name, tool_args)

                        # 添加函数调用消息
                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": tool_call["id"],
                                "type": "function",
                                "function": {
                                    "name": tool_name,
                                    "arguments": json.dumps(tool_args),
                                },
                            }],
                        })

                        # 添加函数结果消息
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": json.dumps(tool_result),
                        })

                    # 再次调用 LLM 获取最终回复
                    final_reply = await self.llm.complete(
                        messages=messages,
                        temperature=0.85,
                        max_tokens=1024,
                    )
                else:
                    final_reply = text_reply
            else:
                final_reply = await self.llm.complete(
                    messages=messages,
                )

            if not final_reply:
                final_reply = "抱歉，我刚才走神了，能再说一遍吗？"

            # 8. 保存 Nova 的回复
            await self.memory.add_assistant_message(final_reply)

            # 9. 触发后台记忆提取
            await self.memory.maybe_extract_memories()

            # 10. 语音合成 (如果启用)
            if self.voice.enabled:
                asyncio.create_task(self.voice.speak(final_reply))

            return final_reply

        except Exception as e:
            logger.error(f"❌ 对话处理出错: {e}")
            return "抱歉，我遇到了一点问题，能再说一遍吗？"
        finally:
            self._processing = False

    async def reset_conversation(self):
        """
        重置对话

        清除短期记忆，开始新的会话。
        """
        from datetime import datetime
        self.memory.short_term.clear()
        self.memory.short_term.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info("🔄 对话已重置，开始新的会话")

    def get_status(self) -> dict[str, Any]:
        """
        获取 Nova 的状态信息

        Returns:
            包含状态信息的字典
        """
        return {
            "memory": {
                "short_term_count": len(self.memory.short_term),
                "user_profile": self.memory.user_profile.summary(),
            },
            "emotion": {
                "mood": self.emotion.state.mood,
                "warmth": self.emotion.state.warmth,
                "concern": self.emotion.state.concern,
            },
            "tools": {
                "enabled": self.tools.list_enabled_tools(),
            },
            "voice": {
                "enabled": self.voice.enabled,
            },
        }
