from cmo_studio.export.compiler import compile_build_data, compile_event, ordered_units
from cmo_studio.model import Action, Event, Trigger


def test_hosts_come_first(sample):
    base = sample.units[0]
    sample.units.remove(base)
    sample.units.append(base)          # host now last in the list
    order = [u.id for u in ordered_units(sample)]
    for u in sample.units:
        if u.host and not u.reserve:
            assert order.index(u.host) < order.index(u.id)


def test_reserves_are_not_built(sample):
    D = compile_build_data(sample)
    ids = {u["id"] for u in D["UNITS"]}
    assert not any(u.id in ids for u in sample.units if u.reserve)
    for m in D["MISSIONS"]:
        assert not any(sample.unit(x).reserve for x in m["units"])


def test_time_trigger_becomes_guarded_repeatable_event(sample):
    e = Event(name="At start", repeatable=False, triggers=[Trigger("StudioAfterDelay", {"Minutes": 30})],
              actions=[Action("EndScenario")])
    c = compile_event(sample, e)
    assert c["repeatable"] is True
    assert c["triggers"][0]["spec"] == {"type": "RegularTime", "Interval": 4}
    assert str(sample.clock.start_epoch() + 1800) in c["script"]
    assert "StudioSetFlag" in c["script"] and "ScenEdit_EndScenario" in c["script"]


def test_plain_event_keeps_flags(sample):
    e = Event(name="Plain", repeatable=False,
              triggers=[Trigger("UnitDestroyed", {"TargetSide": sample.sides[0].id})],
              actions=[Action("Score", {"Side": sample.sides[1].id, "Change": 5})])
    c = compile_event(sample, e)
    assert c["repeatable"] is False
    assert c["triggers"][0]["spec"]["TargetFilter"]["TargetSide"] == sample.sides[0].name
    assert "StudioFlag" not in c["script"]


def test_raw_actions_are_native(sample):
    e = Event(name="Raw", triggers=[Trigger("ScenLoaded")],
              actions=[Action("Raw", {"Spec": "{ type = 'Points', SideId = 'Blue', PointChange = 5 }"})])
    c = compile_event(sample, e)
    assert c["script"] == ""
    assert c["actions"][0]["spec"].startswith("{ type = 'Points'")


def test_hosted_unit_has_no_position(sample):
    D = compile_build_data(sample)
    hosted = [u for u in D["UNITS"] if "host" in u]
    assert hosted and all("lat" not in u for u in hosted)
