"""A machine that has never learned anything must still start with what the repository knows.

The store being inside the repository is not the same as the lessons being *in* the repository.
The SQLite file is gitignored (it is generated state), and that had a consequence nobody had
measured: at the end of one session the store held six rules, and at the start of the next it held
zero. Same machine, same checkout, empty. Otherwise durable, but only within a sandbox's lifetime --
which is precisely the sense in which "learned permanently" was still false.

So the lessons ship as a bundle (small, text, content-addressed, reviewable) and the database stays
the fast local index. A first run seeds itself from the bundle.

Two things must stay true, and they pull against each other:

1. seeding must actually happen on a machine with no state;
2. a broken, edited or hostile bundle must never stop the machine from learning, and must never be
   able to smuggle a rule in under another rule's identity. So a bad seed is recorded and skipped,
   never raised, and every entry still goes through the content-address check.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry  # noqa: E402

SHIPPED = ROOT / "canonical" / "astra_runtime" / "skills" / "VERIFIED_SKILLS_BUNDLE_V1.json"


def test_the_repository_ships_a_real_bundle() -> None:
    """Not an empty placeholder: the lessons have to be in version control to travel."""
    assert SHIPPED.is_file(), f"the shipped bundle is missing: {SHIPPED}"
    bundle = json.loads(SHIPPED.read_text(encoding="utf-8"))
    assert bundle["schema"] == cry.BUNDLE_SCHEMA
    assert bundle["rule_count"] >= 1
    assert len(bundle["rules"]) == bundle["rule_count"]
    for entry in bundle["rules"]:
        assert entry["skill_id"] == cry.skill_identity(entry["rule"]), entry["skill_id"]
        assert entry["provenance"], "a shipped rule with no provenance cannot be audited"
        assert entry["language"]


def test_a_machine_with_no_state_starts_from_the_bundle(tmp_path: pathlib.Path,
                                                        monkeypatch: pytest.MonkeyPatch) -> None:
    """The claim under test: a new checkout, no history, and the lessons are already there."""
    db = tmp_path / "never_learned_anything.sqlite"
    monkeypatch.setenv("BRAIN_VERIFIED_SKILL_DB", str(db))
    assert not db.exists()

    store = cry.VerifiedSkillStore()
    assert store.seed_result is not None, "a fresh store did not even attempt to seed"
    assert store.seed_result["refused"] == 0
    assert store.count() == store.seed_result["accepted"] > 0
    assert db.exists()


def test_a_seeded_rule_is_usable_not_just_counted(tmp_path: pathlib.Path,
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    """Seeded rules must reach recall, and still have to pass the caller's verifier."""
    db = tmp_path / "fresh.sqlite"
    monkeypatch.setenv("BRAIN_VERIFIED_SKILL_DB", str(db))
    store = cry.VerifiedSkillStore()
    languages = {row["language"] for row in store.provenance()}
    assert languages, "seeding produced no queryable rules"

    for language in sorted(languages):
        rules = store.lookup_rules(language)
        assert rules, language
        for rule in rules:
            assert rule["pattern_tokens"] and rule["replacement_tokens"]
            assert cry.skill_identity(rule) == rule["skill_id"]

    # Every rule is a hypothesis: with a verifier that refuses everything, recall returns nothing.
    for language in sorted(languages):
        assert store.recall_and_apply_verified(
            source_text="def f():\n    return 1\n", language=language,
            verifier=lambda _s: False) is None


def test_a_corrupt_bundle_is_recorded_and_skipped_never_raised(tmp_path: pathlib.Path,
                                                               monkeypatch: pytest.MonkeyPatch) -> None:
    """A bad seed must not make learning impossible -- that would be a memory that bricks the tool."""
    bad = tmp_path / "bad_bundle.json"
    bad.write_text("{ this is not json", encoding="utf-8")
    monkeypatch.setenv("BRAIN_SKILL_SEED_BUNDLE", str(bad))
    monkeypatch.setenv("BRAIN_VERIFIED_SKILL_DB", str(tmp_path / "s.sqlite"))

    store = cry.VerifiedSkillStore()
    assert store.seed_result is not None
    assert store.seed_result["accepted"] == 0
    assert store.seed_result["refused"] == 1
    assert store.count() == 0
    # and it can still learn
    taught = store.crystallize_code_fix(
        before_snippet="def tally(xs):\n    t = 0\n    for i in range(len(xs) - 1):\n        t += xs[i]\n    return t\n",
        after_snippet="def tally(xs):\n    t = 0\n    for i in range(len(xs)):\n        t += xs[i]\n    return t\n",
        language="python", error_class="OFF_BY_ONE")
    assert taught["crystallized"] is True
    assert store.count() == 1


def test_a_tampered_seed_rule_is_refused(tmp_path: pathlib.Path,
                                         monkeypatch: pytest.MonkeyPatch) -> None:
    """The seed is text a person can edit, so it is checked, not trusted."""
    bundle = json.loads(SHIPPED.read_text(encoding="utf-8"))
    rule = bundle["rules"][0]["rule"]
    rule["replacement_tokens"] = [["id", "definitely_not_what_was_verified"]]
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(bundle), encoding="utf-8")
    monkeypatch.setenv("BRAIN_SKILL_SEED_BUNDLE", str(tampered))
    monkeypatch.setenv("BRAIN_VERIFIED_SKILL_DB", str(tmp_path / "t.sqlite"))

    store = cry.VerifiedSkillStore()
    assert store.seed_result["refused"] >= 1
    assert store.seed_result["refusals"][0]["reason"] == "CONTENT_ADDRESS_MISMATCH"
    assert store.count() == len(bundle["rules"]) - store.seed_result["refused"]


def test_seeding_happens_once_not_on_every_open(tmp_path: pathlib.Path,
                                                monkeypatch: pytest.MonkeyPatch) -> None:
    """A second open must not re-import; the provenance would otherwise grow without bound."""
    db = tmp_path / "once.sqlite"
    monkeypatch.setenv("BRAIN_VERIFIED_SKILL_DB", str(db))
    first = cry.VerifiedSkillStore()
    count = first.count()
    origins = len(first.provenance()[0]["origins"])

    second = cry.VerifiedSkillStore()
    assert second.seed_result is None, "a populated store was seeded again"
    assert second.count() == count
    assert len(second.provenance()[0]["origins"]) == origins


def test_sync_writes_the_shipped_bundle_from_a_local_store(tmp_path: pathlib.Path) -> None:
    """The update path: teach, then publish. Round-trips through the same format the seed reads."""
    db = tmp_path / "local.sqlite"
    store = cry.VerifiedSkillStore(db_path=db, seed=False)
    store.crystallize_code_fix(
        before_snippet="def tally(xs):\n    t = 0\n    for i in range(len(xs) - 1):\n        t += xs[i]\n    return t\n",
        after_snippet="def tally(xs):\n    t = 0\n    for i in range(len(xs)):\n        t += xs[i]\n    return t\n",
        language="python", error_class="OFF_BY_ONE", origin="test-origin")
    target = tmp_path / "published.json"
    assert cry.sync_seed_bundle(db_path=db, bundle_path=target) == 1

    fresh = cry.VerifiedSkillStore(db_path=tmp_path / "consumer.sqlite", seed=False)
    assert fresh.import_from_file(target)["accepted"] == 1
    assert fresh.count() == 1
