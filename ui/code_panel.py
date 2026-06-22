"""
Боковая панель редактора кода.

Изменения (чек-лист п.3):
  - Кнопка «Проверить» вызывает полноценную проверку через
    core/sketch_interpreter.check_syntax() (теперь прокинута из CodeEditor).
  - on_errors_changed колбэк: редактор вызывает CodePanel автоматически
    при каждом дебаунс-тике (600 мс после ввода) — статус обновляется
    в реальном времени без нажатия кнопки.
  - Статус-строка показывает все ошибки, а не только первые несколько.
"""

from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui.code_editor import CodeEditor
from ui.theme import BG_DARK, ERROR, SUCCESS, TEXT_SECONDARY


class CodePanel(QWidget):
    """Панель со встроенным редактором скетча и проверкой синтаксиса."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: %s;" % BG_DARK)
        self.setMinimumWidth(350)
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
        # Подключаем колбэк: при каждой автопроверке редактор сообщает нам
        # об ошибках и мы обновляем статус-строку без нажатия кнопки.
        self.editor.on_errors_changed = self._show_errors
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
        """Ручная проверка по кнопке — немедленная, без дебаунса."""
        errors = self.editor.check_syntax()
        self.editor.apply_error_marks(errors)
        self._show_errors(errors)

    def _show_errors(self, errors):
        if not errors:
            self.status_label.setStyleSheet("color: %s; font-size: 11px;" % SUCCESS)
            self.status_label.setText("Синтаксических ошибок не найдено.")
        else:
            self.status_label.setStyleSheet("color: %s; font-size: 11px;" % ERROR)
            lines = "; ".join("строка %d: %s" % (line, msg) for line, msg in errors[:5])
            suffix = " ещё %d..." % (len(errors) - 5) if len(errors) > 5 else ""
            self.status_label.setText("Ошибки: %s%s" % (lines, suffix))
