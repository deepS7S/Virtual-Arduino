"""
Главное окно приложения, оформленное в стиле Arduino IDE 2.3.6.

Изменения (чек-лист п.4):
  - После построения UI создаётся SimulationEngine (core/simulation_engine.py).
  - Кнопка "Загрузить" (UploadButton на плате) подключена к
    sim_engine.upload_and_run(code_panel.get_code()).
  - sim_engine.status_changed / error_occurred выводятся в статус-бар.
  - Кнопка питания (PowerButton на плате) управляет sim_engine.toggle_power().
  - Вся остальная логика главного окна не изменилась.
"""

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.constants import APP_NAME, PROJECT_FILE_FILTER
from core.project import Project, ProjectError, ProjectLoadError, ProjectSaveError
from core.config import get_config
from core.simulation_engine import SimulationEngine
from ui.circuit_view import CircuitScene, CircuitView
from ui.code_panel import CodePanel
from ui.components_panel import ComponentsPanel
from ui.theme import ACCENT, BG_ACTIVITY_BAR, BG_ELEVATED


class MainWindow(QWidget):
    """Главное окно IDE."""

    def __init__(self, project):
        super().__init__()
        self.project = project
        self.config = get_config()

        self.setWindowTitle("%s | %s" % (self.project.name, APP_NAME))
        self.resize(1280, 800)

        self._build_ui()
        self._init_simulation()
        self._load_project_into_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Создаём сцену и вид
        self.circuit_scene = CircuitScene()
        self.circuit_view = CircuitView(self.circuit_scene, self)

        # Создаём панели
        self.code_panel = CodePanel()
        self.components_panel = ComponentsPanel()
        self.components_panel.component_chosen.connect(self._on_component_chosen)

        self.components_panel.setFixedWidth(310)

        # Создаём QSplitter для боковых панелей
        self.side_splitter = QSplitter(Qt.Horizontal)
        self.side_splitter.setChildrenCollapsible(False)
        self.side_splitter.setHandleWidth(4)
        self.side_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #2b2b2b;
                width: 4px;
            }
            QSplitter::handle:hover {
                background-color: #00979D;
            }
        """)

        # Добавляем панели в сплиттер
        self.side_splitter.addWidget(self.code_panel)
        self.side_splitter.addWidget(self.components_panel)

        self.side_splitter.setStretchFactor(0, 1)
        self.side_splitter.setStretchFactor(1, 0)

        # Устанавливаем начальные ширины (пропорции)
        self.side_splitter.setSizes([400, 260])  # [код, компоненты]
        self.side_splitter.setCollapsible(0, False)
        self.side_splitter.setCollapsible(1, False)

        # Скрываем панели по умолчанию
        self.code_panel.hide()
        self.components_panel.hide()

        # Основной сплиттер между панелями и схемой
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(4)
        self.main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #2b2b2b;
                width: 4px;
            }
            QSplitter::handle:hover {
                background-color: #00979D;
            }
        """)

        self.main_splitter.addWidget(self.side_splitter)
        self.main_splitter.addWidget(self.circuit_view)
        self.main_splitter.setSizes([400, 880])  # [панели, схема]
        self.main_splitter.setCollapsible(0, False)

        # Добавляем тулбар и основной контент
        root.addWidget(self._build_toolbar())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        body.addWidget(self._build_activity_bar())
        body.addWidget(self.main_splitter, stretch=1)

        root.addLayout(body, stretch=1)
        root.addWidget(self._build_status_bar())

    # Подключение движка симуляции
    def _init_simulation(self):
        """
        Создаёт SimulationEngine и подключает его к кнопкам на плате
        (upload/power) и к статус-бару.
        """
        self.sim_engine = SimulationEngine(self.circuit_scene)

        # Кнопка "Загрузить код" (UploadButton на плате) — берёт актуальный
        # код из редактора и запускает его через интерпретатор.
        self.circuit_scene.on_upload_requested = self._on_upload_code

        # Статус и ошибки симуляции → статус-бар внизу окна
        self.sim_engine.status_changed.connect(self._set_status)
        self.sim_engine.error_occurred.connect(self._on_sim_error)

        # Всплывающее окно с предупреждениями о неисправностях (новое)
        self.sim_engine.faults_detected.connect(self._on_faults_popup)

    def _on_upload_code(self):
        """Вызывается кнопкой "↑" на плате: компилирует и запускает скетч."""
        code = self.code_panel.get_code()
        # Сначала проверяем синтаксис через редактор (чтобы подчеркнуть ошибки)
        errors = self.code_panel.editor.check_syntax()
        self.code_panel.editor.apply_error_marks(errors)
        if errors:
            self.code_panel._show_errors(errors)
            self._set_status("Ошибки в коде — заливка отменена")
            return
        ok = self.sim_engine.upload_and_run(code)
        if not ok:
            self._set_status("Ошибка компиляции — см. редактор кода")

    def _on_faults_popup(self, messages):
        if not messages:
            return
        text = "\n\n".join("⚠  " + m for m in messages)
        QMessageBox.warning(
            self,
            "⚠  Обнаружены неисправности в схеме",
            text + "\n\nКомпоненты с нарушениями подсвечены красным на схеме.",
        )

    def _on_sim_error(self, msg):
        """Показывает ошибку симуляции в статус-баре (красным через QSS)."""
        self.status_label.setStyleSheet("color: #ff6b6b; font-size: 11px;")
        self.status_label.setText(msg)

    def _set_status(self, msg):
        self.status_label.setStyleSheet("color: white; font-size: 11px;")
        self.status_label.setText(msg)

    # Тулбар
    def _build_toolbar(self):
        bar = QWidget()
        bar.setStyleSheet("background-color: %s; border-bottom: 1px solid #1b1b1b;" % BG_ELEVATED)
        bar.setFixedHeight(42)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(6)

        new_btn = QPushButton("Новый")
        new_btn.clicked.connect(self._on_new_project)
        open_btn = QPushButton("Открыть")
        open_btn.clicked.connect(self._on_open_project)
        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("PrimaryButton")
        save_btn.clicked.connect(self._on_save_project)

        for b in (new_btn, open_btn, save_btn):
            b.setFixedHeight(32)
            layout.addWidget(b)

        layout.addStretch()

        # Кнопка координат курсора
        coords_btn = QPushButton("CursCoord")
        coords_btn.setFixedSize(100, 32)
        coords_btn.setToolTip("Показать координаты курсора (Ctrl+Shift+C)")
        coords_btn.clicked.connect(self.circuit_view.toggle_cursor_coords)
        layout.addWidget(coords_btn)

        # Кнопка отладки
        debug_btn = QPushButton("Debug")
        debug_btn.setFixedSize(70, 32)
        debug_btn.setToolTip("Показать все координаты (Ctrl+D)")
        debug_btn.clicked.connect(self.circuit_view.debug_coordinator.dump_coordinates)
        layout.addWidget(debug_btn)

        # Зум экрана эмулятора
        zoom_out_btn = QPushButton("-")
        zoom_out_btn.setFixedSize(38, 28)
        zoom_out_btn.clicked.connect(lambda: self.circuit_view.scale(1 / 1.15, 1 / 1.15))
        zoom_reset_btn = QPushButton("Сброс вида")
        zoom_reset_btn.setFixedHeight(32)
        zoom_reset_btn.clicked.connect(self.circuit_view.reset_zoom)
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedSize(38, 28)
        zoom_in_btn.clicked.connect(lambda: self.circuit_view.scale(1.15, 1.15))
        for b in (zoom_out_btn, zoom_reset_btn, zoom_in_btn):
            layout.addWidget(b)

        return bar

    def _build_activity_bar(self):
        bar = QWidget()
        bar.setFixedWidth(48)
        bar.setStyleSheet("background-color: %s; border-right: 1px solid #1b1b1b;" % BG_ACTIVITY_BAR)
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignTop)

        self.code_toggle_btn = QPushButton("</>")
        self.code_toggle_btn.setObjectName("ActivityButton")
        self.code_toggle_btn.setCheckable(True)
        self.code_toggle_btn.setFixedSize(48, 44)
        self.code_toggle_btn.setToolTip("Показать/скрыть редактор кода")
        self.code_toggle_btn.clicked.connect(self._toggle_code_panel)

        self.components_toggle_btn = QPushButton("\u2699")
        self.components_toggle_btn.setObjectName("ActivityButton")
        self.components_toggle_btn.setCheckable(True)
        self.components_toggle_btn.setFixedSize(48, 44)
        self.components_toggle_btn.setToolTip("Показать/скрыть панель компонентов")
        self.components_toggle_btn.clicked.connect(self._toggle_components_panel)

        for b in (self.code_toggle_btn, self.components_toggle_btn):
            b.setStyleSheet(b.styleSheet() + "font-size: 16px;")
            layout.addWidget(b)

        return bar

    # Статус-бар
    def _build_status_bar(self):
        bar = QWidget()
        bar.setFixedHeight(24)
        bar.setStyleSheet("background-color: %s; color: white;" % ACCENT)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 0, 10, 0)
        self.status_label = QLabel("Готово")
        self.status_label.setStyleSheet("color: white; font-size: 11px;")
        layout.addWidget(self.status_label)
        layout.addStretch()
        self.board_label = QLabel("Плата: Arduino UNO")
        self.board_label.setStyleSheet("color: white; font-size: 11px;")
        layout.addWidget(self.board_label)
        return bar

    # Переключение панелей
    def _toggle_code_panel(self):
        if self.code_panel.isVisible():
            self.code_panel.hide()
            self.code_toggle_btn.setChecked(False)
        else:
            self.code_panel.show()
            self.code_toggle_btn.setChecked(True)

    def _toggle_components_panel(self):
        if self.components_panel.isVisible():
            self.components_panel.hide()
            self.components_toggle_btn.setChecked(False)
        else:
            self.components_panel.show()
            self.components_toggle_btn.setChecked(True)

    def _on_component_chosen(self, component_type):
        center = self.circuit_view.mapToScene(self.circuit_view.viewport().rect().center())
        self.circuit_scene.add_component(component_type, center)
        self._set_status("Компонент добавлен: %s" % component_type)

    # Работа с проектом
    def _load_project_into_ui(self):
        self.code_panel.set_code(self.project.source_code)
        if self.project.circuit_data:
            self.circuit_scene.load_from_dict(self.project.circuit_data)
        self.setWindowTitle("%s | %s" % (self.project.name, APP_NAME))
        self.board_label.setText("Плата: %s" % self.project.board.value)

    def _on_save_project(self):
        self.project.source_code = self.code_panel.get_code()
        self.project.circuit_data = self.circuit_scene.to_dict()
        try:
            self.project.save()
            self.config.add_recent_project(self.project.file_path)
        except ProjectSaveError as exc:
            QMessageBox.critical(self, "Ошибка сохранения", str(exc))
            return
        self._set_status("Проект сохранён")

    def _on_open_project(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Открыть проект", str(Path.home()), PROJECT_FILE_FILTER
        )
        if not file_path:
            return
        try:
            project = Project.load(Path(file_path))
        except (ProjectLoadError, ProjectError) as exc:
            QMessageBox.critical(self, "Ошибка открытия проекта", str(exc))
            return
        self.config.add_recent_project(project.file_path)
        self.project = project
        self._load_project_into_ui()

    def _on_new_project(self):
        from ui.new_project_dialog import NewProjectDialog

        dialog = NewProjectDialog(self)
        if dialog.exec_() != NewProjectDialog.Accepted:
            return
        name, directory, board = dialog.get_result()
        try:
            project = Project.create_new(name=name, board=board, directory=Path(directory))
        except ProjectSaveError as exc:
            QMessageBox.critical(self, "Ошибка создания проекта", str(exc))
            return
        self.config.add_recent_project(project.file_path)
        self.project = project
        self.circuit_scene.load_from_dict({"components": [], "wires": []})
        self._load_project_into_ui()

