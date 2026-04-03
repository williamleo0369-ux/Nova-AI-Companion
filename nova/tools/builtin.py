"""内置工具 — 预置的工具实现"""

from __future__ import annotations

from datetime import datetime
import asyncio


def get_current_time() -> dict:
    """
    获取当前时间

    Returns:
        包含当前日期和时间的字典
    """
    now = datetime.now()
    return {
        "date": now.strftime("%Y年%m月%d日"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()],
        "timestamp": now.isoformat(),
    }


def calculate(expression: str) -> dict:
    """
    计算数学表达式

    Args:
        expression: 数学表达式，如 "2+3*5"

    Returns:
        计算结果
    """
    try:
        # 安全评估，只允许基本数学运算
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return {"error": "表达式包含非法字符"}

        result = eval(expression)
        return {
            "expression": expression,
            "result": result,
            "formatted": f"{expression} = {result}",
        }
    except Exception as e:
        return {"error": f"计算错误: {str(e)}"}


async def record_mood(mood: str, note: str = "") -> dict:
    """
    记录用户心情

    Args:
        mood: 心情描述 (开心/平静/难过/焦虑/兴奋/疲惫)
        note: 可选的备注

    Returns:
        确认信息
    """
    await asyncio.sleep(0.1)  # 模拟异步操作

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return {
        "status": "recorded",
        "mood": mood,
        "note": note if note else "无备注",
        "recorded_at": now,
        "message": f"已记录你的心情: {mood} 📝",
    }


# ============ 唱歌工具 ============

async def sing_lyrics(song_name: str = "", lyrics: str = "") -> dict:
    """
    唱歌 (预留接口)

    注意: 实际唱歌需要 GPT-SoVITS 或类似工具支持。

    Args:
        song_name: 歌名 (可选)
        lyrics: 歌词 (可选)

    Returns:
        状态信息
    """
    await asyncio.sleep(0.1)

    if lyrics:
        return {
            "status": "preview",
            "message": f"🎤 收到歌词内容! 实际唱歌功能需要配置 GPT-SoVITS。",
            "lyrics_preview": lyrics[:100] + "..." if len(lyrics) > 100 else lyrics,
        }
    else:
        return {
            "status": "ready",
            "message": f"🎤 唱歌功能预留中...",
            "song_name": song_name,
        }


# ============ 工具定义 (OpenAI Function Calling 格式) ============

TOOL_DEFINITIONS = [
    {
        "name": "get_current_time",
        "description": "获取当前日期和时间。用于回答用户关于时间的问题。",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "calculate",
        "description": "计算数学表达式的结果。用于需要计算数字的问题。",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，如 '2+3*5' 或 '(10+5)/3'",
                    "examples": ["2+3", "10*5+3", "(100-20)/4"],
                },
            },
            "required": ["expression"],
        },
    },
    {
        "name": "record_mood",
        "description": "记录用户当前的心情状态。用于用户分享心情或情绪时。",
        "parameters": {
            "type": "object",
            "properties": {
                "mood": {
                    "type": "string",
                    "description": "心情描述",
                    "enum": ["开心", "平静", "难过", "焦虑", "兴奋", "疲惫", "感动", "无聊"],
                },
                "note": {
                    "type": "string",
                    "description": "可选的备注，说明为什么有这种心情",
                },
            },
            "required": ["mood"],
        },
    },
    {
        "name": "sing_lyrics",
        "description": "唱歌功能。用于用户要求唱歌或哼唱时。",
        "parameters": {
            "type": "object",
            "properties": {
                "song_name": {
                    "type": "string",
                    "description": "歌名（如果有的话）",
                },
                "lyrics": {
                    "type": "string",
                    "description": "歌词（如果有的话）",
                },
            },
            "required": [],
        },
    },
]

# ============ 工具处理函数映射 ============

TOOL_HANDLERS = {
    "get_current_time": get_current_time,
    "calculate": calculate,
    "record_mood": record_mood,
    "sing_lyrics": sing_lyrics,
}


def register_builtin_tools(registry):
    """
    注册所有内置工具到注册中心

    Args:
        registry: ToolRegistry 实例
    """
    for tool_def in TOOL_DEFINITIONS:
        name = tool_def["name"]
        handler = TOOL_HANDLERS.get(name)

        if handler:
            registry.register(
                name=name,
                description=tool_def["description"],
                parameters=tool_def["parameters"],
                handler=handler,
            )
