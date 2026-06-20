"""
Модуль работы с проектом приложения.

Формат файла проекта (*.aproj) — ZIP-архив со следующей структурой:

    metadata.json        — метаданные проекта (имя, плата, даты, версия формата)
    source/sketch.ino    — исходный код скетча
    circuit/schema.json  — описание электрической схемы (пока пустое/заглушка)

Класс Project инкапсулирует создание нового проекта, сохранение
и загрузку существующего файла проекта.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.constants import (
    BoardType,
    CIRCUIT_FILENAME,
    DEFAULT_SKETCH_TEMPLATE,
    METADATA_FILENAME,
    PROJECT_EXTENSION,
    SOURCE_FILENAME,
)

PROJECT_FORMAT_VERSION = 1


class ProjectError(Exception):
    """Базовое исключение для ошибок работы с проектом."""


class ProjectLoadError(ProjectError):
    """Не удалось открыть/прочитать файл проекта."""


class ProjectSaveError(ProjectError):
    """Не удалось сохранить файл проекта."""


@dataclass
class Project:
    """Представление проекта Arduino IDE Simulator."""

    name: str
    board: BoardType
    file_path: Optional[Path] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    source_code: str = field(default_factory=lambda: DEFAULT_SKETCH_TEMPLATE)
    circuit_data: dict = field(default_factory=dict)

    # Создание нового проекта
    @classmethod
    def create_new(cls, name: str, board: BoardType, directory: Path) -> "Project":
        """
        Создаёт новый проект с заданным именем и платой и сразу сохраняет
        его в виде файла *.aproj в указанной директории.

        :param name: Имя проекта (используется и как имя файла).
        :param board: Тип платы из BoardType.
        :param directory: Папка, в которой будет создан файл проекта.
        :raises ProjectSaveError: если сохранение не удалось.
        """
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        file_path = directory / f"{cls._safe_filename(name)}{PROJECT_EXTENSION}"
        if file_path.exists():
            raise ProjectSaveError(
                f"Файл проекта уже существует: {file_path}"
            )

        project = cls(name=name, board=board, file_path=file_path)
        project.save()
        return project

    @staticmethod
    def _safe_filename(name: str) -> str:
        """Убирает из имени проекта символы, недопустимые в имени файла."""
        invalid = '<>:"/\\|?*'
        cleaned = "".join(c for c in name if c not in invalid).strip()
        return cleaned or "project"

    # Сохранение
    def save(self, file_path: Optional[Path] = None) -> None:
        """Сохраняет текущее состояние проекта в ZIP-архив."""
        target = Path(file_path) if file_path else self.file_path
        if target is None:
            raise ProjectSaveError("Не указан путь для сохранения проекта.")

        self.modified_at = datetime.now().isoformat(timespec="seconds")

        metadata = {
            "format_version": PROJECT_FORMAT_VERSION,
            "name": self.name,
            "board": self.board.value if isinstance(self.board, BoardType) else self.board,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
        }

        tmp_path = target.with_suffix(target.suffix + ".tmp")
        try:
            with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(METADATA_FILENAME, json.dumps(metadata, ensure_ascii=False, indent=2))
                archive.writestr(SOURCE_FILENAME, self.source_code)
                archive.writestr(CIRCUIT_FILENAME, json.dumps(self.circuit_data, ensure_ascii=False, indent=2))
            tmp_path.replace(target)
        except OSError as exc:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise ProjectSaveError(f"Ошибка записи файла проекта: {exc}") from exc

        self.file_path = target

    # Загрузка
    @classmethod
    def load(cls, file_path: Path) -> "Project":
        """Загружает проект из файла *.aproj."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise ProjectLoadError(f"Файл проекта не найден: {file_path}")

        try:
            with zipfile.ZipFile(file_path, "r") as archive:
                with archive.open(METADATA_FILENAME) as meta_file:
                    metadata = json.load(meta_file)

                try:
                    with archive.open(SOURCE_FILENAME) as src_file:
                        source_code = src_file.read().decode("utf-8")
                except KeyError:
                    source_code = DEFAULT_SKETCH_TEMPLATE

                try:
                    with archive.open(CIRCUIT_FILENAME) as circuit_file:
                        circuit_data = json.load(circuit_file)
                except KeyError:
                    circuit_data = {}
        except (zipfile.BadZipFile, KeyError, json.JSONDecodeError) as exc:
            raise ProjectLoadError(
                f"Файл повреждён или имеет неверный формат: {file_path}\n{exc}"
            ) from exc

        try:
            board = BoardType(metadata.get("board"))
        except ValueError:
            board = BoardType.UNO

        return cls(
            name=metadata.get("name", file_path.stem),
            board=board,
            file_path=file_path,
            created_at=metadata.get("created_at", datetime.now().isoformat(timespec="seconds")),
            modified_at=metadata.get("modified_at", datetime.now().isoformat(timespec="seconds")),
            source_code=source_code,
            circuit_data=circuit_data,
        )
