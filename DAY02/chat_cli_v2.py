"""
W1 Day2 · 命令行问答脚本 v2：流式输出 + 错误重试 + 用量统计
---------------------------------------------------------------
相对 v1 的三处升级：
  1. 流式输出（stream=True）——AI 边想边吐字，不用等整段生成完
  2. 错误重试（指数退避）——遇到 429/超时自动重试，而不是直接挂
  3. 用量统计——每次结束打印 token 消耗，建立成本意识
运行：python chat_cli_v2.py
"""
import os
import sys
import time

from dotenv import load_dotenv
from openai import OpenAI

# 只有这些情况值得重试：限流 + 服务端抖动 + 超时
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def should_retry(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    if status is not None:
        return status in RETRYABLE_STATUS
    # 没有状态码的，多半是超时/连接断开 → 可重试
    name = type(exc).__name__.lower()
    return "timeout" in name or "connect" in name

load_dotenv()

API_KEY = os.environ.get("OPENAI_API_KEY")
BASE_URL = os.getenv("OPENAI_BASE_URL")
MODEL = os.getenv("MODEL", "deepseek-flash")   # 官方 DeepSeek 可用 deepseek-chat

SYSTEM_PROMPT = "你是一个简洁、准确的助手，回答不超过 200 字。"
MAX_RETRIES = 3


def build_client() -> OpenAI:
    if not API_KEY:
        sys.exit("❌ 没找到 OPENAI_API_KEY，请检查 .env")
    return OpenAI(api_key=API_KEY, base_url=BASE_URL or None)


def _create_stream(client: OpenAI, messages: list):
    """创建流式请求；顺便尝试开启用量回传（部分厂商不支持则降级）。"""
    kwargs = dict(
        model=MODEL,
        messages=messages,
        temperature=0.3,
        stream=True,
        stream_options={"include_usage": True},
    )
    try:
        return client.chat.completions.create(**kwargs)
    except Exception as e:
        # 有些兼容厂商不认识 stream_options，去掉再试一次
        if "stream_options" in str(e):
            kwargs.pop("stream_options")
            return client.chat.completions.create(**kwargs)
        raise


def ask_stream(client: OpenAI, question: str, history: list) -> str | None:
    """发一轮对话并把回答实时打印出来。失败时回滚本轮提问。"""
    history.append({"role": "user", "content": question})
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    buffer = ""
    usage = None
    stream = None

    # —— 指数退避重试：只重试"创建连接"阶段（429/超时多半发生在这里）——
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            stream = _create_stream(client, messages)
            break
        except Exception as e:
            if attempt == MAX_RETRIES or not should_retry(e):
                history.pop()
                print(f"\n[失败] {type(e).__name__}: {e}")
                return None
            wait = 2 ** (attempt - 1)
            print(f"\n[重试 {attempt}/{MAX_RETRIES}] {type(e).__name__}: {e}，{wait}s 后重试…")

    try:
        for chunk in stream:
            if getattr(chunk, "usage", None):
                usage = chunk.usage
            if chunk.choices and chunk.choices[0].delta.content:
                piece = chunk.choices[0].delta.content
                buffer += piece
                print(piece, end="", flush=True)
    except Exception as e:
        history.pop()
        print(f"\n[流式中断] {type(e).__name__}: {e}\n已收到 {len(buffer)} 字，请重新提问。")
        return None

    print()
    history.append({"role": "assistant", "content": buffer})
    if usage:
        print(f"[用量] prompt={usage.prompt_tokens} "
              f"completion={usage.completion_tokens} total={usage.total_tokens} tokens")
    return buffer


def main() -> None:
    client = build_client()
    print(f"模型：{MODEL}（流式模式）")
    print("输入问题后回车；输入 exit 退出。\n")

    history: list = []
    while True:
        try:
            question = input("你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见 👋")
            break
        if question.lower() in ("exit", "quit"):
            print("再见 👋")
            break
        if not question:
            continue

        print("AI> ", end="", flush=True)
        ask_stream(client, question, history)


if __name__ == "__main__":
    main()
