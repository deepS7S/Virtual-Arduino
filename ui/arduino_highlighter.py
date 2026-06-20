"""
Подсветка синтаксиса языка Arduino C++ для встроенного редактора кода.
Выделяются ключевые слова языка, типы данных, встроенные функции Arduino,
строковые литералы, числа, комментарии и директивы препроцессора.
"""

from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

from ui.theme import (
    SYNTAX_COMMENT,
    SYNTAX_FUNCTION,
    SYNTAX_KEYWORD,
    SYNTAX_NUMBER,
    SYNTAX_PREPROCESSOR,
    SYNTAX_STRING,
    SYNTAX_TYPE,
)

CPP_KEYWORDS = [
    "if", "else", "for", "while", "do", "switch", "case", "default", "break",
    "continue", "return", "goto", "void", "const", "static", "volatile",
    "struct", "class", "public", "private", "protected", "new", "delete",
    "true", "false", "namespace", "using", "typedef", "enum", "sizeof",
    "this", "virtual", "friend", "template", "try", "catch", "throw",
]

CPP_TYPES = [
    "int", "float", "double", "char", "bool", "long", "short", "unsigned",
    "signed", "byte", "word", "String", "boolean", "size_t", "uint8_t",
    "uint16_t", "uint32_t", "int8_t", "int16_t", "int32_t",
]

ARDUINO_FUNCTIONS = [
    "setup", "loop", "pinMode", "digitalWrite", "digitalRead", "analogRead",
    "analogWrite", "delay", "delayMicroseconds", "millis", "micros",
    "Serial", "print", "println", "begin", "available", "read", "write",
    "map", "constrain", "min", "max", "abs", "pow", "sqrt", "random",
    "randomSeed", "attachInterrupt", "detachInterrupt", "tone", "noTone",
    "pulseIn", "shiftOut", "shiftIn",
]

ARDUINO_CONSTANTS = [
    "HIGH", "LOW", "INPUT", "OUTPUT", "INPUT_PULLUP", "LED_BUILTIN",
    "A0", "A1", "A2", "A3", "A4", "A5", "PI", "HALF_PI", "TWO_PI",
]


def _format(color_hex: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(color_hex))
    if bold:
        fmt.setFontWeight(QFont.Bold)
    fmt.setFontItalic(italic)
    return fmt


class ArduinoHighlighter(QSyntaxHighlighter):
    """QSyntaxHighlighter с правилами для скетчей Arduino (.ino)."""

    def __init__(self, document):
        super().__init__(document)

        self._rules = []

        keyword_fmt = _format(SYNTAX_KEYWORD, bold=True)
        for word in CPP_KEYWORDS:
            self._rules.append((QRegExp(r"\b%s\b" % word), keyword_fmt))

        type_fmt = _format(SYNTAX_TYPE)
        for word in CPP_TYPES:
            self._rules.append((QRegExp(r"\b%s\b" % word), type_fmt))

        function_fmt = _format(SYNTAX_FUNCTION)
        for word in ARDUINO_FUNCTIONS:
            self._rules.append((QRegExp(r"\b%s\b" % word), function_fmt))

        constant_fmt = _format(SYNTAX_TYPE, bold=True)
        for word in ARDUINO_CONSTANTS:
            self._rules.append((QRegExp(r"\b%s\b" % word), constant_fmt))

        # Числа
        self._rules.append((QRegExp(r"\b[0-9]+\.?[0-9]*\b"), _format(SYNTAX_NUMBER)))

        # Строки и символы
        self._rules.append((QRegExp(r'"[^"]*"'), _format(SYNTAX_STRING)))
        self._rules.append((QRegExp(r"'[^']*'"), _format(SYNTAX_STRING)))

        # Директивы препроцессора
        self._rules.append((QRegExp(r"^\s*#\w+"), _format(SYNTAX_PREPROCESSOR, bold=True)))

        # Однострочные комментарии (обрабатываются последними, чтобы перекрыть остальное)
        self._single_comment = QRegExp(r"//[^\n]*")
        self._comment_format = _format(SYNTAX_COMMENT, italic=True)

        # Многострочные комментарии
        self._comment_start = QRegExp(r"/\*")
        self._comment_end = QRegExp(r"\*/")

    # ------------------------------------------------------------------
    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self._rules:
            index = pattern.indexIn(text)
            while index >= 0:
                length = pattern.matchedLength()
                self.setFormat(index, length, fmt)
                index = pattern.indexIn(text, index + length)

        # Однострочные комментарии поверх остального
        index = self._single_comment.indexIn(text)
        if index >= 0:
            length = len(text) - index
            self.setFormat(index, length, self._comment_format)

        # Многострочные комментарии (упрощённая обработка через blockState)
        self.setCurrentBlockState(0)
        start_index = 0
        if self.previousBlockState() != 1:
            start_index = self._comment_start.indexIn(text)

        while start_index >= 0:
            end_index = self._comment_end.indexIn(text, start_index)
            if end_index == -1:
                self.setCurrentBlockState(1)
                comment_length = len(text) - start_index
            else:
                comment_length = end_index - start_index + self._comment_end.matchedLength()
            self.setFormat(start_index, comment_length, self._comment_format)
            start_index = self._comment_start.indexIn(text, start_index + comment_length)
