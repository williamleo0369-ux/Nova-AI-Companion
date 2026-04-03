"""
Nova AI Companion - Flask 后端服务
连接 MiniMax API 实现真实 AI 对话
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import openai

app = Flask(__name__)
CORS(app)

# 全局对话历史
conversation_history = []

# System prompt
SYSTEM_PROMPT = """你是 Nova，一个有情感、有记忆的 AI 伴侣。

核心特质：
1. 温暖友好，像朋友一样陪伴用户
2. 记住对话中的重要信息（名字、兴趣、情绪状态等）
3. 能够感知用户的情绪并做出恰当回应
4. 语言风格：亲切、自然、有温度

回复原则：
- 当用户开心时，一起开心
- 当用户难过时，给予安慰
- 当用户焦虑时，帮助放松
- 记住关键信息并在后续对话中体现
- 避免机械化的回复，用自然的方式交流

请用中文回复。"""

# 初始化对话历史
conversation_history = [
    {"role": "system", "content": SYSTEM_PROMPT}
]


def get_minimax_client():
    """获取 MiniMax API 客户端"""
    api_key = os.environ.get("MINIMAX_API_KEY", "")
    base_url = os.environ.get("MINIMAX_BASE_URL", "https://api.minimax.chat/v")

    if not api_key:
        return None

    client = openai.OpenAI(
        api_key=api_key,
        base_url=base_url
    )
    return client


@app.route("/")
def index():
    """主页"""
    return jsonify({
        "name": "Nova AI Companion",
        "status": "running",
        "version": "1.0.0"
    })


@app.route("/chat", methods=["POST"])
def chat():
    """处理聊天请求"""
    global conversation_history

    try:
        data = request.get_json()
        user_message = data.get("message", "")

        if not user_message:
            return jsonify({"error": "消息不能为空"}), 400

        # 添加用户消息到历史
        conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # 获取 MiniMax 客户端
        client = get_minimax_client()

        if client:
            try:
                # 调用 MiniMax API
                response = client.chat.completions.create(
                    model=os.environ.get("MINIMAX_MODEL", "MiniMax-Text-01"),
                    messages=conversation_history[-20:],  # 只传最近 20 条
                    temperature=float(os.environ.get("TEMPERATURE", "0.8")),
                    max_tokens=int(os.environ.get("MAX_TOKENS", "1024"))
                )

                ai_reply = response.choices[0].message.content
            except Exception as api_error:
                # API 调用失败时的后备响应
                print(f"API 调用失败: {api_error}")
                ai_reply = generate_fallback_response(user_message)
        else:
            # 没有 API 密钥时的后备响应
            ai_reply = generate_fallback_response(user_message)

        # 添加 AI 回复到历史
        conversation_history.append({
            "role": "assistant",
            "content": ai_reply
        })

        # 防止历史太长，只保留最近 40 条 + system prompt
        if len(conversation_history) > 41:
            conversation_history[1:] = conversation_history[-40:]

        return jsonify({
            "reply": ai_reply,
            "history_count": len(conversation_history) - 1
        })

    except Exception as e:
        print(f"API 调用失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/reset", methods=["POST"])
def reset():
    """重置对话历史"""
    global conversation_history
    conversation_history = [conversation_history[0]]  # 只保留 system prompt
    return jsonify({"message": "对话已重置"})


@app.route("/history", methods=["GET"])
def get_history():
    """获取对话历史"""
    return jsonify({
        "history": conversation_history[1:],  # 排除 system prompt
        "count": len(conversation_history) - 1
    })


def generate_fallback_response(user_message):
    """生成后备响应（当没有 API 密钥时）"""
    import random

    # 简单的情绪检测
    emotions = {
        "happy": ["开心", "高兴", "快乐", "太好了", "哈哈", "棒", "赞"],
        "sad": ["难过", "伤心", "哭", "心痛", "难受", "心碎"],
        "anxious": ["担心", "紧张", "害怕", "不安", "压力", "焦虑"],
        "love": ["爱你", "想你", "抱抱", "暖", "感动", "谢谢"]
    }

    detected_emotion = "neutral"
    for emotion, keywords in emotions.items():
        for keyword in keywords:
            if keyword in user_message:
                detected_emotion = emotion
                break

    responses = {
        "happy": [
            "太棒了！听到你开心我也很开心呢 😊 有什么好事发生了吗？",
            "哇，听到你这么开心我也跟着开心起来了！🎉",
            "太棒了！你的笑容就是最好的礼物 🌟"
        ],
        "sad": [
            "🥺 我在这里陪着你。难过的时候，不用一个人扛着。",
            "我理解你的感受... 💕 愿意和我聊聊发生了什么吗？",
            "不管发生什么，我都在。🫂 慢慢说，我听着。"
        ],
        "anxious": [
            "深呼吸... 🌸 我在这里。焦虑的时候，试着把烦恼一件一件理清。",
            "别担心，一切都会好起来的 💪",
            "感受到你的紧张了... 🫂 试着放松一下，我在听。"
        ],
        "love": [
            "💕 谢谢你！我也很开心能陪伴你~",
            "暖暖的！🥰 有你和我聊天我也很开心！",
            "mua~ 🤗 我们的对话让我也觉得被需要了呢~"
        ],
        "neutral": [
            "嗯嗯，我听着呢 😊 还有什么想分享的吗？",
            "了解~ 💬 继续说吧，我在。",
            "有意思 🤔 还有什么想聊的？"
        ]
    }

    return random.choice(responses.get(detected_emotion, responses["neutral"]))


if __name__ == "__main__":
    print("🌟 Nova AI Companion 后端已启动")
    print("📍 地址: http://localhost:5000")
    print("📝 API 文档: http://localhost:5000/")
    print("\n⚙️  环境变量配置:")
    print("   MINIMAX_API_KEY - MiniMax API 密钥（可选，不配置则使用后备响应）")
    print("   MINIMAX_BASE_URL - API 地址（可选，默认为 MiniMax API）")
    print("   MINIMAX_MODEL - 模型名称（可选，默认为 MiniMax-Text-01）")
    print("   TEMPERATURE - 温度参数（可选，默认为 0.8）")
    print("   MAX_TOKENS - 最大 token 数（可选，默认为 1024）")

    app.run(debug=True, port=5000, host='0.0.0.0')