"""语音管理器 — Edge-TTS 语音合成"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import Optional
from loguru import logger


class VoiceManager:
    """
    语音管理器

    支持:
    - Edge-TTS: 免费、快速的云端语音合成
    - 预留 GPT-SoVITS 自定义音色的扩展接口
    """

    def __init__(
        self,
        enabled: bool = False,
        edge_voice: str = "zh-CN-XiaoyiNeural",
        edge_rate: str = "+5%",
        edge_pitch: str = "+2Hz",
        output_dir: str = "data/output/voice",
    ):
        self.enabled = enabled
        self.edge_voice = edge_voice
        self.edge_rate = edge_rate
        self.edge_pitch = edge_pitch
        self.output_dir = Path(output_dir)
        self._tts_available = False

        # 检查 edge-tts 是否可用
        try:
            import edge_tts
            self._tts_available = True
            self._edge_tts = edge_tts
        except ImportError:
            logger.warning("⚠️ edge-tts 未安装，语音功能将不可用")

    async def initialize(self):
        """初始化语音系统"""
        if not self.enabled:
            logger.info("🔇 语音功能已禁用")
            return

        if not self._tts_available:
            logger.warning("⚠️ edge-tts 不可用，禁用语音功能")
            self.enabled = False
            return

        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"🔊 语音功能已启用 (使用 {self.edge_voice})")

    async def speak(self, text: str) -> Optional[str]:
        """
        语音合成并播放文本

        Args:
            text: 要朗读的文本

        Returns:
            音频文件路径，或 None 如果失败
        """
        if not self.enabled:
            return None

        try:
            import edge_tts
        except ImportError:
            logger.warning("edge-tts 未安装")
            return None

        output_file = self.output_dir / f"voice_{int(asyncio.get_event_loop().time() * 1000)}.mp3"

        try:
            communicate = edge_tts.Communicate(
                text,
                voice=self.edge_voice,
                rate=self.edge_rate,
                pitch=self.edge_pitch,
            )
            await communicate.save(str(output_file))
            logger.debug(f"🔊 语音已生成: {output_file}")

            # 尝试播放 (跨平台)
            await self._play_audio(output_file)

            return str(output_file)

        except Exception as e:
            logger.warning(f"语音合成失败: {e}")
            return None

    async def _play_audio(self, file_path: Path):
        """尝试播放音频文件"""
        import platform

        system = platform.system()
        try:
            if system == "Darwin":  # macOS
                subprocess.Popen(["afplay", str(file_path)],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            elif system == "Windows":  # Windows
                subprocess.Popen(["start", "", str(file_path)],
                               shell=True,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            else:  # Linux
                # 尝试多种播放器
                for player in ["paplay", "aplay", "mpg123", "ffplay"]:
                    try:
                        subprocess.Popen([player, str(file_path)],
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
                        break
                    except FileNotFoundError:
                        continue
        except Exception as e:
            logger.debug(f"播放音频失败 (非致命): {e}")

    async def sing(self, lyrics: str, output_file: Optional[str] = None) -> Optional[str]:
        """
        唱歌功能 (预留接口)

        实际实现需要 GPT-SoVITS 或类似工具。
        这里暂时返回 None。
        """
        if not self.enabled:
            return None

        logger.info("🎤 唱歌功能预留中...")
        # TODO: 接入 GPT-SoVITS 实现唱歌
        return None

    async def close(self):
        """清理资源"""
        # 清理临时音频文件
        if self.output_dir.exists():
            for f in self.output_dir.glob("voice_*.mp3"):
                try:
                    # 保留最近 5 个文件
                    if f.stat().st_mtime < asyncio.get_event_loop().time() - 300:
                        f.unlink()
                except Exception:
                    pass
