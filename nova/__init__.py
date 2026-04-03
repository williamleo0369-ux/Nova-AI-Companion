"""Nova AI Companion - 有记忆、有情感、有温度的 AI 伴侣"""

from .core import LLMClient, Nova
from .memory import MemoryManager
from .emotion import EmotionEngine
from .voice import VoiceManager
from .tools import ToolRegistry
from .prompts import PromptBuilder

__version__ = "0.1.0"
__all__ = [
    "LLMClient",
    "Nova",
    "MemoryManager",
    "EmotionEngine",
    "VoiceManager",
    "ToolRegistry",
    "PromptBuilder",
]
