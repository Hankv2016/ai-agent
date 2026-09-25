# client.py
import os
from openai import OpenAI


def load_env_file(path=".env"):
    """零依赖读取 .env 文件（KEY=VALUE），仅在对应环境变量尚未设置时填充。

    这样既能安全地把密钥留在被 .gitignore 忽略的 .env 中，
    又允许用户用系统环境变量覆盖。
    """
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


# 模块导入时即尝试加载 .env（仅填充缺失项）
load_env_file()


class AIClient:
    """通用 OpenAI 兼容客户端，可指向任意兼容端点"""

    DEFAULT_BASE_URL = "https://api.openai.com/v1"
    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(self, api_key=None, base_url=None, model=None, timeout=60):
        self.timeout = timeout
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = (
            base_url
            or os.environ.get("OPENAI_BASE_URL")
            or self.DEFAULT_BASE_URL
        ).rstrip("/")
        self.model = (
            model
            or os.environ.get("OPENAI_MODEL")
            or self.DEFAULT_MODEL
        )

        if not self.api_key:
            raise ValueError(
                "未找到 API Key。请设置环境变量 OPENAI_API_KEY，"
                "或在项目根目录创建 .env 文件（见 .env 示例），或通过参数传入 api_key。"
            )

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def _build_messages(self, prompt, history=None):
        messages = list(history) if history else []
        messages.append({"role": "user", "content": prompt})
        return messages

    def chat(self, prompt, timeout=None, history=None):
        """一次性返回完整回复文本（兼容 CLI 交互模式与单轮调用）。"""
        timeout = timeout or self.timeout
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(prompt, history),
            timeout=timeout,
        )
        return response.choices[0].message.content

    def stream_chat(self, prompt, timeout=None, history=None):
        """流式返回回复（生成器），每个元素是增量文本片段。

        配合 GUI 线程可在每次 yield 间检查中断；迭代结束（正常或异常）
        时都会尝试关闭底层连接。
        """
        timeout = timeout or self.timeout
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(prompt, history),
            stream=True,
            timeout=timeout,
        )
        try:
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
        finally:
            try:
                stream.close()
            except Exception:
                pass
