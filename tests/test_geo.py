import pytest

from cmo_studio.geo import distance_km, from_world, parse_latlon, to_world


@pytest.mark.parametrize("text,lat,lon", [
    ("59.377, 28.19", 59.377, 28.19),
    ("-33.5; 151.2", -33.5, 151.2),
    ("59°22'12\"N 28°11'24\"E", 59.37, 28.19),
    ("59 22 12 N, 28 11 24 W", 59.37, -28.19),
])
def test_parse(text, lat, lon):
    assert parse_latlon(text) == pytest.approx((lat, lon), abs=1e-3)


def test_parse_rejects_nonsense():
    assert parse_latlon("hello") is None
    assert parse_latlon("95, 10") is None


def test_mercator_roundtrip():
    x, y = to_world(59.4, 24.7, 7)
    assert from_world(x, y, 7) == pytest.approx((59.4, 24.7), abs=1e-6)


def test_distance():
    assert distance_km(59.437, 24.745, 60.170, 24.938) == pytest.approx(82, abs=2)   # Tallinn-Helsinki
