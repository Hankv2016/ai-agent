import os
import sys
import json
import shutil
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import gui
from gui import MainWindow
from PyQt5.QtWidgets import QApplication, QInputDialog

tmp = tempfile.mkdtemp()
settings_bak = gui.SETTINGS_FILE + ".bak"
had_settings = os.path.exists(gui.SETTINGS_FILE)
if had_settings:
    shutil.copy(gui.SETTINGS_FILE, settings_bak)
with open(gui.SETTINGS_FILE, "w", encoding="utf-8") as f:
    json.dump({"autosave_dir": tmp}, f)

try:
    app = QApplication([])
    w = MainWindow()

    # 1) 新控件
    for name in ["expandButton", "collapseButton", "imageLabel", "imageEdit"]:
        assert hasattr(w, name), f"缺少控件: {name}"
    print("WIDGETS_OK")

    # 2) 图片 URL 解析（仅 http/https，过滤 ftp 等）
    assert w._parse_image_urls("") == []
    assert w._parse_image_urls(
        "https://a.com/x.png  ftp://bad  http://c/img.jpg"
    ) == ["https://a.com/x.png", "http://c/img.jpg"]
    print("PARSE_IMG_OK")

    # 3) 按 OpenAI 多模态规范构建 content
    c = w._build_user_content("描述这张图", ["https://a/x.png"])
    assert c == [
        {"type": "text", "text": "描述这张图"},
        {"type": "image_url", "image_url": {"url": "https://a/x.png", "detail": "auto"}},
    ], c
    assert w._build_user_content("hi", []) == "hi"
    # 纯图片（无文字）也必须是 content 数组
    c3 = w._build_user_content("", ["https://a/x.png"])
    assert c3 == [{"type": "image_url", "image_url": {"url": "https://a/x.png", "detail": "auto"}}], c3
    print("BUILD_CONTENT_OK")

    # 4) 渲染 content 数组（文本 + 图片链接）
    w.outputEdit.clear()
    w._append_user([
        {"type": "text", "text": "看图说话"},
        {"type": "image_url", "image_url": {"url": "https://x/y.png", "detail": "auto"}},
    ])
    html = w.outputEdit.toHtml()
    assert "看图说话" in html and "https://x/y.png" in html
    print("RENDER_IMG_OK")

    # 5) 折叠 / 展开（用 isHidden 判定，避免 offscreen 未 show 窗口 isVisible 失真）
    w.on_collapse()
    assert w.leftPanel.isHidden() and (not w.expandButton.isHidden())
    w.on_expand()
    assert (not w.leftPanel.isHidden()) and w.expandButton.isHidden()
    print("COLLAPSE_OK")

    # 6) 双击重命名会话（patch 掉输入框）
    QInputDialog.getText = staticmethod(lambda *a, **k: ("改名了", True))
    item = w.sessionList.item(0)
    w.on_rename_session(item)
    sid = w.session_order[0]
    assert w.sessions[sid]["title"] == "改名了"
    with open(w._session_path(sid), encoding="utf-8") as f:
        assert json.load(f)["title"] == "改名了"
    print("RENAME_OK")

    print("ALL_OK")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
    if had_settings:
        shutil.move(settings_bak, gui.SETTINGS_FILE)
    else:
        if os.path.exists(gui.SETTINGS_FILE):
            os.remove(gui.SETTINGS_FILE)
