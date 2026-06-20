"""
Стартовый экран приложения.

Показывается при запуске и предоставляет пользователю возможность:
  - создать новый проект (с выбором платы);
  - открыть существующий проект через диалог выбора файла;
  - открыть один из недавних проектов из списка.
"""

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.constants import APP_NAME, APP_VERSION, PROJECT_FILE_FILTER
from core.project import Project, ProjectError, ProjectLoadError, ProjectSaveError
from core.config import get_config
from ui.new_project_dialog import NewProjectDialog
from ui.theme import BG_DARKEST


class StartScreen(QWidget):
    """
    Стартовое окно приложения. При успешном создании или открытии проекта
    вызывает self.on_project_ready(project), которую должен переопределить
    или подключить вызывающий код (см. main.py).
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — Начало работы")
        self.resize(640, 440)
        self.setStyleSheet(f"background-color: {BG_DARKEST};")

        self.config = get_config()
        self.on_project_ready = None

        self._build_ui()
        self._populate_recent_list()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(16)

        title = QLabel(APP_NAME)
        title.setObjectName("TitleLabel")
        subtitle = QLabel(f"Версия {APP_VERSION} — Среда разработки и симуляции Arduino UNO")
        subtitle.setObjectName("SubtitleLabel")
        root.addWidget(title)
        root.addWidget(subtitle)

        actions_row = QHBoxLayout()
        self.new_project_button = QPushButton("Создать новый проект")
        self.new_project_button.setObjectName("PrimaryButton")
        self.new_project_button.setMinimumHeight(40)
        self.new_project_button.clicked.connect(self._on_new_project)

        self.open_project_button = QPushButton("Открыть проект...")
        self.open_project_button.setMinimumHeight(40)
        self.open_project_button.clicked.connect(self._on_open_project)

        actions_row.addWidget(self.new_project_button)
        actions_row.addWidget(self.open_project_button)
        root.addLayout(actions_row)

        recent_label = QLabel("НЕДАВНИЕ ПРОЕКТЫ")
        recent_label.setObjectName("SectionLabel")
        recent_label.setStyleSheet(recent_label.styleSheet() + "margin-top: 12px;")
        root.addWidget(recent_label)

        self.recent_list = QListWidget()
        self.recent_list.itemDoubleClicked.connect(self._on_recent_item_activated)
        root.addWidget(self.recent_list, stretch=1)

        hint = QLabel("Дважды щёлкните по проекту в списке, чтобы открыть его.")
        hint.setObjectName("SubtitleLabel")
        hint.setStyleSheet("color: gray; font-size: 11px;")
        root.addWidget(hint)

    def _populate_recent_list(self) -> None:
        self.recent_list.clear()
        recents = self.config.get_recent_projects()
        if not recents:
            placeholder = QListWidgetItem("Нет недавних проектов")
            placeholder.setFlags(Qt.NoItemFlags)
            self.recent_list.addItem(placeholder)
            return

        for path_str in recents:
            path = Path(path_str)
            if not path.exists():
                continue
            item = QListWidgetItem(f"{path.stem}    —    {path}")
            item.setData(Qt.UserRole, path_str)
            self.recent_list.addItem(item)

    def _on_new_project(self) -> None:
        # Передаём директорию по умолчанию из конфига
        default_dir = str(self.config.get_projects_directory())
        dialog = NewProjectDialog(self, default_directory=default_dir)
        if dialog.exec_() != NewProjectDialog.Accepted:
            return

        name, directory, board = dialog.get_result()
        try:
            project = Project.create_new(name=name, board=board, directory=Path(directory))
        except ProjectSaveError as exc:
            QMessageBox.critical(self, "Ошибка создания проекта", str(exc))
            return

        self.config.add_recent_project(project.file_path)
        self._open_project(project)

    def _on_open_project(self) -> None:
        # Начинаем с директории по умолчанию
        default_dir = str(self.config.get_projects_directory())
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Открыть проект", default_dir, PROJECT_FILE_FILTER
        )
        if not file_path:
            return
        self._load_and_open(Path(file_path))

    def _on_recent_item_activated(self, item: QListWidgetItem) -> None:
        path_str = item.data(Qt.UserRole)
        if not path_str:
            return
        self._load_and_open(Path(path_str))

    def _load_and_open(self, file_path: Path) -> None:
        try:
            project = Project.load(file_path)
        except ProjectLoadError as exc:
            QMessageBox.critical(self, "Ошибка открытия проекта", str(exc))
            self.config.remove_recent_project(file_path)
            self._populate_recent_list()
            return
        except ProjectError as exc:
            QMessageBox.critical(self, "Ошибка", str(exc))
            return

        self.config.add_recent_project(file_path)
        self._open_project(project)

    def _open_project(self, project: Project) -> None:
        if self.on_project_ready:
            self.on_project_ready(project)
