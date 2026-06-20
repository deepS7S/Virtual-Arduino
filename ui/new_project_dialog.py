"""
Диалоговое окно создания нового проекта: имя проекта, папка сохранения
и выбор типа платы.

На текущем этапе доступна только Arduino UNO — комбобокс показывает
единственный вариант (см. BoardType.available_values()), но логика
оставлена расширяемой под будущие платы.
"""

from pathlib import Path

from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.constants import BoardType


class NewProjectDialog(QDialog):

    def __init__(self, parent=None, default_directory: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Новый проект")
        self.setMinimumWidth(420)

        self._project_name: str = ""
        self._project_directory: str = default_directory or str(Path.home())
        self._board: BoardType = BoardType.UNO

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("MyArduinoProject")
        self.name_edit.setText("NewProject")
        form.addRow("Имя проекта:", self.name_edit)

        location_row = QHBoxLayout()
        self.location_edit = QLineEdit(self._project_directory)
        self.browse_button = QPushButton("Обзор...")
        self.browse_button.clicked.connect(self._choose_directory)
        location_row.addWidget(self.location_edit)
        location_row.addWidget(self.browse_button)
        form.addRow("Расположение:", location_row)

        self.board_combo = QComboBox()
        self.board_combo.addItems(BoardType.available_values())
        self.board_combo.setEnabled(len(BoardType.available_values()) > 1)
        form.addRow("Тип платы:", self.board_combo)

        board_hint = QLabel("На данном этапе поддерживается только Arduino UNO.")
        board_hint.setStyleSheet("color: gray; font-size: 11px;")
        form.addRow("", board_hint)

        layout.addLayout(form)

        self.preview_label = QLabel()
        self.preview_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.preview_label)
        self.name_edit.textChanged.connect(self._update_preview)
        self.location_edit.textChanged.connect(self._update_preview)
        self._update_preview()

        buttons_row = QHBoxLayout()
        buttons_row.addStretch()
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)
        self.create_button = QPushButton("Создать")
        self.create_button.setObjectName("PrimaryButton")
        self.create_button.setDefault(True)
        self.create_button.clicked.connect(self._on_create)
        buttons_row.addWidget(self.cancel_button)
        buttons_row.addWidget(self.create_button)
        layout.addLayout(buttons_row)

    def _choose_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Выберите папку для проекта", self.location_edit.text()
        )
        if directory:
            self.location_edit.setText(directory)

    def _update_preview(self) -> None:
        name = self.name_edit.text().strip() or "NewProject"
        directory = self.location_edit.text().strip() or str(Path.home())
        self.preview_label.setText(f"Файл проекта: {Path(directory) / (name + '.aproj')}")

    def _on_create(self) -> None:
        name = self.name_edit.text().strip()
        directory = self.location_edit.text().strip()

        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите имя проекта.")
            return
        if not directory:
            QMessageBox.warning(self, "Ошибка", "Укажите папку для сохранения проекта.")
            return
        if not Path(directory).exists():
            answer = QMessageBox.question(
                self,
                "Папка не найдена",
                f"Папка '{directory}' не существует. Создать её?",
            )
            if answer != QMessageBox.Yes:
                return

        self._project_name = name
        self._project_directory = directory
        self._board = BoardType(self.board_combo.currentText())
        self.accept()


    def get_result(self):
        return self._project_name, self._project_directory, self._board
