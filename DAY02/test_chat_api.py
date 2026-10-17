"""
W1 Day2 · 合并动作：给 LLM 接口写第一个 pytest 测试
---------------------------------------------------------------
这一个文件同时服务两条线：
  · AI 应用开发线 —— 建立"给代码写测试"的意识
  · 软件测试线   —— 接口自动化的第一个真实用例

运行：pytest test_chat_api.py -v
依赖：pip install pytest httpx python-dotenv
"""
import os
import time

import httpx
import pytest
from dotenv import load_dotenv

load_dotenv()

BASE_URL = (os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("MODEL", "deepseek-flash")
URL = f"{BASE_URL}/chat/completions"

# 没配置 key 时整体跳过，避免满屏红
pytestmark = pytest.mark.skipif(
    not API_KEY, reason="未配置 OPENAI_API_KEY，跳过接口测试"
)


def make_payload(question: str, **kwargs) -> dict:
    """构造请求体——这就是"接口测试参数化"的最小形态。"""
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": question}],
        "temperature": 0.3,
    }
    body.update(kwargs)
    return body


@pytest.fixture(scope="module")
def client():
    headers = {"Authorization": f"Bearer {API_KEY}"}
    with httpx.Client(timeout=60, headers=headers) as c:
        yield c


class TestChatAPI:
    """按「正向 / 异常 / 结构 / 性能」四类组织——和测试岗的用例分类思路一致。"""

    # ---------- 正向用例 ----------
    def test_正常请求返回200且回答非空(self, client):
        resp = client.post(URL, json=make_payload("1+1 等于几？只回答数字"))
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["choices"][0]["message"]["content"].strip()

    # ---------- 结构断言 ----------
    def test_响应结构完整(self, client):
        data = client.post(URL, json=make_payload("说一句话")).json()
        message = data["choices"][0]["message"]
        assert message["role"] == "assistant"
        assert isinstance(message["content"], str)
        assert "usage" in data, "响应里应包含 usage 字段"

    # ---------- 异常用例：错误 key ----------
    def test_错误key被拒绝(self):
        resp = httpx.post(
            URL,
            headers={"Authorization": "Bearer sk-this-key-is-invalid"},
            json=make_payload("hi"),
            timeout=30,
        )
        # 401 或 403 都算正确。注意：这类错误**不该重试**
        assert resp.status_code in (401, 403), f"实际 {resp.status_code}"

    # ---------- 异常用例：非法模型名 ----------
    def test_非法模型名返回4xx(self, client):
        resp = client.post(
            URL,
            json={**make_payload("hi"), "model": "this-model-does-not-exist"},
        )
        assert 400 <= resp.status_code < 500, f"实际 {resp.status_code}"

    # ---------- 性能用例：响应时间 ----------
    def test_非流式请求响应时间在阈值内(self, client):
        start = time.perf_counter()
        client.post(URL, json=make_payload("说一句话"))
        elapsed = time.perf_counter() - start
        print(f"\n响应耗时：{elapsed:.2f}s")
        assert elapsed < 60, f"太慢了：{elapsed:.2f}s"
