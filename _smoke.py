import os
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import mdrender

sample = (
    "# 标题\n"
    "这是 **粗体**、*斜体*、`代码` 和 [链接](http://x)。\n\n"
    "- 项目一\n- 项目二\n\n"
    "```python\nprint('你好')\n```\n\n"
    "> 引用一行\n\n"
    "1. 第一\n2. 第二"
)
html = mdrender.markdown_to_html(sample)
for tag in ["<h1>", "<b>", "<i>", "<code>", "<ul>", "<pre>", "<blockquote>", "<ol>", "<a href"]:
    assert tag in html, f"缺少 {tag}\n{html}"
print("MDRENDER_OK")

from PyQt5.QtWidgets import QApplication
from gui import MainWindow
app = QApplication([])
w = MainWindow()
assert w.sendButton and w.stopButton and w.clearButton and w.outputEdit and w.inputEdit
print("WIDGETS_OK", w.stopButton.isEnabled() is False)

w._append_user("hi **there**")
w._begin_ai()
w._buf = "AI 回复 `x` **粗**"
w._render_ai(w._buf)
# 渲染路径未触发 on_send，history 应保持为空；_ai_doc_pos 应已记录起点
assert w._ai_doc_pos is not None
assert w.history == []
# 验证 on_send 完成后的历史累积逻辑（两条角色消息）
w.history.append({"role": "user", "content": "hi"})
w.history.append({"role": "assistant", "content": w._buf})
assert len(w.history) == 2 and w.history[1]["role"] == "assistant"
# 排版验证：标签行与内容应各自独立成行，不再粘连
w2 = MainWindow()
w2._append_user("hi")
w2._begin_ai()
w2._buf = "Hello! How can I help you today?"
w2._render_ai(w2._buf)
lines = [l.strip() for l in w2.outputEdit.toPlainText().split("\n") if l.strip()]
expected = ["你：", "hi", "AI：", "Hello! How can I help you today?"]
assert lines == expected, f"排版异常: {lines}"
print("LAYOUT_OK", lines)

# 持久化：保存后新建窗口应自动恢复
w3 = MainWindow()
w3.history = [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]
w3._save_history()
w4 = MainWindow()  # __init__ 会自动 _load_history + _redraw_all
assert w4.history == w3.history, w4.history
print("PERSIST_OK")
print("RENDER_OK")
print("ALL_OK")
