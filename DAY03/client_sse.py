"""
W1 Day3 · 客户端：消费 SSE 流
----------------------------------
这个文件相当于"前端"。它演示了浏览器 EventSource 在干的事：
一行一行读 data:，拼出完整回答。

前置：先启动服务  uvicorn app:app --reload --port 8000
运行：python client_sse.py
"""
import json

import httpx

URL = "http://127.0.0.1:8000/chat/stream"


def main() -> None:
    payload = {"question": "用三句话讲讲 RAG 的完整流程"}

    with httpx.Client(timeout=60) as client:
        with client.stream("POST", URL, json=payload) as resp:
            print("状态码：", resp.status_code)
            print("Content-Type：", resp.headers.get("content-type"))
            print("-" * 40)

            for line in resp.iter_lines():
                if not line:
                    continue                      # 空行是 SSE 的消息分隔符，跳过
                if not line.startswith("data: "):
                    continue
                data = line[len("data: "):]

                if data == "[DONE]":
                    print("\n" + "-" * 40)
                    print("[流已结束]")
                    break

                obj = json.loads(data)
                if "delta" in obj:
                    print(obj["delta"], end="", flush=True)
                elif "error" in obj:
                    print("\n[服务端返回错误]", obj["error"])


if __name__ == "__main__":
    main()
