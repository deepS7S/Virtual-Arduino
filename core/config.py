"""
Модуль для управления настройками приложения VirtualArduino.

Хранит настройки в JSON-файле в локальной папке приложения.
"""

import json
from pathlib import Path
from typing import Any, Dict


class Config:
    """Класс для работы с настройками приложения."""

    # Имя файла конфигурации
    CONFIG_FILENAME = "config.json"

    # Настройки по умолчанию
    DEFAULT_CONFIG = {
        "projects_directory": "Projects",  # Относительно папки приложения
        "recent_projects": [],
        "theme": "dark",
        "auto_save": True,
    }

    def __init__(self, config_dir: Path = None):
        """
        Инициализирует менеджер конфигурации.

        :param config_dir: Директория для хранения конфига.
                           Если None - используется папка приложения.
        """
        if config_dir is None:
            # Определяем папку приложения
            self._config_dir = Path(__file__).parent.parent
        else:
            self._config_dir = Path(config_dir)

        self._config_file = self._config_dir / self.CONFIG_FILENAME
        self._config: Dict[str, Any] = {}
        self._load_or_create()

    def _load_or_create(self) -> None:
        """Загружает конфигурацию или создаёт новую с настройками по умолчанию."""
        if self._config_file.exists():
            try:
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                # Проверяем, что все ключи из DEFAULT_CONFIG присутствуют
                for key, value in self.DEFAULT_CONFIG.items():
                    if key not in self._config:
                        self._config[key] = value
                        self._save()
            except (json.JSONDecodeError, OSError):
                # Если файл повреждён, создаём новый
                self._config = self.DEFAULT_CONFIG.copy()
                self._save()
        else:
            self._config = self.DEFAULT_CONFIG.copy()
            self._save()

    def _save(self) -> None:
        """Сохраняет текущую конфигурацию в файл."""
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except OSError:
            pass  # Игнорируем ошибки записи

    def get(self, key: str, default: Any = None) -> Any:
        """Возвращает значение настройки по ключу."""
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Устанавливает значение настройки и сохраняет."""
        self._config[key] = value
        self._save()

    def get_projects_directory(self) -> Path:
        """Возвращает директорию для проектов."""
        projects_dir = self.get("projects_directory", "Projects")
        # Если путь относительный, преобразуем относительно папки приложения
        path = Path(projects_dir)
        if not path.is_absolute():
            path = self._config_dir / path
        return path

    def set_projects_directory(self, path: Path) -> None:
        """Устанавливает директорию для проектов."""
        # Сохраняем относительный путь если папка внутри приложения
        try:
            rel_path = path.relative_to(self._config_dir)
            self.set("projects_directory", str(rel_path))
        except ValueError:
            # Если папка вне приложения, сохраняем абсолютный путь
            self.set("projects_directory", str(path))

    def get_recent_projects(self) -> list:
        """Возвращает список недавних проектов."""
        return self.get("recent_projects", [])

    def add_recent_project(self, project_path: Path) -> None:
        """Добавляет проект в список недавних."""
        recent = self.get_recent_projects()
        path_str = str(project_path)
        if path_str in recent:
            recent.remove(path_str)
        recent.insert(0, path_str)
        self.set("recent_projects", recent[:10])

    def remove_recent_project(self, project_path: Path) -> None:
        """Удаляет проект из списка недавних."""
        recent = self.get_recent_projects()
        path_str = str(project_path)
        if path_str in recent:
            recent.remove(path_str)
            self.set("recent_projects", recent)

    @property
    def config_file(self) -> Path:
        """Возвращает путь к файлу конфигурации."""
        return self._config_file


# Глобальный экземпляр конфигурации
_config_instance = None


def get_config() -> Config:
    """Возвращает глобальный экземпляр конфигурации."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance