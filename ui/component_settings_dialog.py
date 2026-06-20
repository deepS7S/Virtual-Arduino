"""
Диалог настройки параметров компонента.

Отображает все настраиваемые параметры компонента в зависимости от его типа.
Поддерживает различные типы полей: int, float, bool, choice, color, str.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ui.theme import ACCENT, BG_DARK, BG_INPUT, TEXT_PRIMARY


class ComponentSettingsDialog(QDialog):
    """Диалог настройки параметров компонента."""

    def __init__(self, component, parent=None):
        super().__init__(parent)
        self.component = component
        self.params = component.params.copy()
        self.widgets = {}

        self.setWindowTitle(f"Настройки компонента — {component.spec['label']}")
        self.setMinimumWidth(400)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {BG_DARK};
            }}
            QLabel {{
                color: {TEXT_PRIMARY};
            }}
        """)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Заголовок
        title = QLabel(f"Настройки: {self.component.spec['label']}")
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {ACCENT};")
        layout.addWidget(title)

        # Форма с параметрами
        form = QFormLayout()
        form.setSpacing(8)

        spec_params = self.component.spec.get("params", {})
        for param_name, param_config in spec_params.items():
            current_value = self.params.get(param_name, param_config["default"])
            widget = self._create_widget(param_name, param_config, current_value)
            if widget:
                label = QLabel(param_config["label"])
                form.addRow(label, widget)
                self.widgets[param_name] = widget

        layout.addLayout(form)

        # Кнопки
        buttons = QHBoxLayout()
        buttons.addStretch()

        reset_btn = QPushButton("Сбросить")
        reset_btn.clicked.connect(self._reset_to_defaults)
        buttons.addWidget(reset_btn)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)

        ok_btn = QPushButton("Применить")
        ok_btn.setObjectName("PrimaryButton")
        ok_btn.clicked.connect(self._apply_and_close)
        buttons.addWidget(ok_btn)

        layout.addLayout(buttons)

    def _create_widget(self, param_name, param_config, current_value):
        """Создаёт виджет для параметра в зависимости от его типа."""
        param_type = param_config["type"]

        if param_type == "int":
            widget = QSpinBox()
            widget.setRange(param_config.get("min", -2147483648), param_config.get("max", 2147483647))
            widget.setValue(int(current_value))
            return widget

        elif param_type == "float":
            widget = QDoubleSpinBox()
            widget.setRange(param_config.get("min", -1e9), param_config.get("max", 1e9))
            widget.setDecimals(2)
            widget.setValue(float(current_value))
            return widget

        elif param_type == "bool":
            widget = QCheckBox()
            widget.setChecked(bool(current_value))
            return widget

        elif param_type == "choice":
            widget = QComboBox()
            widget.addItems(param_config.get("choices", []))
            if current_value in param_config.get("choices", []):
                widget.setCurrentText(current_value)
            return widget

        elif param_type == "color":
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(4)

            color_btn = QPushButton("Выбрать цвет")
            color_btn.setFixedWidth(100)

            color_preview = QLabel()
            color_preview.setFixedSize(30, 30)
            color_preview.setStyleSheet(
                f"background-color: {current_value}; border: 1px solid #555; border-radius: 4px;")

            def on_color_click():
                color = QColorDialog.getColor(QColor(current_value), self, "Выберите цвет")
                if color.isValid():
                    hex_color = color.name()
                    color_preview.setStyleSheet(
                        f"background-color: {hex_color}; border: 1px solid #555; border-radius: 4px;")
                    color_btn.setProperty("color", hex_color)

            color_btn.clicked.connect(on_color_click)
            color_btn.setProperty("color", current_value)

            layout.addWidget(color_btn)
            layout.addWidget(color_preview)
            return container

        elif param_type == "str":
            widget = QLineEdit()
            widget.setText(str(current_value))
            return widget

        return None

    def _get_value_from_widget(self, param_name, param_config, widget):
        """Извлекает значение из виджета."""
        param_type = param_config["type"]

        if param_type == "int":
            return widget.value()
        elif param_type == "float":
            return widget.value()
        elif param_type == "bool":
            return widget.isChecked()
        elif param_type == "choice":
            return widget.currentText()
        elif param_type == "color":
            return widget.property("color") or widget.findChild(QPushButton).property("color")
        elif param_type == "str":
            return widget.text()
        return None

    def _reset_to_defaults(self):
        """Сбрасывает все параметры к значениям по умолчанию."""
        spec_params = self.component.spec.get("params", {})
        for param_name, param_config in spec_params.items():
            widget = self.widgets.get(param_name)
            if widget:
                default = param_config["default"]
                self._set_widget_value(widget, param_config["type"], default)

    def _set_widget_value(self, widget, param_type, value):
        """Устанавливает значение виджета."""
        if param_type == "int":
            widget.setValue(int(value))
        elif param_type == "float":
            widget.setValue(float(value))
        elif param_type == "bool":
            widget.setChecked(bool(value))
        elif param_type == "choice":
            index = widget.findText(str(value))
            if index >= 0:
                widget.setCurrentIndex(index)
        elif param_type == "color":
            # Обновляем цвет в виджете
            preview = widget.findChild(QLabel)
            if preview:
                preview.setStyleSheet(f"background-color: {value}; border: 1px solid #555; border-radius: 4px;")
            btn = widget.findChild(QPushButton)
            if btn:
                btn.setProperty("color", value)
        elif param_type == "str":
            widget.setText(str(value))

    def _apply_and_close(self):
        """Применяет настройки и закрывает диалог."""
        spec_params = self.component.spec.get("params", {})
        for param_name, param_config in spec_params.items():
            widget = self.widgets.get(param_name)
            if widget:
                value = self._get_value_from_widget(param_name, param_config, widget)
                if value is not None:
                    self.params[param_name] = value

        # Применяем параметры к компоненту
        self.component.params = self.params
        self.component.apply_params()

        self.accept()