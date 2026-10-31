# PROJECT_BRAIN
"""A mutant must change its stated AST span, not unrelated source bytes."""
from __future__ import annotations

import difflib
import json
import sys

import pytest

from canonical.runtime.bound_capabilities import python_review_diff_mutation_gate as gate


@pytest.mark.parametrize("prefix,old,new,suffix", [
    ("LABEL = 'plain'\n", "1", "2", ""),
    ("LABEL = 'café 🧠'\n", "1", "2", ""),
    ("LABEL = 'comment'\n", "1", "2", "  # unchanged trailing comment"),
    ("LABEL = 'float'\n", "1.5", "2.5", ""),
], ids=["plain", "utf8-prefix", "trailing-comment", "floating-point"])
def test_blind_suite_cannot_kill_a_mutant_by_losing_the_rest_of_the_file(
        tmp_path, monkeypatch, prefix, old, new, suffix):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    anchor = tmp_path / "anchor"
    (anchor / "tests").mkdir(parents=True)
    tail = "\n\ndef preserved():\n    return 'still here'\n"
    original = prefix + f"VALUE = {old}{suffix}" + tail
    patched = prefix + f"VALUE = {new}{suffix}" + tail
    (anchor / "subject.py").write_text(original, encoding="utf-8")
    (anchor / "tests/test_subject.py").write_text(
        "from subject import preserved\ndef test_preserved():\n    assert preserved() == 'still here'\n")
    diff = "".join(difflib.unified_diff(original.splitlines(keepends=True),
                                        patched.splitlines(keepends=True), n=1,
                                        fromfile="a/subject.py", tofile="b/subject.py"))
    (tmp_path / "change.diff").write_text(diff, encoding="utf-8")
    result = gate.run({"anchor_path": "anchor", "diff_path": "change.diff",
                       "output_path": "out/mutation.json", "python_executable": sys.executable,
                       "max_mutants": 1, "timeout_s": 30}, tmp_path)
    artifact = json.loads((tmp_path / "out/mutation.json").read_text())
    assert artifact["mutants_generated"] == 1
    assert artifact["survivors"][0]["operator"] == "numeric_bump"
    assert result["gate"] == "FAIL"
    assert result["mutants_killed"] == 0
    assert result["mutants_survived"] == 1


@pytest.mark.parametrize("source,line,operator,old,new", [
    ("def f(é):\n    return é <= 2\n", 2, "compare_swap", "<=", ">"),
    ("def f():\n    return 'é' if True else 'no'\n", 2, "bool_swap", "True", "False"),
    ("def f():\n    return len('é') + 2\n", 2, "arith_swap", "+", "-"),
    ("def f(é):\n    é += 2\n    return é\n", 2, "aug_swap", "+=", "-="),
    ("def f():\n    return 2.5  # café\n", 2, "numeric_bump", "2.5", "3.5"),
    ("def f():\n    return len('é')  # preserve comment\n", 2, "return_none", "return len('é')", "return None"),
], ids=["comparison", "boolean", "arithmetic", "augmented", "numeric", "return"])
def test_existing_byte_splice_preserves_everything_outside_the_site(source, line, operator, old, new):
    sites = [site for site in gate._mutants_for_text("subject.py", source, {line}, 50)
             if site.kind == operator]
    assert len(sites) == 1
    mutated = gate._apply_splice(source, "subject.py", sites[0])
    assert mutated == source.replace(old, new, 1)


@pytest.mark.parametrize("value", [0, 1])
def test_numeric_zero_and_one_are_not_misclassified_as_boolean_constants(value):
    source = f"VALUE = {value}\n"
    sites = [site for site in gate._mutants_for_text("subject.py", source, {1}, 10)
             if site.kind == "numeric_bump"]
    assert len(sites) == 1
    assert gate._apply_splice(source, "subject.py", sites[0]) == f"VALUE = {value + 1}\n"
