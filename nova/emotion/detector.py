"""情绪检测器 — 从用户消息中识别情绪"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class EmotionResult:
    """情绪检测结果"""
    primary: str          # 主要情绪
    intensity: float      # 强度 0.0 ~ 1.0
    valence: float        # 效价: -1.0(消极) ~ 1.0(积极)
    needs_comfort: bool   # 是否需要安慰

    def __str__(self) -> str:
        return f"{self.primary}(强度:{self.intensity:.1f})"


class EmotionDetector:
    """基于关键词的情绪检测 — 快速、无需API调用"""

    EMOTION_KEYWORDS: dict[str, dict] = {
        "happy": {
            "words": ["开心", "高兴", "快乐", "太好了", "哈哈",
                     "嘿嘿", "nice", "棒", "赞", "耶", "好耶",
                     "太棒了", "绝了", "爽", "终于", "成功",
                     "通过", "升职", "加薪", "录取", "表白成功",
                     "笑死", "乐", "美滋滋", "舒服", "满意"],
            "valence": 0.8, "intensity": 0.6,
        },
        "excited": {
            "words": ["兴奋", "激动", "天哪", "我靠", "卧槽",
                     "不敢相信", "太疯狂", "amazing", "wow",
                     "冲冲冲", "冲", "爆", "燃"],
            "valence": 0.9, "intensity": 0.8,
        },
        "sad": {
            "words": ["难过", "伤心", "哭", "泪", "心痛",
                     "失去", "分手", "离开", "想念", "怀念",
                     "再也不", "没了", "走了", "不在了", "去世",
                     "好难受", "心碎", "痛", "寂寞", "孤独",
                     "一个人", "好想哭", "emo", "丧", "抑郁",
                     "活着好累", "没意思", "不开心", "郁闷"],
            "valence": -0.8, "intensity": 0.7,
        },
        "angry": {
            "words": ["生气", "愤怒", "烦死", "气死", "受不了",
                     "恶心", "讨厌", "垃圾", "过分", "太过分",
                     "凭什么", "不公平", "憋屈", "窝火"],
            "valence": -0.7, "intensity": 0.8,
        },
        "anxious": {
            "words": ["焦虑", "担心", "紧张", "害怕", "恐惧",
                     "不安", "忐忑", "慌", "怎么办", "完了",
                     "来不及", "压力", "deadline", "ddl",
                     "救命", "崩溃", "撑不住", "好烦",
                     "睡不着", "失眠", "面试", "考试"],
            "valence": -0.5, "intensity": 0.7,
        },
        "tired": {
            "words": ["累", "疲惫", "困", "好困", "加班",
                     "熬夜", "通宵", "没睡", "不想动",
                     "躺平", "摆烂", "好倦", "想休息", "犯困"],
            "valence": -0.3, "intensity": 0.5,
        },
        "love": {
            "words": ["喜欢你", "爱你", "想你", "抱抱",
                     "亲亲", "么么", "❤", "♥", "好甜",
                     "暖", "感动", "谢谢你", "幸好有你",
                     "mua", "比心", "宝贝", "亲爱"],
            "valence": 0.9, "intensity": 0.7,
        },
        "neutral": {
            "words": [], "valence": 0.0, "intensity": 0.1,
        },
    }

    def detect(self, text: str) -> EmotionResult:
        text_lower = text.lower()
        scores: dict[str, float] = {}

        for emotion, config in self.EMOTION_KEYWORDS.items():
            if emotion == "neutral": continue
            score = 0.0
            for word in config["words"]:
                if word in text_lower:
                    score += 1.0
            exclamation_count = text.count("！") + text.count("!")
            score += exclamation_count * 0.3
            if "..." in text or "…" in text:
                if emotion in ("sad", "tired", "anxious"):
                    score += 0.5
            if score > 0:
                scores[emotion] = score

        if not scores:
            return EmotionResult(
                primary="neutral", intensity=0.1,
                valence=0.0, needs_comfort=False,
            )

        primary = max(scores, key=scores.get)
        config = self.EMOTION_KEYWORDS[primary]
        raw_intensity = min(scores[primary] / 3.0, 1.0)
        intensity = max(config["intensity"], raw_intensity)
        needs_comfort = config["valence"] < -0.3 and intensity > 0.4

        return EmotionResult(
            primary=primary, intensity=intensity,
            valence=config["valence"], needs_comfort=needs_comfort,
        )
