import re

from canonical.runtime import livebench_legacy15_parameter_geometry_v1 as g


def test_verify_parameter_geometry():
    out = g.verify()
    assert out["status"].startswith("PASS__")
    assert out["terminal_rows_read"] == 0
    assert out["acceptance_credit"] is False


def test_compact_section_marker_preserves_checker_shape_and_breaks_word_boundary():
    marker = g.section_marker("Section", 3, ["section"])
    assert marker == "Section3"
    assert g.section_marker_checker_shape(marker, "Section")
    assert re.search(r"\bsection\b", marker, re.IGNORECASE) is None


def test_exact_end_phrase_forbidden_collision_is_irreducible():
    assert g.exact_end_forbidden_obstruction(
        "Any other questions?", ["other", "rock"]
    ) == ("other",)
    assert set(g.exact_end_forbidden_obstruction(
        "Is there anything else I can help with?", ["anything", "can", "help"]
    )) == {"anything", "can", "help"}


def test_nth_first_word_forbidden_collision_is_irreducible():
    assert g.nth_first_word_forbidden_obstruction("River", ["river"])
    assert not g.nth_first_word_forbidden_obstruction("River", ["rock"])
