"""
Индикатор координат курсора на схеме.

Показывает текущие координаты мыши в реальном времени.
Полезно для настройки позиций пинов и компонентов.
"""

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QLabel


class CursorCoordLabel(QLabel):
    """Виджет для отображения координат курсора."""

    def __init__(self, view, parent=None):
        super().__init__(parent)
        self.view = view
        self.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 180);
                color: #00ff00;
                font-family: 'Consolas', monospace;
                font-size: 12px;
                padding: 4px 8px;
                border: 1px solid #00ff00;
                border-radius: 3px;
            }
        """)
        self.setAlignment(Qt.AlignCenter)
        self.setText("X: 0, Y: 0")
        self.setFixedWidth(200)
        self.setFixedHeight(30)

        # Таймер для обновления (опционально)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_coords)
        self.timer.start(50)  # Обновляем каждые 50 мс

        # Показываем виджет поверх всего
        self.raise_()
        self.setWindowFlags(Qt.ToolTip)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def update_coords(self):
        """Обновляет координаты курсора."""
        if not self.view or not self.view.underMouse():
            return

        # Получаем позицию курсора в сцене
        mouse_pos = self.view.mapFromGlobal(self.view.cursor().pos())
        scene_pos = self.view.mapToScene(mouse_pos)

        # Обновляем текст
        self.setText(f"X: {int(scene_pos.x()):4}, Y: {int(scene_pos.y()):4}")

        # Перемещаем виджет рядом с курсором
        cursor_pos = self.view.cursor().pos()
        self.move(cursor_pos.x() + 15, cursor_pos.y() + 15)

        # Показываем/скрываем в зависимости от режима
        if hasattr(self.view, 'show_coords') and self.view.show_coords:
            self.show()
        else:
            self.hide()