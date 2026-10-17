import re
from collections import Counter


def show_text(text):
    """打印文本内容"""
    print("\n--- 文件内容 ---")
    print(text)


def count_words(text):
    """统计以空格分隔的词数（适合英文）"""
    words = text.split()
    print(f"\n--- 单词统计 ---")
    print(f"文件一共有 {len(words)} 个词（按空格分隔计算）")


def top_n_words(text, n):
    """提取前 n 个高频词（支持中英混排）"""
    if not text:
        return []
    # 转小写
    text_lower = text.lower()
    # 正则匹配英文单词或连续中文
    pattern = r"\b[a-z]+(?:'[a-z]+)?\b|[\u4e00-\u9fa5]+"
    words = re.findall(pattern, text_lower)

    counter = Counter(words)
    return counter.most_common(n)


if __name__ == '__main__':
    path = input("请输入文件地址:").strip().strip('"')

    # 1. 统一在这里读取一次文件
    try:
        with open(path, "r", encoding="utf-8") as f:
            # 统一把换行符替换为空格，防止英文单词粘连
            text = f.read().replace("\n", " ").replace("\r", " ")
    except FileNotFoundError:
        print("文件不存在，请检查路径是否正确！")
        exit()  # 文件不存在直接退出程序
    except UnicodeDecodeError:
        print("编码错误！文件可能不是 UTF-8 格式（比如是 GBK），请转换编码后重试。")
        exit()
    except OSError as e:
        print(f"读取失败: {e}")
        exit()

    # 2. 调用各个功能函数（直接传入 text，不再传 path）
    show_text(text)
    count_words(text)

    # 3. 调用 top_n_words
    print("\n--- 前 5 个高频词 ---")
    top_words = top_n_words(text, 5)
    if not top_words:
        print("没有提取到有效的词汇。")
    else:
        for rank, (word, count) in enumerate(top_words, 1):
            print(f"No.{rank}: {word} (出现 {count} 次)")