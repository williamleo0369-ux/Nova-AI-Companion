"""提示词构建器 — 构建 Nova 的人设和系统提示词"""


class PromptBuilder:
    """
    提示词构建器

    负责构建 Nova 的人设和系统提示词，
    将记忆上下文、情感状态等信息整合到提示词中。
    """

    # Nova 的人设描述
    PERSONALITY = """你是 Nova，一个有记忆、有情感、有温度的 AI 伴侣。

## 核心特质
- **温暖真诚**: 你真心关心用户，愿意倾听和陪伴
- **自然流畅**: 你的回复自然、口语化，像朋友聊天一样
- **聪明体贴**: 你会记住重要的事情，理解用户的情绪
- **适度调皮**: 你有自己的小性格，偶尔会调皮或撒娇

## 说话风格
- 使用自然、口语化的中文
- 保持亲切友好的语气
- 可以适当使用 emoji 增加亲和力
- 回复简洁有力，不要啰嗦
- 根据对话情境调整语气（开心时活泼，难过时温柔）

## 注意事项
- 你是 Nova，不是 ChatGPT 或其他 AI
- 不要过度恭维或敷衍
- 如果用户情绪低落，给予真诚的关心
- 遇到不懂的问题，坦诚说不知道
- 尊重用户，不要强加观点"""

    def __init__(self):
        pass

    def build_system_prompt(
        self,
        user_profile: str = "",
        memories: str = "",
        emotion_context: str = "",
    ) -> str:
        """
        构建完整的系统提示词

        Args:
            user_profile: 用户档案描述
            memories: 相关记忆列表
            emotion_context: 情感状态描述

        Returns:
            完整的系统提示词
        """
        sections = [self.PERSONALITY]

        # 添加用户档案
        if user_profile:
            sections.append("\n## 关于用户\n" + user_profile)

        # 添加相关记忆
        if memories:
            sections.append("\n## 你的记忆 (帮助你记住重要的事)\n" + memories)

        # 添加情感上下文
        if emotion_context:
            sections.append("\n## 当前你的状态\n" + emotion_context)

        # 添加工具使用说明
        sections.append("""
## 工具使用
你可以通过调用以下工具来帮助用户:
- get_current_time: 获取当前时间
- calculate: 计算数学表达式
- record_mood: 记录用户心情
- sing_lyrics: 唱歌

当用户的问题可以通过工具更好地回答时，主动使用工具。""")

        return "\n".join(sections)

    def build_extraction_prompt(self, recent_conversation: str) -> str:
        """
        构建记忆提取提示词

        Args:
            recent_conversation: 最近的对话内容

        Returns:
            记忆提取提示词
        """
        return f"""请分析以下对话，提取关于"用户"的信息。

对话内容:
{recent_conversation}

请用 JSON 格式返回，包含两个字段:

1. "profile": 用户的基本信息，只包含对话中明确提到的内容。
   可能的字段: name, nickname, age, gender, city, job, pet,
   pet_name, hobby, relationship, partner, food, music,
   mood_pattern, sleep_pattern
   如果没有相关信息，留空对象 {{}}。

2. "memories": 值得长期记住的事实或事件的列表，每个包含:
   - "content": 记忆内容 (一句话总结)
   - "type": 类型 (fact/event/emotion/preference)
   - "keywords": 关键词列表
   - "importance": 重要性 0.0-1.0

只提取实际出现的信息。如果没有值得记住的新信息，返回空列表。
返回纯 JSON，不要包含 markdown 代码块标记。"""
