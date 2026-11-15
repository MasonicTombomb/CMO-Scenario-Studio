from cmo_studio.model import Mission, Unit, Zone
from cmo_studio.model.validation import ERROR, validate


def errors(p):
    return [i.message for i in validate(p) if i.level == ERROR]


def test_sample_is_clean(sample):
    assert errors(sample) == []


def test_patrol_needs_three_points_and_own_side_area(sample):
    red = sample.sides[1]
    z = Zone(side=sample.sides[0].id, name="TINY", points=[[1, 1], [2, 2]])
    sample.zones.append(z)
    sample.missions.append(Mission(side=red.id, name="Bad", mclass="patrol", subtype="aaw", zone=z.id))
    msgs = " ".join(errors(sample))
    assert "3 points" in msgs and "belongs to" in msgs


def test_spawn_needs_reserve(sample):
    for u in sample.units:
        u.reserve = False
    assert any("reinforcement" in m for m in errors(sample))


def test_wrong_side_assignment(sample):
    red_ship = next(u for u in sample.units if u.type == "Ship")
    sample.missions[0].units.append(red_ship.id)
    assert any("belongs to another side" in m for m in errors(sample))


def test_unplaceable_type(sample):
    sample.units.append(Unit(side=sample.sides[0].id, type="Satellite", dbid=1, name="Sat", lat=1, lon=1))
    assert any("cannot be placed" in m for m in errors(sample))
