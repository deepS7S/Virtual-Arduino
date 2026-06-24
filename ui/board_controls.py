"""
ui/board_controls.py
======================
Кнопки загрузки кода (Upload) и питания (Power) на плате Arduino UNO.

Редизайн: вместо простых кружков — аккуратные прямоугольные кнопки
в стиле физических PCB-компонентов:
  - скруглённый прямоугольник с тонкой рамкой и 3D-фаской (светлый верх,
    тёмный низ), как настоящая тактильная кнопка на плате;
  - крупная иконка по центру + подпись под кнопкой (UPLOAD / POWER);
  - выраженный idle-цвет (кнопки заметны даже без наведения);
  - нажатое/активное состояние — кнопка «утоплена» (фаска инвертируется),
    цвет меняется.
  - обе кнопки стоят вертикально рядом, в левой части PCB.
"""

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QLinearGradient, QPen
from PyQt5.QtWidgets import QGraphicsItem

# Размеры тела кнопки
BTN_W = 40        # ширина кнопки
BTN_H = 36        # высота кнопки
LABEL_H = 13      # высота области подписи под кнопкой
TOTAL_H = BTN_H + LABEL_H   # полная высота виджета (для boundingRect)
RADIUS = 5        # скругление углов


class _BoardButton(QGraphicsItem):
    """
    Базовый класс кнопки на плате: прямоугольник с фаской + иконка + подпись.
    """

    def __init__(self, parent_board, icon_text, label_text, tooltip,
                 on_click, idle_top, idle_bot, active_top, active_bot,
                 border_idle, border_active):
        super().__init__(parent_board)
        self.on_click = on_click
        self.icon_text = icon_text
        self.label_text = label_text

        # Цвета градиента тела (idle)
        self.idle_top = QColor(idle_top)
        self.idle_bot = QColor(idle_bot)
        # Цвета градиента тела (active / pressed)
        self.active_top = QColor(active_top)
        self.active_bot = QColor(active_bot)
        self.border_idle = QColor(border_idle)
        self.border_active = QColor(border_active)

        self.active = False
        self._hovered = False
        self._pressed = False

        self.setToolTip(tooltip)
        self.setCursor(Qt.PointingHandCursor)
        self.setAcceptHoverEvents(True)
        self.setZValue(50)

    def boundingRect(self):
        return QRectF(-2, -2, BTN_W + 4, TOTAL_H + 4)

    def set_active(self, active):
        self.active = active
        self.update()

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(painter.Antialiasing)

        body = QRectF(0, 0, BTN_W, BTN_H)
        is_down = self.active or self._pressed

        # --- Градиент тела ---
        grad = QLinearGradient(QPointF(0, 0), QPointF(0, BTN_H))
        if is_down:
            # Активное/нажатое: инвертируем градиент (эффект утопленности)
            top_c = self.active_bot
            bot_c = self.active_top
        else:
            top_c = self.idle_top
            bot_c = self.idle_bot
        if self._hovered and not is_down:
            top_c = top_c.lighter(115)
            bot_c = bot_c.lighter(115)
        grad.setColorAt(0, top_c)
        grad.setColorAt(1, bot_c)

        # --- Тень под кнопкой (имитация рельефа) ---
        shadow_rect = QRectF(2, 2, BTN_W, BTN_H)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 80)))
        painter.drawRoundedRect(shadow_rect, RADIUS, RADIUS)

        # --- Основное тело ---
        border_color = self.border_active if is_down else self.border_idle
        pen = QPen(border_color, 1.5)
        painter.setPen(pen)
        painter.setBrush(QBrush(grad))
        painter.drawRoundedRect(body, RADIUS, RADIUS)

        # --- Верхняя фаска (светлая полоска — 3D-эффект выступания) ---
        if not is_down:
            highlight = QColor(255, 255, 255, 55)
            bevel_pen = QPen(highlight, 1)
            painter.setPen(bevel_pen)
            painter.setBrush(Qt.NoBrush)
            bevel = QRectF(1.5, 1.5, BTN_W - 3, BTN_H - 3)
            painter.drawRoundedRect(bevel, RADIUS - 1, RADIUS - 1)

        # --- Иконка ---
        icon_color = QColor("#ffffff") if not is_down else QColor("#e0e0e0")
        painter.setPen(icon_color)
        font_icon = QFont("Segoe UI", 14, QFont.Bold)
        painter.setFont(font_icon)
        icon_rect = QRectF(0, -1, BTN_W, BTN_H)
        painter.drawText(icon_rect, Qt.AlignCenter, self.icon_text)

        # --- Подпись под кнопкой ---
        label_rect = QRectF(0, BTN_H + 1, BTN_W, LABEL_H)
        label_color = QColor("#c8c8c8") if not is_down else QColor(self.border_active).lighter(140)
        painter.setPen(label_color)
        font_label = QFont("Segoe UI", 6, QFont.Bold)
        font_label.setLetterSpacing(QFont.AbsoluteSpacing, 0.5)
        painter.setFont(font_label)
        painter.drawText(label_rect, Qt.AlignHCenter | Qt.AlignTop, self.label_text)

    # --- Интерактивность ---
    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self._pressed = False
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        self._pressed = True
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self.update()
        if self.boundingRect().contains(event.pos()) and self.on_click is not None:
            self.on_click()
        event.accept()


class UploadButton(_BoardButton):
    """Кнопка загрузки кода — зелёная, иконка ↑."""

    def __init__(self, parent_board, on_click):
        super().__init__(
            parent_board,
            icon_text="\u2191",
            label_text="UPLOAD",
            tooltip="Загрузить код из редактора в микроконтроллер",
            on_click=on_click,
            # idle: тёмно-зелёный градиент
            idle_top="#2e7d32",
            idle_bot="#1b5e20",
            # active: яркий зелёный (код выполняется)
            active_top="#66bb6a",
            active_bot="#43a047",
            border_idle="#388e3c",
            border_active="#a5d6a7",
        )


class PowerButton(_BoardButton):
    """Кнопка питания — серая (выкл.) / красная (вкл.)."""

    def __init__(self, parent_board, on_click):
        super().__init__(
            parent_board,
            icon_text="\u23fb",
            label_text="POWER",
            tooltip="Подать / отключить питание (5V)",
            on_click=on_click,
            # idle: тёмно-серый
            idle_top="#424242",
            idle_bot="#212121",
            # active: красный
            active_top="#ef5350",
            active_bot="#b71c1c",
            border_idle="#757575",
            border_active="#ff8a80",
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
    upload_btn.setPos(x + 15, chip_center_y - 6 - 95)

    power_btn = PowerButton(board, on_power_toggle)
    power_btn.setPos(x + 42, chip_center_y + 100 - 30)

    return upload_btn, power_btn
