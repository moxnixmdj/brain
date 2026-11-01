"""A lesson learned on one machine must reach another, and importing must never make recall unsafe.

The store became durable in the previous change: a rule now survives the session that learned it.
Durable is not portable, though. The store lives inside one checkout and is gitignored, so a second
computer starts empty and two machines that learn for a month cannot pool a single rule. Measured
before this change: export did not exist, so "permanently learned on any computer" was false in the
most ordinary way -- the file was simply not there.

A bundle is the transport. Two things have to be true and they pull in opposite directions:

1. **The rule must actually arrive and fire in the new place.** A cross-repo transfer is the only
   evidence that memory is portable rather than merely durable-in-place. This is tested the hard
   way: teach in checkout A, export, open a store in checkout B that has never seen anything, import,
   and require the rule to rewrite a *different* source text with different identifiers and a
   different literal, then pass B's own verifier.

2. **Importing must not be able to make recall less safe.** A bundle is just a file; it can be
   edited, truncated, or produced by a machine you do not control. Recall still runs the caller's
   verifier before returning a patch, so the worst an untrusted bundle can do is cost a verification.
   The tests pin that as a falsifier, plus two integrity checks -- a rule whose stated id does not
   match its own payload is refused, and a malformed entry is refused by name rather than aborting
   the bundle or being silently dropped.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry  # noqa: E402

# An off-by-one repair, written the way a person would: a concrete identifier and a concrete bound.
BEFORE = "def tally(xs):\n    t = 0\n    for i in range(len(xs) - 1):\n        t += xs[i]\n    return t\n"
AFTER = "def tally(xs):\n    t = 0\n    for i in range(len(xs)):\n        t += xs[i]\n    return t\n"

# The neighbour: same shape, different name, different loop bound, different arithmetic.
NEIGHBOUR_BEFORE = "def total(items):\n    acc = 0\n    for k in range(len(items) - 2):\n        acc += items[k]\n    return acc\n"


def _store(tmp_path: pathlib.Path, name: str) -> cry.VerifiedSkillStore:
    (tmp_path / name).mkdir(parents=True, exist_ok=True)
    # seed=False: these tests are about transport, so a store must start empty or the assertions
    # would be measuring the shipped bundle instead of the bundle under test.
    return cry.VerifiedSkillStore(db_path=tmp_path / name / "skills.sqlite", seed=False)


def _teach(store: cry.VerifiedSkillStore, *, origin: str) -> dict:
    return store.crystallize_code_fix(
        before_snippet=BEFORE,
        after_snippet=AFTER,
        language="python",
        error_class="OFF_BY_ONE",
        origin=origin,
    )


def test_a_rule_learned_here_fires_there(tmp_path: pathlib.Path) -> None:
    """The claim under test: learn in checkout A, recall in checkout B, with no shared state."""
    a = _store(tmp_path / "machine_a", "skills")
    taught = _teach(a, origin="machine-a:repo-a")
    assert taught["crystallized"] is True
    assert a.count() == 1
    bundle_path = tmp_path / "transfer.bundle.json"
    assert a.export_to_file(bundle_path) == 1

    b = _store(tmp_path / "machine_b", "skills")
    assert b.count() == 0, "checkout B must start empty or the test proves nothing"
    assert b.recall_and_apply_verified(
        source_text=NEIGHBOUR_BEFORE, language="python", verifier=lambda s: True) is None

    result = b.import_from_file(bundle_path)
    assert (result["accepted"], result["refused"]) == (1, 0)
    assert b.count() == 1

    def verifier(source: str) -> bool:
        # B's own oracle, not A's: the repaired loop must cover the whole sequence.
        compile(source, "<b>", "exec")
        return "range(len(items))" in source

    recalled = b.recall_and_apply_verified(
        source_text=NEIGHBOUR_BEFORE, language="python", verifier=verifier)
    assert recalled is not None, "the imported rule did not reach the neighbour"
    assert recalled["skill_id"] == taught["skill_id"], "a different rule answered than was shipped"
    assert "range(len(items) - 2)" not in recalled["patched_source"]
    assert "range(len(items))" in recalled["patched_source"]


def test_the_transport_preserves_identity_and_provenance(tmp_path: pathlib.Path) -> None:
    a = _store(tmp_path / "a", "skills")
    taught = _teach(a, origin="machine-a:repo-a")
    bundle = a.export_bundle()

    assert bundle["schema"] == cry.BUNDLE_SCHEMA
    assert bundle["rule_count"] == 1
    entry = bundle["rules"][0]
    assert entry["skill_id"] == taught["skill_id"]
    # The stated id must be the id of the payload, or an edit could rename a rule.
    assert cry.skill_identity(entry["rule"]) == entry["skill_id"]
    assert [p["origin"] for p in entry["provenance"]] == ["machine-a:repo-a"]

    b = _store(tmp_path / "b", "skills")
    b.import_bundle(bundle)
    row = b.provenance()[0]
    assert row["skill_id"] == taught["skill_id"]
    assert [p["origin"] for p in row["origins"]] == ["machine-a:repo-a"]


def test_importing_the_same_lesson_twice_collapses_instead_of_duplicating(tmp_path: pathlib.Path) -> None:
    """Content addressing: two machines that learn the same rule hold one rule, not two."""
    a = _store(tmp_path / "a", "skills")
    _teach(a, origin="machine-a:repo-a")
    bundle = a.export_bundle()

    b = _store(tmp_path / "b", "skills")
    first = b.import_bundle(bundle)
    second = b.import_bundle(bundle)
    assert (first["accepted"], first["merged"]) == (1, 0)
    assert (second["accepted"], second["merged"]) == (0, 1), "a re-import must merge, not insert"
    assert b.count() == 1

    # Two machines' evidence for the same rule must not be summed as if it were independent.
    louder = json.loads(json.dumps(bundle))
    louder["rules"][0]["verified_hits"] = 9
    b.import_bundle(louder)
    assert b.provenance()[0]["verified_hits"] == 9
    assert b.count() == 1


def test_provenance_unions_across_machines(tmp_path: pathlib.Path) -> None:
    """After a merge, a rule that misbehaves can be traced to every machine that vouched for it."""
    a = _store(tmp_path / "a", "skills")
    _teach(a, origin="machine-a:repo-a")
    bundle_a = a.export_bundle()

    b = _store(tmp_path / "b", "skills")
    b.import_bundle(bundle_a)
    _teach(b, origin="machine-b:repo-b")
    provenance = b.provenance()[0]["origins"]
    origins = [p["origin"] for p in provenance]
    assert "machine-a:repo-a" in origins
    assert any(o.startswith("machine-b") for o in origins)


def test_a_bundle_cannot_rename_a_rule(tmp_path: pathlib.Path) -> None:
    """Stated id != payload id is refused, so an edited bundle cannot impersonate a rule."""
    a = _store(tmp_path / "a", "skills")
    _teach(a, origin="machine-a")
    bundle = a.export_bundle()
    bundle["rules"][0]["rule"] = cry.anti_unify_code_rule(
        BEFORE, BEFORE.replace("- 1", ""), language="python", error_class="OTHER")
    b = _store(tmp_path / "b", "skills")
    result = b.import_bundle(bundle)
    assert (result["accepted"], result["refused"]) == (0, 1)
    assert result["refusals"][0]["reason"] == "CONTENT_ADDRESS_MISMATCH"
    assert b.count() == 0


@pytest.mark.parametrize("mutation,reason", [
    ({"rule": {}}, "MISSING_PATTERN_TOKENS"),
    ({"rule": {"pattern_tokens": [["id", "?id0"]], "replacement_tokens": []}}, "MISSING_REPLACEMENT_TOKENS"),
    ({"rule": {"pattern_tokens": [["id"]], "replacement_tokens": [["id", "x"]], "language": "python"}},
     "MALFORMED_PATTERN_TOKENS"),
])
def test_a_malformed_entry_is_refused_by_name(tmp_path: pathlib.Path,
                                             mutation: dict, reason: str) -> None:
    """Refuse the entry, name it, keep going -- never abort the bundle and never drop it silently."""
    a = _store(tmp_path / "a", "skills")
    _teach(a, origin="machine-a")
    bundle = a.export_bundle()
    good = json.loads(json.dumps(bundle["rules"][0]))
    bad = json.loads(json.dumps(bundle["rules"][0]))
    bad.update(mutation)
    bundle["rules"] = [bad, good]

    b = _store(tmp_path / "b", "skills")
    result = b.import_bundle(bundle)
    assert result["refused"] == 1
    assert result["refusals"][0]["reason"] == reason
    assert result["accepted"] == 1, "one bad entry must not cost the good entries"
    assert b.count() == 1


def test_a_wrong_schema_bundle_is_refused_whole(tmp_path: pathlib.Path) -> None:
    b = _store(tmp_path / "b", "skills")
    result = b.import_bundle({"schema": "SOMETHING_ELSE", "rules": [{"skill_id": "x"}]})
    assert (result["accepted"], result["refused"]) == (0, 1)
    assert result["refusals"][0]["reason"] == "BUNDLE_SCHEMA_SOMETHING_ELSE"
    assert b.count() == 0


def test_an_imported_rule_still_cannot_bypass_the_verifier(tmp_path: pathlib.Path) -> None:
    """The safety property that makes an untrusted bundle safe to import.

    If this ever fails, importing is a remote code-edit channel and no bundle may be imported at all.
    """
    a = _store(tmp_path / "a", "skills")
    _teach(a, origin="machine-a")
    b = _store(tmp_path / "b", "skills")
    b.import_bundle(a.export_bundle())

    assert b.recall_and_apply_verified(
        source_text=NEIGHBOUR_BEFORE, language="python", verifier=lambda _s: False) is None


def test_importing_does_not_leave_a_stale_cache_behind(tmp_path: pathlib.Path) -> None:
    """A cached empty list would hide every import for the rest of the process."""
    b = _store(tmp_path / "b", "skills")
    assert b.lookup_rules("python") == []          # populates the cache with nothing
    a = _store(tmp_path / "a", "skills")
    _teach(a, origin="machine-a")
    b.import_bundle(a.export_bundle())
    assert len(b.lookup_rules("python")) == 1


def test_export_round_trips_without_loss(tmp_path: pathlib.Path) -> None:
    """Export -> import -> export must be the same document bar timestamps."""
    a = _store(tmp_path / "a", "skills")
    _teach(a, origin="machine-a")
    first = a.export_bundle()

    b = _store(tmp_path / "b", "skills")
    b.import_bundle(first)
    second = b.export_bundle()

    def strip(bundle: dict) -> dict:
        return {"rules": [{k: v for k, v in r.items() if k != "provenance"} for r in bundle["rules"]]}

    assert strip(first) == strip(second)
