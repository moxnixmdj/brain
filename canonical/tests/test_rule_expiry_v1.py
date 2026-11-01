"""A learned rule must stop being offered when the world underneath it moved.

`VerifiedSkillStore.invalidate()` already works and is tested, but it has to be *called*.
Measured 2026-11-01: nothing aged a rule out when the interpreter, platform or tool inventory
changed, so "permanently learned" also meant "permanently offered, even when stale".

Three states and one permission: only FRESH may be offered. UNKNOWN fails closed for the same
reason unknown provenance fails closed everywhere else in this repo.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import rule_expiry_v1 as expiry  # noqa: E402
from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry  # noqa: E402

BEFORE = "def within(x, hi):\n    return x <= hi\n"
AFTER = "def within(x, hi):\n    return x < hi\n"


def _twin_oracle(source: str) -> bool:
    ns: dict = {}
    try:
        exec(compile(source, "<twin>", "exec"), ns)
    except Exception:
        return False
    fn = next((v for v in ns.values() if callable(v) and not isinstance(v, type)), None)
    return bool(fn) and fn(10, 10) is False and fn(9, 10) is True


@pytest.fixture()
def taught(tmp_path):
    db = tmp_path / "skills.sqlite"
    store = cry.VerifiedSkillStore(db_path=db, seed=False)
    result = store.crystallize_code_fix(
        before_snippet=BEFORE, after_snippet=AFTER,
        language="python", error_class="BOUNDARY", twin_oracle=_twin_oracle,
    )
    assert result["crystallized"] is True
    return store, db, result["skill_id"]


def _moved(**changes):
    fp = expiry.world_fingerprint()
    fp.update(changes)
    return fp


# --------------------------------------------------------------------------- states
def test_an_unstamped_rule_is_unknown_and_not_usable(taught):
    store, db, sid = taught
    assert expiry.audit(db, skill_ids=[sid])["rules"][0]["state"] == expiry.UNKNOWN
    assert expiry.usable(db, sid) is False


def test_a_freshly_stamped_rule_is_fresh_and_usable(taught):
    _, db, sid = taught
    expiry.record_taught(db, sid)
    assert expiry.audit(db, skill_ids=[sid])["rules"][0]["state"] == expiry.FRESH
    assert expiry.usable(db, sid) is True


def test_a_changed_interpreter_makes_the_rule_stale(taught):
    _, db, sid = taught
    expiry.record_taught(db, sid)
    moved = _moved(python_major_minor="99.0")
    row = expiry.audit(db, skill_ids=[sid], now=moved)["rules"][0]
    assert row["state"] == expiry.STALE
    assert any("python_major_minor" in d for d in row["differences"])
    assert expiry.usable(db, sid, now=moved) is False


def test_a_changed_platform_makes_the_rule_stale(taught):
    _, db, sid = taught
    expiry.record_taught(db, sid)
    assert expiry.usable(db, sid, now=_moved(platform="SOMEWHERE_ELSE")) is False


def test_a_tool_disappearing_makes_the_rule_stale():
    taught_fp = {"python_major_minor": "3.11", "platform": "Linux", "machine": "x86_64",
                 "tools": {"tar": {"path": "/bin/tar", "size": 1, "mtime_ns": 1}}}
    now_fp = {"python_major_minor": "3.11", "platform": "Linux", "machine": "x86_64",
              "tools": {"tar": None}}
    diffs = expiry.material_differences(taught_fp, now_fp)
    assert "tool_disappeared:tar" in diffs


def test_a_new_tool_appearing_is_not_a_reason_to_distrust():
    """A machine that installed something new has not invalidated an old lesson."""
    taught_fp = {"python_major_minor": "3.11", "platform": "Linux", "machine": "x86_64",
                 "tools": {}}
    now_fp = {"python_major_minor": "3.11", "platform": "Linux", "machine": "x86_64",
              "tools": {"tar": {"path": "/bin/tar", "size": 1, "mtime_ns": 1}}}
    assert expiry.material_differences(taught_fp, now_fp) == []


def test_a_replaced_binary_makes_the_rule_stale():
    taught_fp = {"python_major_minor": "3.11", "platform": "Linux", "machine": "x86_64",
                 "tools": {"gzip": {"path": "/bin/gzip", "size": 1, "mtime_ns": 1}}}
    now_fp = {"python_major_minor": "3.11", "platform": "Linux", "machine": "x86_64",
              "tools": {"gzip": {"path": "/bin/gzip", "size": 2, "mtime_ns": 9}}}
    assert "tool_replaced:gzip" in expiry.material_differences(taught_fp, now_fp)


# --------------------------------------------------------------------------- re-verification
def test_reverify_refuses_a_rule_that_no_longer_reproduces_its_lesson(taught):
    _, db, sid = taught
    expiry.record_taught(db, sid)
    moved = _moved(python_major_minor="99.0")
    out = expiry.reverify(db, sid, lambda: False, now=moved)
    assert out["reverified"] is False
    assert out["reason"] == "RULE_NO_LONGER_REPRODUCES_ITS_LESSON"
    assert expiry.usable(db, sid, now=moved) is False


def test_reverify_refreshes_the_stamp_when_the_rule_still_holds(taught):
    _, db, sid = taught
    expiry.record_taught(db, sid)
    moved = _moved(python_major_minor="99.0")
    assert expiry.reverify(db, sid, lambda: True, now=moved)["reverified"] is True
    assert expiry.usable(db, sid, now=moved) is True


def test_a_verifier_that_raises_has_not_passed(taught):
    _, db, sid = taught

    def explode():
        raise RuntimeError("no interpreter")

    out = expiry.reverify(db, sid, explode)
    assert out["reverified"] is False
    assert "VERIFIER_RAISED" in out["reason"]


def test_reverify_without_a_verifier_is_refused(taught):
    _, db, sid = taught
    with pytest.raises(expiry.ExpiryError):
        expiry.reverify(db, sid, None)


# --------------------------------------------------------------------------- expiry
def test_expire_stale_invalidates_through_the_store(taught):
    store, db, sid = taught
    expiry.record_taught(db, sid)
    moved = _moved(platform="SOMEWHERE_ELSE")
    out = expiry.expire_stale(store, db, now=moved)
    assert out["expired"] == [sid]
    # the store's own recall now refuses it
    assert store.recall_and_apply_verified(
        source_text=BEFORE, language="python", verifier=_twin_oracle,
        error_class="BOUNDARY",
    ) is None


def test_expire_stale_does_not_destroy_an_unstamped_rule(taught):
    """A missing stamp is a gap in our bookkeeping, not evidence against the rule."""
    store, db, sid = taught
    out = expiry.expire_stale(store, db)
    assert out["expired"] == []
    assert sid in out["skipped"]


def test_expire_stale_leaves_a_fresh_rule_alone(taught):
    store, db, sid = taught
    expiry.record_taught(db, sid)
    out = expiry.expire_stale(store, db)
    assert out["expired"] == []
    assert out["counts"][expiry.FRESH] == 1


def test_audit_covers_every_rules_without_a_stamp(taught):
    _, db, _ = taught
    report = expiry.audit(db, skill_ids=[])
    assert report["counts"][expiry.UNKNOWN] == 0
    assert report["schema"] == expiry.SCHEMA


def test_the_fingerprint_is_not_a_proof():
    """Named honestly: a matching world means 'not known to be stale', not 'verified'."""
    doc = (expiry.__doc__ or "").lower()
    assert "hint" in doc and "not a proof" in doc
