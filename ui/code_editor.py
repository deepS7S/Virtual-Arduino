"""
Виджет редактора кода: QPlainTextEdit с панелью номеров строк, подсветкой
синтаксиса Arduino C++, автоотступом после '{' и подсветкой текущей строки.

Изменения (чек-лист п.3):
  - check_syntax() теперь использует core/sketch_interpreter.check_syntax()
    вместо простой проверки скобок — возвращает полноценные ошибки с
    номерами строк от реального парсера.
  - Новый метод apply_error_marks(errors) рисует красные волнистые
    подчёркивания (QTextCharFormat.SpellCheckUnderline) на строках с ошибками
    через QTextEdit.ExtraSelection.
  - QTimer-дебаунс (600 мс после последнего нажатия клавиши): текст
    автоматически проверяется без нажатия кнопки «Проверить».
"""

from PyQt5.QtCore import QRect, QSize, Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QPainter, QTextCharFormat, QTextCursor, QTextFormat
from PyQt5.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

from ui.arduino_highlighter import ArduinoHighlighter
from ui.theme import ACCENT, BG_DARKEST, TEXT_SECONDARY


class _LineNumberArea(QWidget):
    def __init__(self, editor):
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
        self.setStyleSheet("background-color: %s; border: none; padding: 4px;" % BG_DARKEST)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

        self.highlighter = ArduinoHighlighter(self.document())

        self._line_number_area = _LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)

        # Дебаунс-таймер: 600 мс после последнего ввода → автопроверка
        self._check_timer = QTimer()
        self._check_timer.setSingleShot(True)
        self._check_timer.setInterval(600)
        self._check_timer.timeout.connect(self._auto_check)
        self.textChanged.connect(lambda: self._check_timer.start())

        # Колбэк, который CodePanel подключает для отображения статуса ошибок
        # в своём status_label; вызывается после каждой автопроверки.
        self.on_errors_changed = None

        self._update_line_number_area_width(0)
        self._highlight_current_line()

    # Номера строк
    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy):
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def paint_line_numbers(self, event):
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor(BG_DARKEST).darker(105))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        painter.setPen(QColor(TEXT_SECONDARY))
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(
                    0, top, self._line_number_area.width() - 6,
                    self.fontMetrics().height(), Qt.AlignRight,
                    str(block_number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def _highlight_current_line(self):
        selections = self._get_error_selections()
        if not self.isReadOnly():
            sel = QTextEdit.ExtraSelection()
            line_color = QColor(ACCENT)
            line_color.setAlpha(25)
            sel.format.setBackground(line_color)
            sel.format.setProperty(QTextFormat.FullWidthSelection, True)
            sel.cursor = self.textCursor()
            sel.cursor.clearSelection()
            selections.append(sel)
        self.setExtraSelections(selections)

    # Красные волнистые подчёркивания
    _error_lines = None   # список (line_number, message) последней проверки

    def _get_error_selections(self):
        """Строит ExtraSelection с волнистым подчёркиванием для каждой ошибки."""
        if not self._error_lines:
            return []
        selections = []
        doc = self.document()
        err_fmt = QTextCharFormat()
        err_fmt.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)
        err_fmt.setUnderlineColor(QColor("#f14c4c"))
        for line_num, _msg in self._error_lines:
            block = doc.findBlockByLineNumber(line_num - 1)
            if not block.isValid():
                continue
            sel = QTextEdit.ExtraSelection()
            sel.format = err_fmt
            cursor = QTextCursor(block)
            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            sel.cursor = cursor
            selections.append(sel)
        return selections

    def apply_error_marks(self, errors):
        """
        Принимает список (line, message) от check_syntax() и рисует
        красные волнистые подчёркивания. Вызывается из CodePanel.
        """
        self._error_lines = errors if errors else []
        self._highlight_current_line()

    def _auto_check(self):
        """Запускается дебаунс-таймером после каждого изменения текста."""
        errors = self.check_syntax()
        self.apply_error_marks(errors)
        if self.on_errors_changed is not None:
            self.on_errors_changed(errors)

    # Проверка синтаксиса (теперь через реальный парсер из sketch_interpreter)
    def check_syntax(self):
        """
        Возвращает список (line, message).
        Использует core.sketch_interpreter.check_syntax() — полноценный
        рекурсивный парсер с пониманием C++-подобного синтаксиса Arduino,
        а не простую проверку скобок как раньше.
        """
        try:
            from core.sketch_interpreter import check_syntax as _check
            return _check(self.toPlainText())
        except Exception:
            return []

    # Автоотступ после '{'
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            cursor = self.textCursor()
            current_line = cursor.block().text()
            indent = current_line[: len(current_line) - len(current_line.lstrip())]
            extra = "    " if current_line.rstrip().endswith("{") else ""
            super().keyPressEvent(event)
            self.insertPlainText(indent + extra)
            return
        super().keyPressEvent(event)
