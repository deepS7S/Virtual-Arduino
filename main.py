"""
Точка входа в приложение.

Запускает стартовый экран (StartScreen). После того как пользователь
создаст новый проект или откроет существующий, стартовый экран закрывается
и открывается главное окно (MainWindow) с этим проектом.
"""

import sys
import traceback

from PyQt5.QtWidgets import QApplication

from core.constants import APP_NAME, ORG_NAME
from ui.main_window import MainWindow
from ui.start_screen import StartScreen
from ui.theme import APP_STYLESHEET


def _install_exception_hook() -> None:
    """
    Перехватывает необработанные исключения и пишет их в crash.log рядом
    с приложением, а не только в консоль (которую некоторые IDE/способы
    запуска могут не показывать). Помогает диагностировать сбои, которые
    выглядят как "тихое" падение процесса.
    """

    def handle_exception(exc_type, exc_value, exc_traceback):
        message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        sys.stderr.write(message)
        try:
            with open("crash.log", "a", encoding="utf-8") as f:
                f.write(message + "\n")
        except OSError:
            pass

    sys.excepthook = handle_exception


class Application:
    """Связывает стартовый экран и главное окно, управляет переходом между ними."""

    def __init__(self):
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setApplicationName(APP_NAME)
        self.qt_app.setOrganizationName(ORG_NAME)
        self.qt_app.setStyleSheet(APP_STYLESHEET)

        self.start_screen = StartScreen()
        self.start_screen.on_project_ready = self._show_main_window
        self.main_window = None

    def _show_main_window(self, project) -> None:
        try:
            self.main_window = MainWindow(project)
            self.main_window.show()
            self.start_screen.close()
        except Exception:
            traceback.print_exc()
            raise

    def run(self) -> int:
        self.start_screen.show()
        return self.qt_app.exec_()


def main() -> int:
    _install_exception_hook()
    app = Application()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
