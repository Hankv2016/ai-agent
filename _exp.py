import os
os.environ.setdefault("OPENAI_API_KEY", "t")
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt5.QtWidgets import QApplication, QTextEdit
from PyQt5.QtGui import QTextCursor

app = QApplication([])

# E1: QTextEdit.append() x2
te = QTextEdit()
te.append("<p>A1</p>")
te.append("<p>A2</p>")
print("E1 append x2      :", repr(te.toPlainText()))

# E2: insertHtml + insertBlock + insertHtml
te2 = QTextEdit()
c = te2.textCursor()
c.movePosition(QTextCursor.End)
c.insertHtml("<p>B1</p>")
c.insertBlock()
c.insertHtml("<p>B2</p>")
print("E2 block between  :", repr(te2.toPlainText()))

# E3: append + cursor tail-replace + insertHtml
te3 = QTextEdit()
te3.append("<p>C1</p>")
c3 = te3.textCursor()
c3.movePosition(QTextCursor.End)
pos = c3.position()
c3c = te3.textCursor()
c3c.setPosition(pos)
c3c.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
c3c.removeSelectedText()
c3c.insertHtml("<p>C2</p>")
print("E3 append+replace :", repr(te3.toPlainText()))

# E4: one insertHtml with two <p>
te4 = QTextEdit()
c4 = te4.textCursor()
c4.movePosition(QTextCursor.End)
c4.insertHtml("<p>D1</p><p>D2</p>")
print("E4 single call    :", repr(te4.toPlainText()))
