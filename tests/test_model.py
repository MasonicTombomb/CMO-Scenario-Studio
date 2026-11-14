from cmo_studio.model import Project, Unit, new_project
from cmo_studio.model.project import safe_folder_name, safe_prefix


def test_roundtrip(sample):
    again = Project.from_json(sample.to_json())
    assert again.to_dict() == sample.to_dict()


def test_unknown_keys_are_ignored_and_missing_get_defaults():
    p = Project.from_dict({"format": "cmo-scenario-studio", "meta": {"title": "X", "future_field": 1},
                           "units": [{"name": "A", "count": "3"}]})
    assert p.meta.title == "X"
    assert p.units[0].count == 3
    assert p.units[0].type == "Facility"


def test_remove_unit_cascades_to_hosted_and_missions(sample):
    base = sample.units[0]
    hosted = [u.id for u in sample.hosted_by(base.id)]
    assert hosted
    sample.remove_unit(base.id)
    assert not any(u.id in hosted for u in sample.units)
    assert all(h not in m.units for m in sample.missions for h in hosted)


def test_remove_side_cascades(sample):
    red = sample.sides[1]
    sample.remove_side(red.id)
    assert all(u.side != red.id for u in sample.units)
    assert all(red.id not in s.postures for s in sample.sides)
    assert all(red.id not in v.computer_sides for v in sample.variants)


def test_new_side_gets_postures():
    p = new_project("T")
    c = p.add_side("Civ")
    assert all(c.id in s.postures for s in p.sides if s is not c)
    assert set(c.postures) == {s.id for s in p.sides if s is not c}


def test_safe_names():
    assert safe_folder_name('If: Russia "Wins"?') == "If Russia Wins"
    assert safe_prefix("If Russia Wins") == "IfRussiaWins"


def test_unique_unit_name():
    p = new_project()
    sid = p.sides[0].id
    p.units.append(Unit(side=sid, name="Ship"))
    assert p.unique_unit_name("Ship", sid) == "Ship 2"
