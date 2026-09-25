# gui.py
import os
import sys
import re
import json
import time
import uuid
from PyQt5 import uic
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QFileDialog,
    QInputDialog,
)
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QTextCursor

from client import AIClient, load_env_file
import mdrender

load_env_file()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
# 旧版单文件历史（启动时若无可迁移为首个会话）
LEGACY_HISTORY_FILE = os.path.join(BASE_DIR, "conversation.json")
# 会话目录默认值（用户可在 GUI 中修改）
DEFAULT_AUTOSAVE_DIR = os.path.join(BASE_DIR, "conversations")


# ---------- 导入解析辅助（模块级，便于测试） ----------
def map_role(title):
    """根据 `## 你` / `## AI` 之类的标题推断角色。"""
    t = (title or "").lower()
    if re.search(r"你|用户|user", t):
        return "user"
    if re.search(r"ai|助手|assistant|bot", t):
        return "assistant"
    return None


def parse_markdown_history(text):
    """把 `## 你` / `## AI` 分段的 Markdown 解析回 [{role, content}]。"""
    msgs = []
    cur_role = None
    buf = []

    def flush():
        if cur_role and buf:
            msgs.append({"role": cur_role, "content": "\n".join(buf).strip()})
        buf.clear()

    for line in (text or "").split("\n"):
        m = re.match(r"^##\s*(.*)$", line)
        if m:
            role = map_role(m.group(1))
            if role:
                flush()
                cur_role = role
                continue
        if cur_role is not None:
            buf.append(line)
    flush()
    return [m for m in msgs if m["content"]]


def parse_json_history(data):
    """接受 list 或含 messages/history 字段的 dict。"""
    if isinstance(data, list):
        msgs = data
    elif isinstance(data, dict):
        msgs = data.get("messages") or data.get("history") or []
    else:
        return []
    out = []
    for m in msgs:
        if isinstance(m, dict) and m.get("role") in ("user", "assistant"):
            out.append({"role": m["role"], "content": m.get("content") or ""})
    return out


def parse_import_file(path):
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".json":
            with open(path, "r", encoding="utf-8") as f:
                return parse_json_history(json.load(f))
        else:  # .md / .txt
            with open(path, "r", encoding="utf-8") as f:
                return parse_markdown_history(f.read())
    except Exception as e:
        raise RuntimeError(f"读取导入文件失败: {e}")


class RequestThread(QThread):
    chunk = pyqtSignal(str)
    finished_ok = pyqtSignal(str, bool)  # (完整文本, 是否被用户中断)
    failed = pyqtSignal(str)

    def __init__(self, prompt, history=None):
        super().__init__()
        self.prompt = prompt
        self.history = history or []
        self._stream = None

    def run(self):
        try:
            # 优化：直接在主线程外调用 SDK，省去每次启动 Python 子进程的开销
            client = AIClient()
            full = []
            self._stream = client.stream_chat(self.prompt, history=self.history)
            for delta in self._stream:
                if self.isInterruptionRequested():
                    break
                full.append(delta)
                self.chunk.emit(delta)
            text = "".join(full)
            self.finished_ok.emit(text, self.isInterruptionRequested())
        except Exception as e:
            self.failed.emit(str(e))

    def stop(self):
        """请求中断：先通知线程退出循环，再关闭底层流。"""
        self.requestInterruption()
        try:
            if self._stream is not None:
                self._stream.close()
        except Exception:
            pass


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        ui_path = os.path.join(BASE_DIR, "gui", "main.ui")
        uic.loadUi(ui_path, self)

        # ---- 设置 / 会话管理状态 ----
        self.settings = self._load_settings()
        self.sessions_dir = self.settings.get("autosave_dir") or DEFAULT_AUTOSAVE_DIR
        os.makedirs(self.sessions_dir, exist_ok=True)

        self.sessions = {}      # sid -> {id,title,created_at,updated_at,messages}
        self.session_order = []  # 列表显示顺序（sid）
        self.current_id = None
        self._refreshing = False

        # ---- 对话显示状态 ----
        self.thread = None
        self._buf = ""
        self._ai_doc_pos = None
        self._last_render = 0.0
        self._pending_user_content = None  # 进行中的用户消息（str 或 OpenAI content 数组）

        self._bind_widgets()
        self._migrate_legacy_if_needed()
        self._load_sessions()
        if not self.sessions:
            self._create_session(persist=False)
        else:
            self._switch_to(self.session_order[0], redraw=True)

        self._refresh_session_list()
        self._init_status()

    # ---------------- 设置 ----------------
    def _load_settings(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    s = json.load(f)
                if isinstance(s, dict):
                    return s
        except Exception:
            pass
        return {}

    def _save_settings(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.statusBar().showMessage(f"保存设置失败: {e}")

    # ---------------- 会话文件读写 ----------------
    def _session_path(self, sid):
        return os.path.join(self.sessions_dir, f"session_{sid}.json")

    def _write_session_file(self, sess):
        try:
            with open(self._session_path(sess["id"]), "w", encoding="utf-8") as f:
                json.dump(sess, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.statusBar().showMessage(f"保存会话失败: {e}")

    def _delete_session_file(self, sid):
        try:
            p = self._session_path(sid)
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

    def _migrate_legacy_if_needed(self):
        """旧版 conversation.json 存在且无任何新会话时，迁移为首会话。"""
        existing = [
            f for f in os.listdir(self.sessions_dir)
            if f.startswith("session_") and f.endswith(".json")
        ]
        if existing or not os.path.exists(LEGACY_HISTORY_FILE):
            return
        try:
            with open(LEGACY_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            msgs = data if isinstance(data, list) else []
            msgs = [
                m for m in msgs
                if isinstance(m, dict) and m.get("role") in ("user", "assistant")
            ]
            if msgs:
                sid = self._new_sid()
                sess = self._make_session(sid, msgs)
                self.sessions[sid] = sess
                self._write_session_file(sess)
                os.remove(LEGACY_HISTORY_FILE)
        except Exception:
            pass

    def _new_sid(self):
        return time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]

    @staticmethod
    def _make_session(sid, messages):
        now = time.time()
        title = ""
        for m in messages:
            if m.get("role") == "user":
                title = (m.get("content") or "").strip().replace("\n", " ")[:24]
                break
        return {
            "id": sid,
            "title": title or "新对话",
            "created_at": now,
            "updated_at": now,
            "messages": messages,
        }

    # ---------------- 会话列表 ----------------
    def _load_sessions(self):
        self.sessions = {}
        self.session_order = []
        try:
            for f in os.listdir(self.sessions_dir):
                if f.startswith("session_") and f.endswith(".json"):
                    p = os.path.join(self.sessions_dir, f)
                    try:
                        with open(p, "r", encoding="utf-8") as fh:
                            sess = json.load(fh)
                        if isinstance(sess, dict) and sess.get("id"):
                            self.sessions[sess["id"]] = sess
                    except Exception:
                        continue
        except Exception:
            pass
        # 按更新时间倒序
        self.session_order = sorted(
            self.sessions.keys(),
            key=lambda s: self.sessions[s].get("updated_at", 0),
            reverse=True,
        )

    def _refresh_session_list(self):
        self._refreshing = True
        self.sessionList.clear()
        for sid in self.session_order:
            self.sessionList.addItem(self.sessions[sid].get("title") or "（无标题）")
        if self.current_id in self.session_order:
            self.sessionList.setCurrentRow(self.session_order.index(self.current_id))
        self._refreshing = False

    def _bind_widgets(self):
        self.sendButton.clicked.connect(self.on_send)
        self.stopButton.clicked.connect(self.on_stop)
        self.clearButton.clicked.connect(self.on_clear)
        self.exportButton.clicked.connect(self.on_export)
        self.inputEdit.returnPressed.connect(self.on_send)

        self.newSessionButton.clicked.connect(self.on_new_session)
        self.deleteSessionButton.clicked.connect(self.on_delete_session)
        self.importButton.clicked.connect(self.on_import)
        self.settingsButton.clicked.connect(self.on_settings)
        self.sessionList.currentRowChanged.connect(self._on_session_row_changed)

        self.collapseButton.clicked.connect(self.on_collapse)
        self.expandButton.clicked.connect(self.on_expand)
        self.sessionList.itemDoubleClicked.connect(self.on_rename_session)
        self.setAcceptDrops(True)

        self.outputEdit.setLineWrapMode(self.outputEdit.WidgetWidth)

    def _init_status(self):
        base = os.environ.get("OPENAI_BASE_URL") or AIClient.DEFAULT_BASE_URL
        model = os.environ.get("OPENAI_MODEL") or AIClient.DEFAULT_MODEL
        if not os.environ.get("OPENAI_API_KEY"):
            self.statusBar().showMessage(
                "⚠ 未检测到 OPENAI_API_KEY，请配置 .env 或系统环境变量"
            )
        else:
            self.statusBar().showMessage(
                f"就绪 | 模型: {model} | 保存目录: {self.sessions_dir}"
            )

    # ---------------- 当前会话操作 ----------------
    def _current_messages(self):
        if self.current_id and self.current_id in self.sessions:
            return self.sessions[self.current_id].get("messages", [])
        return []

    def _save_current_session(self):
        if not self.current_id:
            return
        sess = self.sessions.get(self.current_id)
        if not sess:
            return
        sess["messages"] = self.history
        sess["updated_at"] = time.time()
        if not sess.get("title") or sess["title"] == "新对话":
            for m in self.history:
                if m.get("role") == "user":
                    sess["title"] = (m.get("content") or "").strip().replace("\n", " ")[:24] or "新对话"
                    break
        self._write_session_file(sess)

    def _create_session(self, persist=True):
        sid = self._new_sid()
        sess = self._make_session(sid, [])
        self.sessions[sid] = sess
        if persist:
            self._write_session_file(sess)
        self.session_order.insert(0, sid)
        self.current_id = sid
        self.history = []
        self.outputEdit.clear()
        self._refresh_session_list()
        return sid

    def _switch_to(self, sid, redraw=False):
        if sid not in self.sessions:
            return
        self.current_id = sid
        self.history = list(self.sessions[sid].get("messages", []))
        if redraw:
            self._redraw_all()
        self._refresh_session_list()

    def _on_session_row_changed(self, row):
        if self._refreshing:
            return
        if row < 0 or row >= len(self.session_order):
            return
        sid = self.session_order[row]
        if sid == self.current_id:
            return
        # 切换前保存当前会话
        self._save_current_session()
        self._switch_to(sid, redraw=True)

    # ---------------- 槽函数：会话 ----------------
    def on_new_session(self):
        if self.thread is not None and self.thread.isRunning():
            self.thread.stop()
        self._save_current_session()
        self._create_session(persist=True)
        self.statusBar().showMessage("已新建会话")

    def on_delete_session(self):
        if not self.current_id:
            return
        sid = self.current_id
        if len(self.sessions) <= 1:
            QMessageBox.information(self, "提示", "至少保留一个会话。")
            return
        reply = QMessageBox.question(
            self, "删除会话",
            f"确定删除会话「{self.sessions[sid].get('title') or ''}」？此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        del self.sessions[sid]
        self._delete_session_file(sid)
        self.session_order.remove(sid)
        self.current_id = self.session_order[0]
        self._switch_to(self.current_id, redraw=True)
        self._refresh_session_list()
        self.statusBar().showMessage("已删除会话")

    def _do_import(self, path):
        try:
            msgs = parse_import_file(path)
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))
            return
        if not msgs:
            QMessageBox.warning(self, "导入", "未从文件中解析出有效对话内容。")
            return
        sid = self._new_sid()
        sess = self._make_session(sid, msgs)
        sess["title"] = "导入-" + (sess["title"] or "对话")
        self.sessions[sid] = sess
        self._write_session_file(sess)
        self.session_order.insert(0, sid)
        self._switch_to(sid, redraw=True)
        self._refresh_session_list()
        self.statusBar().showMessage(f"已导入 {len(msgs)} 条消息")

    def on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入对话",
            self.sessions_dir,
            "对话文件 (*.md *.txt *.json)",
        )
        if not path:
            return
        self._do_import(path)

    def on_settings(self):
        d = QFileDialog.getExistingDirectory(
            self, "选择对话自动保存目录", self.sessions_dir
        )
        if not d:
            return
        # 把内存中的会话写入新目录，并切换到新目录
        self.sessions_dir = d
        self.settings["autosave_dir"] = d
        self._save_settings()
        os.makedirs(d, exist_ok=True)
        for sess in self.sessions.values():
            self._write_session_file(sess)
        self._load_sessions()
        if not self.session_order:
            self._create_session(persist=True)
        else:
            self._switch_to(self.session_order[0], redraw=True)
        self._refresh_session_list()
        self.statusBar().showMessage(f"自动保存目录已设为: {d}")

    def on_export(self):
        ts = time.strftime("%Y%m%d_%H%M%S")
        default = os.path.join(self.sessions_dir, f"对话记录_{ts}")
        path, _ = QFileDialog.getSaveFileName(
            self, "导出对话", default,
            "Markdown (*.md);;JSON (*.json)",
        )
        if not path:
            return
        try:
            if path.lower().endswith(".json"):
                sess = self.sessions.get(self.current_id, {})
                data = {
                    "title": sess.get("title", ""),
                    "messages": self.history,
                }
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                parts = []
                for msg in self.history:
                    role = msg.get("role")
                    content = msg.get("content") or ""
                    if role == "user":
                        parts.append("## 你\n\n" + content + "\n")
                    elif role == "assistant":
                        parts.append("## AI\n\n" + content + "\n")
                with open(path, "w", encoding="utf-8") as f:
                    f.write("# 对话记录\n\n" + "\n".join(parts))
            self.statusBar().showMessage(f"已导出: {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    # ---------------- 图片 / 折叠 / 重命名 / 拖拽 ----------------
    @staticmethod
    def _parse_image_urls(text):
        if not text:
            return []
        out = []
        for tok in re.split(r"[\s,;]+", text.strip()):
            tok = tok.strip()
            if re.match(r"^https?://", tok, re.I):
                out.append(tok)
        return out

    @staticmethod
    def _build_user_content(prompt, urls):
        """按 OpenAI 多模态规范构建 user 消息内容（纯文本为 str，含图则为 content 数组）。"""
        parts = []
        if prompt:
            parts.append({"type": "text", "text": prompt})
        for u in urls:
            parts.append({"type": "image_url", "image_url": {"url": u, "detail": "auto"}})
        return parts if urls else prompt

    def on_collapse(self):
        self.leftPanel.hide()
        self.expandButton.setVisible(True)

    def on_expand(self):
        self.leftPanel.show()
        self.expandButton.setVisible(False)

    def on_rename_session(self, item):
        row = self.sessionList.row(item)
        if row < 0 or row >= len(self.session_order):
            return
        sid = self.session_order[row]
        old = self.sessions[sid].get("title", "")
        new, ok = QInputDialog.getText(self, "重命名会话", "会话标题:", text=old)
        if not ok:
            return
        new = new.strip()
        if not new:
            return
        self.sessions[sid]["title"] = new
        self._write_session_file(self.sessions[sid])
        self._refresh_session_list()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if p and p.lower().endswith((".md", ".json", ".txt")):
                self._do_import(p)
                break

    # ---------------- 显示辅助 ----------------
    def _scroll_bottom(self):
        cursor = self.outputEdit.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.outputEdit.setTextCursor(cursor)
        self.outputEdit.ensureCursorVisible()

    def _append_user(self, content):
        if isinstance(content, list):
            text = "".join(
                p.get("text", "") for p in content
                if isinstance(p, dict) and p.get("type") == "text"
            )
            imgs = [
                p["image_url"]["url"] for p in content
                if isinstance(p, dict) and p.get("type") == "image_url" and p.get("image_url")
            ]
        else:
            text = content
            imgs = []
        if self.outputEdit.toPlainText().strip():
            self.outputEdit.append("<p>&nbsp;</p>")
        self.outputEdit.append('<p><font color="#1a73e8"><b>你：</b></font></p>')
        if text:
            self.outputEdit.append(mdrender.markdown_to_html(text) or "<p>&nbsp;</p>")
        for img in imgs:
            self.outputEdit.append(
                f'<p><font color="#888">[图片] <a href="{img}">{img}</a></font></p>'
            )
        self._scroll_bottom()

    def _begin_ai(self):
        self.outputEdit.append('<p><font color="#0a8043"><b>AI：</b></font></p>')
        cursor = self.outputEdit.textCursor()
        cursor.movePosition(QTextCursor.End)
        self._ai_doc_pos = cursor.position()

    def _render_ai(self, md_text):
        cursor = self.outputEdit.textCursor()
        cursor.setPosition(self._ai_doc_pos)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertBlock()
        cursor.insertHtml(mdrender.markdown_to_html(md_text) or "<p>&nbsp;</p>")
        self._scroll_bottom()

    def _redraw_all(self):
        self.outputEdit.clear()
        for msg in self.history:
            role = msg.get("role")
            content = msg.get("content") or ""
            if role == "user":
                self._append_user(content)
            elif role == "assistant":
                self._begin_ai()
                self._render_ai(content)
        self._scroll_bottom()

    # ---------------- 状态切换 ----------------
    def _set_busy(self, busy):
        self.sendButton.setEnabled(not busy)
        self.stopButton.setEnabled(busy)
        self.inputEdit.setEnabled(not busy)
        self.newSessionButton.setEnabled(not busy)
        self.deleteSessionButton.setEnabled(not busy)

    # ---------------- 槽函数：对话 ----------------
    def on_send(self):
        prompt = self.inputEdit.text().strip()
        if self.thread is not None and self.thread.isRunning():
            return

        urls = self._parse_image_urls(self.imageEdit.text())
        if not prompt and not urls:
            return

        # 按 OpenAI 多模态规范构建 user 消息：纯文本保持 str，含图片则为 content 数组
        user_content = self._build_user_content(prompt, urls)

        self.inputEdit.clear()
        self.imageEdit.clear()
        self._pending_user_content = user_content
        self._append_user(user_content)
        self._begin_ai()
        self._buf = ""
        self._set_busy(True)
        self.statusBar().showMessage("正在请求...")

        self.thread = RequestThread(user_content, self._current_messages())
        self.thread.chunk.connect(self._on_chunk)
        self.thread.finished_ok.connect(self._on_success)
        self.thread.failed.connect(self._on_error)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _on_chunk(self, delta):
        self._buf += delta
        now = time.time()
        if now - self._last_render >= 0.08:
            self._last_render = now
            self._render_ai(self._buf)

    def _on_success(self, _reply, stopped):
        self._render_ai(self._buf)
        if stopped:
            self._render_ai(self._buf + "\n\n_(已停止)_")
        self.history.append({"role": "user", "content": self._pending_user_content})
        self.history.append({"role": "assistant", "content": self._buf})
        self._pending_user_content = None
        self._save_current_session()
        self._refresh_session_list()
        self._set_busy(False)
        self.statusBar().showMessage("已停止（可继续提问）" if stopped else "完成")
        self._buf = ""
        self.thread = None

    def _on_error(self, err):
        if self._buf:
            self._render_ai(self._buf)
        self._set_busy(False)
        self.statusBar().showMessage("请求失败")
        self._buf = ""
        self.thread = None
        QMessageBox.critical(self, "请求出错", err)

    def on_stop(self):
        if self.thread is not None and self.thread.isRunning():
            self.thread.stop()

    def on_clear(self):
        if self.thread is not None and self.thread.isRunning():
            self.thread.stop()
        self.outputEdit.clear()
        self.history = []
        self._pending_user_content = None
        self._buf = ""
        self._save_current_session()
        self._refresh_session_list()
        self.statusBar().showMessage("已清空当前会话")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
