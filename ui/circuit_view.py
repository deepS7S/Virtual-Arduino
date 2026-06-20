"""
Сцена и представление визуального редактора схем.

CircuitScene  - QGraphicsScene, которая хранит плату Arduino UNO, компоненты
                и провода; умеет создавать/удалять провода по клику на пины
                и сериализовать/десериализовать своё состояние в dict (для
                сохранения внутри файла проекта в circuit/schema.json).
CircuitView   - QGraphicsView с зумом колесом мыши и панорамированием
                средней кнопкой мыши (или левой кнопкой по пустому месту).
"""

from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QBrush, QColor, QPainter
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView, QMenu, QMessageBox

from ui.circuit_items import ArduinoUnoItem, ComponentItem, PinItem, WireItem
from ui.component_settings_dialog import ComponentSettingsDialog
from ui.cursor_coords import CursorCoordLabel
from ui.debug_coords import DebugCoordinator
from ui.theme import BG_DARKEST


class CircuitScene(QGraphicsScene):
    """Сцена со схемой: плата Arduino UNO, компоненты, провода."""

    def __init__(self):
        super().__init__()
        self.setSceneRect(-1500, -1500, 3000, 3000)
        self.setBackgroundBrush(QBrush(QColor(BG_DARKEST)))

        self.board = ArduinoUnoItem()
        self.board.setPos(-self.board.width / 2, -self.board.height / 2)
        self.addItem(self.board)

        self.components = []
        self.wires = []
        self._pending_pin = None

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        grid = 20
        left = int(rect.left()) - (int(rect.left()) % grid)
        top = int(rect.top()) - (int(rect.top()) % grid)

        painter.setPen(QColor(45, 45, 45))
        x = left
        while x < rect.right():
            painter.drawLine(int(x), int(rect.top()), int(x), int(rect.bottom()))
            x += grid
        y = top
        while y < rect.bottom():
            painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))
            y += grid

    def add_component(self, component_type, scene_pos=None):
        item = ComponentItem(component_type)
        if scene_pos is None:
            scene_pos = QPointF(
                self.board.width / 2 + 60,
                -self.board.height / 2 + 40 * (len(self.components) % 6),
            )
        item.setPos(scene_pos)
        self.addItem(item)
        self.components.append(item)
        return item

    def remove_component(self, item):
        for pin in list(item.pins):
            for wire in list(pin.connected_wires):
                self.remove_wire(wire)
        if item in self.components:
            self.components.remove(item)
        self.removeItem(item)

    def on_component_moved(self, item):
        for pin in item.pins:
            for wire in pin.connected_wires:
                wire.update_path()

    def handle_pin_clicked(self, pin):
        if self._pending_pin is None:
            self._pending_pin = pin
            pin.setBrush(QBrush(QColor("#ffffff")))
            return

        if pin is self._pending_pin:
            self._reset_pending_pin()
            return

        if pin.owner is self._pending_pin.owner:
            self._reset_pending_pin()
            return

        wire = WireItem(self._pending_pin, pin)
        self.addItem(wire)
        self.wires.append(wire)
        self._reset_pending_pin()

    def _reset_pending_pin(self):
        if self._pending_pin is not None:
            self._pending_pin.setBrush(QBrush(self._pending_pin._base_color))
        self._pending_pin = None

    def remove_wire(self, wire):
        wire.detach()
        if wire in self.wires:
            self.wires.remove(wire)
        self.removeItem(wire)

    def remove_selected(self):
        for item in list(self.selectedItems()):
            if isinstance(item, WireItem):
                self.remove_wire(item)
            elif isinstance(item, ComponentItem):
                self.remove_component(item)

    def to_dict(self):
        return {
            "board": "Arduino UNO",
            "components": [c.to_dict() for c in self.components],
            "wires": [w.to_dict() for w in self.wires],
        }

    def load_from_dict(self, data):
        for component in list(self.components):
            self.remove_component(component)

        pin_lookup = {pin.pin_id: pin for pin in self.board.pins}

        for comp_data in data.get("components", []):
            item = ComponentItem(comp_data["type"], instance_id=comp_data.get("instance_id"))
            item.setPos(comp_data.get("x", 0), comp_data.get("y", 0))
            # Загружаем параметры, если есть
            if "params" in comp_data:
                item.params = comp_data["params"]
                item.apply_params()
            self.addItem(item)
            self.components.append(item)
            for pin in item.pins:
                pin_lookup[pin.pin_id] = pin

        for wire_data in data.get("wires", []):
            start = pin_lookup.get(wire_data.get("start_pin"))
            end = pin_lookup.get(wire_data.get("end_pin"))
            if start is not None and end is not None:
                wire = WireItem(start, end)
                self.addItem(wire)
                self.wires.append(wire)


class CircuitView(QGraphicsView):
    """
    Представление схемы: колесо мыши - зум, средняя кнопка (или левая по
    пустому месту) - панорамирование, Delete - удаление выделенного.
    """

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)
        self._zoom = 1.0
        self._panning = False
        self._pan_start = None
        self.centerOn(0, 0)

        # Флаг показа координат
        self.show_coords = False

        # Инициализация отладчика координат
        self.debug_coordinator = DebugCoordinator(scene, self, parent)

        # Создаём индикатор координат
        self.coord_label = CursorCoordLabel(self, parent)
        self.coord_label.hide()  # По умолчанию скрыт

        # Отслеживаем движение мыши для обновления координат
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        # Обновляем координаты если включены
        if self.show_coords and hasattr(self, 'coord_label'):
            scene_pos = self.mapToScene(event.pos())
            self.coord_label.setText(f"X: {int(scene_pos.x()):4}, Y: {int(scene_pos.y()):4}")
            # Перемещаем виджет
            cursor_pos = self.mapToGlobal(event.pos())
            self.coord_label.move(cursor_pos.x() + 15, cursor_pos.y() + 15)

        if self._panning and self._pan_start is not None:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()
            h_bar.setValue(h_bar.value() - delta.x())
            v_bar.setValue(v_bar.value() - delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        new_zoom = self._zoom * factor
        if 0.2 <= new_zoom <= 4.0:
            self._zoom = new_zoom
            self.scale(factor, factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton or (
            event.button() == Qt.LeftButton
            and event.modifiers() == Qt.NoModifier
            and self.itemAt(event.pos()) is None
        ):
            self._panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._panning and event.button() in (Qt.MiddleButton, Qt.LeftButton):
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        # Ctrl+Shift+C - показать/скрыть координаты курсора
        if event.key() == Qt.Key_C and event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier):
            self.toggle_cursor_coords()
            event.accept()
            return

        # Ctrl+D - отладка координат
        if event.key() == Qt.Key_D and event.modifiers() == Qt.ControlModifier:
            self.debug_coordinator.dump_coordinates()
            event.accept()
            return

        # Ctrl+Shift+D - показать конфигурацию пинов
        if event.key() == Qt.Key_D and event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier):
            self.debug_coordinator.get_pin_positions_for_config()
            event.accept()
            return

        # Ctrl+Alt+D - включить/выключить режим отладки
        if event.key() == Qt.Key_D and event.modifiers() == (Qt.ControlModifier | Qt.AltModifier):
            self.debug_coordinator.toggle_debug()
            event.accept()
            return

        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.scene().remove_selected()
            event.accept()
            return
        if event.key() == Qt.Key_0 and event.modifiers() == Qt.ControlModifier:
            self.reset_zoom()
            event.accept()
            return
        super().keyPressEvent(event)

    def toggle_cursor_coords(self):
        """Включает/выключает отображение координат курсора."""
        self.show_coords = not self.show_coords
        if self.show_coords:
            self.coord_label.show()
            status = "включено"
        else:
            self.coord_label.hide()
            status = "выключено"

        if self.parent() and hasattr(self.parent(), 'status_label'):
            self.parent().status_label.setText(f"Отображение координат {status}")

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())

        if item and isinstance(item, PinItem):
            item = item.owner

        if isinstance(item, ComponentItem):
            menu = QMenu(self)
            properties_action = menu.addAction("⚙ Настройки")
            delete_action = menu.addAction("🗑 Удалить")
            menu.addSeparator()
            info_action = menu.addAction("ℹ Информация")
            debug_action = menu.addAction("🔍 Координаты")
            coords_action = menu.addAction("📍 Координаты курсора")

            action = menu.exec_(event.globalPos())

            if action == properties_action:
                self._show_component_settings(item)
            elif action == delete_action:
                item.setSelected(True)
                self.scene().remove_selected()
            elif action == info_action:
                self._show_component_info(item)
            elif action == debug_action:
                self.debug_coordinator.dump_coordinates()
            elif action == coords_action:
                self.toggle_cursor_coords()

        elif isinstance(item, WireItem):
            menu = QMenu(self)
            delete_action = menu.addAction("🗑 Удалить провод")
            coords_action = menu.addAction("📍 Координаты курсора")
            action = menu.exec_(event.globalPos())

            if action == delete_action:
                item.setSelected(True)
                self.scene().remove_selected()
            elif action == coords_action:
                self.toggle_cursor_coords()
        else:
            # Стандартное контекстное меню для пустого места
            menu = QMenu(self)
            delete_action = menu.addAction("Удалить выделенное")
            coords_action = menu.addAction("📍 Координаты курсора")
            debug_action = menu.addAction("🔍 Координаты всех элементов")
            action = menu.exec_(event.globalPos())
            if action == delete_action:
                self.scene().remove_selected()
            elif action == coords_action:
                self.toggle_cursor_coords()
            elif action == debug_action:
                self.debug_coordinator.dump_coordinates()

    def _show_component_settings(self, component):
        """Показывает диалог настроек компонента."""
        dialog = ComponentSettingsDialog(component, self)
        if dialog.exec_() == ComponentSettingsDialog.Accepted:
            # Обновляем внешний вид компонента
            component.apply_params()
            # Обновляем сцену
            self.scene().update()
            # Показываем сообщение
            if self.parent() and hasattr(self.parent(), 'status_label'):
                self.parent().status_label.setText(f"Настройки компонента {component.spec['label']} обновлены")

    def _show_component_info(self, component):
        """Показывает информацию о компоненте."""
        info = f"Тип: {component.spec['label']}\n"
        info += f"ID: {component.instance_id}\n"
        info += f"Позиция: ({int(component.pos().x())}, {int(component.pos().y())})\n"
        info += f"Количество пинов: {len(component.pins)}\n\n"
        info += "Параметры:\n"
        for param_name, param_value in component.params.items():
            param_config = component.spec.get("params", {}).get(param_name, {})
            label = param_config.get("label", param_name)
            info += f"  {label}: {param_value}\n"

        QMessageBox.information(self, "Информация о компоненте", info)

    def reset_zoom(self):
        self.resetTransform()
        self._zoom = 1.0
        self.centerOn(0, 0)