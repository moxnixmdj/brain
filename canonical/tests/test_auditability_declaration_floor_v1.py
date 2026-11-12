"""The floor must count what the instrument counts, and it must not execute anything.

`--audit` answers "what currently holds" by running 605 commands for ~13 minutes and writing
into the tree it measures. That is the right instrument for a diagnosis and the wrong one for a
gate: its verdicts move with what the machine has installed (8 of the 58 failures measured on
2026-11-12 name another machine's filesystem outright, and 19 predicates land in the 30s timeout
budget), so a CI gate on that number would be flaky by construction -- and a flaky gate gets
muted, which is worse than having no gate at all.

What is machine-independent is the DECLARATION: whether a record asked for anything to be checked.
So the gate counts declarations instead. Measured 2026-11-12, 595 of 605 predicates (98.3%)
declare no expectation, which is why 98.3% of the corpus could only ever be contradicted by an
exit code and never by an output.

Two properties make that substitution legitimate rather than convenient, and both are pinned here
because both are easy to lose silently:

  1. the floor must count EXACTLY the corpus the executed audit runs -- a gate over a different
     set of records could stay green while the thing it protects got worse;
  2. the floor must execute nothing and write nothing -- the moment it runs a command it inherits
     every machine dependence the design was chosen to avoid.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.tools import auditability_report_v1 as A   # noqa: E402

COMMITTED_FLOOR = (pathlib.Path(__file__).resolve().parents[2] / "canonical" / "verification"
                   / "AUDITABILITY_DECLARATION_FLOOR_20261112_V1.json")


def py(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def record(verification: dict) -> dict:
    return {"status": "VERIFIED_BOUND_CAPABILITY", "adapter_module": "a",
            "verification": verification}


def tree_with(root: pathlib.Path, *verifications: dict) -> pathlib.Path:
    (root / "canonical").mkdir(parents=True, exist_ok=True)
    for index, verification in enumerate(verifications):
        (root / "canonical" / f"record_{index}.json").write_text(
            json.dumps(record(verification)), encoding="utf-8")
    return root


def write_baseline(path: pathlib.Path, declaring_none: int) -> pathlib.Path:
    path.write_text(json.dumps({"schema": "AUDITABILITY_DECLARATION_FLOOR_V1",
                                "declaring_none": declaring_none}), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# property 1: the floor counts exactly what the audit runs
# ---------------------------------------------------------------------------
def test_the_floor_counts_exactly_what_the_executed_audit_runs(tmp_path):
    """THE pin. If these two ever disagree, the gate is measuring a different corpus than the
    instrument and is decoration: it can stay green while the audit gets worse."""
    tree_with(tmp_path,
              {"argv": py("pass")},
              {"argv": py("print('promised')"), "expect_stdout_contains": "promised"},
              {"argv": py("raise SystemExit(3)")})

    floor = A.declaration_floor(tmp_path)
    executed = A.audit(tmp_path, run=True)

    assert floor["predicates_declared"] == executed["predicates_run"] == 3
    assert floor["declaring_an_expectation"] == executed["predicates_declaring_an_expectation"] == 1
    assert floor["declaring_none"] == executed["pass_started"] + sum(
        1 for item in executed["predicate_results"]
        if item["verdict"] != "PASS" and not item.get("expectations"))


def test_a_predicate_nested_in_a_list_is_counted_once_by_both(tmp_path):
    """One check per RECORD, not per dict -- descending into a record's own `verification`
    block would count the same evidence twice and report more than exists."""
    (tmp_path / "canonical").mkdir(parents=True)
    (tmp_path / "canonical" / "nested.json").write_text(json.dumps(
        {"items": [record({"argv": py("pass")}), record({"argv": py("pass")})]}), encoding="utf-8")

    floor = A.declaration_floor(tmp_path)
    executed = A.audit(tmp_path, run=True)
    assert floor["predicates_declared"] == executed["predicates_run"] == 2


def test_the_binary_identity_corpus_is_included_in_the_floor(tmp_path):
    """The corpus lives in a different shape (`arg`, not `argv`) and is easy to drop when the
    walk is refactored, which would quietly shrink the denominator and flatter the fraction."""
    corpus_dir = tmp_path / "canonical" / "tools" / "predicates"
    corpus_dir.mkdir(parents=True)
    (corpus_dir / "binary_identity_predicates_20261112_v1.json").write_text(json.dumps({
        "predicates": [{"name": "one", "arg": py("pass")},
                       {"name": "two", "arg": py("print('x')"),
                        "expect_stdout_contains": "x"}]}), encoding="utf-8")

    floor = A.declaration_floor(tmp_path)
    assert floor["predicates_declared"] == 2
    assert floor["declaring_an_expectation"] == 1
    assert floor["declaring_none"] == 1


# ---------------------------------------------------------------------------
# property 2: the floor executes nothing and writes nothing
# ---------------------------------------------------------------------------
def test_the_floor_executes_no_declared_command(tmp_path):
    """The whole reason the gate counts declarations instead of running them. A floor that
    executes inherits every machine dependence the design was chosen to avoid."""
    marker = tmp_path / "PROOF_IT_RAN"
    tree_with(tmp_path, {"argv": py(f"open({str(marker)!r}, 'w').write('ran')")})

    floor = A.declaration_floor(tmp_path)

    assert floor["predicates_declared"] == 1
    assert not marker.exists(), "the floor ran a declared command"


def test_the_floor_writes_nothing_into_the_tree_it_measures(tmp_path):
    """`--audit` leaves 4 tracked files modified and 3 new ones behind on this tree. The gate
    may not: a gate that dirties the working tree cannot be trusted to leave the verdict it
    read intact."""
    tree_with(tmp_path, {"argv": py("pass")})
    before = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}

    A.declaration_floor(tmp_path)

    assert {p.relative_to(tmp_path) for p in tmp_path.rglob("*")} == before


# ---------------------------------------------------------------------------
# the ratchet: down is the point, up is a regression
# ---------------------------------------------------------------------------
def test_a_fully_checked_tree_reports_no_floor_at_all(tmp_path):
    tree_with(tmp_path, {"argv": py("print('a')"), "expect_stdout_contains": "a"},
              {"argv": py("raise SystemExit(3)"), "expect_exit": 3})
    floor = A.declaration_floor(tmp_path)
    assert floor["declaring_none"] == 0
    assert floor["declaring_an_expectation"] == 2
    assert floor["fraction_checked"] == 1.0


def test_the_gate_holds_when_the_number_equals_the_floor(tmp_path):
    """The only green state: floor == measurement. Ceiling == baseline == actual."""
    tree_with(tmp_path, {"argv": py("pass")}, {"argv": py("pass")})
    baseline = write_baseline(tmp_path / "floor.json", 2)
    gate = A.floor_gate(A.declaration_floor(tmp_path), str(baseline))
    assert gate["verdict"] == "HELD"
    assert gate["reason"] == "declaring_none 2 == floor 2"
    assert A.main(["--root", str(tmp_path), "--floor", "--baseline", str(baseline)]) == 0


def test_an_improvement_that_is_not_locked_in_is_a_failure(tmp_path):
    """Ratchet direction, and the hole in the obvious design. A floor that merely allows the
    number to fall banks the gain as spendable headroom: improve 595 -> 400 without lowering
    the floor and 195 unchecked declarations can come back later, every step green. That is a
    documented failure, not a hypothetical -- AutoBot-AI #14498 (2026-08-17) lost 344 lines
    exactly this way and fixed it by re-baselining on every shrink, so ceiling == baseline ==
    actual, always. Falling must therefore be red until it is written down."""
    tree_with(tmp_path, {"argv": py("pass")})
    baseline = write_baseline(tmp_path / "floor.json", 5)
    gate = A.floor_gate(A.declaration_floor(tmp_path), str(baseline))
    assert gate["verdict"] == "IMPROVED_NOT_LOCKED_IN"
    assert "--write-baseline" in gate["reason"], "the failure must carry the one command that fixes it"
    assert A.main(["--root", str(tmp_path), "--floor", "--baseline", str(baseline)]) == 1


def test_a_gain_cannot_be_spent_back(tmp_path):
    """The whole point of locking in, end to end: improve, lock, then try to spend the gain
    back one declaration at a time. Every step must be red from the first one."""
    tree_with(tmp_path, {"argv": py("pass")}, {"argv": py("pass")}, {"argv": py("pass")})
    baseline = tmp_path / "floor.json"
    write_baseline(baseline, 5)
    assert A.floor_gate(A.declaration_floor(tmp_path), str(baseline))["verdict"] \
        == "IMPROVED_NOT_LOCKED_IN"

    A.write_baseline(baseline, tmp_path)
    assert A.floor_gate(A.declaration_floor(tmp_path), str(baseline))["verdict"] == "HELD"
    assert json.loads(baseline.read_text())["declaring_none"] == 3

    # spend one back
    (tmp_path / "canonical" / "record_3.json").write_text(
        json.dumps(record({"argv": py("pass")})), encoding="utf-8")
    gate = A.floor_gate(A.declaration_floor(tmp_path), str(baseline))
    assert gate["verdict"] == "REGRESSED", "a locked-in gain was spendable"
    assert gate["declaring_none"] == 4 and gate["baseline"] == 3


def test_write_baseline_records_the_measured_number_not_a_typed_one(tmp_path):
    """A floor retyped by hand is a floor nobody measured. The builder reads the tree."""
    tree_with(tmp_path, {"argv": py("pass")},
              {"argv": py("print('x')"), "expect_stdout_contains": "x"})
    baseline = tmp_path / "floor.json"
    doc = A.write_baseline(baseline, tmp_path)
    on_disk = json.loads(baseline.read_text(encoding="utf-8"))

    assert on_disk["declaring_none"] == 1 == doc["declaring_none"]
    assert on_disk["floor"]["predicates_declared"] == 2
    assert on_disk["floor"]["declaring_an_expectation"] == 1
    assert on_disk["declaring_none"] == on_disk["floor"]["declaring_none"]
    assert on_disk["authority"].startswith("NONE")
    assert on_disk["measured_at_git_head"]


def test_rewriting_a_floor_preserves_the_reasoning_a_human_wrote(tmp_path):
    """Two-sided on the builder: it must update the numbers and must NOT delete the
    justification, or every re-baseline silently erases why the floor exists."""
    tree_with(tmp_path, {"argv": py("pass")})
    baseline = tmp_path / "floor.json"
    baseline.write_text(json.dumps({
        "declaring_none": 99,
        "what_this_gates": "hand-written reasoning that must survive",
        "reading": ["a hand-written observation"],
    }), encoding="utf-8")

    doc = A.write_baseline(baseline, tmp_path)

    assert doc["declaring_none"] == 1
    assert doc["what_this_gates"] == "hand-written reasoning that must survive"
    assert doc["reading"] == ["a hand-written observation"]




def test_the_gate_goes_red_when_one_more_declaration_asks_for_nothing(tmp_path):
    """THE ratchet. One new receipt that declares a command and asserts nothing about its
    output must be a red build, because that is exactly how 595 accumulated."""
    tree_with(tmp_path, {"argv": py("pass")}, {"argv": py("pass")}, {"argv": py("pass")})
    baseline = write_baseline(tmp_path / "floor.json", 2)
    gate = A.floor_gate(A.declaration_floor(tmp_path), str(baseline))
    assert gate["verdict"] == "REGRESSED"
    assert gate["declaring_none"] == 3 and gate["baseline"] == 2
    assert A.main(["--root", str(tmp_path), "--floor", "--baseline", str(baseline)]) == 1


def test_a_checked_declaration_does_not_trip_the_ratchet(tmp_path):
    """Two-sided: adding evidence must stay free. If a new record that DOES declare an
    expectation reddened the build, the gate would be teaching people to stop adding records."""
    tree_with(tmp_path, {"argv": py("pass")},
              {"argv": py("print('x')"), "expect_stdout_contains": "x"})
    baseline = write_baseline(tmp_path / "floor.json", 1)
    gate = A.floor_gate(A.declaration_floor(tmp_path), str(baseline))
    assert gate["verdict"] == "HELD"
    assert gate["declaring_none"] == 1


# ---------------------------------------------------------------------------
# fails closed, because a gate that passes without its reference is the original defect
# ---------------------------------------------------------------------------
def test_a_missing_baseline_fails_closed(tmp_path):
    tree_with(tmp_path, {"argv": py("pass")})
    gate = A.floor_gate(A.declaration_floor(tmp_path), str(tmp_path / "absent.json"))
    assert gate["verdict"] == "BASELINE_UNUSABLE"
    assert A.main(["--root", str(tmp_path), "--floor",
                   "--baseline", str(tmp_path / "absent.json")]) == 1


def test_a_malformed_baseline_fails_closed(tmp_path):
    tree_with(tmp_path, {"argv": py("pass")})
    broken = tmp_path / "broken.json"
    broken.write_text("{ this is not json", encoding="utf-8")
    assert A.floor_gate(A.declaration_floor(tmp_path), str(broken))["verdict"] == "BASELINE_UNUSABLE"


def test_a_baseline_without_the_floor_field_fails_closed(tmp_path):
    """A baseline that cannot be compared must not be read as a baseline of zero."""
    tree_with(tmp_path, {"argv": py("pass")})
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"schema": "AUDITABILITY_DECLARATION_FLOOR_V1"}), encoding="utf-8")
    gate = A.floor_gate(A.declaration_floor(tmp_path), str(empty))
    assert gate["verdict"] == "BASELINE_UNUSABLE"
    assert gate["reason"] == "BASELINE_HAS_NO_declaring_none"


def test_a_baseline_that_is_not_an_object_fails_closed(tmp_path):
    tree_with(tmp_path, {"argv": py("pass")})
    scalar = tmp_path / "scalar.json"
    scalar.write_text("595", encoding="utf-8")
    assert A.floor_gate(A.declaration_floor(tmp_path),
                        str(scalar))["verdict"] == "BASELINE_UNUSABLE"


def test_measuring_without_a_baseline_is_not_a_gate(tmp_path):
    """`--floor` alone is a measurement and must never redden a build; only `--baseline` makes
    it a claim about a trend."""
    tree_with(tmp_path, {"argv": py("pass")})
    gate = A.floor_gate(A.declaration_floor(tmp_path), None)
    assert gate["verdict"] == "MEASURED"
    assert A.main(["--root", str(tmp_path), "--floor"]) == 0


def test_an_empty_tree_reports_none_not_a_confident_zero(tmp_path):
    """Learned from this repo's own history: 0/0 reads as 'nothing to see' when the truth is
    'could not measure'."""
    (tmp_path / "canonical").mkdir()
    floor = A.declaration_floor(tmp_path)
    assert floor["predicates_declared"] == 0
    assert floor["fraction_checked"] is None


# ---------------------------------------------------------------------------
# the real tree, and the committed floor
# ---------------------------------------------------------------------------
def test_the_committed_floor_of_the_real_tree_holds():
    """No exact number is asserted -- the floor is allowed to improve. What is asserted is that
    the committed baseline and the live tree still agree, which is the gate CI runs."""
    assert COMMITTED_FLOOR.exists(), "the committed floor document is missing"
    gate = A.floor_gate(A.declaration_floor(A.REPO_ROOT), str(COMMITTED_FLOOR))
    assert gate["verdict"] == "HELD", gate["reason"]


def test_the_committed_floor_document_states_its_own_authority():
    """A measurement that does not name its authority gets cited as a verification."""
    doc = json.loads(COMMITTED_FLOOR.read_text(encoding="utf-8"))
    assert doc["authority"].startswith("NONE")
    assert doc["carrier"] == "SANDBOX"
    assert doc["producer"].endswith("--floor")
    assert doc["declaring_none"] == doc["floor"]["declaring_none"]


def test_the_real_gap_is_named_by_source_so_it_is_actionable():
    """A total is a complaint; a ranked source list is a task. One file held 184 of the 595 at
    measurement, which is why the floor is cheap to move rather than hopeless."""
    floor = A.declaration_floor(A.REPO_ROOT)
    assert floor["worst_sources"], "no sources named"
    named = sum(n for _source, n in floor["worst_sources"])
    assert named <= floor["declaring_none"]
    assert floor["predicates_declared"] > 0
    assert 0.0 <= floor["fraction_checked"] <= 1.0


# ---------------------------------------------------------------------------
# the double count, found by this file and corrected
# ---------------------------------------------------------------------------
def test_the_corpus_is_counted_once_not_once_per_code_path():
    """The corpus is read by TWO paths: an explicit branch (the only place an entry's `name`
    survives) and the generic JSON walk, because `predicate_of` also accepts `arg`. Before the
    walk skipped it, the file declared 5 predicates and the iteration yielded 10 -- so the
    published claim that "10 predicates declare an expectation, 1.7% of the corpus" was 5
    predicates counted twice. The most flattering number in the report was the wrong one."""
    corpus = A.REPO_ROOT / A.BINARY_PREDICATE_CORPUS
    assert corpus.exists(), "corpus moved; this test must move with it"
    declared = len(json.loads(corpus.read_text(encoding="utf-8")).get("predicates") or [])

    yielded = [row for row in A._iter_predicate_specs(A.REPO_ROOT)
               if row[0] == A.BINARY_PREDICATE_CORPUS]

    assert len(yielded) == declared
    assert declared == 5, "if the corpus grew, this pin must be updated deliberately"


def test_removing_the_double_count_did_not_drop_the_corpus():
    """Two-sided: the fix must not become a deletion. The corpus is the one fully checkable
    layer in the tree, so losing it would flatter nothing and hide the only working examples."""
    yielded = [row for row in A._iter_predicate_specs(A.REPO_ROOT)
               if row[0] == A.BINARY_PREDICATE_CORPUS]
    assert yielded, "the corpus is no longer counted at all"
    assert [row[1].get("name") for row in yielded] == [
        "gnu_tar_identity", "gnu_git_identity", "python3_identity", "node_identity",
        "jq_identity"]
    floor = A.declaration_floor(A.REPO_ROOT)
    assert floor["declaring_an_expectation"] == 5
    assert floor["predicates_declared"] == 600


def test_two_records_declaring_the_same_command_are_still_counted_twice(tmp_path):
    """A deliberate non-fix, pinned so nobody 'cleans it up' later. 18 (source, argv) pairs
    repeat in this tree. Deduplicating them would shrink the denominator by a guess about what
    a repeated declaration means, and a smaller denominator flatters the fraction. Two records
    are two declarations until someone shows they are one claim."""
    (tmp_path / "canonical").mkdir(parents=True)
    for name in ("one.json", "two.json"):
        (tmp_path / "canonical" / name).write_text(
            json.dumps(record({"argv": py("pass")})), encoding="utf-8")

    floor = A.declaration_floor(tmp_path)
    assert floor["predicates_declared"] == 2
    assert floor["declaring_none"] == 2


def test_the_floor_and_the_audit_agree_after_the_deduplication_fix(tmp_path):
    """Re-pinned on a tree that CONTAINS the corpus shape, because that is the case where the
    two paths used to disagree."""
    corpus_dir = tmp_path / "canonical" / "tools" / "predicates"
    corpus_dir.mkdir(parents=True)
    (corpus_dir / "binary_identity_predicates_20261112_v1.json").write_text(json.dumps({
        "predicates": [{"name": "one", "arg": py("pass"), "expect_exit": 0}]}), encoding="utf-8")
    (tmp_path / "canonical" / "plain.json").write_text(
        json.dumps(record({"argv": py("pass")})), encoding="utf-8")

    floor = A.declaration_floor(tmp_path)
    executed = A.audit(tmp_path, run=True)

    assert floor["predicates_declared"] == executed["predicates_run"] == 2
    assert floor["declaring_an_expectation"] == executed["predicates_declaring_an_expectation"] == 1
