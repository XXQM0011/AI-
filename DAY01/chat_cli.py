import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.getenv("OPENAI_BASE_URL"),
)

MODEL = "deepseek-flash"   # 按你实际可用的模型名改

def ask(question: str, history: list) -> str:
    history.append({"role": "user", "content": question})
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": "你是一个简洁、准确的助手。"}] + history,
        temperature=0.3,
    )
    answer = resp.choices[0].message.content
    history.append({"role": "assistant", "content": answer})
    return answer

def main():
    print("输入问题，回车提问；输入 exit 退出。")
    history = []
    while True:
        q = input("\n你> ").strip()
        if q.lower() in ("exit", "quit"):
            break
        if not q:
            continue
        try:
            print("AI>", ask(q, history))
        except Exception as e:
            print(f"[出错] {type(e).__name__}: {e}")

if __name__ == "__main__":
    main()