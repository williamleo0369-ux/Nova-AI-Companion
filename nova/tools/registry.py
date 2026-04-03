"""工具注册中心 — 管理所有可用工具"""

from __future__ import annotations

from typing import Any, Callable, Optional
from loguru import logger
from dataclasses import dataclass, field


@dataclass
class Tool:
    """工具定义"""
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Any]
    enabled: bool = True


class ToolRegistry:
    """
    工具注册中心

    管理所有可用工具，支持 OpenAI Function Calling 格式。
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._enabled_tools: list[str] = []

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: Callable[..., Any],
        enabled: bool = True,
    ):
        """
        注册一个工具

        Args:
            name: 工具名称
            description: 工具描述
            parameters: OpenAI function calling 格式的参数定义
            handler: 处理函数
            enabled: 是否启用
        """
        tool = Tool(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            enabled=enabled,
        )
        self._tools[name] = tool

        if enabled:
            self._enabled_tools.append(name)

        logger.debug(f"🔧 工具已注册: {name}")

    def unregister(self, name: str):
        """取消注册工具"""
        if name in self._tools:
            del self._tools[name]
        if name in self._enabled_tools:
            self._enabled_tools.remove(name)

    def enable(self, name: str):
        """启用工具"""
        if name in self._tools and not self._tools[name].enabled:
            self._tools[name].enabled = True
            if name not in self._enabled_tools:
                self._enabled_tools.append(name)

    def disable(self, name: str):
        """禁用工具"""
        if name in self._tools:
            self._tools[name].enabled = False
            if name in self._enabled_tools:
                self._enabled_tools.remove(name)

    def get_tool(self, name: str) -> Optional[Tool]:
        """获取工具定义"""
        return self._tools.get(name)

    def get_enabled_tools(self) -> list[Tool]:
        """获取所有已启用的工具"""
        return [self._tools[name] for name in self._enabled_tools if name in self._tools]

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """
        获取所有工具的 OpenAI Function Calling 格式定义

        用于 LLM 的 function_call 参数。
        """
        schemas = []
        for tool in self.get_enabled_tools():
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            })
        return schemas

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """
        执行工具

        Args:
            name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        tool = self.get_tool(name)
        if not tool:
            return {"error": f"工具 {name} 不存在"}

        if not tool.enabled:
            return {"error": f"工具 {name} 已禁用"}

        try:
            # 调用处理函数
            result = tool.handler(**arguments)

            # 如果是异步函数，等待结果
            import asyncio
            if asyncio.iscoroutine(result):
                result = await result

            return result

        except Exception as e:
            logger.error(f"工具执行失败 [{name}]: {e}")
            return {"error": str(e)}

    def list_tools(self) -> list[str]:
        """列出所有工具名称"""
        return list(self._tools.keys())

    def list_enabled_tools(self) -> list[str]:
        """列出所有已启用的工具名称"""
        return self._enabled_tools.copy()
