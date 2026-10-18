import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from analyzer import build_report, count_words, read_text_file, top_n_words


def run_gui():
    """启动 tkinter 图形界面。"""
    root = tk.Tk()
    root.title("TextLens")
    root.geometry("800x560")
    root.minsize(600, 400)

    selected_path = tk.StringVar(value="尚未选择文件")
    result_box = ScrolledText(
        root,
        wrap="word",
        font=("Microsoft YaHei UI", 10),
        padx=10,
        pady=10,
    )
    result_box.configure(state="disabled")

    batch_frame = tk.Frame(root)
    batch_table = ttk.Treeview(
        batch_frame,
        columns=("file", "words", "top_words", "status"),
        show="headings",
        selectmode="browse",
    )
    batch_table.heading("file", text="文件名")
    batch_table.heading("words", text="词数")
    batch_table.heading("top_words", text="前 5 个高频词")
    batch_table.heading("status", text="状态")
    batch_table.column("file", width=180, minwidth=120, anchor="w")
    batch_table.column("words", width=80, minwidth=60, anchor="center")
    batch_table.column("top_words", width=360, minwidth=220, anchor="w")
    batch_table.column("status", width=100, minwidth=80, anchor="center")
    batch_table.grid(row=0, column=0, sticky="nsew")

    batch_y_scroll = ttk.Scrollbar(
        batch_frame,
        orient="vertical",
        command=batch_table.yview,
    )
    batch_y_scroll.grid(row=0, column=1, sticky="ns")
    batch_x_scroll = ttk.Scrollbar(
        batch_frame,
        orient="horizontal",
        command=batch_table.xview,
    )
    batch_x_scroll.grid(row=1, column=0, sticky="ew")
    batch_table.configure(
        yscrollcommand=batch_y_scroll.set,
        xscrollcommand=batch_x_scroll.set,
    )
    batch_frame.rowconfigure(0, weight=1)
    batch_frame.columnconfigure(0, weight=1)

    current_report = ""
    batch_report = ""
    batch_folder = ""

    def show_text_results():
        batch_frame.pack_forget()
        if not result_box.winfo_manager():
            result_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def show_batch_results():
        result_box.pack_forget()
        if not batch_frame.winfo_manager():
            batch_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def choose_file():
        nonlocal current_report, batch_report, batch_folder

        path = filedialog.askopenfilename(
            parent=root,
            title="选择文本文件",
            filetypes=[
                ("文本文件", "*.txt *.md *.csv"),
                ("所有文件", "*.*"),
            ],
        )
        if not path:
            return

        current_report = ""
        batch_report = ""
        batch_folder = ""
        selected_path.set(path)
        show_text_results()
        result_box.configure(state="normal")
        result_box.delete("1.0", "end")
        result_box.insert("end", "文件已选择，请点击“开始分析”。")
        result_box.configure(state="disabled")

    def analyze_file():
        nonlocal current_report, batch_report, batch_folder

        path = selected_path.get()
        if path == "尚未选择文件":
            messagebox.showwarning("提示", "请先选择一个文本文件。", parent=root)
            return

        current_report = ""
        batch_report = ""
        batch_folder = ""
        try:
            text = read_text_file(path)
        except FileNotFoundError:
            messagebox.showerror(
                "读取失败", "文件不存在，请检查路径是否正确！", parent=root
            )
            return
        except UnicodeDecodeError:
            messagebox.showerror(
                "编码错误",
                "文件可能不是 UTF-8 格式（比如是 GBK），请转换编码后重试。",
                parent=root,
            )
            return
        except OSError as error:
            messagebox.showerror("读取失败", f"读取文件时出错：{error}", parent=root)
            return

        show_text_results()
        n = 5
        top_words = top_n_words(text, n)
        word_count = count_words(text)
        lines = [
            "--- 文件内容 ---",
            text,
            "",
            "--- 单词统计 ---",
            f"文件一共有 {word_count} 个词（统一正则切词）",
            "",
            f"--- 前 {n} 个高频词 ---",
        ]
        if top_words:
            lines.extend(
                f"No.{rank}: {word} (出现 {count} 次)"
                for rank, (word, count) in enumerate(top_words, 1)
            )
        else:
            lines.append("没有提取到有效的词汇。")

        result_box.configure(state="normal")
        result_box.delete("1.0", "end")
        result_box.insert("end", "\n".join(lines))
        result_box.configure(state="disabled")

        current_report = build_report(Path(path).name, text, top_words, n)

    def export_report():
        if not current_report:
            messagebox.showwarning("提示", "请先完成一次文本分析。", parent=root)
            return

        source_path = Path(selected_path.get())
        save_path = filedialog.asksaveasfilename(
            parent=root,
            title="导出分析报告",
            initialfile=f"{source_path.stem}_分析报告.md",
            defaultextension=".md",
            filetypes=[
                ("Markdown 文件", "*.md"),
                ("所有文件", "*.*"),
            ],
        )
        if not save_path:
            return
        if Path(save_path).suffix.lower() != ".md":
            save_path = str(Path(save_path).with_suffix(".md"))

        try:
            with open(save_path, "w", encoding="utf-8", newline="\n") as report_file:
                report_file.write(current_report)
        except OSError as error:
            messagebox.showerror("导出失败", f"保存报告时出错：{error}", parent=root)
            return

        messagebox.showinfo(
            "导出成功",
            f"分析报告已保存到：\n{save_path}",
            parent=root,
        )

    def analyze_folder():
        nonlocal current_report, batch_report, batch_folder

        folder = filedialog.askdirectory(
            parent=root,
            title="选择包含 .txt 文件的文件夹",
        )
        if not folder:
            return

        try:
            files = sorted(
                (
                    path
                    for path in Path(folder).iterdir()
                    if path.is_file() and path.suffix.lower() == ".txt"
                ),
                key=lambda path: path.name.lower(),
            )
        except OSError as error:
            messagebox.showerror(
                "读取失败",
                f"无法读取所选文件夹：{error}",
                parent=root,
            )
            return

        current_report = ""
        batch_report = ""
        batch_folder = ""
        for row in batch_table.get_children():
            batch_table.delete(row)

        if not files:
            messagebox.showinfo(
                "提示",
                "所选文件夹中没有 .txt 文件。",
                parent=root,
            )
            return

        batch_folder = folder
        n = 5
        batch_entries = []
        for file_path in files:
            status = "完成"
            word_count = "-"
            top_summary = "-"
            text = None
            top_words = []
            try:
                text = read_text_file(str(file_path))
                word_count = count_words(text)
                top_words = top_n_words(text, n)
                top_summary = (
                    ", ".join(f"{word}({count})" for word, count in top_words)
                    or "无"
                )
            except UnicodeDecodeError:
                status = "编码错误"
            except OSError:
                status = "读取失败"

            batch_table.insert(
                "",
                "end",
                values=(file_path.name, word_count, top_summary, status),
            )
            batch_entries.append(
                {
                    "name": file_path.name,
                    "text": text,
                    "word_count": word_count,
                    "top_words": top_words,
                    "status": status,
                }
            )

        batch_report = build_report(
            Path(batch_folder).name,
            n=n,
            batch_entries=batch_entries,
        )
        show_batch_results()

    def export_batch_report():
        if not batch_report:
            messagebox.showwarning(
                "提示",
                "请先完成一次文件夹批量分析。",
                parent=root,
            )
            return

        folder_name = Path(batch_folder).name or "文件夹"
        save_path = filedialog.asksaveasfilename(
            parent=root,
            title="导出批量分析报告",
            initialfile=f"{folder_name}_批量分析报告.md",
            defaultextension=".md",
            filetypes=[
                ("Markdown 文件", "*.md"),
                ("所有文件", "*.*"),
            ],
        )
        if not save_path:
            return
        if Path(save_path).suffix.lower() != ".md":
            save_path = str(Path(save_path).with_suffix(".md"))

        try:
            with open(save_path, "w", encoding="utf-8", newline="\n") as report_file:
                report_file.write(batch_report)
        except OSError as error:
            messagebox.showerror(
                "导出失败",
                f"保存批量分析报告时出错：{error}",
                parent=root,
            )
            return

        messagebox.showinfo(
            "导出成功",
            f"批量分析报告已保存到：\n{save_path}",
            parent=root,
        )

    controls = tk.Frame(root, padx=12, pady=10)
    controls.pack(fill="x")
    button_row = tk.Frame(controls)
    button_row.pack(fill="x")
    tk.Button(
        button_row,
        text="选择文件",
        command=choose_file,
        width=12,
    ).pack(side="left")
    tk.Button(
        button_row,
        text="开始分析",
        command=analyze_file,
        width=12,
    ).pack(side="left", padx=(8, 0))
    tk.Button(
        button_row,
        text="选择文件夹",
        command=analyze_folder,
        width=12,
    ).pack(side="left", padx=(8, 0))
    tk.Button(
        button_row,
        text="导出报告",
        command=export_report,
        width=12,
    ).pack(side="left", padx=(8, 0))
    tk.Button(
        button_row,
        text="导出汇总报告",
        command=export_batch_report,
        width=12,
    ).pack(side="left", padx=(8, 0))
    tk.Label(
        controls,
        textvariable=selected_path,
        anchor="w",
    ).pack(fill="x", pady=(8, 0))

    result_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))
    root.mainloop()
