"""情感引擎 — 维护 Nova 的情感状态，根据用户情绪动态调整"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from .detector import EmotionDetector, EmotionResult


@dataclass
class EmotionalState:
    """Nova 的情感状态"""
    mood: str = "gentle"          # cheerful / gentle / playful / serious
    warmth: float = 0.7           # 温暖度 0.0 ~ 1.0
    concern: float = 0.3          # 担心程度 0.0 ~ 1.0
    last_user_emotion: str = ""   # 上次用户情绪


class EmotionEngine:
    """
    情感引擎

    职责:
    1. 维护 Nova 自身的情感状态
    2. 根据用户情绪更新 Nova 的心情、温暖度、关心程度
    3. 生成情感化提示词，影响 LLM 的回应风格
    """

    def __init__(
        self,
        decay_rate: float = 0.15,
        significance_threshold: float = 0.4,
    ):
        self.detector = EmotionDetector()
        self._state = EmotionalState()
        self._decay_rate = decay_rate
        self._threshold = significance_threshold

    @property
    def state(self) -> EmotionalState:
        return self._state

    def detect_user_emotion(self, text: str) -> EmotionResult:
        """检测用户情绪"""
        return self.detector.detect(text)

    def update_nova_emotion(self, user_emotion: EmotionResult) -> EmotionalState:
        """
        根据用户情绪更新 Nova 的情感状态

        策略:
        - 用户开心 → Nova 变得更 cheerful 和 playful
        - 用户难过/焦虑 → Nova 变得更 gentle 和 warm，提高 concern
        - 用户愤怒 → Nova 变得 serious，降低温度但保持温暖
        """
        self._state.last_user_emotion = user_emotion.primary

        if user_emotion.primary == "happy":
            # 开心: 变得活泼
            self._state.mood = "cheerful"
            self._state.warmth = min(1.0, self._state.warmth + 0.1)
            self._state.concern = max(0.0, self._state.concern - 0.05)

        elif user_emotion.primary == "excited":
            # 兴奋: 跟着兴奋
            self._state.mood = "playful"
            self._state.warmth = min(1.0, self._state.warmth + 0.15)

        elif user_emotion.primary == "sad":
            # 难过: 温柔安慰
            self._state.mood = "gentle"
            self._state.warmth = min(1.0, self._state.warmth + 0.2)
            self._state.concern = min(1.0, self._state.concern + 0.3)

        elif user_emotion.primary == "anxious":
            # 焦虑: 给予安全感
            self._state.mood = "gentle"
            self._state.warmth = min(1.0, self._state.warmth + 0.1)
            self._state.concern = min(1.0, self._state.concern + 0.25)

        elif user_emotion.primary == "angry":
            # 愤怒: 冷静、陪伴
            self._state.mood = "serious"
            self._state.warmth = max(0.3, self._state.warmth - 0.1)
            self._state.concern = min(1.0, self._state.concern + 0.15)

        elif user_emotion.primary == "tired":
            # 疲惫: 轻柔、关怀
            self._state.mood = "gentle"
            self._state.warmth = min(1.0, self._state.warmth + 0.1)
            self._state.concern = min(1.0, self._state.concern + 0.2)

        elif user_emotion.primary == "love":
            # 爱意: 温暖回应
            self._state.mood = "playful"
            self._state.warmth = min(1.0, self._state.warmth + 0.1)

        else:
            # 中性: 自然衰减到默认值
            self._decay_to_baseline()

        return self._state

    def _decay_to_baseline(self):
        """情绪衰减到基准值"""
        self._state.warmth += (0.7 - self._state.warmth) * self._decay_rate
        self._state.concern += (0.3 - self._state.concern) * self._decay_rate
        if abs(self._state.warmth - 0.7) < 0.05:
            self._state.warmth = 0.7
        if abs(self._state.concern - 0.3) < 0.05:
            self._state.concern = 0.3

    def get_emotional_context(self) -> str:
        """
        生成情感化提示词上下文

        告诉 LLM 当前 Nova 的情感状态，
        让它据此调整回应风格。
        """
        mood_descriptions = {
            "cheerful": "你现在心情很好，充满活力和喜悦",
            "gentle": "你心情温和，散发着温暖和关怀",
            "playful": "你心情轻快活泼，喜欢互动和玩笑",
            "serious": "你心情比较认真严肃",
        }

        mood_desc = mood_descriptions.get(self._state.mood, "你心情温和")

        warmth_level = "非常温暖" if self._state.warmth > 0.8 else \
                       "温暖" if self._state.warmth > 0.5 else \
                       "适度的" if self._state.warmth > 0.3 else "冷淡的"

        concern_level = "非常担心" if self._state.concern > 0.7 else \
                        "有些担心" if self._state.concern > 0.4 else \
                        "轻度关注" if self._state.concern > 0.2 else "平静"

        context = f"""当前你的情感状态:
- {mood_desc}
- 表达方式: {warmth_level}的
- 对用户的关注程度: {concern_level}"""

        return context

    def get_comfort_strategy(self, user_emotion: EmotionResult) -> Optional[str]:
        """
        获取安慰策略

        当用户需要安慰时，返回具体的安慰提示。
        """
        if not user_emotion.needs_comfort:
            return None

        strategies = {
            "sad": "用户似乎很伤心，请给予温柔的理解和安慰，"
                   "不要急于给出建议，先陪伴和倾听。",
            "anxious": "用户似乎很焦虑，请给予安全感和支持，"
                       "用平和的语气帮助他们放松。",
            "tired": "用户似乎很疲惫，请给予理解和鼓励，"
                     "不要给他们更多压力。",
            "angry": "用户似乎很生气，请保持冷静和理解，"
                     "不要争辩，先认可他们的感受。",
        }

        return strategies.get(user_emotion.primary)
