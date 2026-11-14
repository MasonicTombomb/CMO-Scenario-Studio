from cmo_studio.export.lua_writer import LuaRaw, lua_key, lua_long_str, lua_str, lua_value


def test_strings_are_escaped():
    assert lua_str('a"b\\c\nd') == '"a\\"b\\\\c\\nd"'


def test_long_string_level_avoids_collisions():
    s = lua_long_str("x ]] y ]=] z")
    assert s.startswith("[==[\n") and s.endswith("]==]")


def test_keys():
    assert lua_key("name") == "name"
    assert lua_key("end") == '["end"]'
    assert lua_key("with space") == '["with space"]'
    assert lua_key(3) == "[3]"


def test_values():
    assert lua_value(None) == "nil"
    assert lua_value(True) == "true"
    assert lua_value(1.0) == "1.0"
    assert lua_value([1, 2]) == "{ 1, 2 }"
    assert lua_value({"a": 1, "b": None}) == "{ a = 1 }"
    assert lua_value(LuaRaw("{ type = 'X' }")) == "{ type = 'X' }"
