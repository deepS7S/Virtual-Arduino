"""
ui/board_controls.py
======================
Новый модуль: две кликабельные кнопки прямо на изображении платы Arduino
UNO, слева от микроконтроллера (чек-лист, п.4):

    UploadButton (сверху)  - заливает код из редактора в "микроконтроллер"
                              и запускает его выполнение (setup()+loop());
    PowerButton  (снизу)   - подаёт/снимает питание (5V/VIN) на схему.

Это самостоятельные QGraphicsItem, не требующие изменений в ArduinoUnoItem -
создаются в ui/circuit_view.py как дочерние элементы платы (board) и
позиционируются относительно её ширины/высоты, поэтому работают одинаково
и с placeholder-отрисовкой, и с реальным изображением платы.
"""

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPen
from PyQt5.QtWidgets import QGraphicsItem

BUTTON_SIZE = 30


class _BoardButton(QGraphicsItem):
    """Базовый класс кликабельной кнопки на плате."""

    def __init__(self, parent_board, icon_text, tooltip, on_click, idle_color, active_color):
        super().__init__(parent_board)
        self.on_click = on_click
        self.icon_text = icon_text
        self.idle_color = QColor(idle_color)
        self.active_color = QColor(active_color)
        self.active = False
        self.setToolTip(tooltip)
        self.setCursor(Qt.PointingHandCursor)
        self.setAcceptHoverEvents(True)
        self._hovered = False
        self.setZValue(50)

    def boundingRect(self):
        return QRectF(0, 0, BUTTON_SIZE, BUTTON_SIZE)

    def set_active(self, active):
        self.active = active
        self.update()

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(painter.Antialiasing)
        color = self.active_color if self.active else self.idle_color
        if self._hovered:
            color = color.lighter(125)

        painter.setPen(QPen(QColor("#000000"), 1.5))
        painter.setBrush(QBrush(color))
        painter.drawEllipse(self.boundingRect())

        painter.setPen(QColor("#ffffff"))
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.boundingRect(), Qt.AlignCenter, self.icon_text)

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        event.accept()

    def mouseReleaseEvent(self, event):
        if self.boundingRect().contains(event.pos()) and self.on_click is not None:
            self.on_click()
        event.accept()


class UploadButton(_BoardButton):
    """Кнопка заливки кода - сверху, слева от микроконтроллера."""

    def __init__(self, parent_board, on_click):
        super().__init__(
            parent_board, "\u2191", "Загрузить код из редактора в микроконтроллер",
            on_click, idle_color="#3da5d9", active_color="#4caf50",
        )


class PowerButton(_BoardButton):
    """Кнопка подачи питания - снизу, слева от микроконтроллера."""

    def __init__(self, parent_board, on_click):
        super().__init__(
            parent_board, "\u23fb", "Подать/отключить питание (5V)",
            on_click, idle_color="#616161", active_color="#f14c4c",
        )


def place_board_controls(board, on_upload, on_power_toggle):
    """
    Создаёт обе кнопки как дочерние элементы board и позиционирует их
    слева от условного центра микроконтроллера: заливка - сверху,
    питание - снизу
    Возвращает (upload_button, power_button).
    """
    chip_center_x = board.width * 0.46
    chip_center_y = board.height * 0.58
    x = chip_center_x - 200

    upload_btn = UploadButton(board, on_upload)
    upload_btn.setPos(x + 15, chip_center_y - BUTTON_SIZE - 6 - 60)

    power_btn = PowerButton(board, on_power_toggle)
    power_btn.setPos(x + 45, chip_center_y + 100 - 23)

    return upload_btn, power_btn
