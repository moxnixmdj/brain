from canonical.runtime.livebench_legacy15_composition_archetypes_v1 import (
    ARCHETYPE_ORDER,
    enumerate_compatible_sets,
    archetype,
)
from canonical.runtime.livebench_legacy15_unified_composer_v1 import (
    GENERAL_ARCHETYPES,
    SPECIAL_ARCHETYPES,
    SUPPORTED_ARCHETYPES,
    route_for_ids,
)


def test_all_seven_archetypes_are_owned_by_exactly_one_route():
    assert set(ARCHETYPE_ORDER) == SUPPORTED_ARCHETYPES
    assert SPECIAL_ARCHETYPES.isdisjoint(GENERAL_ARCHETYPES)
    assert SPECIAL_ARCHETYPES | GENERAL_ARCHETYPES == SUPPORTED_ARCHETYPES


def test_all_928_conflict_compatible_active15_sets_have_a_route():
    sets = enumerate_compatible_sets()
    assert len(sets) == 928
    routes = [route_for_ids(ids) for ids in sets]
    assert len(routes) == 928
    assert set(routes) == {"SPECIAL", "GENERAL"}


def test_route_agrees_with_archetype_partition_for_all_928_sets():
    for ids in enumerate_compatible_sets():
        mode = archetype(ids)
        expected = "SPECIAL" if mode in SPECIAL_ARCHETYPES else "GENERAL"
        assert route_for_ids(ids) == expected


def test_empty_or_conflicting_sets_fail_closed():
    for ids in [
        (),
        ("detectable_format:json_format", "startend:end_checker"),
        ("detectable_format:title", "startend:quotation"),
    ]:
        try:
            route_for_ids(ids)
        except ValueError:
            pass
        else:
            raise AssertionError(ids)
