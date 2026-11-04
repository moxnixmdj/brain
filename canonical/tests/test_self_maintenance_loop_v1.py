"""The self-maintenance loop's own honesty, pinned.

Each test here exists because the loop was already wrong in that exact way at least once, or
because a plausible version of it would be wrong and nobody would notice:

  * v1 reported 841 defects by scanning the intent archive. The drift guard only loads the
    intents in the change set, so those 841 were artefacts of a bad world model, not debts.
  * v1 wrote 2,436 lines into the real ignorance ledger during a `--apply`-less run.
  * v1's measurement class compared in-memory tuples against on-disk lists, so every run
    "found" a stale artifact and every repair rewrote the file. A fix that fires forever is
    churn wearing the costume of a fix.

The last one is the reason this file spends most of its effort on the verifier rather than
the fixer: a fixer is allowed to be wrong as long as the verifier refuses its claim.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import self_maintenance_loop_v1 as loop  # noqa: E402


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- the verifier
def test_a_fixer_that_lies_is_not_counted_as_closed():
    """The whole point. A fixer that returns success without changing the tree must fail.

    If this test ever passes with `closed == 1`, the loop has become a machine for
    confirming its own opinions and every number it reports is worthless.
    """
    defects = [{"defect_id": "SYNTHETIC:1", "path": "nowhere.json", "defect_class": "FAKE"}]

    class Liar:
        class_id = "FAKE"
        describes = "claims a repair it never made"

        def find(self):
            return defects

        def fix(self, defect):
            return {"applied": True, "before": "broken", "after": "fixed"}

        def verify(self, defect):
            return False          # the independent recomputation disagrees

        def as_dict(self):
            return {"class_id": self.class_id, "describes": self.describes}

    result = loop.run(rounds=1, apply=True, classes=[Liar()],
                      ledger_path=str(Path(_tmpdir()) / "ledger.json"))
    assert result["defects_found"] == 1
    assert result["defects_closed"] == 0, "a lying fixer was credited with a closure"
    assert result["unaided_closure_rate"] == 0.0
    assert result["history"][0]["rows"][0]["verified"] is False


def _tmpdir() -> Path:
    import tempfile
    return Path(tempfile.mkdtemp(prefix="sml-test-"))


def test_verification_reads_the_tree_and_not_the_fixers_return_value():
    """Corrupt the artifact after the fix; the verifier must now refuse to confirm."""
    work = _tmpdir()
    artifact = work / "ARTIFACT.json"
    artifact.write_text(json.dumps({"capabilities_reached": 3, "rows": []}), encoding="utf-8")

    def recompute():
        return {"capabilities_reached": 7, "rows": []}

    klass = loop.make_stale_measurement_class(artifact=str(artifact), recompute=recompute)
    found = klass.find()
    assert len(found) == 1, "a recorded measurement that no longer reproduces was not found"

    klass.fix(found[0])
    assert klass.verify(found[0]) is True, "a genuine repair was not confirmed"

    # The fixer's return value said "applied"; the tree now says otherwise.
    artifact.write_text(json.dumps({"capabilities_reached": 99, "rows": []}), encoding="utf-8")
    assert klass.verify(found[0]) is False, "verification trusted a stale claim"


# --------------------------------------------------------------------------- the churn bug
def test_a_reproducing_measurement_is_not_a_defect():
    """Tuples in memory, lists on disk: same document. Otherwise repair never terminates."""
    work = _tmpdir()
    artifact = work / "ARTIFACT.json"
    artifact.write_text(json.dumps({"reach_magnets": [["cap.a", 2], ["cap.b", 1]],
                                    "rows": []}), encoding="utf-8")

    def recompute():
        return {"reach_magnets": [("cap.a", 2), ("cap.b", 1)], "rows": []}

    klass = loop.make_stale_measurement_class(artifact=str(artifact), recompute=recompute)
    assert klass.find() == [], "a measurement that reproduces was reported as stale"


def test_repair_terminates_because_the_second_pass_finds_nothing():
    work = _tmpdir()
    artifact = work / "ARTIFACT.json"
    artifact.write_text(json.dumps({"capabilities_reached": 1, "rows": []}), encoding="utf-8")
    klass = loop.make_stale_measurement_class(
        artifact=str(artifact), recompute=lambda: {"capabilities_reached": 5, "rows": []})
    first = loop.run(rounds=3, apply=True, classes=[klass],
                     ledger_path=str(work / "ledger.json"))
    assert first["defects_closed"] == 1
    assert first["defects_remaining_after"] == 0, "the loop kept finding its own repair"
    assert first["rounds_run"] == 1, "it looped after having nothing left to close"


# --------------------------------------------------------------------------- the scope bug
def test_the_archive_is_not_perceived(monkeypatch):
    """841 was measured on the archive. The guard never looks there, so neither may we.

    The finder is forced to see an empty change set while the archive on disk still contains
    receipts whose recorded shas no longer match. If the count moves, the finder has gone
    back to scanning history and every number it produces is fiction.
    """
    monkeypatch.setattr(loop, "intents_in_change_set", lambda base=None: [])
    klass = loop.make_stale_receipt_class()
    assert klass.find() == [], "the finder perceived defects outside the change set"


def test_the_archive_really_does_contain_stale_receipts():
    """Bound the test above: prove the empty result is scope, not an empty repository.

    Without this, `test_the_archive_is_not_perceived` would also pass on a repository with
    no intents at all, and would be measuring nothing.
    """
    intents = sorted((ROOT / loop.INTENT_DIR).glob("*.json"))
    assert len(intents) > 100, "the intent archive is gone; the scope test proves nothing"
    stale = 0
    for path in intents:
        doc = loop._load(path)
        if not isinstance(doc, dict):
            continue
        for row in loop._receipts(doc):
            if not isinstance(row, dict):
                continue
            recorded = str(row.get("git_blob_sha") or "")
            actual = loop.blob_sha(str(row.get("path") or ""))
            if actual and recorded and actual != recorded:
                stale += 1
    assert stale > 0, ("no archived receipt is stale, so the change-set scope buys nothing "
                       "and the 841 measurement is unexplained")


# --------------------------------------------------------------------------- measure is not act
class _FindsOne:
    """A class that always reports one defect, so PERCEIVE→MODEL actually runs.

    The first version of the ledger test used `classes=[]`, which found nothing, recorded
    nothing, and therefore passed even against a build that wrote every note straight into
    the real ledger. A test that cannot fail is not a test; this fixture is what makes the
    assertion below non-vacuous.
    """

    class_id = "SYNTHETIC_ONE"
    describes = "always finds exactly one defect"

    def find(self):
        return [{"defect_id": "SYNTHETIC_ONE:0", "path": "nowhere.json", "detail": "d"}]

    def fix(self, defect):
        return {"applied": True}

    def verify(self, defect):
        return True

    def as_dict(self):
        return {"class_id": self.class_id, "describes": self.describes}


def test_measuring_does_not_touch_the_real_ledger():
    """A dry run wrote 2,436 lines into the ledger once. Measurement is not an action."""
    before = _digest(loop.LEDGER) if loop.LEDGER.is_file() else None
    result = loop.run(rounds=1, apply=False, classes=[_FindsOne()])
    after = _digest(loop.LEDGER) if loop.LEDGER.is_file() else None
    assert result["learning_cost"]["search_invocations"] == 1, "the fixture found nothing, so this test proves nothing"
    assert before == after, "a measure-only run mutated the ignorance ledger"


def test_apply_does_not_touch_the_real_ledger_either_when_given_its_own():
    work = _tmpdir()
    before = _digest(loop.LEDGER) if loop.LEDGER.is_file() else None
    loop.run(rounds=1, apply=True, classes=[],
             ledger_path=str(work / "elsewhere.json"))
    after = _digest(loop.LEDGER) if loop.LEDGER.is_file() else None
    assert before == after


# --------------------------------------------------------------------------- the reported number
def test_an_empty_round_reports_no_rate_rather_than_a_perfect_one():
    """0/0 is not 100%. A loop with nothing to close must not look like a success."""
    result = loop.run(rounds=1, apply=True, classes=[], ledger_path=str(_tmpdir() / "l.json"))
    assert result["defects_found"] == 0
    assert result["unaided_closure_rate"] is None


def test_cost_is_reported_as_search_invocations_never_as_a_solve_rate():
    result = loop.run(rounds=1, apply=False, classes=[], ledger_path=str(_tmpdir() / "l.json"))
    assert set(result["learning_cost"]) == {"search_invocations"}
    assert "solve_rate" not in json.dumps(result["learning_cost"])


def test_the_result_carries_its_non_claims():
    result = loop.run(rounds=1, apply=False, classes=[], ledger_path=str(_tmpdir() / "l.json"))
    assert "NO_CAPABILITY_CREDIT_A_TIDY_TREE_IS_NOT_A_MORE_CAPABLE_ONE" in result["non_claims"]
    assert result["authority"] == "NO_CAPABILITY_CREDIT_SELF_MAINTENANCE_ONLY"
    assert "SCOPE_IS_THE_CHANGE_SET_NOT_THE_INTENT_ARCHIVE" in result["non_claims"]


# --------------------------------------------------------------------------- certification
def test_a_repair_before_the_commit_is_not_credited_as_a_closure(monkeypatch):
    """Measured 2026-11-04: the loop said 2/2 closed (100%) while the drift guard still
    reported the same two receipts as stale. The guard resolves at `ref:path`; the repair
    only becomes true when a commit exists to resolve it against. So a repair the enforcer
    would still reject must not enter the rate.
    """
    monkeypatch.setattr(loop, "certify", lambda *a, **k: False)
    result = loop.run(rounds=1, apply=True, classes=[_FindsOne()],
                      ledger_path=str(_tmpdir() / "l.json"))
    assert result["defects_closed"] == 1, "the fixture must produce a verified repair"
    assert result["defects_certified"] == 0
    assert result["unaided_closure_rate"] == 0.0, (
        "the rate was credited on the fixer's own verification rather than the enforcer's")


def test_certification_has_no_ref_form_for_a_working_tree_measurement():
    """A stale measurement is about bytes, not about a ref, and must not pretend otherwise."""
    defect = {"defect_id": "STALE_VERIFICATION_ARTIFACT:ARTIFACT.json"}
    assert loop.certify(defect, ref="HEAD", base=loop.resolve_base(None)) is None


def test_an_intent_outside_the_refs_change_set_cannot_contradict_a_repair():
    defect = {"defect_id": "STALE_ACTION_INTENT_RECEIPT:NOT_AN_INTENT_IN_THIS_CHANGE.json:0"}
    assert loop.certify(defect, ref="HEAD", base=loop.resolve_base(None)) is True


def test_the_certify_report_recomputes_rather_than_trusting_the_written_result(monkeypatch):
    """The written result says what the run believed; the report asks the ref instead."""
    work = _tmpdir()
    doc = {"base": loop.resolve_base(None), "history": [{"rows": [
        {"defect_id": "STALE_ACTION_INTENT_RECEIPT:a.json:0", "verified": True},
        {"defect_id": "STALE_ACTION_INTENT_RECEIPT:b.json:0", "verified": True},
        {"defect_id": "STALE_ACTION_INTENT_RECEIPT:c.json:0", "verified": False},
    ]}]}
    path = work / "run.json"
    path.write_text(json.dumps(doc), encoding="utf-8")

    seen = []

    def fake_certify(defect, *, ref="HEAD", base=None):
        seen.append(defect["defect_id"])
        return defect["defect_id"].endswith("a.json:0")

    monkeypatch.setattr(loop, "certify", fake_certify)
    report = loop.certify_report(str(path))
    assert report["prepared"] == 2, "unverified rows must not be counted as prepared repairs"
    assert report["certified"] == 1
    assert report["uncertified"] == ["STALE_ACTION_INTENT_RECEIPT:b.json:0"]
    assert report["unaided_closure_rate"] == 0.5
    assert seen, "the report reused the recorded verdict instead of recomputing"
