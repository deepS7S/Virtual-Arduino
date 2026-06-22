"""
Графические элементы (QGraphicsItem) визуального редактора схем:

  PinItem        - контактная точка компонента или платы, к которой можно
                    подключить провод;
  ComponentItem   - обобщённый компонент из набора Arduino (LED, резистор,
                    кнопка, потенциометр, зуммер, фоторезистор, сервопривод,
                    мотор постоянного тока) - перетаскивается по полю;
  ArduinoUnoItem  - неподвижное изображение платы Arduino UNO с пинами;
  WireItem        - провод, соединяющий два пина и обновляющий свою
                    геометрию при перемещении компонентов.
"""

import math
import time
import uuid
from pathlib import Path

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsPixmapItem,
    QGraphicsTextItem,
)

from core.components_data import COMPONENT_SPECS, UNO_BOARD_HEIGHT, UNO_BOARD_WIDTH, build_uno_pins
from ui.theme import BOARD_PCB, BOARD_PCB_DARK, BOARD_SILK, WIRE_DEFAULT

PIN_RADIUS = 5


class PinItem(QGraphicsEllipseItem):
    """Контактная точка. Клик по пину начинает/завершает прокладку провода."""

    def __init__(self, owner, pin_id, name, x, y, color="#d4af37"):
        super().__init__(-PIN_RADIUS, -PIN_RADIUS, PIN_RADIUS * 2, PIN_RADIUS * 2, owner)
        self.owner = owner
        self.pin_id = pin_id
        self.pin_name = name
        self.setPos(x, y)
        self._base_color = QColor(color)
        self.setBrush(QBrush(self._base_color))
        self.setPen(QPen(QColor("#000000"), 0.5))
        self.setAcceptHoverEvents(True)
        self.setZValue(10)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(name)
        self.connected_wires = []

    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(QColor(WIRE_DEFAULT)))
        r = PIN_RADIUS * 1.6
        self.setRect(-r, -r, r * 2, r * 2)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(QBrush(self._base_color))
        self.setRect(-PIN_RADIUS, -PIN_RADIUS, PIN_RADIUS * 2, PIN_RADIUS * 2)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        scene = self.scene()
        if scene is not None and hasattr(scene, "handle_pin_clicked"):
            scene.handle_pin_clicked(self)
        event.accept()

    def scene_center(self):
        return self.mapToScene(0, 0)


class WireNode(QGraphicsEllipseItem):
    """
    Свободная (не привязанная к компоненту) точка соединения провода.
    Новый класс для пункта чек-листа 1.1/1.4/1.5: провод теперь — полноценный
    объект из двух концов (PinItem ИЛИ WireNode), а не просто линия между
    двумя существующими пинами. Узел можно:
      - перетаскивать по полю (его конец провода тянется следом);
      - кликнуть, чтобы начать/закончить новое соединение (как у PinItem);
      - "уронить" рядом с другим узлом/пином — они автоматически
        притянутся и совместятся (см. CircuitScene._try_snap_node).
    Несколько проводов могут ссылаться на один и тот же WireNode — так
    реализуется разветвление (1.5): достаточно, чтобы новый провод при
    создании использовал существующий узел вместо нового.
    """

    RADIUS = 6
    SNAP_RADIUS = 14

    def __init__(self, x, y, pin_id=None):
        super().__init__(-self.RADIUS, -self.RADIUS, self.RADIUS * 2, self.RADIUS * 2)
        self.owner = None
        self.pin_id = pin_id or f"NODE:{uuid.uuid4().hex[:10]}"
        self.pin_name = "Узел провода"
        self.setPos(x, y)
        self._base_color = QColor("#bdbdbd")
        self.setBrush(QBrush(self._base_color))
        self.setPen(QPen(QColor("#000000"), 0.5))
        self.setZValue(9)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Свободный конец провода — перетащите к пину или другому проводу")
        self.connected_wires = []

        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self._press_scene_pos = None
        self._dragged = False

    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(QColor(WIRE_DEFAULT)))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(QBrush(self._base_color))
        super().hoverLeaveEvent(event)

    def scene_center(self):
        return self.mapToScene(0, 0)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            scene = self.scene()
            if scene is not None and hasattr(scene, "on_node_moved"):
                scene.on_node_moved(self)
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        self._press_scene_pos = event.scenePos()
        self._dragged = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_scene_pos is not None:
            moved = (event.scenePos() - self._press_scene_pos).manhattanLength()
            if moved > 4:
                self._dragged = True
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        scene = self.scene()
        if scene is None:
            return
        if self._dragged:
            if hasattr(scene, "try_snap_node"):
                scene.try_snap_node(self)
        else:
            if hasattr(scene, "handle_pin_clicked"):
                scene.handle_pin_clicked(self)
        self._press_scene_pos = None
        self._dragged = False


class ComponentItem(QGraphicsItem):
    """Обобщённый компонент Arduino-набора, перетаскиваемый мышью."""

    def __init__(self, component_type, instance_id=None):
        super().__init__()
        self.component_type = component_type
        self.instance_id = instance_id or uuid.uuid4().hex[:8]
        self.spec = COMPONENT_SPECS[component_type]
        self.width = self.spec["width"]
        self.height = self.spec["height"]
        self.color = QColor(self.spec["color"])

        # Параметры компонента
        self.params = {}
        for param_name, param_config in self.spec.get("params", {}).items():
            self.params[param_name] = param_config["default"]

        self.setFlags(
            QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setZValue(5)
        self.setCursor(Qt.OpenHandCursor)

        self.pins = []
        for i, pin_spec in enumerate(self.spec["pins"]):
            pin_id = f"{self.instance_id}:{i}"
            pin = PinItem(self, pin_id, pin_spec["name"], pin_spec["dx"], pin_spec["dy"], "#d4af37")
            self.pins.append(pin)

        label = QGraphicsTextItem(self.spec["label"], self)
        label.setDefaultTextColor(QColor("#cccccc"))
        font = QFont()
        font.setPointSize(7)
        label.setFont(font)
        label.setPos(-10, -18)

        # Применяем параметры
        self.apply_params()

        # Подсветка неисправности (короткое замыкание / перегорание) -
        # новое поле для core/electrical_engine.py, см. ui/circuit_view.py
        self.fault_until = 0.0
        self.fault_message = ""

        # Состояние, управляемое движком симуляции (core/simulation_engine.py):
        # светится ли LED, нажата ли кнопка, активен ли зуммер.
        self.sim_led_lit = False
        self.sim_pressed = False
        self.sim_buzzer_active = False

    def boundingRect(self):
        return QRectF(-4, -4, self.width + 8, self.height + 8)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(painter.Antialiasing)
        shape = self.spec["shape"]
        rect = QRectF(0, 0, self.width, self.height)

        pen = QPen(QColor("#000000"), 1)
        if self.isSelected():
            pen = QPen(QColor(WIRE_DEFAULT), 2, Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(QBrush(self.color))

        if shape == "led":
            led_color = QColor(self.color)
            if self.sim_led_lit:
                painter.setBrush(QBrush(led_color.lighter(150)))
                glow = QPen(led_color.lighter(180), 6)
                glow.setColor(QColor(led_color.red(), led_color.green(), led_color.blue(), 90))
                painter.save()
                painter.setPen(glow)
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QRectF(-5, -5, self.width + 10, (self.height * 0.75) + 10))
                painter.restore()
                painter.setBrush(QBrush(led_color.lighter(150)))
            else:
                painter.setBrush(QBrush(led_color.darker(160)))
            painter.drawEllipse(QRectF(0, 0, self.width, self.height * 0.75))
            painter.drawRect(QRectF(self.width * 0.25, self.height * 0.6, self.width * 0.5, self.height * 0.35))
        elif shape == "resistor":
            painter.drawRect(rect)
            # Используем параметры для отображения сопротивления
            resistance = self.params.get("resistance", 1000)
            # Цвета для колец в зависимости от сопротивления
            band_colors = self._get_resistor_bands(resistance)
            band_w = self.width / 8
            for i, c in enumerate(band_colors):
                painter.setBrush(QBrush(QColor(c)))
                painter.drawRect(QRectF(self.width * 0.2 + i * band_w, 0, band_w * 0.6, self.height))
        elif shape == "button":
            painter.drawRoundedRect(rect, 4, 4)
            cap_color = QColor("#90a4ae") if self.sim_pressed else QColor("#cfd8dc")
            painter.setBrush(QBrush(cap_color))
            inset = self.width * 0.22
            if self.sim_pressed:
                inset += 2
            painter.drawRoundedRect(QRectF(inset, inset, self.width - 2 * inset, self.height - 2 * inset), 3, 3)
        elif shape == "potentiometer":
            painter.drawEllipse(rect)
            painter.setBrush(QBrush(QColor("#d4af37")))
            painter.drawEllipse(QRectF(self.width * 0.35, self.height * 0.1, self.width * 0.3, self.height * 0.3))
            # Рисуем отметку в зависимости от угла
            angle = self.params.get("angle", 270)
            painter.setPen(QPen(QColor("#000000"), 2))
            rad = math.radians(angle / 2)
            x = self.width / 2 + self.width * 0.3 * math.cos(rad)
            y = self.height / 2 + self.height * 0.3 * math.sin(rad)
            painter.drawLine(int(self.width / 2), int(self.height / 2), int(x), int(y))
        elif shape == "buzzer":
            painter.drawEllipse(rect)
            painter.setPen(QPen(QColor("#cfd8dc"), 1))
            painter.drawEllipse(QRectF(self.width * 0.2, self.height * 0.2, self.width * 0.6, self.height * 0.6))
            if self.sim_buzzer_active:
                painter.setPen(QPen(QColor("#ffca28"), 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QRectF(-6, -6, self.width + 12, self.height + 12))
        elif shape == "photoresistor":
            painter.drawRoundedRect(rect, 6, 6)
            painter.setPen(QPen(QColor("#2b2b2b"), 1.5))
            for i in range(4):
                x = self.width * (0.15 + i * 0.22)
                painter.drawLine(QPointF(x, self.height * 0.2), QPointF(x + 5, self.height * 0.8))
        elif shape == "servo":
            painter.drawRoundedRect(rect, 3, 3)
            painter.setBrush(QBrush(QColor("#0d47a1")))
            painter.drawRect(QRectF(self.width * 0.35, -self.height * 0.18, self.width * 0.3, self.height * 0.18))
        elif shape == "dc_motor":
            painter.drawEllipse(rect)
            painter.setBrush(QBrush(QColor("#cfd8dc")))
            painter.drawEllipse(QRectF(self.width * 0.38, self.height * 0.38, self.width * 0.24, self.height * 0.24))
        else:
            painter.drawRect(rect)

        if self.fault_until and time.time() < self.fault_until:
            glow_pen = QPen(QColor("#ff1744"), 3, Qt.SolidLine)
            painter.setPen(glow_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(QRectF(-4, -4, self.width + 8, self.height + 8), 6, 6)

    def mark_fault(self, message, duration_sec=5.0):
        """Подсвечивает компонент красным на duration_sec секунд (см. electrical_engine.Fault)."""
        self.fault_message = message
        self.fault_until = time.time() + duration_sec
        self.setToolTip(message)
        self.update()

    def _get_resistor_bands(self, resistance):
        """Возвращает цвета для колец резистора на основе сопротивления."""
        # Упрощённая реализация для демонстрации
        colors = ["#8d6e63", "#000000", "#f44336", "#d4af37"]
        if resistance < 100:
            colors = ["#8d6e63", "#000000", "#000000", "#d4af37"]  # 10 Ом
        elif resistance < 1000:
            colors = ["#8d6e63", "#000000", "#f44336", "#d4af37"]  # 100 Ом
        elif resistance < 10000:
            colors = ["#8d6e63", "#000000", "#ff9800", "#d4af37"]  # 1 кОм
        elif resistance < 100000:
            colors = ["#8d6e63", "#000000", "#4caf50", "#d4af37"]  # 10 кОм
        elif resistance < 1000000:
            colors = ["#8d6e63", "#000000", "#2196f3", "#d4af37"]  # 100 кОм
        else:
            colors = ["#8d6e63", "#000000", "#9c27b0", "#d4af37"]  # 1 МОм
        return colors

    def apply_params(self):
        """Применяет параметры к компоненту (обновляет внешний вид)."""
        if self.component_type == "led":
            led_color = self.params.get("color", self.spec["color"])
            self.color = QColor(led_color)

        self.update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            scene = self.scene()
            if scene is not None and hasattr(scene, "on_component_moved"):
                scene.on_component_moved(self)
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        scene = self.scene()
        if self.component_type == "button" and scene is not None and getattr(scene, "simulation_running", False):
            self.sim_pressed = True
            self.update()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.component_type == "button" and self.sim_pressed:
            self.sim_pressed = False
            self.update()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def to_dict(self):
        return {
            "instance_id": self.instance_id,
            "type": self.component_type,
            "x": self.pos().x(),
            "y": self.pos().y(),
            "params": self.params,
        }


class ArduinoUnoItem(QGraphicsItem):
    """Неподвижное изображение платы Arduino UNO с пинами."""

    BOARD_WIDTH = 460
    BOARD_HEIGHT = 340

    def __init__(self):
        super().__init__()
        self.setZValue(1)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)

        # Загружаем изображение
        self.pixmap = self._load_pixmap()

        # Если изображение загружено, используем его размеры, иначе стандартные
        if not self.pixmap.isNull():
            self.width = self.pixmap.width()
            self.height = self.pixmap.height()
        else:
            self.width = self.BOARD_WIDTH
            self.height = self.BOARD_HEIGHT

        # Создаём пины
        self.pins = []
        for i, pin_spec in enumerate(build_uno_pins()):
            pin_id = f"UNO:{i}"
            pin = PinItem(
                self,
                pin_id,
                pin_spec["name"],
                pin_spec["dx"],
                pin_spec["dy"],
                pin_spec["color"]
            )
            self.pins.append(pin)

    def _load_pixmap(self):
        """Загружает изображение платы."""
        # Ищем изображение в нескольких местах
        paths = [
            Path("resources/images/ArduinoUNO.png"),
            Path("../resources/images/ArduinoUNO.png"),
            Path(__file__).parent.parent / "resources" / "images" / "ArduinoUNO.png",
        ]

        for path in paths:
            if path.exists():
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    # Масштабируем под нужный размер
                    return pixmap.scaled(
                        self.BOARD_WIDTH,
                        self.BOARD_HEIGHT,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )

        # Если изображение не найдено, создаём заглушку
        print(f"Предупреждение: Изображение ArduinoUNO.png не найдено. Искал в: {paths}")
        return QPixmap()

    def boundingRect(self):
        return QRectF(-10, -30, self.width + 20, self.height + 60)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(painter.Antialiasing)

        if not self.pixmap.isNull():
            # Рисуем изображение
            painter.drawPixmap(0, 0, self.pixmap)
        else:
            # Fallback: рисуем заглушку
            self._draw_placeholder(painter)

    def _draw_placeholder(self, painter):
        """Рисует заглушку, если изображение не загружено."""
        body_rect = QRectF(0, 0, self.width, self.height)
        painter.setPen(QPen(QColor(BOARD_PCB_DARK), 1.5))
        painter.setBrush(QBrush(QColor(BOARD_PCB)))
        painter.drawRoundedRect(body_rect, 8, 8)

        painter.setBrush(QBrush(QColor("#b0bec5")))
        painter.setPen(QPen(QColor("#37474f"), 1))
        painter.drawRect(QRectF(-10, self.height * 0.12, 14, 34))
        painter.drawRoundedRect(QRectF(-6, self.height * 0.65, 16, 24), 3, 3)

        painter.setPen(QColor(BOARD_SILK))
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(0, self.height * 0.32, self.width, 30), Qt.AlignCenter, "ARDUINO")
        font.setPointSize(9)
        font.setBold(False)
        painter.setFont(font)
        painter.drawText(QRectF(0, self.height * 0.32 + 22, self.width, 22), Qt.AlignCenter, "UNO")

        painter.setBrush(QBrush(QColor("#1a1a1a")))
        painter.setPen(QPen(QColor("#000000"), 1))
        chip_w, chip_h = self.width * 0.22, self.height * 0.16
        chip_rect = QRectF(self.width * 0.5 - chip_w / 2, self.height * 0.58, chip_w, chip_h)
        painter.drawRect(chip_rect)
        painter.setPen(QColor("#cfd8dc"))
        small_font = QFont()
        small_font.setPointSize(6)
        painter.setFont(small_font)
        painter.drawText(chip_rect, Qt.AlignCenter, "ATmega328P")

        painter.setPen(QColor(BOARD_SILK))
        painter.setFont(small_font)
        painter.drawText(QRectF(0, -18, self.width, 14), Qt.AlignCenter, "DIGITAL (PWM~)")
        painter.drawText(QRectF(0, self.height + 4, self.width, 14), Qt.AlignCenter, "POWER   ANALOG IN")

    def to_dict(self):
        return {"instance_id": "UNO", "type": "arduino_uno", "x": self.pos().x(), "y": self.pos().y()}


class WireItem(QGraphicsPathItem):
    """Провод между двумя пинами. Геометрия пересчитывается при перемещении."""

    def __init__(self, start_pin, end_pin, color=None):
        super().__init__()
        self.start_pin = start_pin
        self.end_pin = end_pin
        self.color = QColor(color or WIRE_DEFAULT)
        self.setZValue(2)
        self.setPen(QPen(self.color, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        start_pin.connected_wires.append(self)
        end_pin.connected_wires.append(self)
        self.update_path()

    def update_path(self):
        """Провод теперь прямая линия 'из точки А в точку Б' (п. 1.2 чек-листа)."""
        start = self.start_pin.scene_center()
        end = self.end_pin.scene_center()
        path = QPainterPath(start)
        path.lineTo(end)
        self.setPath(path)

    def set_color(self, color):
        """Новый метод: смена цвета провода через контекстное меню (п. 1.3)."""
        self.color = QColor(color)
        pen = self.pen()
        pen.setColor(self.color)
        self.setPen(pen)
        self.update()

    def detach(self):
        if self in self.start_pin.connected_wires:
            self.start_pin.connected_wires.remove(self)
        if self in self.end_pin.connected_wires:
            self.end_pin.connected_wires.remove(self)

    def paint(self, painter, option, widget=None):
        if self.isSelected():
            pen = QPen(QColor("#ffffff"), 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        else:
            pen = self.pen()
        painter.setPen(pen)
        painter.drawPath(self.path())

    def to_dict(self):
        return {"start_pin": self.start_pin.pin_id, "end_pin": self.end_pin.pin_id}