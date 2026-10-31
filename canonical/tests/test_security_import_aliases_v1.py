"""Bounded import qualification: equivalent findings, no scanned-code execution."""
import textwrap

import pytest

from canonical.runtime.bound_capabilities._swe_static_soundness_v1 import security_scan_python_source


def findings(source):
    return security_scan_python_source(textwrap.dedent(source), "sample.py")


@pytest.mark.parametrize("source,code", [
    ("import os as ops\nops.system(command)", "B605"),
    ("from os import system as launch\nlaunch(command)", "B605"),
    ("from os import popen\npopen(command)", "B605"),
    ("import pickle as codec\ncodec.loads(payload)", "B301"),
    ("from pickle import loads as decode\ndecode(payload)", "B301"),
    ("from marshal import load as decode\ndecode(stream)", "B301"),
    ("import yaml as config\nconfig.load(payload)", "B506"),
    ("from yaml import load as parse\nparse(payload)", "B506"),
    ("import hashlib as hashes\nhashes.md5(payload)", "B324"),
    ("from hashlib import sha1 as digest\ndigest(payload)", "B324"),
    ("from builtins import eval as evaluate\nevaluate(payload)", "B307"),
    ("from builtins import exec as execute\nexecute(payload)", "B102"),
])
def test_equivalent_import_spellings_keep_existing_finding_policy(source, code):
    rows = [row for row in findings(source) if row["test_id"] == code]
    assert len(rows) == 1
    assert rows[0]["line"] == 2
    assert rows[0]["file"] == "sample.py"
    assert rows[0]["confidence"] == "HIGH"


@pytest.mark.parametrize("body", [
    "def handler(ops):\n    ops.system(command)",
    "async def handler(ops):\n    ops.system(command)",
    "handler = lambda ops: ops.system(command)",
    "values = [ops.system(command) for ops in objects]",
    "values = {ops.system(command) for ops in objects}",
    "values = {key: ops.system(command) for key, ops in objects}",
    "values = (ops.system(command) for ops in objects)",
    "def handler():\n    ops = service\n    ops.system(command)",
    "def outer(ops):\n    def inner():\n        ops.system(command)",
])
def test_lexical_shadowing_does_not_expand_the_module_alias(body):
    assert not any(row["test_id"] == "B605" for row in findings("import os as ops\n" + body))


@pytest.mark.parametrize("body", [
    "def handler():\n    return ops.system(command)",
    "async def handler():\n    return ops.system(command)",
    "def handler():\n    global ops\n    return ops.system(command)",
    "handler = lambda: ops.system(command)",
    "values = [ops.system(item) for item in commands]",
    "class C:\n    ops = service\n    def handler(self):\n        return ops.system(command)",
    "def outer():\n    def inner():\n        return ops.system(command)",
    "def handler(value=ops.system(command)):\n    pass",
    "class C(ops.system(command)):\n    pass",
])
def test_unshadowed_global_alias_remains_visible_in_nested_contexts(body):
    assert sum(row["test_id"] == "B605" for row in findings("import os as ops\n" + body)) == 1


@pytest.mark.parametrize("source", [
    "import os as ops\nops = service\nops.system(command)",
    "import os as ops\nimport harmless as ops\nops.system(command)",
    "import os as ops\nif condition:\n    import harmless as ops\nops.system(command)",
    "from .os import system as launch\nlaunch(command)",
    "def setup():\n    import os as ops\ndef other():\n    ops.system(command)",
    "import os as ops\ndef reset():\n    global ops\n    ops = service\nops.system(command)",
])
def test_ambiguous_relative_or_other_scope_imports_are_not_qualified(source):
    assert not any(row["test_id"] == "B605" for row in findings(source))


def test_safe_loader_alias_is_recognized_without_accepting_a_name_substring():
    safe = "from yaml import load as parse, SafeLoader as Loader\nparse(payload, Loader=Loader)"
    assert not any(row["test_id"] == "B506" for row in findings(safe))
    unsafe = "import yaml\nyaml.load(payload, Loader=NotReallySafeLoader)"
    assert any(row["test_id"] == "B506" for row in findings(unsafe))


def test_weak_hash_alias_keeps_the_explicit_nonsecurity_exemption():
    source = "from hashlib import md5 as digest\ndigest(payload, usedforsecurity=False)"
    assert not any(row["test_id"] == "B324" for row in findings(source))


def test_same_line_lambdas_get_distinct_compiler_scopes():
    source = "import os as ops\nf = lambda ops: ops.system(command); g = lambda: ops.popen(command)"
    rows = [row for row in findings(source) if row["test_id"] == "B605"]
    assert [row["message"] for row in rows] == ["Starting a process with a shell via os.popen."]


def test_existing_direct_findings_secrets_and_determinism_are_retained():
    source = "import os\nos.system(command)\npassword = 'fixture-value'\n"
    first = findings(source)
    assert {row["test_id"] for row in first} == {"B605", "B105"}
    assert findings(source) == first


def test_scanned_code_is_never_imported_or_executed():
    source = "raise RuntimeError('do not execute')\nfrom os import system as launch\nlaunch(command)"
    assert any(row["test_id"] == "B605" for row in findings(source))


@pytest.mark.parametrize("body", [
    "@ops.system(command)\ndef handler(ops):\n    pass",
    "def handler(ops: ops.system(command)):\n    pass",
    "def handler(ops) -> ops.system(command):\n    pass",
    "values = [item for ops in ops.system(command) for item in ops]",
    "f = lambda ops=ops.system(command): ops.system(command)",
    "values = [(lambda: ops.system(command))() for item in commands]",
])
def test_outer_evaluated_expressions_and_nested_comprehensions(body):
    assert sum(row["test_id"] == "B605" for row in findings("import os as ops\n" + body)) == 1


@pytest.mark.parametrize("source", [
    "import os as ops\nfrom harmless import *\nops.system(command)",
    "import os as ops\nfrom .other import launch as ops\nops.system(command)",
    "import os as ops\ndef handler():\n    import harmless as ops\n    ops.system(command)",
    "import os as ops\nclass C:\n    ops = service\n    ops.system(command)",
])
def test_additional_unknown_bindings_are_not_expanded(source):
    assert not any(row["test_id"] == "B605" for row in findings(source))


def test_legacy_direct_spelling_checks_remain_when_qualification_is_unavailable():
    source = "import os\ndef handler(os):\n    os.system(command)"
    assert any(row["test_id"] == "B605" for row in findings(source))


@pytest.mark.parametrize("loader", ["SafeLoader", "CSafeLoader"])
def test_aliased_safe_loaders_keep_the_exemption(loader):
    source = f"import yaml as config\nfrom yaml import {loader} as Loader\nconfig.load(payload, Loader=Loader)"
    assert not any(row["test_id"] == "B506" for row in findings(source))


def test_shadowed_safe_loader_alias_does_not_exempt_an_unsafe_load():
    source = "from yaml import load as parse, SafeLoader as Loader\ndef handler(Loader):\n    parse(payload, Loader=Loader)"
    assert any(row["test_id"] == "B506" for row in findings(source))


@pytest.fixture(scope="module")
def fallback_python(tmp_path_factory):
    # An actual isolated stdlib interpreter: force no Bandit without replacing
    # imports, subprocess results, the scanner, or its tool probe.
    import os
    import venv
    home = tmp_path_factory.mktemp("security_stdlib")
    venv.EnvBuilder(with_pip=False, symlinks=True).create(home)
    return str(home / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))


@pytest.mark.parametrize("shadowed,changed_call,expected_gate", [
    (False, True, "FAIL"),
    (False, False, "PASS"),
    (True, True, "PASS"),
])
def test_real_fallback_gate_respects_alias_scope_and_changed_lines(
    tmp_path, fallback_python, shadowed, changed_call, expected_gate,
):
    import json
    from canonical.runtime.bound_capabilities import python_review_diff_security_gate as gate

    worktree = tmp_path / "wt"
    worktree.mkdir()
    param = "ops" if shadowed else ""
    source = f"import os as ops\ndef handler({param}):\n    ops.system(command)\n"
    (worktree / "sample.py").write_text(source)
    line = 3 if changed_call else 2
    # A valid one-line replacement hunk in the new-side source.
    new_line = source.splitlines()[line - 1]
    (tmp_path / "change.diff").write_text(
        f"--- a/sample.py\n+++ b/sample.py\n@@ -{line},1 +{line},1 @@\n-old_line\n+{new_line}\n"
    )
    result = gate.run({"diff_path": "change.diff", "worktree_path": "wt",
                       "output_path": "security.json", "python_executable": fallback_python}, tmp_path)
    artifact = json.loads((tmp_path / "security.json").read_text())
    assert result["bandit"].startswith("brain-ast-security-v1")
    assert result["gate"] == expected_gate
    blocking = [row for row in artifact["blocking_findings"] if row["test_id"] == "B605"]
    advisory = [row for row in artifact["advisory_findings"] if row["test_id"] == "B605"]
    if shadowed:
        assert blocking == [] and advisory == []
    elif changed_call:
        assert [row["line"] for row in blocking] == [3]
    else:
        assert blocking == []
        assert [row["out_of_scope"] for row in advisory] == ["preexisting"]


def test_same_line_dictionary_lambdas_follow_compiler_child_order():
    source = ("import os as ops\nvalues = {(lambda ops: ops.system(command))(service): "
              "(lambda: ops.popen(command))() for item in items}")
    rows = [row for row in findings(source) if row["test_id"] == "B605"]
    assert [row["message"] for row in rows] == ["Starting a process with a shell via os.popen."]


def test_same_line_comprehensions_have_separate_compiler_scopes():
    source = ("import os as ops\nbad = [ops.system(command) for ops in objects]; "
              "good = [ops.popen(command) for item in items]")
    rows = [row for row in findings(source) if row["test_id"] == "B605"]
    assert [row["message"] for row in rows] == ["Starting a process with a shell via os.popen."]


def test_same_line_vararg_annotations_follow_compiler_order():
    source = ("import os as ops\ndef handler(*args: (lambda ops: ops.system(command)), "
              "flag: (lambda: ops.popen(command))): pass")
    rows = [row for row in findings(source) if row["test_id"] == "B605"]
    assert [row["message"] for row in rows] == ["Starting a process with a shell via os.popen."]
