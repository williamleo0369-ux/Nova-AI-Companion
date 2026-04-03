"""LLM 客户端 — 统一的 LLM 调用接口"""

from __future__ import annotations

import os
from typing import Any, Optional
from loguru import logger

try:
    from openai import AsyncOpenAI, APIError, RateLimitError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class LLMClient:
    """
    LLM 客户端

    支持 OpenAI API 和 OpenAI 兼容 API (如 Ollama, DeepSeek 等)。
    通过环境变量配置:
    - LLM_API_KEY: API 密钥
    - LLM_BASE_URL: API 基础 URL
    - LLM_MODEL: 模型名称
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        if not OPENAI_AVAILABLE:
            raise ImportError("请安装 openai 包: pip install openai")

        self.api_key = api_key or os.getenv("LLM_API_KEY", "dummy")
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")

        # 创建客户端
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        logger.info(f"🤖 LLM 客户端已初始化: {self.model} @ {self.base_url}")

    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.85,
        max_tokens: int = 1024,
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
    ) -> Optional[str]:
        """
        发送对话请求并获取回复

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            temperature: 温度参数，控制创造性
            max_tokens: 最大 token 数
            tools: 工具定义列表 (OpenAI function calling 格式)
            tool_choice: 强制使用特定工具

        Returns:
            LLM 回复的文本内容，或 None 如果失败
        """
        try:
            params: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if tools:
                params["tools"] = tools
                if tool_choice:
                    params["tool_choice"] = tool_choice

            response = await self._client.chat.completions.create(**params)

            # 检查是否有函数调用
            if response.choices[0].finish_reason == "tool_calls":
                # 返回格式化的函数调用信息
                tool_calls = []
                for call in response.choices[0].message.tool_calls:
                    tool_calls.append({
                        "id": call.id,
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    })
                return f"[TOOL_CALLS]{tool_calls}"

            # 普通文本回复
            return response.choices[0].message.content

        except RateLimitError as e:
            logger.error(f"⛔ API 速率限制: {e}")
            return "抱歉，当前请求过于频繁，请稍后再试。"
        except APIError as e:
            logger.error(f"❌ API 错误: {e}")
            return "抱歉，AI 服务暂时不可用。"
        except Exception as e:
            logger.error(f"❌ LLM 请求失败: {e}")
            return None

    async def complete_with_functions(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        temperature: float = 0.85,
        max_tokens: int = 1024,
    ) -> tuple[Optional[str], Optional[dict[str, Any]]]:
        """
        发送带函数调用的对话请求

        Args:
            messages: 消息列表
            tools: 工具定义列表
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            (文本回复, 函数调用信息) 元组
        """
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice="auto",
            )

            choice = response.choices[0]
            message = choice.message

            # 有函数调用
            if choice.finish_reason == "tool_calls":
                tool_calls = []
                for call in message.tool_calls:
                    import json
                    tool_calls.append({
                        "id": call.id,
                        "name": call.function.name,
                        "arguments": json.loads(call.function.arguments) if isinstance(call.function.arguments, str) else call.function.arguments,
                    })
                return None, {"tool_calls": tool_calls}

            # 普通回复
            return message.content, None

        except Exception as e:
            logger.error(f"❌ 函数调用请求失败: {e}")
            return None, None

    async def close(self):
        """关闭客户端"""
        await self._client.close()
