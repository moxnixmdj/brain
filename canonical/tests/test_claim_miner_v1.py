"""Curiosity is cheap to fake. These tests make it expensive.

A miner that reports everything as a defect generates a thousand findings and zero facts, and it
is indistinguishable from a working one until somebody checks. Measured 2026-11-04: the first
version produced 962 contradictions of which almost none were real -- prose matched as paths, a
fraction matched as a path, a hash paired against an unrelated file, a recorded count compared to
the present. Every rule below exists because one of those happened, and each test fails in the
world where its rule is removed.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import claim_miner_v1 as miner  # noqa: E402


def _claim(**kwargs) -> dict:
    base = {"kind": "FILE_HASH", "source": "canonical/verification/X.json",
            "where": "/x", "asserts": "x", "subject": None, "held": "0" * 64}
    base.update(kwargs)
    return base


# --------------------------------------------------------------------------- what must NOT be called a defect
def test_a_claim_that_names_nothing_testable_is_unpaired_not_false():
    """A hash with no path beside it cannot be tested. Calling it false manufactures a finding
    out of an absence, which is the failure mode that makes a miner worthless."""
    result = miner.test_claim(_claim(subject=None, held="a" * 64))
    assert result["verdict"] == miner.UNPAIRED, result


def test_prose_is_not_a_path():
    """`{'source': 'The writing must reflect a thorough understanding ...'}` is a sentence. The
    first version resolved it to a path, failed to find it, and called the artifact a liar."""
    prose = "The writing must reflect a thorough understanding of the literature"
    assert not miner._looks_like_path(prose)
    assert miner._looks_like_path("canonical/runtime/thing.py")
    assert not miner._looks_like_path("9/10"), "a fraction is not a path"
    assert not miner._looks_like_path("chart.raster.curve_x_at_y_query.v1"), (
        "a capability id is not a file")


def test_a_recorded_count_is_history_not_a_defect():
    """An artifact that says '4000 files' was right when it was written. Comparing it to now
    reports every subsequent edit as a fault."""
    result = miner.test_claim(_claim(kind="COUNT", subject="canonical/a.py", held=4000))
    assert result["verdict"] == miner.HISTORICAL, result


def test_a_missing_field_on_a_degraded_path_is_not_a_false_claim():
    """Measured 2026-11-04: ten of eleven behavioural contradictions were a capability honestly
    reporting an early exit and therefore not producing its full output. Only a run that reports
    success can contradict a claim about what success looks like."""
    miner._RUNS["fake.cap"] = {"reached": True, "verdict": "CLAIM_FALSE",
                               "returned_keys": ["a", "b"]}
    try:
        result = miner.test_claim(_claim(kind="RESULT_FIELD", capability="fake.cap",
                                          subject="c", held="fake.cap"))
        assert result["verdict"] == miner.UNTESTABLE, result
    finally:
        miner._RUNS.pop("fake.cap", None)


def test_a_missing_field_on_a_success_path_is_a_contradiction():
    """The one finding that survived every precision rule. A capability that reports
    output_verified=True and does not return a field it declares is a contract nobody can rely
    on, and that is worth reporting."""
    miner._RUNS["fake.cap"] = {"reached": True, "verdict": "CLAIM_CHECKED",
                               "returned_keys": ["a", "b"]}
    try:
        result = miner.test_claim(_claim(kind="RESULT_FIELD", capability="fake.cap",
                                          subject="c", held="fake.cap"))
        assert result["verdict"] == miner.CONTRADICTED, result
        assert "REPORTED SUCCESS" in result["detail"]
    finally:
        miner._RUNS.pop("fake.cap", None)


def test_two_quantities_with_one_stem_are_unpaired():
    """`source_contract_sha256` and `source_model_projection_sha256` both paired to `source_path`
    and both 'failed' against one file. One file, two subjects: the pairing is a guess."""
    row = {"source_path": "canonical/runtime/bound_capabilities/archive_tarfile.py",
           "source_contract_sha256": "a" * 64,
           "source_model_projection_sha256": "b" * 64}
    assert miner._paired_path(row, "source_contract_sha256") is None
    assert miner._paired_path(row, "source_model_projection_sha256") is None


def test_a_claim_about_a_file_that_changed_afterwards_is_history():
    """A recorded hash of a file that has legitimately changed since is a true statement about a
    past moment. All five file findings that survived the first four rules were this."""
    target = "canonical/runtime/organism_v1.py"
    if not (ROOT / target).exists():
        return
    claim = _claim(subject=target, held="0" * 64,
                   source="canonical/verification/AN_OLD_ARTIFACT.json")
    assert miner._last_commit(target) > 0
    result = miner.test_claim(claim)
    assert result["verdict"] in (miner.HISTORICAL, miner.UNPAIRED), result


# --------------------------------------------------------------------------- the real thing
def test_a_genuine_stale_claim_is_still_found(monkeypatch):
    """The rules above must not be so cautious that nothing is ever reported. A claim whose
    subject has NOT changed since the document describing it is a claim about right now, and if
    it does not match, that is a contradiction. Timing is injected so the test states the world
    it needs instead of depending on this repository's history."""
    target = "canonical/runtime/belief_v1.py"
    if not (ROOT / target).exists():
        return
    # subject older than the document: the claim is about the present, so it is testable
    monkeypatch.setattr(miner, "_last_commit", lambda relative: 100 if "belief_v1" in relative else 200)
    wrong = hashlib.sha256(b"a different world entirely").hexdigest()
    result = miner.test_claim(_claim(kind="FILE_HASH", subject=target, held=wrong))
    assert result["verdict"] == miner.CONTRADICTED, result



def test_the_miner_names_no_capability():
    """Same law as the forge: a hypothesis generator that recognises a capability is a lookup
    table, and it will not transfer to the next thousand claims."""
    import inspect
    source = inspect.getsource(miner)
    import json
    registry = json.loads((ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json")
                          .read_text(encoding="utf-8"))["capabilities"]
    offenders = [cid for cid in registry if cid in source]
    assert not offenders, f"the miner names capabilities: {offenders[:3]}"


def test_zero_claims_were_enumerated_by_a_person():
    """The whole point. If this number is ever above zero, the hypothesis space is mine again."""
    doc = miner.measure()
    assert doc["claims_enumerated_by_a_person"] == 0
    assert doc["claims_mined"] > 1000, doc["claims_mined"]
