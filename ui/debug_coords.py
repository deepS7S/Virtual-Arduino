"""
Модуль отладки координат на схеме.

Позволяет выводить координаты всех элементов сцены при нажатии Ctrl+D.
Полезно для настройки позиций пинов на изображении платы и компонентов.
"""

from PyQt5.QtWidgets import QMessageBox



class DebugCoordinator:
    """Класс для отладки координат элементов на сцене."""

    def __init__(self, scene, view, parent=None):
        self.scene = scene
        self.view = view
        self.parent = parent
        self.enabled = True

    def toggle_debug(self):
        """Включает/выключает режим отладки."""
        self.enabled = not self.enabled
        status = "включён" if self.enabled else "выключен"
        if self.parent and hasattr(self.parent, 'status_label'):
            self.parent.status_label.setText(f"Режим отладки {status}")

    def dump_coordinates(self):
        """Выводит все координаты в консоль и показывает диалог."""
        if not self.enabled:
            return

        output = self._collect_coordinates()

        # Вывод в консоль
        print("\n" + "=" * 80)
        print("КООРДИНАТЫ ЭЛЕМЕНТОВ НА СЦЕНЕ")
        print("=" * 80)
        print(output)
        print("=" * 80 + "\n")

        # Показываем диалог
        QMessageBox.information(
            self.view,
            "Координаты элементов",
            output,
            QMessageBox.Ok
        )

    def _collect_coordinates(self):
        """Собирает координаты всех элементов."""
        lines = []

        # Информация о сцене
        rect = self.scene.sceneRect()
        lines.append(f"СЦЕНА:")
        lines.append(f"  Размер: {int(rect.width())} x {int(rect.height())}")
        lines.append(f"  Центр: ({int(rect.center().x())}, {int(rect.center().y())})")
        lines.append("")

        # Плата Arduino
        board = self.scene.board
        if board:
            lines.append("ПЛАТА ARDUINO UNO:")
            lines.append(f"  Позиция: ({int(board.pos().x())}, {int(board.pos().y())})")
            lines.append(f"  Размер: {int(board.width)} x {int(board.height)}")
            lines.append(
                f"  Центр: ({int(board.pos().x() + board.width / 2)}, {int(board.pos().y() + board.height / 2)})")
            lines.append("")

            # Пины платы
            lines.append("  ПИНЫ ПЛАТЫ:")
            for pin in board.pins:
                pos = pin.scene_center()
                lines.append(f"    {pin.pin_name:6} -> ({int(pos.x()):4}, {int(pos.y()):4})  [id: {pin.pin_id}]")
            lines.append("")

        # Компоненты
        if self.scene.components:
            lines.append(f"КОМПОНЕНТЫ ({len(self.scene.components)}):")
            for i, comp in enumerate(self.scene.components):
                lines.append(f"\n  {i + 1}. {comp.spec['label']} (id: {comp.instance_id})")
                lines.append(f"    Тип: {comp.component_type}")
                lines.append(f"    Позиция: ({int(comp.pos().x())}, {int(comp.pos().y())})")
                lines.append(f"    Размер: {int(comp.width)} x {int(comp.height)}")
                lines.append(
                    f"    Центр: ({int(comp.pos().x() + comp.width / 2)}, {int(comp.pos().y() + comp.height / 2)})")

                # Параметры компонента
                if comp.params:
                    lines.append("    Параметры:")
                    for key, value in comp.params.items():
                        spec = comp.spec.get("params", {}).get(key, {})
                        label = spec.get("label", key)
                        lines.append(f"      {label}: {value}")

                # Пины компонента
                if comp.pins:
                    lines.append("    Пины:")
                    for pin in comp.pins:
                        pos = pin.scene_center()
                        lines.append(f"      {pin.pin_name:10} -> ({int(pos.x()):4}, {int(pos.y()):4})")
            lines.append("")

        # Провода
        if self.scene.wires:
            lines.append(f"ПРОВОДА ({len(self.scene.wires)}):")
            for i, wire in enumerate(self.scene.wires):
                start = wire.start_pin.scene_center()
                end = wire.end_pin.scene_center()
                lines.append(f"  {i + 1}. {wire.start_pin.pin_name} -> {wire.end_pin.pin_name}")
                lines.append(f"    Старт: ({int(start.x())}, {int(start.y())})")
                lines.append(f"    Конец: ({int(end.x())}, {int(end.y())})")
            lines.append("")

        # Общая статистика
        lines.append("СТАТИСТИКА:")
        lines.append(f"  Компонентов: {len(self.scene.components)}")
        lines.append(f"  Проводов: {len(self.scene.wires)}")
        lines.append(f"  Всего пинов: {len(self.scene.board.pins) + sum(len(c.pins) for c in self.scene.components)}")

        return "\n".join(lines)

    def get_pin_positions_for_config(self):
        """
        Возвращает координаты пинов в формате, удобном для настройки
        в components_data.py.
        """
        board = self.scene.board
        if not board:
            return

        lines = []
        lines.append("КОНФИГУРАЦИЯ ПИНОВ ДЛЯ components_data.py:")
        lines.append("")
        lines.append("UNO_BOARD_WIDTH = %d" % int(board.width))
        lines.append("UNO_BOARD_HEIGHT = %d" % int(board.height))
        lines.append("")

        lines.append("# Верхний ряд пинов:")
        for pin in board.pins[:16]:  # Первые 16 пинов - верхний ряд
            pos = pin.scene_center()
            scene_pos = board.mapFromScene(pos)
            lines.append(
                f'    {{"name": "{pin.pin_name}", "dx": {int(scene_pos.x())}, "dy": {int(scene_pos.y())}, "color": PIN_DIGITAL}},')
        lines.append("")

        lines.append("# Нижний ряд пинов:")
        for pin in board.pins[16:]:  # Остальные пины - нижний ряд
            pos = pin.scene_center()
            scene_pos = board.mapFromScene(pos)
            lines.append(
                f'    {{"name": "{pin.pin_name}", "dx": {int(scene_pos.x())}, "dy": {int(scene_pos.y())}, "color": PIN_DIGITAL}},')

        print("\n" + "\n".join(lines) + "\n")