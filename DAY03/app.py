"""
W1 Day3 · 把问答能力做成 HTTP 接口（FastAPI + SSE）
-------------------------------------------------------
两个接口：
  POST /chat         一次性返回（同步）
  POST /chat/stream  SSE 流式返回（打字机效果）

启动：uvicorn app:app --reload --port 8000
文档：http://127.0.0.1:8000/docs
"""
import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("OPENAI_BASE_URL")
MODEL = os.getenv("MODEL", "deepseek-flash")
SYSTEM_PROMPT = "你是一个简洁、准确的助手，回答不超过 200 字。"

if not API_KEY:
    raise RuntimeError("未找到 OPENAI_API_KEY，请检查 .env")

client = OpenAI(api_key=API_KEY, base_url=BASE_URL or None)

app = FastAPI(
    title="Chat API",
    description="W1 Day3：把命令行脚本变成 HTTP 服务",
    version="0.1.0",
)


# ---------- 请求/响应模型（Pydantic 会自动校验并生成文档） ----------
class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="用户问题，不能为空")
    history: list[Message] = Field(default_factory=list, description="历史对话")


class ChatResponse(BaseModel):
    answer: str
    model: str
    total_tokens: int | None = None


def build_messages(req: ChatRequest) -> list[dict]:
    """把请求体翻译成模型认识的 messages 列表。"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [m.model_dump() for m in req.history]
    messages.append({"role": "user", "content": req.question})
    return messages


# ---------- 接口 1：健康检查 ----------
@app.get("/health", summary="健康检查")
def health():
    return {"status": "ok", "model": MODEL}


# ---------- 接口 2：一次性返回 ----------
@app.post("/chat", response_model=ChatResponse, summary="一次性返回回答")
def chat(req: ChatRequest):
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=build_messages(req),
            temperature=0.3,
        )
    except Exception as e:
        # 上游出错不要吞掉，转成 502 让调用方知道"是后端依赖挂了"
        raise HTTPException(status_code=502, detail=f"上游模型调用失败：{type(e).__name__}: {e}")

    return ChatResponse(
        answer=resp.choices[0].message.content,
        model=MODEL,
        total_tokens=getattr(resp.usage, "total_tokens", None),
    )


# ---------- 接口 3：SSE 流式返回 ----------
@app.post("/chat/stream", summary="SSE 流式返回")
def chat_stream(req: ChatRequest):
    def event_generator():
        try:
            stream = client.chat.completions.create(
                model=MODEL,
                messages=build_messages(req),
                temperature=0.3,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    payload = {"delta": chunk.choices[0].delta.content}
                    # SSE 格式：data: <内容>\n\n（两个换行表示一条消息结束）
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': f'{type(e).__name__}: {e}'}, ensure_ascii=False)}\n\n"
        finally:
            # 无论成功失败都要发终止符，否则客户端会一直等
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # 让 Nginx 等反向代理不要缓冲
        },
    )
