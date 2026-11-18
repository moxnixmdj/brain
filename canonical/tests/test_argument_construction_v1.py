"""Tests for argument construction from the environment's own proofs.

The rules that matter, each of which this round measured:

  * a value is encodable only if it survives JSON unchanged -- no approximations;
  * a Name argument is resolved ONLY from a local literal assignment, a module-level literal constant, or
    a builtin type object. Everything else is refused by name, not guessed;
  * an action becomes observable only if the mined call RETURNS and returns the same thing twice;
  * an unlocked action is checked against the later release, because an unlocked action that is silently
    wrong would be worse than an unexercised one;
  * refusals are named one by one: NO_MINEABLE_CALL_SITE, EVERY_CALL_SITE_IS_UNENCODABLE,
    MINED_BUT_NEVER_RETURNED.
"""

from __future__ import annotations

import ast
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import argument_construction_v1 as A  # noqa: E402

OLD = '''\
TAGS = ["cp311-cp311-manylinux_2_17_x86_64", "py3-none-any"]


def parse_tag(tag):
    return tag.split("-")


def needs_state(state):
    return state.pos


def takes_type(parse_float):
    return parse_float("1.5")


def needs_pair(pair):
    return pair[0] + pair[1] + 1


def unused(anything):
    return anything
'''

# the later release moves parse_tag's observable, keeps the others identical
NEW = OLD.replace("    return pair[0] + pair[1] + 1", "    return pair[0] * pair[1] + 1")


def _tree(tmp_path: pathlib.Path, source: str, name: str = "old") -> pathlib.Path:
    root = tmp_path / name
    package = root / "pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "core.py").write_text(source, encoding="utf-8")
    return root


TEST_BODY = ("from pkg.core import needs_pair, parse_tag, takes_type\n\n\n"
             "def test_pair():\n"
             "    assert needs_pair([3, 7]) == 11\n\n\n"
             "def test_tag():\n"
             "    tag = \"cp311-cp311-manylinux_2_17_x86_64\"\n"
             "    assert parse_tag(tag)\n\n\n"
             "def test_type():\n"
             "    assert takes_type(float)\n")


def _with_tests(tmp_path: pathlib.Path, name: str = "oldcalls") -> pathlib.Path:
    tree = _tree(tmp_path, OLD, name)
    tests = tree / "tests"
    tests.mkdir()
    (tests / "test_core.py").write_text(TEST_BODY, encoding="utf-8")
    return tree


def test_schema_and_zero_model(tmp_path):
    report = A.measure(tmp_path / "c", tmp_path / "w", limit=0)
    assert report["schema"] == "BRAIN_ARGUMENT_CONSTRUCTION_V1"
    assert report["model_calls"] == 0 and report["network_calls"] == 0


def test_a_literal_is_encodable_and_an_object_is_not():
    assert A._encodable(ast.parse("'x'").body[0].value) == (True, "x")
    assert A._encodable(ast.parse("[1, 2]").body[0].value) == (True, [1, 2])
    ok, _ = A._encodable(ast.parse("SomeClass()").body[0].value)
    assert ok is False


def test_a_name_resolves_from_a_local_literal_or_a_module_constant_or_a_builtin():
    module = ast.parse("CONST = [1, 2]\n\n\ndef f():\n    local = 'z'\n    return local, CONST, float\n")
    function = [node for node in ast.walk(module) if isinstance(node, ast.FunctionDef)][0]
    constants = A.module_constants(module)
    assert A._resolve_name("local", A._scope_of(function), constants) == "@json:\"z\""
    assert A._resolve_name("CONST", A._scope_of(function), constants) == "@json:[1, 2]"
    assert A._resolve_name("float", A._scope_of(function), constants) == "@builtin:float"
    assert A._resolve_name("state", A._scope_of(function), constants) is None


def test_a_reassigned_local_is_not_propagated():
    module = ast.parse("def f():\n    x = 1\n    x = 2\n    return x\n")
    function = [node for node in ast.walk(module) if isinstance(node, ast.FunctionDef)][0]
    assert "x" not in A._scope_of(function)


def test_call_sites_are_mined_from_the_environment_including_its_tests(tmp_path):
    tree = _with_tests(tmp_path)
    mined = A.mined_vectors(tree, {"parse_tag", "takes_type", "unused"})
    assert mined["parse_tag"]["vectors"] == [['@json:"cp311-cp311-manylinux_2_17_x86_64"']]
    assert mined["takes_type"]["vectors"] == [["@builtin:float"]]
    assert mined["unused"]["refusal"] == A.REFUSED_NO_CALL_SITE


def test_a_call_site_with_a_keyword_or_a_star_is_never_approximated(tmp_path):
    tree = _tree(tmp_path, "def f(a, b):\n    return a\n", "o")
    (tree / "use.py").write_text("from pkg.core import f\nf(a=1, b=2)\nf(*[1, 2])\n", encoding="utf-8")
    mined = A.mined_vectors(tree, {"f"})
    assert mined["f"]["vectors"] == []


def test_an_action_becomes_observable_only_when_the_mined_call_really_returns(tmp_path):
    old, new = _with_tests(tmp_path, "oldexec"), _tree(tmp_path, NEW, "newexec")
    row = A.construct(old, new, "pkg/core.py", "pkg.core")
    verdicts = {entry["function"]: entry for entry in row["callables"]}
    assert verdicts["needs_pair"]["state"] == "BECAME_OBSERVABLE", verdicts["needs_pair"]
    assert verdicts["needs_pair"]["moved_at_new_release"] is True
    assert verdicts["needs_pair"]["move_kind"] == "VALUE_CHANGED"
    assert verdicts["needs_pair"]["witness"]["args"] == ["@json:[3, 7]"]


def test_an_object_argument_is_refused_by_name_not_guessed(tmp_path):
    old, new = _tree(tmp_path, OLD, "old"), _tree(tmp_path, NEW, "new")
    (old / "use.py").write_text("from pkg.core import needs_state\nneeds_state(state)\n", encoding="utf-8")
    row = A.construct(old, new, "pkg/core.py", "pkg.core")
    verdicts = {entry["function"]: entry for entry in row["callables"]}
    assert verdicts["needs_state"]["state"] == A.REFUSED_UNENCODABLE


def test_a_builtin_type_argument_is_accepted_because_real_call_sites_pass_it(tmp_path):
    old, new = _tree(tmp_path, OLD, "old"), _tree(tmp_path, NEW, "new")
    (old / "use.py").write_text("from pkg.core import takes_type\ntakes_type(float)\n", encoding="utf-8")
    row = A.construct(old, new, "pkg/core.py", "pkg.core")
    verdicts = {entry["function"]: entry for entry in row["callables"]}
    assert verdicts["takes_type"]["state"] == "BECAME_OBSERVABLE"
    assert verdicts["takes_type"]["moved_at_new_release"] is False


def test_headline_reports_the_unlock_fraction_and_every_refusal():
    report = {"totals": {"callables": 82, "ALREADY_OBSERVABLE_IN_ROUND_6": 40,
                         "round_6_unexercised": 41, "BECAME_OBSERVABLE": 1,
                         "unexercised_fraction_unlocked": 0.0244, "moved_at_new_release": 0,
                         A.REFUSED_NO_CALL_SITE: 1, A.REFUSED_UNENCODABLE: 34,
                         A.REFUSED_DID_NOT_RUN: 6}}
    line = A._headline(report)
    assert "82 real actions" in line
    assert "1 (0.0244) now RUN" in line
    assert "EVERY_CALL_SITE_IS_UNENCODABLE 34" in line
