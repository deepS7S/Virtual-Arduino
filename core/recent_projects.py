"""
Хранение списка недавно открытых проектов между запусками приложения.
Список сохраняется в JSON-файле в домашней директории пользователя.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from core.constants import MAX_RECENT_PROJECTS, ORG_NAME

CONFIG_DIR = Path.home() / f".{ORG_NAME.lower()}"
CONFIG_FILE = CONFIG_DIR / "recent_projects.json"


class RecentProjectsManager:
    """Простой менеджер списка недавних проектов на основе JSON-файла."""

    def __init__(self, config_file: Path = CONFIG_FILE):
        self._config_file = Path(config_file)

    def get_all(self) -> List[str]:
        """Возвращает список путей к недавним проектам (существующих файлов)."""
        if not self._config_file.exists():
            return []

        try:
            with open(self._config_file, "r", encoding="utf-8") as f:
                paths = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

        existing = [p for p in paths if Path(p).exists()]
        if existing != paths:
            self._write(existing)
        return existing

    def add(self, file_path: Path) -> None:
        """Добавляет проект в начало списка недавних (без дублей)."""
        file_path = str(Path(file_path).resolve())
        paths = [p for p in self.get_all() if p != file_path]
        paths.insert(0, file_path)
        self._write(paths[:MAX_RECENT_PROJECTS])

    def remove(self, file_path: Path) -> None:
        """Убирает проект из списка недавних."""
        file_path = str(Path(file_path).resolve())
        paths = [p for p in self.get_all() if p != file_path]
        self._write(paths)

    def clear(self) -> None:
        self._write([])

    def _write(self, paths: List[str]) -> None:
        self._config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_file, "w", encoding="utf-8") as f:
            json.dump(paths, f, ensure_ascii=False, indent=2)
