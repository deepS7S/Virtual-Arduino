"""
Общие константы приложения: метаданные, поддерживаемые платы,
расширение файла проекта и имена файлов внутри архива проекта.
"""

from enum import Enum


APP_NAME = "Arduino IDE Simulator"
APP_VERSION = "0.1.0"
ORG_NAME = "ArduinoIdeSim"

# Расширение файла проекта (ZIP-архив)
PROJECT_EXTENSION = ".aproj"
PROJECT_FILE_FILTER = f"Проект Arduino IDE Simulator (*{PROJECT_EXTENSION})"

# Имена файлов внутри ZIP-архива проекта
METADATA_FILENAME = "metadata.json"
SOURCE_FILENAME = "source/sketch.ino"
CIRCUIT_FILENAME = "circuit/schema.json"

# Максимальное число проектов в списке "Недавние"
MAX_RECENT_PROJECTS = 10

# Шаблон кода по умолчанию для нового скетча
DEFAULT_SKETCH_TEMPLATE = """void setup() {
    // Код инициализации выполняется один раз
}

void loop() {
    // Основной код выполняется циклически
}
"""


class BoardType(str, Enum):
    """
    Поддерживаемые типы плат Arduino.

    На текущем этапе разработки доступна только Arduino UNO — она же
    единственная плата, для которой реализован визуальный редактор схем.
    MINI и MEGA оставлены в перечислении на будущее (см. ТЗ, п.1.3),
    но не предлагаются пользователю при создании проекта.
    """

    UNO = "Arduino UNO"
    MINI = "Arduino MINI"
    MEGA = "Arduino MEGA"

    @classmethod
    def values(cls):
        return [member.value for member in cls]

    @classmethod
    def available_values(cls):
        """Платы, доступные для выбора в текущей версии приложения."""
        return [cls.UNO.value]


# Технические характеристики плат (понадобятся в дальнейшем для эмулятора,
# уже сейчас удобно хранить рядом с типами плат)
BOARD_SPECS = {
    BoardType.UNO: {"mcu": "ATmega328P", "digital_pins": 14, "analog_pins": 6},
    BoardType.MINI: {"mcu": "ATmega328P", "digital_pins": 14, "analog_pins": 8},
    BoardType.MEGA: {"mcu": "ATmega2560", "digital_pins": 54, "analog_pins": 16},
}
