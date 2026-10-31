"""Recovered SWE mechanisms must compose with the current safeguards.

Fresh source bytes are the oracle; no historical imports or replayed receipts.
The pure index must agree with the incremental adapter without publishing, and
static cost/taint reports must expose the limits of their analysis model.
"""
from __future__ import annotations

import json

import pytest

from canonical.runtime.bound_capabilities import python_source_complexity as complexity
from canonical.runtime.bound_capabilities import python_source_symbol_index as index
from canonical.runtime.bound_capabilities import python_source_taint_flow as taint


def test_pure_index_agrees_with_incremental_adapter_without_publishing(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    source = pkg / "m.py"
    source.write_text("def leaf():\n    return 1\ndef caller():\n    return leaf()\n")
    sibling = pkg / "other.py"
    sibling.write_text("def leaf():\n    return 99\n")
    before = {p.name: p.read_bytes() for p in pkg.iterdir()}

    pure = index.build_index("pkg/m.py", tmp_path)
    assert {p.name: p.read_bytes() for p in pkg.iterdir()} == before
    assert [r["path"] for r in pure["modules"]] == ["pkg/m.py"]
    assert pure["callers_of"]["leaf"] == ["caller"]
    args = {"source_root": "pkg/m.py", "output_path": "index.json"}
    cold = index.run(args, tmp_path)
    assert json.loads((tmp_path / "index.json").read_text()) == pure
    warm = index.run(args, tmp_path)
    assert cold["parsed_module_count"] == 1
    assert warm["parsed_module_count"] == 0
    assert warm["reused_module_count"] == 1
    assert warm["output_sha256"] == cold["output_sha256"]
    assert {p.name: p.read_bytes() for p in pkg.iterdir()} == before


def test_interprocedural_cost_and_cyclomatic_metrics_coexist(tmp_path):
    (tmp_path / "m.py").write_text(
        "def leaf(items):\n"
        "    for x in items:\n"
        "        if x > 0 and x < 10:\n"
        "            print(x)\n"
        "def caller(items):\n"
        "    for item in items:\n"
        "        leaf(items)\n"
        "def fork(n):\n"
        "    if n <= 1:\n"
        "        return n\n"
        "    return fork(n // 2) + fork(n // 2)\n"
    )
    complexity.run({"source_root": "m.py", "output_path": "cost.json"}, tmp_path)
    report = json.loads((tmp_path / "cost.json").read_text())
    rows = {r["name"]: r for r in report["functions"]}
    assert rows["caller"]["local_nesting"] == 1
    assert rows["caller"]["nesting"] == 2
    assert rows["caller"]["complexity_class"] == "O(n^2)"
    assert rows["leaf"]["cyclomatic_complexity"] == 4
    # Two recursive sites alone cannot prove an exponential recurrence: fork
    # halves its argument.  The structural estimate must be labeled as such.
    assert report["analysis_model"] == "STRUCTURAL_UNIT_COST_HEURISTIC"
    assert report["is_asymptotic_proof"] is False
    assert rows["fork"]["recursion_model"] == "BRANCHING_CALL_SITE_HEURISTIC"


@pytest.mark.parametrize("escaping", ["shlex.quote", "html.escape", "urllib.parse.quote"])
def test_shell_html_and_url_escaping_do_not_sanitize_python_execution(tmp_path, escaping):
    (tmp_path / "m.py").write_text(
        "import json, shlex, html, urllib.parse\n"
        "def parse_request(raw):\n"
        "    return json.loads(raw)\n"
        "def forward(code):\n"
        "    exec(code)\n"
        "def handle(raw):\n"
        f"    forward({escaping}(parse_request(raw)['code']))\n"
    )
    result = taint.run({"source_root": "m.py", "output_path": "taint.json"}, tmp_path)
    assert result["answer"] == "yes"
    assert result["reaches"] is True
    assert any(r["sink"] == "exec" for r in result["trace"])


def test_shell_quote_still_blocks_shell_injection_through_helpers(tmp_path):
    (tmp_path / "m.py").write_text(
        "import json, shlex, os\n"
        "def parse_request(raw):\n"
        "    return json.loads(raw)\n"
        "def forward(command):\n"
        "    os.system(command)\n"
        "def handle(raw):\n"
        "    forward(shlex.quote(parse_request(raw)['command']))\n"
    )
    result = taint.run({"source_root": "m.py", "output_path": "taint.json"}, tmp_path)
    assert result["answer"] == "no"
    assert result["trace"] == []


def test_shadowed_numeric_coercion_does_not_sanitize_taint(tmp_path):
    (tmp_path / "m.py").write_text(
        "import json\n"
        "def int(value):\n"
        "    return value\n"
        "def parse_request(raw):\n"
        "    return json.loads(raw)\n"
        "def handle(raw):\n"
        "    exec(int(parse_request(raw)['code']))\n"
    )
    result = taint.run({"source_root": "m.py", "output_path": "taint.json"}, tmp_path)
    assert result["answer"] == "yes"
    assert result["reaches"] is True


def test_extract_region_and_helper_name_are_never_invented(tmp_path):
    from canonical.runtime import declared_input_derivation_v1 as derivation
    from canonical.runtime import goal_front_compiler_v1 as front

    (tmp_path / "m.py").write_text("def big(x):\n    y = x + 1\n    return y\n")
    args = {key: "${input." + key + "}" for key in
            ("source_root", "module", "qualname", "new_name", "start_line", "end_line")}
    entry = {"action_template": {"args": args}}
    goal = "Extract the function big from m.py into a new function named helper"
    values = derivation.derive(goal, entry, tmp_path)
    assert "start_line" not in values
    assert "end_line" not in values
    assert values["new_name"]["value"] == "helper"
    goal = "Extract the function big from m.py lines 2 to 3"
    values = derivation.derive(goal, entry, tmp_path)
    assert "new_name" not in values
    assert front.bind_typed_key(goal, "start_line", tmp_path, entry) == 2
    assert front.bind_typed_key(goal, "end_line", tmp_path, entry) == 3


@pytest.mark.parametrize("suite", ["", (
    "import unittest\n"
    "@unittest.skip('disabled')\n"
    "class TestDisabled(unittest.TestCase):\n"
    "    def test_disabled(self):\n"
    "        self.fail('must not run')\n"
)])
def test_native_crossfile_repair_needs_non_skipped_executed_tests(tmp_path, suite):
    from canonical.runtime.bound_capabilities import software_repair_crossfile_choreograph_v1 as crossfile

    project = tmp_path / "project"
    project.mkdir()
    module = project / "m.py"
    original = b"def add(a, b):\n    return a - b\n"
    module.write_bytes(original)
    if suite:
        tests = project / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("")
        (tests / "test_disabled.py").write_text(suite)
    with pytest.raises(RuntimeError, match="CHOREOGRAPHY_REPAIR_UNRESOLVED"):
        crossfile.run({"source_root": "project", "output_path": "report.json"}, tmp_path)
    assert module.read_bytes() == original
    assert not (tmp_path / "report.json").exists()
