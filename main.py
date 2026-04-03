#!/usr/bin/env python3
"""
Nova AI Companion - 主程序入口

一个有记忆、有情感、有温度的 AI 伴侣。
"""

import asyncio
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from loguru import logger

from nova import (
    Nova,
    LLMClient,
    MemoryManager,
    EmotionEngine,
    VoiceManager,
    ToolRegistry,
    PromptBuilder,
)
from nova.tools.builtin import register_builtin_tools


def setup_logging():
    """配置日志"""
    # 创建日志目录
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # 移除默认的 logger 配置
    logger.remove()

    # 添加控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>",
        level="INFO",
        colorize=True,
    )

    # 添加文件输出
    logger.add(
        log_dir / "nova_{time}.log",
        rotation="1 day",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="DEBUG",
    )


def load_config() -> dict:
    """加载配置文件"""
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


async def create_nova() -> Nova:
    """
    创建并初始化 Nova 实例

    Returns:
        初始化的 Nova 实例
    """
    # 加载环境变量
    load_dotenv()

    # 配置日志
    setup_logging()

    logger.info("🌟 正在启动 Nova AI Companion...")

    # 加载配置
    config = load_config()
    nova_config = config.get("nova", {})
    llm_config = config.get("llm", {})
    memory_config = config.get("memory", {})
    emotion_config = config.get("emotion", {})
    voice_config = config.get("voice", {})

    # 检查 LLM 配置
    if not os.getenv("LLM_API_KEY"):
        logger.error("❌ 请设置 LLM_API_KEY 环境变量")
        logger.info("💡 复制 .env.example 为 .env 并填入您的 API Key")
        sys.exit(1)

    # 创建各组件
    llm_client = LLMClient(
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
        model=os.getenv("LLM_MODEL"),
    )

    memory_manager = MemoryManager(
        db_path=memory_config.get("db_path", "data/nova_memory.db"),
        short_term_rounds=memory_config.get("short_term_rounds", 20),
        extraction_interval=memory_config.get("extraction_interval", 3),
    )

    emotion_engine = EmotionEngine(
        decay_rate=emotion_config.get("decay_rate", 0.15),
        significance_threshold=emotion_config.get("significance_threshold", 0.4),
    )

    voice_manager = VoiceManager(
        enabled=voice_config.get("enabled", False) or os.getenv("VOICE_ENABLED", "").lower() == "true",
        edge_voice=voice_config.get("edge_voice", "zh-CN-XiaoyiNeural"),
        edge_rate=voice_config.get("edge_rate", "+5%"),
        edge_pitch=voice_config.get("edge_pitch", "+2Hz"),
        output_dir=voice_config.get("output_dir", "data/output/voice"),
    )

    tool_registry = ToolRegistry()
    register_builtin_tools(tool_registry)

    prompt_builder = PromptBuilder()

    # 创建 Nova 实例
    nova = Nova(
        llm_client=llm_client,
        memory_manager=memory_manager,
        emotion_engine=emotion_engine,
        voice_manager=voice_manager,
        tool_registry=tool_registry,
        prompt_builder=prompt_builder,
    )

    # 初始化
    await nova.initialize()

    return nova


async def print_welcome():
    """打印欢迎信息"""
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║     🌟  Nova AI Companion  🌟                            ║
║                                                          ║
║     有记忆 · 有情感 · 有温度                              ║
║                                                          ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  欢迎回来！我是 Nova，你的 AI 伴侣。                      ║
║                                                          ║
║  我会记住你说的话，理解你的心情，                        ║
║  用温暖的方式陪伴你。                                    ║
║                                                          ║
║  输入你的消息开始对话                                     ║
║  输入 /help 查看帮助                                      ║
║  输入 /reset 重置对话                                     ║
║  输入 /status 查看状态                                    ║
║  输入 /quit 退出                                          ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)


async def print_help():
    """打印帮助信息"""
    print("""
╔══════════════════════════════════════════════════════════╗
║                        帮助信息                           ║
╠══════════════════════════════════════════════════════════╣
║  /help     - 显示帮助信息                                ║
║  /reset    - 重置对话，开始新的会话                       ║
║  /status   - 查看 Nova 的当前状态                        ║
║  /profile  - 查看已知的用户信息                           ║
║  /memories - 查看 Nova 记住的重要事情                    ║
║  /tools    - 查看可用工具                                 ║
║  /voice    - 切换语音模式                                 ║
║  /quit     - 退出程序                                     ║
╚══════════════════════════════════════════════════════════╝
    """)


async def run_interactive(nova: Nova):
    """
    运行交互式对话

    Args:
        nova: Nova 实例
    """
    await print_welcome()

    while True:
        try:
            user_input = input("\n👤 你: ").strip()

            if not user_input:
                continue

            # 处理命令
            if user_input.startswith("/"):
                cmd = user_input.lower()

                if cmd == "/quit" or cmd == "/exit":
                    print("\n👋 再见！下次见~")
                    break

                elif cmd == "/help":
                    await print_help()
                    continue

                elif cmd == "/reset":
                    await nova.reset_conversation()
                    print("🔄 对话已重置，开始新的会话吧！")
                    continue

                elif cmd == "/status":
                    status = nova.get_status()
                    print(f"""
📊 Nova 状态:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 记忆: {status['memory']['short_term_count']} 条短期记忆
👤 用户: {status['memory']['user_profile']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💕 心情: {status['emotion']['mood']}
🌡️ 温暖度: {status['emotion']['warmth']:.1%}
💗 关心度: {status['emotion']['concern']:.1%}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 工具: {', '.join(status['tools']['enabled']) if status['tools']['enabled'] else '无'}
🔊 语音: {'开启' if status['voice']['enabled'] else '关闭'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    """)
                    continue

                elif cmd == "/profile":
                    profile = nova.memory.user_profile
                    if profile.data:
                        print("\n👤 我知道的关于你的信息:")
                        for key, value in profile.data.items():
                            print(f"  • {key}: {value}")
                    else:
                        print("\n👤 我们刚认识，我还不了解你~")
                    continue

                elif cmd == "/memories":
                    memories = await nova.memory.long_term.get_recent_memories(limit=10)
                    if memories:
                        print("\n💭 我记住的重要事情:")
                        for m in memories:
                            print(f"  • [{m.memory_type}] {m.content}")
                    else:
                        print("\n💭 还没有记住什么特别的事情~")
                    continue

                elif cmd == "/tools":
                    tools = nova.tools.list_enabled_tools()
                    print(f"\n🔧 可用工具: {', '.join(tools) if tools else '无'}")
                    continue

                elif cmd == "/voice":
                    nova.voice.enabled = not nova.voice.enabled
                    print(f"\n🔊 语音模式: {'开启' if nova.voice.enabled else '关闭'}")
                    continue

                else:
                    print(f"❓ 未知命令: {user_input}")
                    print("💡 输入 /help 查看可用命令")
                    continue

            # 正常对话
            print("\n🤖 Nova: ", end="", flush=True)

            response = await nova.chat(user_input)

            # 打字效果
            for char in response:
                print(char, end="", flush=True)
                await asyncio.sleep(0.01)  # 轻微延迟模拟打字

            print()  # 换行

        except KeyboardInterrupt:
            print("\n\n👋 再见！下次见~")
            break
        except Exception as e:
            logger.error(f"错误: {e}")
            print(f"\n❌ 出错了: {e}")


async def main():
    """主函数"""
    nova = None
    try:
        nova = await create_nova()
        await run_interactive(nova)
    except KeyboardInterrupt:
        print("\n\n👋 再见！")
    except Exception as e:
        logger.error(f"启动失败: {e}")
        print(f"❌ 启动失败: {e}")
        sys.exit(1)
    finally:
        if nova:
            await nova.close()


if __name__ == "__main__":
    asyncio.run(main())
