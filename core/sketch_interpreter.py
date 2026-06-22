

import random as _random
import re


class SketchError(Exception):
    """Ошибка разбора или выполнения скетча. Хранит номер строки (для UI)."""

    def __init__(self, message, line=None):
        self.line = line
        self.raw_message = message
        full = "строка %s: %s" % (line, message) if line else message
        super().__init__(full)


_TOKEN_SPEC = [
    ("NUMBER", r"\d+\.\d+|\d+"),
    ("IDENT", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("STRING", r'"[^"\n]*"'),
    ("OP", r"==|!=|<=|>=|&&|\|\||\+\+|--|\+=|-=|\*=|/=|[+\-*/%=<>!]"),
    ("PUNCT", r"[(){};,.]"),
    ("NEWLINE", r"\n"),
    ("SKIP", r"[ \t\r]+"),
    ("MISMATCH", r"."),
]
_TOKEN_RE = re.compile("|".join("(?P<%s>%s)" % (n, p) for n, p in _TOKEN_SPEC))


class _Tok:
    __slots__ = ("kind", "value", "line")

    def __init__(self, kind, value, line):
        self.kind, self.value, self.line = kind, value, line

    def __repr__(self):
        return "<%s:%r>" % (self.kind, self.value)


def _strip_comments(src):
    src = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), src, flags=re.S)
    src = re.sub(r"//[^\n]*", "", src)
    return src


def tokenize(src):
    src = _strip_comments(src)
    out = []
    line = 1
    for m in _TOKEN_RE.finditer(src):
        kind = m.lastgroup
        value = m.group()
        if kind == "NEWLINE":
            line += 1
            continue
        if kind in ("SKIP", "MISMATCH"):
            continue
        out.append(_Tok(kind, value, line))
    out.append(_Tok("EOF", "", line))
    return out


def extract_global_constants(source):

    constants = {}

    boundary = len(source)
    for kw in ("void setup", "void loop"):
        idx = source.find(kw)
        if idx != -1:
            boundary = min(boundary, idx)
    header = source[:boundary]

    for m in re.finditer(r"#define\s+(\w+)\s+([^\n]+)", source):
        constants[m.group(1)] = _coerce_literal(m.group(2).strip())

    type_group = r"(?:unsigned\s+)?(?:int|float|double|long|byte|bool|boolean|char|word|short)"
    for m in re.finditer(r"\bconst\s+" + type_group + r"\s+(\w+)\s*=\s*([^;]+);", header):
        constants[m.group(1)] = _coerce_literal(m.group(2).strip())
    for m in re.finditer(r"(?<!const )\b" + type_group + r"\s+(\w+)\s*(?:=\s*([^;]+))?;", header):
        name = m.group(1)
        if name in constants:
            continue
        raw = m.group(2)
        constants[name] = _coerce_literal(raw.strip()) if raw else 0

    return constants


def _coerce_literal(raw):
    raw = raw.strip()
    try:
        return float(raw) if "." in raw else int(raw)
    except ValueError:
        return raw


def extract_function_body(source, name):
    """Возвращает (тело_без_скобок, номер_строки_открывающей_скобки) или (None, None)."""
    pattern = re.compile(r"\bvoid\s+" + re.escape(name) + r"\s*\(\s*\)\s*\{")
    m = pattern.search(source)
    if not m:
        return None, None
    start_line = source.count("\n", 0, m.start()) + 1
    start = m.end()
    depth = 1
    i = start
    while i < len(source) and depth > 0:
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
        i += 1
    if depth != 0:
        raise SketchError("не найдена закрывающая скобка функции %s()" % name, start_line)
    return source[start:i - 1], start_line


_TYPES = {"int", "float", "double", "long", "short", "byte", "bool", "boolean", "char", "unsigned", "word"}


class Parser:
    def __init__(self, tokens, line_offset=0):
        self.tokens = tokens
        self.pos = 0
        self.line_offset = line_offset

    def peek(self):
        return self.tokens[self.pos]

    def advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, kind, value=None):
        tok = self.peek()
        if tok.kind != kind or (value is not None and tok.value != value):
            raise SketchError(
                "ожидалось '%s', встречено '%s'" % (value or kind, tok.value or "конец блока"),
                tok.line + self.line_offset,
            )
        return self.advance()

    def at(self, kind, value=None):
        tok = self.peek()
        return tok.kind == kind and (value is None or tok.value == value)

    def parse_block(self):
        self.expect("PUNCT", "{")
        body = []
        while not self.at("PUNCT", "}") and not self.at("EOF"):
            body.append(self.parse_statement())
        self.expect("PUNCT", "}")
        return {"type": "Block", "body": body}

    def parse_statement(self):
        tok = self.peek()
        if tok.kind == "PUNCT" and tok.value == "{":
            return self.parse_block()
        if tok.kind == "IDENT" and tok.value == "if":
            return self._parse_if()
        if tok.kind == "IDENT" and tok.value == "while":
            return self._parse_while()
        if tok.kind == "IDENT" and tok.value == "for":
            return self._parse_for()
        if tok.kind == "IDENT" and tok.value in ("break", "continue"):
            self.advance()
            self.expect("PUNCT", ";")
            return {"type": tok.value.capitalize()}
        if tok.kind == "IDENT" and tok.value == "return":
            self.advance()
            if not self.at("PUNCT", ";"):
                self.parse_expression()
            self.expect("PUNCT", ";")
            return {"type": "Return"}
        if tok.kind == "IDENT" and tok.value in _TYPES:
            return self._parse_var_decl()
        return self._parse_expr_stmt()

    def _parse_var_decl(self):
        line = self.peek().line + self.line_offset
        while self.at("IDENT") and self.peek().value in _TYPES:
            self.advance()
        name = self.expect("IDENT").value
        expr = None
        if self.at("OP", "="):
            self.advance()
            expr = self.parse_expression()
        self.expect("PUNCT", ";")
        return {"type": "VarDecl", "name": name, "expr": expr, "line": line}

    def _parse_expr_stmt(self):
        line = self.peek().line + self.line_offset
        expr = self.parse_expression()
        self.expect("PUNCT", ";")
        return {"type": "ExprStmt", "expr": expr, "line": line}

    def _parse_if(self):
        line = self.expect("IDENT", "if").line + self.line_offset
        self.expect("PUNCT", "(")
        cond = self.parse_expression()
        self.expect("PUNCT", ")")
        then_b = self.parse_statement()
        else_b = None
        if self.at("IDENT", "else"):
            self.advance()
            else_b = self.parse_statement()
        return {"type": "If", "cond": cond, "then": then_b, "else": else_b, "line": line}

    def _parse_while(self):
        line = self.expect("IDENT", "while").line + self.line_offset
        self.expect("PUNCT", "(")
        cond = self.parse_expression()
        self.expect("PUNCT", ")")
        body = self.parse_statement()
        return {"type": "While", "cond": cond, "body": body, "line": line}

    def _parse_for(self):
        line = self.expect("IDENT", "for").line + self.line_offset
        self.expect("PUNCT", "(")
        init = None
        if not self.at("PUNCT", ";"):
            if self.at("IDENT") and self.peek().value in _TYPES:
                init = self._parse_var_decl()
            else:
                init = self._parse_expr_stmt()
        else:
            self.advance()
        cond = None
        if not self.at("PUNCT", ";"):
            cond = self.parse_expression()
        self.expect("PUNCT", ";")
        post = None
        if not self.at("PUNCT", ")"):
            post = self.parse_expression()
        self.expect("PUNCT", ")")
        body = self.parse_statement()
        return {"type": "For", "init": init, "cond": cond, "post": post, "body": body, "line": line}

    def parse_expression(self):
        return self._parse_assignment()

    def _parse_assignment(self):
        left = self._parse_or()
        if self.at("OP") and self.peek().value in ("=", "+=", "-=", "*=", "/="):
            op = self.advance().value
            right = self._parse_assignment()
            return {"type": "Assign", "target": left, "op": op, "value": right}
        return left

    def _bin(self, nxt, ops):
        left = nxt()
        while self.at("OP") and self.peek().value in ops:
            op = self.advance().value
            right = nxt()
            left = {"type": "BinOp", "op": op, "left": left, "right": right}
        return left

    def _parse_or(self):
        return self._bin(self._parse_and, ("||",))

    def _parse_and(self):
        return self._bin(self._parse_eq, ("&&",))

    def _parse_eq(self):
        return self._bin(self._parse_cmp, ("==", "!="))

    def _parse_cmp(self):
        return self._bin(self._parse_term, ("<", "<=", ">", ">="))

    def _parse_term(self):
        return self._bin(self._parse_factor, ("+", "-"))

    def _parse_factor(self):
        return self._bin(self._parse_unary, ("*", "/", "%"))

    def _parse_unary(self):
        if self.at("OP") and self.peek().value in ("!", "-", "+"):
            op = self.advance().value
            return {"type": "UnaryOp", "op": op, "operand": self._parse_unary()}
        if self.at("OP") and self.peek().value in ("++", "--"):
            op = self.advance().value
            return {"type": "PreIncDec", "op": op, "operand": self._parse_unary()}
        return self._parse_postfix()

    def _parse_postfix(self):
        expr = self._parse_primary()
        while self.at("OP") and self.peek().value in ("++", "--"):
            op = self.advance().value
            expr = {"type": "PostIncDec", "op": op, "operand": expr}
        return expr

    def _parse_primary(self):
        tok = self.peek()
        line = tok.line + self.line_offset

        if tok.kind == "NUMBER":
            self.advance()
            value = float(tok.value) if "." in tok.value else int(tok.value)
            return {"type": "Num", "value": value}

        if tok.kind == "STRING":
            self.advance()
            return {"type": "Str", "value": tok.value.strip('"')}

        if tok.kind == "PUNCT" and tok.value == "(":
            self.advance()
            expr = self.parse_expression()
            self.expect("PUNCT", ")")
            return expr

        if tok.kind == "IDENT":
            name = self.advance().value
            while self.at("PUNCT", "."):
                self.advance()
                member = self.expect("IDENT").value
                name = name + "." + member
            if self.at("PUNCT", "("):
                self.advance()
                args = []
                if not self.at("PUNCT", ")"):
                    args.append(self.parse_expression())
                    while self.at("PUNCT", ","):
                        self.advance()
                        args.append(self.parse_expression())
                self.expect("PUNCT", ")")
                return {"type": "Call", "name": name, "args": args, "line": line}
            return {"type": "Ident", "name": name, "line": line}

        raise SketchError("неожиданный символ '%s'" % tok.value, line)


def parse_function_body(body_src, start_line):
    tokens = tokenize("{" + body_src + "}")
    parser = Parser(tokens, line_offset=start_line - 1)
    return parser.parse_block()


def compile_sketch(source):
    constants = extract_global_constants(source)
    setup_src, setup_line = extract_function_body(source, "setup")
    loop_src, loop_line = extract_function_body(source, "loop")
    if setup_src is None and loop_src is None:
        raise SketchError("не найдены функции setup() и loop()", 1)

    setup_ast = parse_function_body(setup_src, setup_line) if setup_src is not None else {"type": "Block", "body": []}
    loop_ast = parse_function_body(loop_src, loop_line) if loop_src is not None else {"type": "Block", "body": []}
    return {"constants": constants, "setup": setup_ast, "loop": loop_ast}


def check_syntax(source):
    errors = []
    try:
        compile_sketch(source)
    except SketchError as exc:
        errors.append((exc.line or 1, exc.raw_message))
    return errors


BUILTIN_CONSTANTS = {
    "HIGH": 1, "LOW": 0,
    "INPUT": 0, "OUTPUT": 1, "INPUT_PULLUP": 2,
    "true": True, "false": False,
    "LED_BUILTIN": 13,
    "PI": 3.14159265, "HALF_PI": 1.57079632, "TWO_PI": 6.28318530,
    "A0": "A0", "A1": "A1", "A2": "A2", "A3": "A3", "A4": "A4", "A5": "A5",
}


class _BreakSignal(Exception):
    pass


class _ContinueSignal(Exception):
    pass


class Interpreter:

    def __init__(self, program, io):
        self.io = io
        self.globals = dict(BUILTIN_CONSTANTS)
        self.globals.update(program.get("constants", {}))
        self.setup_ast = program["setup"]
        self.loop_ast = program["loop"]
        self.scopes = [self.globals, {}]

    def _get_var(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise SketchError("необъявленная переменная или функция '%s'" % name)

    def _set_var(self, name, value):
        for scope in reversed(self.scopes):
            if name in scope:
                scope[name] = value
                return
        self.scopes[-1][name] = value

    def run_setup(self):
        for _ in self._exec_block(self.setup_ast):
            pass

    def run_loop_once(self):
        result = yield from self._exec_block(self.loop_ast)
        return result

    def _exec_block(self, node):
        self.scopes.append({})
        try:
            for stmt in node["body"]:
                yield from self._exec_stmt(stmt)
        finally:
            self.scopes.pop()

    def _exec_stmt(self, node):
        kind = node["type"]
        if kind == "Block":
            yield from self._exec_block(node)
        elif kind == "VarDecl":
            value = (yield from self._eval(node["expr"])) if node["expr"] else 0
            self.scopes[-1][node["name"]] = value
        elif kind == "ExprStmt":
            yield from self._eval(node["expr"])
        elif kind == "If":
            cond = yield from self._eval(node["cond"])
            if cond:
                yield from self._exec_stmt(node["then"])
            elif node["else"] is not None:
                yield from self._exec_stmt(node["else"])
        elif kind == "While":
            guard = 0
            while (yield from self._eval(node["cond"])):
                guard += 1
                if guard > 100000:
                    return
                try:
                    yield from self._exec_stmt(node["body"])
                except _BreakSignal:
                    break
                except _ContinueSignal:
                    continue
        elif kind == "For":
            if node["init"] is not None:
                yield from self._exec_stmt(node["init"])
            guard = 0
            while node["cond"] is None or (yield from self._eval(node["cond"])):
                guard += 1
                if guard > 100000:
                    return
                try:
                    yield from self._exec_stmt(node["body"])
                except _BreakSignal:
                    break
                except _ContinueSignal:
                    pass
                if node["post"] is not None:
                    yield from self._eval(node["post"])
        elif kind == "Break":
            raise _BreakSignal()
        elif kind == "Continue":
            raise _ContinueSignal()
        elif kind == "Return":
            return
        else:
            raise SketchError("неизвестная конструкция '%s'" % kind)

    def _eval(self, node):
        kind = node["type"]
        if kind == "Num":
            return node["value"]
        if kind == "Str":
            return node["value"]
        if kind == "Ident":
            return self._get_var(node["name"])
        if kind == "Assign":
            value = yield from self._eval(node["value"])
            if node["op"] != "=":
                current = yield from self._eval(node["target"])
                op = node["op"][0]
                value = self._apply_binop(op, current, value)
            if node["target"]["type"] != "Ident":
                raise SketchError("в левой части присваивания должна быть переменная", node.get("line"))
            self._set_var(node["target"]["name"], value)
            return value
        if kind == "UnaryOp":
            val = yield from self._eval(node["operand"])
            if node["op"] == "-":
                return -val
            if node["op"] == "+":
                return val
            if node["op"] == "!":
                return not val
        if kind in ("PreIncDec", "PostIncDec"):
            if node["operand"]["type"] != "Ident":
                raise SketchError("++/-- применимо только к переменной")
            name = node["operand"]["name"]
            old = self._get_var(name)
            new = old + (1 if node["op"] == "++" else -1)
            self._set_var(name, new)
            return new if kind == "PreIncDec" else old
        if kind == "BinOp":
            left = yield from self._eval(node["left"])
            if node["op"] == "&&":
                if not left:
                    return False
                right = yield from self._eval(node["right"])
                return bool(right)
            if node["op"] == "||":
                if left:
                    return True
                right = yield from self._eval(node["right"])
                return bool(right)
            right = yield from self._eval(node["right"])
            return self._apply_binop(node["op"], left, right)
        if kind == "Call":
            args = []
            for a in node["args"]:
                v = yield from self._eval(a)
                args.append(v)
            result = yield from self._call_builtin(node["name"], args, node.get("line"))
            return result
        raise SketchError("неизвестное выражение '%s'" % kind)

    @staticmethod
    def _apply_binop(op, left, right):
        try:
            if op == "+":
                return left + right
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if op == "/":
                if right == 0:
                    return 0
                if isinstance(left, float) or isinstance(right, float):
                    return left / right
                return int(left / right)
            if op == "%":
                return left % right if right else 0
            if op == "==":
                return left == right
            if op == "!=":
                return left != right
            if op == "<":
                return left < right
            if op == "<=":
                return left <= right
            if op == ">":
                return left > right
            if op == ">=":
                return left >= right
        except TypeError:
            return False
        raise SketchError("неизвестный оператор '%s'" % op)

    def _call_builtin(self, name, args, line):
        io = self.io

        if name == "pinMode":
            io.pin_mode(args[0], args[1])
            return 0
        if name == "digitalWrite":
            io.digital_write(args[0], args[1])
            return 0
        if name == "digitalRead":
            return io.digital_read(args[0])
        if name == "analogWrite":
            io.analog_write(args[0], args[1])
            return 0
        if name == "analogRead":
            return io.analog_read(args[0])
        if name == "tone":
            io.tone(args[0], args[1] if len(args) > 1 else 440)
            return 0
        if name == "noTone":
            io.no_tone(args[0])
            return 0
        if name == "millis":
            return io.millis()
        if name == "delay":
            ms = args[0] if args else 0
            yield ("delay", ms)
            return 0
        if name == "delayMicroseconds":
            return 0
        if name in ("Serial.begin", "Serial.print", "Serial.println", "Serial.flush", "Serial.write"):
            if name == "Serial.println" and args:
                io.log(str(args[0]))
            return 0
        if name == "constrain":
            x, lo, hi = args
            return max(lo, min(hi, x))
        if name == "map":
            x, in_min, in_max, out_min, out_max = args
            if in_max == in_min:
                return out_min
            return int((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)
        if name == "min":
            return min(args[0], args[1])
        if name == "max":
            return max(args[0], args[1])
        if name == "abs":
            return abs(args[0])
        if name == "sqrt":
            return args[0] ** 0.5
        if name == "random":
            if len(args) == 1:
                return _random.randrange(0, max(1, int(args[0])))
            return _random.randrange(int(args[0]), max(int(args[0]) + 1, int(args[1])))
        raise SketchError("неизвестная функция '%s()'" % name, line)
        yield  # pragma: no cover - делает метод генератором на всех путях
