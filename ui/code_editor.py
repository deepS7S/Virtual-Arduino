"""
Виджет редактора кода: QPlainTextEdit с панелью номеров строк, подсветкой
синтаксиса Arduino C++, автоотступом после '{' и подсветкой текущей строки.
"""

from PyQt5.QtCore import QRect, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QTextFormat
from PyQt5.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

from ui.arduino_highlighter import ArduinoHighlighter
from ui.theme import ACCENT, BG_DARKEST, TEXT_SECONDARY


class _LineNumberArea(QWidget):
    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
    """Текстовый редактор скетча с номерами строк и подсветкой синтаксиса."""

    def __init__(self, parent=None):
        super().__init__(parent)

        font = QFont("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(11)
        self.setFont(font)
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self.setStyleSheet(f"background-color: {BG_DARKEST}; border: none; padding: 4px;")
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

        self.highlighter = ArduinoHighlighter(self.document())

        self._line_number_area = _LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)

        self._update_line_number_area_width(0)
        self._highlight_current_line()

    def line_number_area_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_number_area_width(self, _new_block_count: int) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def paint_line_numbers(self, event) -> None:
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor(BG_DARKEST).darker(105))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        painter.setPen(QColor(TEXT_SECONDARY))
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.drawText(
                    0, top, self._line_number_area.width() - 6, self.fontMetrics().height(),
                    Qt.AlignRight, number,
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def _highlight_current_line(self) -> None:
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor(ACCENT)
            line_color.setAlpha(25)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            cursor = self.textCursor()
            current_line = cursor.block().text()
            indent = current_line[: len(current_line) - len(current_line.lstrip())]
            extra = "    " if current_line.rstrip().endswith("{") else ""
            super().keyPressEvent(event)
            self.insertPlainText(indent + extra)
            return
        super().keyPressEvent(event)

    def check_syntax(self) -> list:
        """
        Базовая проверка синтаксических ошибок: парность фигурных и круглых
        скобок. Возвращает список (номер_строки, сообщение).
        """
        errors = []
        stack = []
        text = self.toPlainText()
        line = 1
        for ch in text:
            if ch == "\n":
                line += 1
                continue
            if ch in "{(":
                stack.append((ch, line))
            elif ch in "})":
                expected = "{" if ch == "}" else "("
                if not stack or stack[-1][0] != expected:
                    errors.append((line, f"Непарная закрывающая скобка '{ch}'"))
                else:
                    stack.pop()
        for ch, line in stack:
            errors.append((line, f"Не закрыта скобка '{ch}'"))
        return errors
