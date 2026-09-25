"""零依赖的极简 Markdown -> HTML 渲染器，输出 Qt 富文本（QTextEdit）支持的 HTML 子集。

支持：标题、粗体/斜体/删除线、行内代码、围栏代码块、有序/无序列表、
引用、水平线、链接、软换行。不依赖任何第三方库。
"""
import html
import re

_FENCE_RE = re.compile(r"^\s*```+\s*([\w-]*)\s*$")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_HR_RE = re.compile(r"^\s*([-*_])\1{2,}\s*$")
_UL_RE = re.compile(r"^\s*[-*+]\s+")
_OL_RE = re.compile(r"^\s*\d+[.)]\s+")
_QUOTE_RE = re.compile(r"^\s*>\s?")


def _escape(text):
    return html.escape(text, quote=False)


def _inline(text):
    # 先保护行内代码，避免其中的 *、` 等被当作格式符号
    codes = []

    def protect(m):
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"

    text = re.sub(r"`([^`]+)`", protect, text)
    text = _escape(text)

    def restore(m):
        idx = int(m.group(1))
        return "<code>" + _escape(codes[idx]) + "</code>"

    text = re.sub(r"\x00(\d+)\x00", restore, text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__([^_]+)__", r"<b>\1</b>", text)
    text = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)
    text = re.sub(r"(?<![\w_])_([^_]+)_(?![\w_])", r"<i>\1</i>", text)
    text = re.sub(r"~~([^~]+)~~", r"<s>\1</s>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def _is_block_start(line):
    return (
        line.strip() == ""
        or _FENCE_RE.match(line)
        or _HEADING_RE.match(line)
        or _HR_RE.match(line)
        or _QUOTE_RE.match(line)
        or _UL_RE.match(line)
        or _OL_RE.match(line)
    )


def markdown_to_html(md):
    lines = md.split("\n")
    out = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]

        # 围栏代码块
        fence = _FENCE_RE.match(line)
        if fence:
            i += 1
            code = []
            while i < n and not _FENCE_RE.match(lines[i]):
                code.append(lines[i])
                i += 1
            i += 1  # 跳过结束的 ```
            out.append("<pre>" + _escape("\n".join(code)) + "</pre>")
            continue

        if line.strip() == "":
            i += 1
            continue

        h = _HEADING_RE.match(line)
        if h:
            lvl = len(h.group(1))
            out.append(f"<h{lvl}>{_inline(h.group(2))}</h{lvl}>")
            i += 1
            continue

        if _HR_RE.match(line):
            out.append("<hr>")
            i += 1
            continue

        if _QUOTE_RE.match(line):
            quote = []
            while i < n and _QUOTE_RE.match(lines[i]):
                quote.append(_QUOTE_RE.sub("", lines[i]))
                i += 1
            out.append("<blockquote>" + markdown_to_html("\n".join(quote)) + "</blockquote>")
            continue

        if _UL_RE.match(line):
            items = []
            while i < n and _UL_RE.match(lines[i]):
                items.append(_UL_RE.sub("", lines[i]))
                i += 1
            out.append("<ul>" + "".join(f"<li>{_inline(it)}</li>" for it in items) + "</ul>")
            continue

        if _OL_RE.match(line):
            items = []
            while i < n and _OL_RE.match(lines[i]):
                items.append(_OL_RE.sub("", lines[i]))
                i += 1
            out.append("<ol>" + "".join(f"<li>{_inline(it)}</li>" for it in items) + "</ol>")
            continue

        # 普通段落（遇到空行或新的块级标记即结束）
        para = []
        while i < n and not _is_block_start(lines[i]):
            para.append(lines[i])
            i += 1
        out.append("<p>" + "<br>".join(_inline(l) for l in para) + "</p>")

    return "\n".join(out)
