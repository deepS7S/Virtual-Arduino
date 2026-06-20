"""
Описание базовых компонентов из набора Arduino ("Arduino пак") и схема
расположения пинов платы Arduino UNO. Координаты пинов заданы в локальной
системе координат компонента (0,0 — верхний левый угол его bounding rect).

Эти данные используются графическим слоем (ui/circuit_items.py) для отрисовки
компонентов и пинов, к которым можно подключать провода.
"""

from ui.theme import PIN_ANALOG, PIN_DIGITAL, PIN_GND, PIN_POWER

#
## Базовые компоненты Arduino-набора
#
# Каждый компонент описан как:
#   type        — уникальный идентификатор типа
#   label       — отображаемое название
#   shape       — форма отрисовки ('led', 'resistor', 'button', 'potentiometer',
#                 'buzzer', 'photoresistor', 'servo', 'dc_motor')
#   width/height— размер корпуса в сценовых единицах
#   color       — основной цвет корпуса
#   pins        — список {name, dx, dy} — позиция пина относительно (0,0)
#   params      — настраиваемые параметры компонента {name: default_value, ...}

COMPONENT_SPECS = {
    "led": {
        "label": "Светодиод (LED)",
        "shape": "led",
        "width": 30,
        "height": 46,
        "color": "#e53935",
        "pins": [
            {"name": "anode (+)", "dx": 9, "dy": 46},
            {"name": "cathode (-)", "dx": 21, "dy": 46},
        ],
        "params": {
            "color": {"type": "color", "default": "#e53935", "label": "Цвет свечения"},
            "brightness": {"type": "int", "default": 255, "label": "Яркость (0-255)", "min": 0, "max": 255},
            "forward_voltage": {"type": "float", "default": 2.0, "label": "Прямое напряжение (В)", "min": 0.5, "max": 5.0},
        }
    },
    "resistor": {
        "label": "Резистор",
        "shape": "resistor",
        "width": 64,
        "height": 22,
        "color": "#d8c39a",
        "pins": [
            {"name": "pin1", "dx": 0, "dy": 11},
            {"name": "pin2", "dx": 64, "dy": 11},
        ],
        "params": {
            "resistance": {"type": "float", "default": 1000, "label": "Сопротивление (Ом)", "min": 1, "max": 10000000},
            "tolerance": {"type": "float", "default": 5, "label": "Допуск (%)", "min": 0.1, "max": 20},
            "power": {"type": "float", "default": 0.25, "label": "Мощность (Вт)", "min": 0.0625, "max": 10},
        }
    },
    "button": {
        "label": "Кнопка (Pushbutton)",
        "shape": "button",
        "width": 42,
        "height": 42,
        "color": "#455a64",
        "pins": [
            {"name": "pin1", "dx": 0, "dy": 12},
            {"name": "pin2", "dx": 0, "dy": 30},
            {"name": "pin3", "dx": 42, "dy": 12},
            {"name": "pin4", "dx": 42, "dy": 30},
        ],
        "params": {
            "pullup": {"type": "bool", "default": False, "label": "Использовать подтяжку к VCC"},
            "debounce_ms": {"type": "int", "default": 50, "label": "Антидребезг (мс)", "min": 0, "max": 500},
        }
    },
    "potentiometer": {
        "label": "Потенциометр",
        "shape": "potentiometer",
        "width": 50,
        "height": 50,
        "color": "#6d4c41",
        "pins": [
            {"name": "GND", "dx": 8, "dy": 50},
            {"name": "OUT", "dx": 25, "dy": 50},
            {"name": "VCC", "dx": 42, "dy": 50},
        ],
        "params": {
            "resistance": {"type": "float", "default": 10000, "label": "Полное сопротивление (Ом)", "min": 100, "max": 1000000},
            "taper": {"type": "choice", "default": "linear", "label": "Характеристика", "choices": ["linear", "logarithmic", "anti-logarithmic"]},
            "angle": {"type": "float", "default": 270, "label": "Угол поворота (°)", "min": 180, "max": 360},
        }
    },
    "buzzer": {
        "label": "Пьезодинамик (Buzzer)",
        "shape": "buzzer",
        "width": 44,
        "height": 44,
        "color": "#37474f",
        "pins": [
            {"name": "+", "dx": 14, "dy": 44},
            {"name": "-", "dx": 30, "dy": 44},
        ],
        "params": {
            "frequency": {"type": "int", "default": 440, "label": "Частота (Гц)", "min": 20, "max": 20000},
            "volume": {"type": "int", "default": 80, "label": "Громкость (0-100)", "min": 0, "max": 100},
        }
    },
    "photoresistor": {
        "label": "Фоторезистор (LDR)",
        "shape": "photoresistor",
        "width": 40,
        "height": 24,
        "color": "#9e9d24",
        "pins": [
            {"name": "pin1", "dx": 0, "dy": 12},
            {"name": "pin2", "dx": 40, "dy": 12},
        ],
        "params": {
            "dark_resistance": {"type": "float", "default": 1000000, "label": "Сопротивление в темноте (Ом)", "min": 1000, "max": 10000000},
            "light_resistance": {"type": "float", "default": 1000, "label": "Сопротивление при освещении (Ом)", "min": 100, "max": 100000},
        }
    },
    "servo": {
        "label": "Сервопривод (Servo)",
        "shape": "servo",
        "width": 56,
        "height": 36,
        "color": "#1e88e5",
        "pins": [
            {"name": "GND", "dx": 14, "dy": 36},
            {"name": "VCC", "dx": 28, "dy": 36},
            {"name": "SIG", "dx": 42, "dy": 36},
        ],
        "params": {
            "min_angle": {"type": "int", "default": 0, "label": "Минимальный угол (°)", "min": 0, "max": 180},
            "max_angle": {"type": "int", "default": 180, "label": "Максимальный угол (°)", "min": 0, "max": 180},
            "speed": {"type": "float", "default": 0.1, "label": "Скорость (°/мс)", "min": 0.01, "max": 1.0},
            "pulse_range": {"type": "str", "default": "500-2500", "label": "Диапазон импульсов (мкс)"},
        }
    },
    "dc_motor": {
        "label": "Мотор постоянного тока",
        "shape": "dc_motor",
        "width": 50,
        "height": 50,
        "color": "#6a1b9a",
        "pins": [
            {"name": "pin1", "dx": 0, "dy": 25},
            {"name": "pin2", "dx": 50, "dy": 25},
        ],
        "params": {
            "max_rpm": {"type": "int", "default": 5000, "label": "Макс. оборотов (RPM)", "min": 100, "max": 50000},
            "voltage": {"type": "float", "default": 5.0, "label": "Номинальное напряжение (В)", "min": 1.5, "max": 24},
            "current": {"type": "float", "default": 0.5, "label": "Ток потребления (А)", "min": 0.01, "max": 10},
        }
    },
}

# Порядок компонентов в панели выбора
COMPONENT_ORDER = [
    "led", "resistor", "button", "potentiometer",
    "buzzer", "photoresistor", "servo", "dc_motor",
]


# Расположение пинов платы Arduino UNO (упрощённая, но узнаваемая раскладка)
UNO_BOARD_WIDTH = 460
UNO_BOARD_HEIGHT = 340

# Верхний ряд — цифровые пины (включая AREF, GND, 13, 12, ...)
_UNO_TOP_PINS = ["AREF", "GND", "13", "12", "~11", "~10", "~9", "8",
                 "7", "~6", "~5", "4", "~3", "2", "TX>1", "RX<0"]

# Нижний ряд — питание и аналоговые пины
_UNO_BOTTOM_PINS = ["IOREF", "RESET", "3V3", "5V", "GND", "GND", "VIN",
                     "A0", "A1", "A2", "A3", "A4", "A5"]


def _pin_color(name: str) -> str:
    if name in ("GND",):
        return PIN_GND
    if name in ("5V", "3V3", "VIN", "IOREF", "RESET"):
        return PIN_POWER
    if name.startswith("A"):
        return PIN_ANALOG
    return PIN_DIGITAL


def build_uno_pins() -> list:
    """Возвращает список пинов платы UNO с конкретными координатами."""
    pins = []

    # Перечисление пинов почти как и в ArduinoIDE

    # ВЕРХНИЙ РЯД ПИНОВ (координаты подобраны под изображение)
    # AREF
    pins.append({
        "name": "AREF",
        "dx": 187,
        "dy": 16,
        "color": _pin_color("AREF")
    })
    # GND
    pins.append({
        "name": "GND",
        "dx": 202,
        "dy": 16,
        "color": _pin_color("GND")
    })
    # 13
    pins.append({
        "name": "13",
        "dx": 217,
        "dy": 16,
        "color": _pin_color("13")
    })
    # 12
    pins.append({
        "name": "12",
        "dx": 232,
        "dy": 16,
        "color": _pin_color("12")
    })
    # ~11
    pins.append({
        "name": "~11",
        "dx": 248,
        "dy": 16,
        "color": _pin_color("~11")
    })
    # ~10
    pins.append({
        "name": "~10",
        "dx": 264,
        "dy": 16,
        "color": _pin_color("~10")
    })
    # ~9
    pins.append({
        "name": "~9",
        "dx": 278,
        "dy": 16,
        "color": _pin_color("~9")
    })
    # 8
    pins.append({
        "name": "8",
        "dx": 294,
        "dy": 16,
        "color": _pin_color("8")
    })
    # 7
    pins.append({
        "name": "7",
        "dx": 321,
        "dy": 16,
        "color": _pin_color("7")
    })
    # ~6
    pins.append({
        "name": "~6",
        "dx": 336,
        "dy": 16,
        "color": _pin_color("~6")
    })
    # ~5
    pins.append({
        "name": "~5",
        "dx": 351,
        "dy": 16,
        "color": _pin_color("~5")
    })
    # 4
    pins.append({
        "name": "4",
        "dx": 366,
        "dy": 16,
        "color": _pin_color("4")
    })
    # ~3
    pins.append({
        "name": "~3",
        "dx": 382,
        "dy": 16,
        "color": _pin_color("~3")
    })
    # 2
    pins.append({
        "name": "2",
        "dx": 397,
        "dy": 16,
        "color": _pin_color("2")
    })
    # TX>1
    pins.append({
        "name": "TX>1",
        "dx": 412,
        "dy": 16,
        "color": _pin_color("TX>1")
    })
    # RX<0
    pins.append({
        "name": "RX<0",
        "dx": 428,
        "dy": 16,
        "color": _pin_color("RX<0")
    })

    # НИЖНИЙ РЯД ПИНОВ
    # IOREF
    pins.append({
        "name": "IOREF",
        "dx": 227,
        "dy": 310,
        "color": _pin_color("IOREF")
    })
    # RESET
    pins.append({
        "name": "RESET",
        "dx": 242,
        "dy": 310,
        "color": _pin_color("RESET")
    })
    # 3V3
    pins.append({
        "name": "3V3",
        "dx": 257,
        "dy": 310,
        "color": _pin_color("3V3")
    })
    # 5V
    pins.append({
        "name": "5V",
        "dx": 273,
        "dy": 310,
        "color": _pin_color("5V")
    })
    # GND
    pins.append({
        "name": "GND",
        "dx": 288,
        "dy": 310,
        "color": _pin_color("GND")
    })
    # GND
    pins.append({
        "name": "GND",
        "dx": 303,
        "dy": 310,
        "color": _pin_color("GND")
    })
    # VIN
    pins.append({
        "name": "VIN",
        "dx": 319,
        "dy": 310,
        "color": _pin_color("VIN")
    })
    # A0
    pins.append({
        "name": "A0",
        "dx": 350,
        "dy": 310,
        "color": _pin_color("A0")
    })
    # A1
    pins.append({
        "name": "A1",
        "dx": 366,
        "dy": 310,
        "color": _pin_color("A1")
    })
    # A2
    pins.append({
        "name": "A2",
        "dx": 381,
        "dy": 310,
        "color": _pin_color("A2")
    })
    # A3
    pins.append({
        "name": "A3",
        "dx": 397,
        "dy": 310,
        "color": _pin_color("A3")
    })
    # A4
    pins.append({
        "name": "A4",
        "dx": 412,
        "dy": 310,
        "color": _pin_color("A4")
    })
    # A5
    pins.append({
        "name": "A5",
        "dx": 427,
        "dy": 310,
        "color": _pin_color("A5")
    })

    return pins