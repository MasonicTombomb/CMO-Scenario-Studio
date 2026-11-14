"""Python value -> Lua source literal."""

from __future__ import annotations

import math
import re
from typing import Any

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
LUA_KEYWORDS = {
    "and", "break", "do", "else", "elseif", "end", "false", "for", "function", "goto", "if", "in",
    "local", "nil", "not", "or", "repeat", "return", "then", "true", "until", "while",
}


class LuaRaw(str):
    """A string that is already Lua source and is emitted verbatim (e.g. a user's raw table)."""


def lua_str(s: str) -> str:
    """A double-quoted Lua string literal."""
    out = ['"']
    for ch in str(s):
        o = ord(ch)
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif o < 32 or o == 127:
            out.append(f"\\{o:03d}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def lua_long_str(s: str) -> str:
    """A long-bracket literal ``[==[ ... ]==]`` that keeps the text verbatim (good for scripts)."""
    s = str(s)
    level = 0
    while ("]" + "=" * level + "]") in s:
        level += 1
    eq = "=" * level
    # Lua drops a newline that directly follows the opening bracket, so always add one.
    return f"[{eq}[\n{s}]{eq}]"


def lua_key(k: Any) -> str:
    if isinstance(k, bool):
        return f"[{'true' if k else 'false'}]"
    if isinstance(k, int):
        return f"[{k}]"
    k = str(k)
    if _IDENT.match(k) and k not in LUA_KEYWORDS:
        return k
    return f"[{lua_str(k)}]"


def lua_value(v: Any, indent: int = 0, width: int = 110, long_strings: bool = False) -> str:
    """Serialise ``v`` (None/bool/number/str/list/tuple/dict) as Lua.

    Small tables are written on one line; larger ones one entry per line.
    """
    if v is None:
        return "nil"
    if isinstance(v, LuaRaw):
        return str(v).strip() or "{}"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return "0"
        if v.is_integer() and abs(v) < 1e15:
            return f"{v:.1f}"
        return repr(round(v, 6))
    if isinstance(v, str):
        if long_strings and ("\n" in v or len(v) > 80):
            return lua_long_str(v)
        return lua_str(v)
    if isinstance(v, (list, tuple)):
        items = [lua_value(x, indent + 2, width, long_strings) for x in v]
        return _table(items, indent, width)
    if isinstance(v, dict):
        items = [f"{lua_key(k)} = {lua_value(x, indent + 2, width, long_strings)}" for k, x in v.items()
                 if x is not None]
        return _table(items, indent, width)
    return lua_str(str(v))


def _table(items: list[str], indent: int, width: int) -> str:
    if not items:
        return "{}"
    one = "{ " + ", ".join(items) + " }"
    if "\n" not in one and len(one) + indent <= width:
        return one
    pad = " " * (indent + 2)
    return "{\n" + "".join(f"{pad}{it},\n" for it in items) + " " * indent + "}"
