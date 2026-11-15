"""A tolerant reader for Lua table literals inside a Lua source file.

It understands tables, strings (all three forms), numbers, booleans, nil and
references to simple ``local NAME = literal`` constants. Anything else (function
calls, arithmetic, ``x or y``) is skipped and read as ``None`` instead of failing,
which is what an importer wants.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Tok:
    kind: str      # 'str' | 'num' | 'name' | 'op'
    value: Any
    pos: int


_NUM = re.compile(r"0[xX][0-9a-fA-F]+|\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?")
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_LONG = re.compile(r"\[(=*)\[")


def tokenize(src: str) -> list[Tok]:
    out: list[Tok] = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c in " \t\r\n":
            i += 1
            continue
        if src.startswith("--", i):
            m = _LONG.match(src, i + 2)
            if m:
                close = "]" + m.group(1) + "]"
                end = src.find(close, m.end())
                i = n if end < 0 else end + len(close)
            else:
                end = src.find("\n", i)
                i = n if end < 0 else end + 1
            continue
        m = _LONG.match(src, i)
        if m:
            close = "]" + m.group(1) + "]"
            end = src.find(close, m.end())
            body = src[m.end(): n if end < 0 else end]
            if body.startswith("\r\n"):
                body = body[2:]
            elif body.startswith("\n"):
                body = body[1:]
            out.append(Tok("str", body, i))
            i = n if end < 0 else end + len(close)
            continue
        if c in "'\"":
            j = i + 1
            buf = []
            while j < n and src[j] != c:
                if src[j] == "\\" and j + 1 < n:
                    nx = src[j + 1]
                    buf.append({"n": "\n", "t": "\t", "r": "\r", "\\": "\\", "'": "'", '"': '"'}.get(nx, nx))
                    j += 2
                else:
                    buf.append(src[j])
                    j += 1
            out.append(Tok("str", "".join(buf), i))
            i = j + 1
            continue
        m = _NUM.match(src, i)
        if m and (c.isdigit() or (c == "." and i + 1 < n and src[i + 1].isdigit())):
            t = m.group(0)
            v: Any = int(t, 16) if t.lower().startswith("0x") else (float(t) if any(x in t for x in ".eE") else int(t))
            out.append(Tok("num", v, i))
            i = m.end()
            continue
        m = _NAME.match(src, i)
        if m:
            out.append(Tok("name", m.group(0), i))
            i = m.end()
            continue
        for op in ("==", "~=", "<=", ">=", "..", "::"):
            if src.startswith(op, i):
                out.append(Tok("op", op, i))
                i += len(op)
                break
        else:
            out.append(Tok("op", c, i))
            i += 1
    return out


class Unresolved:
    """Marker for a value that could not be evaluated."""

    def __repr__(self) -> str:
        return "<unresolved>"


UNRESOLVED = Unresolved()


class LuaTableReader:
    def __init__(self, src: str):
        self.toks = tokenize(src)
        self.env: dict[str, Any] = {}
        self._read_locals()

    # ------------------------------------------------------------------ locals
    def _read_locals(self) -> None:
        t = self.toks
        i = 0
        while i < len(t):
            if t[i].kind == "name" and t[i].value == "local":
                names, j = [], i + 1
                while j < len(t) and t[j].kind == "name":
                    names.append(t[j].value)
                    if j + 1 < len(t) and t[j + 1].value == ",":
                        j += 2
                    else:
                        j += 1
                        break
                if names and j < len(t) and t[j].value == "=":
                    j += 1
                    values = []
                    while j < len(t) and len(values) < len(names):
                        tok = t[j]
                        nxt = t[j + 1] if j + 1 < len(t) else None
                        simple = tok.kind in ("str", "num") or (tok.kind == "op" and tok.value == "-" and nxt and
                                                                 nxt.kind == "num")
                        if not simple:
                            break
                        if tok.kind == "op":
                            values.append(-nxt.value)
                            j += 2
                        else:
                            values.append(tok.value)
                            j += 1
                        if j < len(t) and t[j].value == ",":
                            j += 1
                        else:
                            break
                    # only plain literal assignments are trusted
                    end_ok = j >= len(t) or t[j].kind == "name" or t[j].value in (";",)
                    if end_ok:
                        for nm, v in zip(names, values):
                            self.env[nm] = v
                i = j
            else:
                i += 1

    # ------------------------------------------------------------------ assignments
    def find_assignment(self, dotted: str) -> Optional[int]:
        """Index of the '{' that starts ``dotted = {`` (e.g. 'RW.DB'), or None."""
        parts = dotted.split(".")
        pattern: list[str] = []
        for k, p in enumerate(parts):
            if k:
                pattern.append(".")
            pattern.append(p)
        pattern += ["=", "{"]
        t = self.toks
        for i in range(len(t) - len(pattern) + 1):
            if all(t[i + k].value == pv for k, pv in enumerate(pattern)):
                if i > 0 and t[i - 1].value == ".":
                    continue
                return i + len(pattern) - 1
        return None

    def table_prefixes(self, key: str) -> list[str]:
        """Names X for which ``X.key = {`` appears (e.g. 'RW' for key 'UNITS')."""
        t = self.toks
        out = []
        for i in range(len(t) - 4):
            if (t[i].kind == "name" and t[i + 1].value == "." and t[i + 2].value == key and t[i + 3].value == "="
                    and t[i + 4].value == "{"):
                out.append(t[i].value)
        return out

    def read(self, dotted: str) -> Any:
        i = self.find_assignment(dotted)
        if i is None:
            return None
        value, _ = self._value(i)
        return value

    # ------------------------------------------------------------------ parser
    def _value(self, i: int) -> tuple[Any, int]:
        t = self.toks
        if i >= len(t):
            return None, i
        tok = t[i]
        if tok.value == "{" and tok.kind == "op":
            return self._table(i)
        if tok.kind == "op" and tok.value == "-" and i + 1 < len(t) and t[i + 1].kind == "num":
            return self._finish(-t[i + 1].value, i + 2)
        if tok.kind in ("str", "num"):
            return self._finish(tok.value, i + 1)
        if tok.kind == "name":
            if tok.value == "true":
                return self._finish(True, i + 1)
            if tok.value == "false":
                return self._finish(False, i + 1)
            if tok.value == "nil":
                return self._finish(None, i + 1)
            if tok.value in self.env:
                return self._finish(self.env[tok.value], i + 1)
            return self._skip_expr(i)
        return self._skip_expr(i)

    def _finish(self, value: Any, i: int) -> tuple[Any, int]:
        """A literal must be followed by ',', ';', '}' or ']'; otherwise it is an expression we skip."""
        t = self.toks
        if i >= len(t) or (t[i].kind == "op" and t[i].value in (",", ";", "}", "]")):
            return value, i
        return self._skip_expr(i, None)

    def _skip_expr(self, i: int, value: Any = None) -> tuple[Any, int]:
        t = self.toks
        depth = 0
        while i < len(t):
            v = t[i].value if t[i].kind == "op" else None
            if v in ("{", "(", "["):
                depth += 1
            elif v in ("}", ")", "]"):
                if depth == 0:
                    break
                depth -= 1
            elif v in (",", ";") and depth == 0:
                break
            i += 1
        return value, i

    def _table(self, i: int) -> tuple[Any, int]:
        t = self.toks
        i += 1   # past '{'
        arr: list[Any] = []
        hsh: dict[Any, Any] = {}
        while i < len(t) and not (t[i].kind == "op" and t[i].value == "}"):
            if t[i].kind == "op" and t[i].value == "[":
                key, i = self._value(i + 1)
                while i < len(t) and t[i].value != "]":
                    i += 1
                i += 1  # ']'
                if i < len(t) and t[i].value == "=":
                    val, i = self._value(i + 1)
                    hsh[key] = val
            elif t[i].kind == "name" and i + 1 < len(t) and t[i + 1].value == "=" and t[i + 1].kind == "op":
                key = t[i].value
                val, i = self._value(i + 2)
                hsh[key] = val
            else:
                val, i = self._value(i)
                arr.append(val)
            if i < len(t) and t[i].kind == "op" and t[i].value in (",", ";"):
                i += 1
        i += 1   # '}'
        if hsh and not arr:
            return hsh, i
        if arr and not hsh:
            return arr, i
        if not arr and not hsh:
            return [], i
        out = dict(hsh)
        for k, v in enumerate(arr, 1):
            out[k] = v
        return out, i
