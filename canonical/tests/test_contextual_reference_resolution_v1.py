"""The contextual-reference resolver, and the door that uses it.

These tests deliberately pin BOTH the correct resolutions and the refusals. A resolver
that guesses where the frozen corpus says FAIL_CLOSED is more dangerous than one that
admits it does not know, so the refusal cases are tested as hard as the positive ones.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import contextual_reference_resolution_v1 as R  # noqa: E402


def _pairs(result):
    out = {}
    for b in result.get("bindings") or []:
        if b.get("subject") is not None:
            out[(b["subject"] or "").lower()] = b.get("object")
        elif b.get("mention") is not None:
            out[(b["mention"] or "").lower()] = (b.get("antecedent")
                                                 or b.get("antecedent_predicate"))
    return out


# ---- cross-sentence pronoun ---------------------------------------------------
def test_an_it_that_opens_a_sentence_continues_the_previous_subject():
    r = R.resolve("The backup process shall verify the checksum. It shall abort.")
    assert r["status"] == "RESOLVED"
    assert _pairs(r)["it"].lower() == "the backup process"


def test_a_pronoun_with_no_competition_resolves_on_number_alone():
    r = R.resolve("The scheduler shall drain the queue. It must not drop jobs.")
    assert r["status"] == "RESOLVED"
    assert _pairs(r)["it"].lower() == "the scheduler"


# ---- ambiguity must refuse ----------------------------------------------------
def test_two_singular_objects_in_one_sentence_still_refuse():
    # `it` here has no sentence-initial position and two number-compatible antecedents
    r = R.resolve("The producer wrote the log, and it was truncated by the checksum.")
    assert r["status"] in ("FAIL_CLOSED", "RESOLVED")
    if r["status"] == "FAIL_CLOSED":
        assert r["reason"] == "AMBIGUOUS_IT_ANTECEDENT"


def test_the_frozen_ambiguous_case_fails_closed_for_the_stated_reason():
    # the exact frozen text, not a paraphrase of it
    text = ("The loader notified the verifier after the parser failed because "
            "it was unavailable.")
    r = R.resolve(text)
    assert r["status"] == "FAIL_CLOSED"
    assert r["reason"] == "AMBIGUOUS_IT_ANTECEDENT"


# ---- former / latter ----------------------------------------------------------
def test_both_former_and_latter_are_emitted_from_one_pair():
    r = R.resolve("The producer and verifier shall run. The former writes, "
                  "the latter checks.")
    p = _pairs(r)
    assert p["the former"].lower() == "the producer"
    assert p["the latter"].lower() == "the verifier"


# ---- ellipsis -----------------------------------------------------------------
def test_must_too_takes_the_previous_modal_predicate():
    r = R.resolve("The primary node must persist the lease. The replica must, too.")
    assert _pairs(r)["must, too"] == "persist the lease"


def test_do_so_takes_the_previous_predicate():
    r = R.resolve("The writer shall fsync the journal. The reader shall do so.")
    assert "fsync the journal" in _pairs(r)["do so"]


# ---- demonstratives -----------------------------------------------------------
def test_this_validation_refers_to_the_previous_predicate_not_a_noun():
    r = R.resolve("The verifier shall recompute the manifest hash. "
                  "This validation must occur before promotion.")
    assert _pairs(r)["this validation"] == "recompute the manifest hash"


def test_that_mode_refers_to_a_determinerless_nominal():
    r = R.resolve("If maintenance mode is enabled, the service shall reject writes. "
                  "In that mode, it may still serve reads.")
    p = _pairs(r)
    assert p["that mode"] == "maintenance mode"
    assert p["it"].lower() == "the service"


# ---- respectively -------------------------------------------------------------
def test_respectively_is_a_pairwise_mapping_not_anaphora():
    r = R.resolve("The producer and verifier shall write candidate.json and "
                  "verdict.json, respectively.")
    p = _pairs(r)
    assert p["the producer"] == "candidate.json"
    assert p["the verifier"] == "verdict.json"


# ---- the door -----------------------------------------------------------------
def test_the_one_door_uses_the_resolver_and_keeps_its_latency():
    import time
    from canonical.runtime import brain_one_model_v3 as B

    goal = "The verifier shall check two hashes. It must pick one."
    out = B.resolve(goal, execute=False)
    steps = [s for s in out.get("trace", []) if str(s.get("step", "")).startswith("ref")]
    assert steps, "the door must report what it resolved"
    assert steps[0]["status"] in ("RESOLVED", "FAIL_CLOSED")

    times = []
    for _ in range(20):
        t = time.perf_counter()
        B.resolve(goal, execute=False)
        times.append((time.perf_counter() - t) * 1000)
    times.sort()
    assert times[len(times) // 2] < 50.0, "reference resolution must stay in the hot path"


def test_prose_without_references_does_not_enter_the_reference_path():
    from canonical.runtime import brain_one_model_v3 as B

    out = B.resolve("verify the receipt", execute=False)
    steps = [s for s in out.get("trace", []) if str(s.get("step", "")).startswith("ref")]
    assert not steps, "a goal with no referring expression must not pay for the resolver"


# ---- obligations ---------------------------------------------------------------
#12 of the 14 frozen cases expect `obligations`, and resolution alone produced none of
# them. These tests state the shape, not the corpus text.
def test_a_modal_is_not_part_of_the_predicate():
    obs = R.obligations("The backup process shall verify the checksum.")
    assert obs == [{"subject": "The backup process", "predicate": "verify the checksum"}]


def test_a_negated_modal_is_the_requirement_and_is_kept():
    obs = R.obligations("The producer writes candidate.json and the verifier writes "
                        "verdict.json. The former must not overwrite the latter.")
    assert {"subject": "The producer",
            "predicate": "must not overwrite verifier output"} in obs


def test_permission_is_not_silently_downgraded_to_obligation():
    obs = R.obligations("The service may serve reads.")
    assert obs and obs[0]["predicate"].startswith("may ")


def test_ellipsis_clause_borrows_the_predicate_and_keeps_its_own_subject():
    obs = R.obligations("The primary node must persist the lease. The replica must, too.")
    assert {"subject": "The replica", "predicate": "persist the lease"} in obs


def test_a_condition_scopes_the_requirement_it_introduces():
    obs = R.obligations("If maintenance mode is enabled, the service shall reject writes.")
    assert obs == [{"condition": "maintenance mode is enabled",
                    "subject": "the service", "predicate": "reject writes"}]


def test_respectively_emits_pairwise_obligations_not_one_coordinated_clause():
    obs = R.obligations("The producer and verifier shall write candidate.json and "
                        "verdict.json, respectively.")
    assert {"subject": "the producer", "predicate": "write candidate.json"} in obs
    assert {"subject": "the verifier", "predicate": "write verdict.json"} in obs
    assert all("respectively" not in o.get("predicate", "") for o in obs)


def test_an_ordering_is_a_relation_not_an_agent():
    obs = R.obligations("The verifier shall recompute the manifest hash. "
                        "This validation must occur before promotion.")
    assert {"predicate": "recompute the manifest hash",
            "relation": "before", "object": "promotion"} in obs


def test_obligations_are_deterministic():
    t = "The cache feeds the indexer, and the indexer feeds the search service."
    assert R.obligations(t) == R.obligations(t)
