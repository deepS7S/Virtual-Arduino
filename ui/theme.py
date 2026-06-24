
BG_DARKEST = "#1e1e1e"        # фон центральной рабочей области
BG_DARK = "#252526"           # фон боковых панелей
BG_ACTIVITY_BAR = "#2b2b2b"   # узкая панель с кнопками-переключателями
BG_ELEVATED = "#2d2d2d"       # фон тулбара/менюбара
BG_INPUT = "#3c3c3c"          # поля ввода, кнопки
BORDER = "#1b1b1b"

TEXT_PRIMARY = "#d4d4d4"
TEXT_SECONDARY = "#9a9a9a"
TEXT_DISABLED = "#6a6a6a"

ACCENT = "#00979D"
ACCENT_HOVER = "#00b3ba"
ACCENT_PRESSED = "#00787d"

ERROR = "#f14c4c"
WARNING = "#cca700"
SUCCESS = "#4caf50"

SYNTAX_KEYWORD = "#569cd6"
SYNTAX_TYPE = "#4ec9b0"
SYNTAX_FUNCTION = "#dcdcaa"
SYNTAX_STRING = "#ce9178"
SYNTAX_COMMENT = "#6a9955"
SYNTAX_NUMBER = "#b5cea8"
SYNTAX_PREPROCESSOR = "#c586c0"

BOARD_PCB = "#0f7a8c"
BOARD_PCB_DARK = "#0b5e6c"
BOARD_SILK = "#e8e8e8"
PIN_COLOR = "#d4af37"
PIN_DIGITAL = "#3da5d9"
PIN_ANALOG = "#9ccc65"
PIN_POWER = "#f14c4c"
PIN_GND = "#2b2b2b"
WIRE_DEFAULT = "#e0a526"

APP_STYLESHEET = f"""
QWidget {{
    background-color: {BG_DARKEST};
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}}

QMainWindow {{
    background-color: {BG_DARKEST};
}}

QMenuBar {{
    background-color: {BG_ELEVATED};
    color: {TEXT_PRIMARY};
    border-bottom: 1px solid {BORDER};
    padding: 2px;
}}
QMenuBar::item {{
    background: transparent;
    padding: 4px 10px;
}}
QMenuBar::item:selected {{
    background-color: {BG_INPUT};
}}
QMenu {{
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
}}
QMenu::item:selected {{
    background-color: {ACCENT};
    color: white;
}}

QToolBar {{
    background-color: {BG_ELEVATED};
    border-bottom: 1px solid {BORDER};
    spacing: 4px;
    padding: 4px;
}}

QStatusBar {{
    background-color: {ACCENT};
    color: white;
}}

QPushButton {{
    background-color: #3a3a3a;
    color: #e8e8e8;
    border: 1px solid #5a5a5a;
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
    color: white;
}}
QPushButton:pressed {{
    background-color: {ACCENT_PRESSED};
    border-color: {ACCENT_PRESSED};
}}
QPushButton:disabled {{
    background-color: #2a2a2a;
    color: {TEXT_DISABLED};
    border-color: #333333;
}}

QPushButton#PrimaryButton {{
    background-color: {ACCENT};
    color: white;
    font-weight: 600;
}}
QPushButton#PrimaryButton:hover {{
    background-color: {ACCENT_HOVER};
}}

QPushButton#ActivityButton {{
    background-color: #333333;
    border: none;
    border-left: 2px solid transparent;
    border-radius: 0px;
    padding: 10px;
    color: #bbbbbb;
    font-size: 16px;
}}
QPushButton#ActivityButton:hover {{
    background-color: #484848;
    color: white;
}}
QPushButton#ActivityButton:checked {{
    border-left: 2px solid {ACCENT};
    background-color: {BG_DARK};
    color: white;
}}

QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QListWidget {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 3px;
    selection-background-color: {ACCENT};
}}

QListWidget::item {{
    padding: 6px;
    border-radius: 3px;
}}
QListWidget::item:selected {{
    background-color: {ACCENT};
    color: white;
}}
QListWidget::item:hover {{
    background-color: {BG_DARK};
}}

QLabel#TitleLabel {{
    font-size: 22px;
    font-weight: 600;
    color: {TEXT_PRIMARY};
}}
QLabel#SubtitleLabel {{
    color: {TEXT_SECONDARY};
}}
QLabel#SectionLabel {{
    color: {ACCENT};
    font-weight: 600;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 1px;
}}

QScrollBar:vertical {{
    background: {BG_DARKEST};
    width: 12px;
}}
QScrollBar::handle:vertical {{
    background: {BG_INPUT};
    border-radius: 5px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT};
}}
QScrollBar:horizontal {{
    background: {BG_DARKEST};
    height: 12px;
}}
QScrollBar::handle:horizontal {{
    background: {BG_INPUT};
    border-radius: 5px;
    min-width: 20px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {ACCENT};
}}

QSplitter::handle {{
    background-color: {BORDER};
}}

QGraphicsView {{
    background-color: {BG_DARKEST};
    border: none;
}}

QToolTip {{
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
    border: 1px solid {ACCENT};
    padding: 4px;
}}
"""
