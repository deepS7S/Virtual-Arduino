"""
Боковая панель выбора компонентов из набора Arduino. Открывается кнопкой
на узкой "activity bar" слева. Клик по компоненту добавляет его на
рабочее поле (в центр текущего вида редактора схем).
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.components_data import COMPONENT_ORDER, COMPONENT_SPECS
from ui.theme import BG_DARK, TEXT_SECONDARY


class ComponentsPanel(QWidget):
    """Панель со списком базовых компонентов Arduino-набора."""

    component_chosen = pyqtSignal(str)  # испускает component_type

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {BG_DARK};")
        self.setMinimumWidth(200)
        self.setMaximumWidth(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("КОМПОНЕНТЫ")
        title.setObjectName("SectionLabel")
        layout.addWidget(title)

        hint = QLabel("Выберите компонент, чтобы добавить его на схему")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(hint)

        self.list_widget = QListWidget()
        self.list_widget.setSpacing(4)
        for component_type in COMPONENT_ORDER:
            spec = COMPONENT_SPECS[component_type]
            item = QListWidgetItem(f"  {spec['label']}")
            item.setData(Qt.UserRole, component_type)
            item.setForeground(QColor(spec["color"]))
            self.list_widget.addItem(item)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget, stretch=1)

        wires_hint = QLabel(
            "Подключение проводов:\n"
            "кликните по контакту компонента, затем по контакту платы "
            "(или другого компонента), чтобы создать провод.\n\n"
            "Колесо мыши — масштаб поля.\n"
            "Средняя кнопка / ЛКМ по пустому месту — перемещение поля.\n"
            "Delete — удалить выделенный провод/компонент."
        )
        wires_hint.setWordWrap(True)
        wires_hint.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; padding-top: 8px;")
        layout.addWidget(wires_hint)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        component_type = item.data(Qt.UserRole)
        if component_type:
            self.component_chosen.emit(component_type)
