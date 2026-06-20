"""
Боковая панель редактора кода. Открывается кнопкой на узкой "activity bar"
слева (рядом с кнопкой компонентов). Оборачивает CodeEditor заголовком
и кнопкой базовой проверки синтаксиса.
"""

from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui.code_editor import CodeEditor
from ui.theme import BG_DARK, ERROR, SUCCESS, TEXT_SECONDARY


class CodePanel(QWidget):
    """Панель со встроенным редактором скетча и проверкой синтаксиса."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: %s;" % BG_DARK)
        self.setMinimumWidth(300)
        self.setMaximumWidth(800)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(6)

        header_row = QHBoxLayout()
        title = QLabel("РЕДАКТОР КОДА — sketch.ino")
        title.setObjectName("SectionLabel")
        header_row.addWidget(title)
        header_row.addStretch()
        self.check_button = QPushButton("Проверить")
        self.check_button.setMaximumWidth(100)
        self.check_button.clicked.connect(self._on_check_syntax)
        header_row.addWidget(self.check_button)
        layout.addLayout(header_row)

        self.editor = CodeEditor()
        layout.addWidget(self.editor, stretch=1)

        self.status_label = QLabel("Готово")
        self.status_label.setStyleSheet("color: %s; font-size: 11px;" % TEXT_SECONDARY)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

    def set_code(self, code):
        self.editor.setPlainText(code)

    def get_code(self):
        return self.editor.toPlainText()

    def _on_check_syntax(self):
        errors = self.editor.check_syntax()
        if not errors:
            self.status_label.setStyleSheet("color: %s; font-size: 11px;" % SUCCESS)
            self.status_label.setText("Синтаксических ошибок не найдено.")
        else:
            self.status_label.setStyleSheet("color: %s; font-size: 11px;" % ERROR)
            messages = "; ".join("строка %d: %s" % (line, msg) for line, msg in errors[:5])
            self.status_label.setText("Найдены ошибки: %s" % messages)