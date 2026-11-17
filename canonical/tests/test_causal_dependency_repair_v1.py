"""A repair built on the wrong read set reports success and leaves the work wrong.

Pinned: the receipt. Live: the discovery rule itself, re-run against states this file builds -- a perturbation
finds a dependency that no argument names, and does not invent one that only an argument names.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import causal_dependency_repair_v1 as repair  # noqa: E402
from canonical.swe_kernel.computer_use_check_density_v1 import _has  # noqa: E402

RECEIPT = ROOT / "canonical" / "verification" / "CAUSAL_DEPENDENCY_REPAIR_20261116_V1.json"


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# live: the rule, not the recording of the rule
# --------------------------------------------------------------------------- #
def test_a_path_named_only_by_data_is_discovered_by_perturbation(tmp_path: pathlib.Path) -> None:
    """`tar -T list.txt` never says `payload.dat`; changing payload.dat changes the tarball anyway."""
    if not _has("tar"):
        pytest.skip("tar not on PATH")
    state = {"list.txt": b"payload.dat\n", "payload.dat": b"original\n", "other.dat": b"unrelated\n"}
    found = repair.read_set_intervention("tar -cf out.tar -T list.txt", state, tmp_path)
    assert "payload.dat" in found["dependent_on"]
    assert "list.txt" in found["dependent_on"]
    assert "other.dat" not in found["dependent_on"]
    # and the syntactic reading of the same command cannot see it
    assert "payload.dat" not in repair.read_set_argv("tar -cf out.tar -T list.txt", state)


def test_a_name_that_is_only_mentioned_is_not_a_dependency(tmp_path: pathlib.Path) -> None:
    """`ls payload.dat` names the path and does not depend on its content: the argv set over-declares."""
    if not _has("ls"):
        pytest.skip("ls not on PATH")
    state = {"payload.dat": b"original\n"}
    command = "ls payload.dat"
    assert repair.read_set_argv(command, state) == {"payload.dat"}
    assert repair.read_set_intervention(command, state, tmp_path)["dependent_on"] == []


def test_the_perturbation_matches_the_kind_of_fact() -> None:
    """A content probe answers a content question. Stated as a test so the limit cannot drift into a claim."""
    assert b"\nprobe marker" in repair.PROBE_SUFFIX
    assert repair.PROBE_SUFFIX  # appended, never truncating: the perturbation is a content change


def test_a_step_that_only_reads_its_source_cannot_see_the_rest_of_the_state(tmp_path: pathlib.Path) -> None:
    if not _has("cp"):
        pytest.skip("cp not on PATH")
    state = {"a": b"1\n", "b": b"2\n", "c": b"3\n"}
    found = repair.read_set_intervention("cp a out", state, tmp_path)
    assert found["dependent_on"] == ["a"]
    assert found["probes"] == 3


# --------------------------------------------------------------------------- #
# pinned: the receipt
# --------------------------------------------------------------------------- #
def test_the_receipt_numbers(report: dict) -> None:
    assert report["chains"] == 3
    assert report["steps"] == 17
    assert report["model_calls"] == 0 and report["network_calls"] == 0
    assert report["arms"]["declared_deps"]["goals_passing"] == 3
    assert report["arms"]["intervention_deps"]["goals_passing"] == 3
    assert report["arms"]["argv_deps"]["goals_passing"] == 1
    assert report["arms"]["redo_everything"]["goals_passing"] == 3


def test_syntax_loses_and_intervention_does_not(report: dict) -> None:
    assert report["chains_where_syntax_misses_a_real_dependency"] == [
        "tar_reads_a_name_from_a_list", "xargs_reads_a_name_from_stdin"]
    assert report["missed_by_argv"]["tar_reads_a_name_from_a_list"] == [
        "bundle_by_list", "digest_the_bundle", "keep_the_digest"]
    assert report["missed_by_argv"]["xargs_reads_a_name_from_stdin"] == [
        "digest_by_xargs", "digest_the_checks"]
    for chain, missed in report["missed_by_intervention"].items():
        assert missed == [], chain
    for chain, over in report["over_declared_by_intervention"].items():
        assert over == [], chain
    assert all(report["intervention_matches_declared"].values())


def test_the_argv_set_is_wrong_in_both_directions(report: dict) -> None:
    """Over-declares on the step that only lists the name; under-declares on the step that consumes it."""
    assert report["over_declared_by_argv"]["tar_reads_a_name_from_a_list"] == ["list_it"]
    assert report["blamed_by"]["tar_reads_a_name_from_a_list"]["argv_reads"] == ["list_it"]
    assert report["blamed_by"]["tar_reads_a_name_from_a_list"]["intervention"] == ["bundle_by_list"]
    assert report["blamed_by"]["xargs_reads_a_name_from_stdin"]["intervention"] == ["digest_by_xargs"]


def test_the_control_chain_does_not_separate_the_arms(report: dict) -> None:
    """Where the dependency is syntactic, both arms agree -- so the difference above is the dependency, not luck."""
    control = [entry for entry in report["per_chain"]
               if entry["chain"] == "control_the_dependency_is_syntactic"][0]
    assert control["repair"]["argv_deps"]["redone"] == control["repair"]["declared_deps"]["redone"]
    assert control["repair"]["intervention_deps"]["redone"] == control["repair"]["declared_deps"]["redone"]
    assert control["invalidated"] == ["a.dat"]


def test_repair_is_cheaper_than_rebuilding(report: dict) -> None:
    assert report["arms"]["intervention_deps"]["steps_redone"] < report["arms"]["redo_everything"]["steps_redone"]
    assert report["arms"]["intervention_deps"]["steps_redone"] == report["arms"]["declared_deps"]["steps_redone"]


def test_the_goal_is_an_independent_program_and_it_really_fails(report: dict) -> None:
    """A repair that reports success while the work is wrong is the failure mode; the symptom must be real."""
    symptoms = [entry["repair"]["argv_deps"]["symptom"] for entry in report["per_chain"]
                if entry["chain"] != "control_the_dependency_is_syntactic"]
    assert all(symptoms), symptoms
    assert any("differ" in symptom or "FAILED" in symptom for symptom in symptoms)
    for entry in report["per_chain"]:
        assert entry["repair"]["argv_deps"]["goal_passes"] is False or \
            entry["chain"] == "control_the_dependency_is_syntactic"


def test_the_receipt_is_history_not_a_declaration(report: dict) -> None:
    """Rows keyed `command` are counted as declared predicates by the auditability floor. Rows are invocations."""
    text = RECEIPT.read_text(encoding="utf-8")
    assert '"command"' not in text
    assert '"argv":' not in text      # a dict with an `argv` key is counted as a declared predicate
    for entry in report["per_chain"]:
        assert entry["goal"]["invocation"]
        for step in entry["steps"]:
            assert step["invocation"]
