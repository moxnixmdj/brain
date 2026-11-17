"""Tests for the coding instruction contract.

Two things have to be true before the corpus census means anything:

  1. the compiler CAN produce a discriminating contract -- instruction's own value, grounded in the
     environment's own callable, passing at the fixed state and failing at the parent;
  2. every refusal is a named missing half, not a swallowed exception.

The corpus result (2 of 40 real commit messages compile, 0 discriminate) is a statement about the supply of
specifications in real history, and it is only readable if the machinery is shown working first.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import textwrap

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import instruction_contract_for_code_v1 as I  # noqa: E402


def test_schema_and_no_model_no_network():
    assert I.SCHEMA == "BRAIN_INSTRUCTION_CONTRACT_FOR_CODE_V1"
    assert I.AUTHORITY == "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
    report = I.measure(None)
    assert report["model_calls"] == 0 and report["network_calls"] == 0
    assert "not fetched in this run" in report["corpus"]


def test_the_pattern_is_reused_from_the_computer_use_contract():
    """The clause language and its refusals are the tree's existing discipline, not a new one."""
    source = (pathlib.Path(__file__).resolve().parents[2] / "canonical" / "runtime"
              / "instruction_contract_v1.py").read_text(encoding="utf-8")
    assert "REFUSED__NO_CLAUSE_UNDERSTOOD" in source
    assert "compile_contract" in source
    assert I.NO_VALUE.startswith("REFUSED__") and I.NO_DIRECTION.startswith("REFUSED__")


# --------------------------------------------------------------------------- #
# the two halves of a discriminating pair
# --------------------------------------------------------------------------- #
def test_named_values_reads_quotes_first_and_ignores_prose():
    assert I.named_values('Add riscv64 as a supported manylinux architecture') == ["riscv64"]
    assert I.named_values('Fix the message "Expected matching RIGHT_PARENTHESIS" for now') == [
        "Expected matching RIGHT_PARENTHESIS"], I.named_values(
            'Fix the message "Expected matching RIGHT_PARENTHESIS" for now')
    assert I.named_values("Apply some ruff suggestions") == []
    # "Version 5.0" does name a value -- and names no direction, which is the refusal it earns
    assert I.named_values("Version 5.0") == ["5.0"]
    assert I.direction_of("Version 5.0") is None


def test_direction_is_a_closed_vocabulary_and_absence_is_named():
    assert I.direction_of("Add riscv64 as a supported architecture") == "WIDENING"
    assert I.direction_of("Remove the deprecated alias") == "NARROWING"
    assert I.direction_of("Fix the parser error message") == "REPAIR"
    assert I.direction_of("Apply some ruff suggestions") is None


def test_a_value_that_the_environment_does_not_contain_is_refused_by_name():
    contract = I.compile_contract("Add riscv64 as a supported architecture", "m", "def f(x):\n    return x\n")
    assert not contract["clauses"]
    assert contract["refusals"][0]["refusal"] == I.VALUE_NOT_IN_ENVIRONMENT


def test_a_value_that_lives_only_in_prose_is_refused_by_name():
    source = '"""Handles riscv64 in prose only."""\n\n\ndef f(x):\n    return x\n'
    contract = I.compile_contract("Add riscv64 as a supported architecture", "m", source)
    assert contract["refusals"][0]["refusal"] in (I.VALUE_NOT_IN_A_CALLABLE, I.VALUE_NOT_IN_ENVIRONMENT)


def test_a_value_is_grounded_in_every_callable_that_contains_it_and_the_parameter_is_chosen_by_name():
    source = textwrap.dedent(
        '''\
        def _have_compatible_abi(executable, archs):
            return "riscv64" in archs


        def supports_arch(arch):
            return arch in {"riscv64"}
        '''
    )
    sites, refusal = I.ground_sites("riscv64", source)
    assert refusal is None
    names = {site["function"] for site in sites}
    assert names == {"_have_compatible_abi", "supports_arch"}
    two = [site for site in sites if site["function"] == "_have_compatible_abi"]
    # one site per parameter position: which one carries the value is decided by execution, not by names
    assert sorted(site["value_index"] for site in two) == [0, 1]


def test_a_callable_that_needs_too_many_arguments_is_not_used_as_a_site():
    source = "def f(a, b, c, d):\n    return 'riscv64'\n"
    sites, refusal = I.ground_sites("riscv64", source)
    assert sites == []
    assert refusal == I.VALUE_NOT_IN_A_CALLABLE


def test_no_direction_refuses_even_when_the_value_grounds():
    contract = I.compile_contract("riscv64 was mentioned in passing", "m",
                                 "def f(x):\n    return 'riscv64' + x\n")
    assert not contract["clauses"]
    assert contract["refusals"][0]["refusal"] == I.NO_DIRECTION


# --------------------------------------------------------------------------- #
# end to end on a real two-state history: the compiler must be able to discriminate
# --------------------------------------------------------------------------- #
def _repo(tmp_path: pathlib.Path, parent: str, fixed: str) -> tuple[pathlib.Path, dict]:
    def git(*argv: str) -> str:
        return subprocess.run(("git",) + argv, cwd=str(tmp_path), capture_output=True, text=True,
                              check=True).stdout

    git("init", "-q")
    git("config", "user.email", "producer@localhost")
    git("config", "user.name", "producer")
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "tags.py").write_text(parent, encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "before")
    (package / "tags.py").write_text(fixed, encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "Support riscv64 as a supported architecture")
    sha = git("rev-parse", "HEAD").strip()
    return tmp_path, {"sha": sha, "message": "Support riscv64 as a supported architecture",
                      "sources": ["pkg/tags.py"], "tests": []}


def test_a_real_instruction_compiles_into_a_discriminating_contract(tmp_path):
    parent = 'def supports_arch(arch):\n    raise ValueError("unknown architecture")\n'
    fixed = 'def supports_arch(arch):\n    return arch in {"riscv64"}\n'
    repo, commit = _repo(tmp_path, parent, fixed)
    work = tmp_path / "work"
    work.mkdir()
    record = I.judge_commit(repo, commit, work)
    assert record["verdict"] == "DISCRIMINATING", record
    clause = record["modules"][0]["clauses"][0]
    assert clause["operator"] == "ACCEPTS_NAMED"
    assert clause["parent"]["outcome"] == "RAISED"
    assert clause["fixed"]["outcome"] == "RETURNED"


def test_a_contract_that_the_change_does_not_move_is_reported_vacuous(tmp_path):
    parent = '# a\ndef supports_arch(arch):\n    return "riscv64" in str(arch)\n'
    fixed = '# b\ndef supports_arch(arch):\n    return "riscv64" in str(arch)\n'
    repo, commit = _repo(tmp_path, parent, fixed)
    work = tmp_path / "work"
    work.mkdir()
    record = I.judge_commit(repo, commit, work)
    assert record["verdict"] == "VACUOUS", record


def test_a_contract_that_the_fixed_state_violates_is_reported_wrong(tmp_path):
    """The always-pass grader this tree already refused: a compiler scored only on its wins lies."""
    parent = 'def supports_arch(arch):\n    return arch\n'
    fixed = 'def supports_arch(arch):\n    raise ValueError("unknown architecture: riscv64")\n'
    repo, commit = _repo(tmp_path, parent, fixed)
    work = tmp_path / "work"
    work.mkdir()
    record = I.judge_commit(repo, commit, work)
    assert record["verdict"] == "WRONG_AT_FIXED", record


def test_a_bool_false_return_is_not_acceptance():
    """The always-pass bug one level down: returning False is the environment refusing the value."""
    assert I._succeeded({"outcome": "RETURNED", "type": "bool", "value_repr": "False"}) is False
    assert I._succeeded({"outcome": "RETURNED", "type": "bool", "value_repr": "True"}) is True
    assert I._succeeded({"outcome": "RETURNED", "type": "list", "value_repr": "['riscv64']"}) is True
    assert I._succeeded({"outcome": "RETURNED", "type": "list", "value_repr": "[]"}) is False
    assert I._succeeded({"outcome": "RAISED", "type": None, "value_repr": None}) is False


def test_a_site_that_returns_false_for_the_named_value_is_reported_wrong(tmp_path):
    parent = 'def supports(arch):\n    return "riscv64" in str(arch)\n'
    fixed = 'def supports(arch):\n    return "riscv64" in str(arch) and False\n'
    repo, commit = _repo(tmp_path, parent, fixed)
    work = tmp_path / "work"
    work.mkdir()
    record = I.judge_commit(repo, commit, work)
    assert record["verdict"] == "WRONG_AT_FIXED", record


def test_headline_reports_the_census_and_both_error_directions():
    report = {"states": {"commits": 40, "compiled": 2, "refused": 38, "discriminating": 0,
                         "vacuous": 1, "wrong_at_fixed": 1},
              "refusal_census": {"REFUSED__NO_DIRECTION_IN_THE_INSTRUCTION": 19,
                                 "REFUSED__THE_NAMED_VALUE_IS_NOT_IN_THE_ENVIRONMENT": 15}}
    line = I._headline(report)
    assert "40 real commits" in line
    assert "NO_DIRECTION_IN_THE_INSTRUCTION x19" in line
    assert "WRONG AT THE FIXED STATE" in line
    assert "always-pass grader" in line
