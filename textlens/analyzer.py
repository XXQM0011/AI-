import re
from collections import Counter


WORD_PATTERN = re.compile(r"\b[a-z]+(?:'[a-z]+)?\b|[\u4e00-\u9fa5]+")


def _tokenize_words(text):
    """按统一正则切词，并过滤长度为 1 的英文词。"""
    words = WORD_PATTERN.findall(text.lower())
    return [
        word
        for word in words
        if not (len(word) == 1 and word.isascii() and word.isalpha())
    ]


def read_text_file(path):
    """读取 UTF-8 文本，并把换行符统一替换为空格。"""
    with open(path, "r", encoding="utf-8") as file:
        return (
            file.read()
            .replace("\r\n", " ")
            .replace("\r", " ")
            .replace("\n", " ")
        )


def count_words(text):
    """统计统一正则切词后的词数。"""
    return len(_tokenize_words(text))


def top_n_words(text, n):
    """提取前 n 个高频词（支持中英混排）"""
    if not text:
        return []
    words = _tokenize_words(text)
    counter = Counter(words)
    return counter.most_common(n)


def build_report(
    source_name,
    text=None,
    top_words=None,
    n=5,
    *,
    batch_entries=None,
):
    """生成单文件或批量分析的 Markdown 报告。"""
    if batch_entries is None:
        word_count = count_words(text)
        if top_words is None:
            top_words = top_n_words(text, n)

        report_lines = [
            "# 文本分析报告",
            "",
            f"**源文件：** `{source_name}`",
            "",
            "## 文件内容",
            "",
            text or "（空文件）",
            "",
            "## 单词统计",
            "",
            f"- 词数：**{word_count}**（统一正则切词）",
            "",
            f"## 前 {n} 个高频词",
            "",
        ]
        if top_words:
            report_lines.extend(
                [
                    "| 排名 | 词语 | 出现次数 |",
                    "| ---: | --- | ---: |",
                ]
            )
            report_lines.extend(
                f"| {rank} | {word} | {count} |"
                for rank, (word, count) in enumerate(top_words, 1)
            )
        else:
            report_lines.append("没有提取到有效的词汇。")
        return "\n".join(report_lines) + "\n"

    summary_lines = [
        "| 文件名 | 词数 | 状态 |",
        "| --- | ---: | --- |",
    ]
    detail_lines = []
    for entry in batch_entries:
        file_name = entry["name"]
        text = entry["text"]
        word_count = entry["word_count"]
        top_words = entry["top_words"]
        status = entry["status"]

        summary_lines.append(f"| {file_name} | {word_count} | {status} |")
        detail_lines.extend(
            [
                f"### {file_name}",
                "",
            ]
        )
        if status == "完成":
            detail_lines.extend(
                [
                    "#### 文件内容",
                    "",
                    text or "（空文件）",
                    "",
                    "#### 单词统计",
                    "",
                    f"- 词数：**{word_count}**（统一正则切词）",
                    "",
                    f"#### 前 {n} 个高频词",
                    "",
                ]
            )
            if top_words:
                detail_lines.extend(
                    [
                        "| 排名 | 词语 | 出现次数 |",
                        "| ---: | --- | ---: |",
                    ]
                )
                detail_lines.extend(
                    f"| {rank} | {word} | {count} |"
                    for rank, (word, count) in enumerate(top_words, 1)
                )
            else:
                detail_lines.append("没有提取到有效的词汇。")
            detail_lines.append("")
        else:
            detail_lines.extend(
                [
                    f"- 状态：{status}",
                    "",
                ]
            )

    return (
        "\n".join(
            [
                "# 批量文本分析报告",
                "",
                f"**文件夹：** `{source_name}`",
                "",
                f"**文件数量：** {len(batch_entries)}",
                "",
                "## 汇总",
                "",
                *summary_lines,
                "",
                "## 文件分析",
                "",
                *detail_lines,
            ]
        )
        + "\n"
    )
