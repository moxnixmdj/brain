"""Decision-relative control over a complete OEWN release sense universe.

This module does not guess word sense from similarity. It binds the exact
release-relative OEWN candidate sense set to an independently authenticated
decision manifest containing complete terminal signatures and complete declared
observation outcome maps. It then reuses the Brain's exact semantic ambiguity
controller.

The result is deliberately decision-relative:
- if every surviving sense has the same terminal signature, continue without
  identifying the intended sense;
- if senses imply different terminal actions and an authenticated observation can
  separate them, return the exact minimum-cost discriminator;
- if authenticated observed outcomes narrow the set, recompute immediately;
- if the declared evidence model cannot distinguish action-changing senses, fail
  closed instead of guessing.

No open-world English completeness, semantic truth, execution, acceptance,
promotion, or terminal authority is minted here.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.semantic_ambiguity_control_v1 import decide as decide_ambiguity
from canonical.runtime.oewn_release_sense_universe_v1 import (
    RELEASE_ID,
    RELEASE_SHA256,
    SCHEMA as OEWN_SCHEMA,
)

SCHEMA = "PROJECT_BRAIN_OEWN_DECISION_SENSE_CONTROL_V1"
MANIFEST_SCHEMA = "PROJECT_BRAIN_OEWN_DECISION_SENSE_MANIFEST_V1"
AUTHORITY_SCHEMA = "PROJECT_BRAIN_OEWN_DECISION_SENSE_AUTHORITY_RECEIPT_V1"
OBSERVATION_SCHEMA = "PROJECT_BRAIN_OEWN_SENSE_OBSERVATION_RECEIPT_V1"
_HEX = set("0123456789abcdef")


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _sha_ok(value: Any) -> bool:
    text = str(value or "").lower()
    return len(text) == 64 and all(ch in _HEX for ch in text)


def manifest_sha256(manifest: Mapping[str, Any]) -> str:
    if not isinstance(manifest, Mapping):
        raise TypeError("MANIFEST_NOT_OBJECT")
    return _sha(manifest)


def _base(status: str, passed: bool, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "candidate_sense_set_complete_relative_to_oewn_release": False,
        "decision_manifest_authenticated": False,
        "observation_evidence_authenticated": False,
        "decision_sufficient": False,
        "intended_sense_identified": False,
        "open_world_english_sense_completeness_claimed": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _validate_sense_universe(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("SENSE_UNIVERSE_REQUIRED")
    if value.get("schema") != OEWN_SCHEMA:
        raise ValueError("SENSE_UNIVERSE_SCHEMA_INVALID")
    if value.get("pass") is not True:
        raise ValueError("SENSE_UNIVERSE_NOT_PASS")
    if value.get("release_id") != RELEASE_ID:
        raise ValueError("SENSE_UNIVERSE_RELEASE_ID_INVALID")
    if value.get("archive_sha256") != RELEASE_SHA256:
        raise ValueError("SENSE_UNIVERSE_RELEASE_HASH_INVALID")
    if value.get("candidate_set_complete_relative_to_release") is not True:
        raise ValueError("SENSE_UNIVERSE_COMPLETENESS_UNPROVED")
    if value.get("open_world_english_sense_completeness_claimed") is not False:
        raise ValueError("OPEN_WORLD_COMPLETENESS_MUST_REMAIN_FALSE")

    lemma = value.get("lemma")
    pos = value.get("requested_part_of_speech")
    senses = value.get("senses")
    if not isinstance(lemma, str) or not lemma.strip():
        raise ValueError("LEMMA_REQUIRED")
    if pos is not None and (not isinstance(pos, str) or not pos.strip()):
        raise ValueError("PART_OF_SPEECH_INVALID")
    if not isinstance(senses, Sequence) or isinstance(senses, (str, bytes)) or not senses:
        raise ValueError("NONEMPTY_SENSE_SET_REQUIRED")

    normalized = []
    seen_ids: set[str] = set()
    seen_pairs: set[tuple[str, str]] = set()
    for i, raw in enumerate(senses):
        if not isinstance(raw, Mapping):
            raise ValueError(f"SENSE_NOT_OBJECT:{i}")
        sid = str(raw.get("sense_id") or "").strip()
        synset = str(raw.get("synset_id") or "").strip()
        sense_pos = str(raw.get("part_of_speech") or "").strip()
        if not sid or not synset or not sense_pos:
            raise ValueError(f"SENSE_ID_SYNSET_OR_POS_MISSING:{i}")
        if sid in seen_ids:
            raise ValueError("SENSE_ID_DUPLICATE:" + sid)
        pair = (sense_pos, synset)
        if pair in seen_pairs:
            raise ValueError("SENSE_SYNSET_PAIR_DUPLICATE:" + synset)
        seen_ids.add(sid)
        seen_pairs.add(pair)
        normalized.append(
            {
                "sense_id": sid,
                "synset_id": synset,
                "part_of_speech": sense_pos,
            }
        )

    normalized.sort(key=lambda x: (x["part_of_speech"], x["sense_id"], x["synset_id"]))
    return {
        "lemma": lemma.strip().casefold(),
        "part_of_speech": pos,
        "senses": normalized,
        "sense_ids": [x["sense_id"] for x in normalized],
    }


def _validate_manifest(
    manifest: Mapping[str, Any],
    *,
    universe: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(manifest, Mapping):
        raise ValueError("MANIFEST_REQUIRED")
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("MANIFEST_SCHEMA_INVALID")

    scope_id = str(manifest.get("scope_id") or "").strip()
    lemma = str(manifest.get("lemma") or "").strip().casefold()
    pos = manifest.get("part_of_speech")
    if not scope_id:
        raise ValueError("SCOPE_ID_REQUIRED")
    if lemma != universe["lemma"]:
        raise ValueError("MANIFEST_LEMMA_MISMATCH")
    if pos != universe["part_of_speech"]:
        raise ValueError("MANIFEST_PART_OF_SPEECH_MISMATCH")
    if manifest.get("release_id") != RELEASE_ID:
        raise ValueError("MANIFEST_RELEASE_ID_INVALID")
    if manifest.get("release_sha256") != RELEASE_SHA256:
        raise ValueError("MANIFEST_RELEASE_HASH_INVALID")

    bindings = manifest.get("sense_bindings")
    if not isinstance(bindings, Sequence) or isinstance(bindings, (str, bytes)):
        raise ValueError("SENSE_BINDINGS_INVALID")
    by_id: dict[str, dict[str, Any]] = {}
    synset_by_id = {x["sense_id"]: x["synset_id"] for x in universe["senses"]}
    for i, raw in enumerate(bindings):
        if not isinstance(raw, Mapping):
            raise ValueError(f"SENSE_BINDING_NOT_OBJECT:{i}")
        sid = str(raw.get("sense_id") or "").strip()
        synset = str(raw.get("synset_id") or "").strip()
        if not sid or sid in by_id:
            raise ValueError("SENSE_BINDING_ID_INVALID_OR_DUPLICATE:" + str(i))
        if sid not in synset_by_id or synset != synset_by_id[sid]:
            raise ValueError("SENSE_BINDING_NOT_IN_OEWN_UNIVERSE:" + sid)
        if raw.get("terminal_signature_complete") is not True:
            raise ValueError("TERMINAL_SIGNATURE_COMPLETENESS_UNPROVED:" + sid)
        signature = raw.get("terminal_signature")
        if not isinstance(signature, Mapping):
            raise ValueError("TERMINAL_SIGNATURE_INVALID:" + sid)
        by_id[sid] = {
            "sense_id": sid,
            "synset_id": synset,
            "terminal_signature_complete": True,
            "terminal_signature": deepcopy(dict(signature)),
        }

    if set(by_id) != set(universe["sense_ids"]):
        raise ValueError("SENSE_BINDING_SET_NOT_EXACTLY_COMPLETE")

    observations_raw = manifest.get("observations", [])
    if not isinstance(observations_raw, Sequence) or isinstance(observations_raw, (str, bytes)):
        raise ValueError("OBSERVATIONS_INVALID")
    observations: list[dict[str, Any]] = []
    seen_obs: set[str] = set()
    sense_set = set(universe["sense_ids"])
    for i, raw in enumerate(observations_raw):
        if not isinstance(raw, Mapping):
            raise ValueError(f"OBSERVATION_NOT_OBJECT:{i}")
        oid = str(raw.get("observation_id") or "").strip()
        if not oid or oid in seen_obs:
            raise ValueError("OBSERVATION_ID_INVALID_OR_DUPLICATE:" + str(i))
        seen_obs.add(oid)
        outcomes = raw.get("outcomes")
        cost = raw.get("cost_units")
        if raw.get("outcome_map_complete") is not True:
            raise ValueError("OBSERVATION_OUTCOME_COMPLETENESS_UNPROVED:" + oid)
        if not isinstance(outcomes, Mapping) or set(str(x) for x in outcomes) != sense_set:
            raise ValueError("OBSERVATION_OUTCOME_MAP_NOT_EXACT:" + oid)
        if isinstance(cost, bool) or not isinstance(cost, (int, float)) or float(cost) < 0:
            raise ValueError("OBSERVATION_COST_INVALID:" + oid)
        observations.append(
            {
                "observation_id": oid,
                "outcome_map_complete": True,
                "outcomes": {sid: deepcopy(outcomes[sid]) for sid in universe["sense_ids"]},
                "cost_units": float(cost),
            }
        )

    normalized = {
        "schema": MANIFEST_SCHEMA,
        "scope_id": scope_id,
        "release_id": RELEASE_ID,
        "release_sha256": RELEASE_SHA256,
        "lemma": universe["lemma"],
        "part_of_speech": universe["part_of_speech"],
        "sense_bindings": [by_id[sid] for sid in universe["sense_ids"]],
        "observations": observations,
    }
    return {
        "manifest": normalized,
        "manifest_sha256": _sha(manifest),
        "sense_bindings_by_id": by_id,
        "observations": observations,
    }


def _authenticate_manifest(
    *,
    checked: Mapping[str, Any],
    authority_receipt: Mapping[str, Any] | None,
    authority_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None,
) -> dict[str, Any]:
    if not isinstance(authority_receipt, Mapping) or not callable(authority_verifier):
        return {"pass": False, "status": "AUTHORITY_NOT_BOUND"}
    out = authority_verifier(deepcopy(dict(authority_receipt)))
    if not isinstance(out, Mapping):
        return {"pass": False, "status": "FAIL_CLOSED", "reason": "AUTHORITY_VERIFIER_RETURNED_NO_RECEIPT"}
    out = deepcopy(dict(out))
    manifest = checked["manifest"]
    required = {
        "pass": True,
        "schema": AUTHORITY_SCHEMA,
        "manifest_sha256": checked["manifest_sha256"],
        "scope_id": manifest["scope_id"],
        "release_id": RELEASE_ID,
        "release_sha256": RELEASE_SHA256,
        "lemma": manifest["lemma"],
        "part_of_speech": manifest["part_of_speech"],
        "sense_set_binding_complete": True,
        "sense_terminal_signatures_authenticated": True,
        "observation_outcomes_authenticated": True,
        "verification_authority_mutated": False,
    }
    bad = [k for k, v in required.items() if out.get(k) != v]
    if not _sha_ok(out.get("receipt_sha256")):
        bad.append("receipt_sha256")
    if bad:
        return {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "AUTHORITY_RECEIPT_BINDING_INVALID",
            "mismatch_fields": sorted(set(bad)),
            "authority_result": out,
        }
    return out


def _verified_observations(
    *,
    scope_id: str,
    observations: Sequence[Mapping[str, Any]],
    evidence_receipts: Sequence[Mapping[str, Any]] | None,
    evidence_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if evidence_receipts is None:
        return {}, []
    if not isinstance(evidence_receipts, Sequence) or isinstance(evidence_receipts, (str, bytes)):
        raise ValueError("EVIDENCE_RECEIPTS_INVALID")
    if not callable(evidence_verifier):
        raise ValueError("EVIDENCE_VERIFIER_REQUIRED")

    known = {str(x["observation_id"]): x for x in observations}
    observed: dict[str, Any] = {}
    verified: list[dict[str, Any]] = []
    for i, raw in enumerate(evidence_receipts):
        if not isinstance(raw, Mapping):
            raise ValueError(f"EVIDENCE_RECEIPT_NOT_OBJECT:{i}")
        out = evidence_verifier(deepcopy(dict(raw)))
        if not isinstance(out, Mapping):
            raise ValueError("EVIDENCE_VERIFIER_RETURNED_NO_RECEIPT")
        out = deepcopy(dict(out))
        oid = str(out.get("observation_id") or "").strip()
        required = {
            "pass": True,
            "schema": OBSERVATION_SCHEMA,
            "scope_id": scope_id,
            "source_authorized_for_scope": True,
            "verification_authority_mutated": False,
        }
        bad = [k for k, v in required.items() if out.get(k) != v]
        if oid not in known:
            bad.append("observation_id")
        if not _sha_ok(out.get("receipt_sha256")):
            bad.append("receipt_sha256")
        if "observed_outcome" not in out:
            bad.append("observed_outcome")
        if bad:
            raise ValueError("OBSERVATION_RECEIPT_BINDING_INVALID:" + ",".join(sorted(set(bad))))
        value = deepcopy(out["observed_outcome"])
        if oid in observed and observed[oid] != value:
            raise ValueError("CONFLICTING_AUTHENTICATED_OBSERVATION_OUTCOMES:" + oid)
        observed[oid] = value
        verified.append(out)
    return observed, verified


def resolve(
    *,
    sense_universe: Mapping[str, Any],
    decision_manifest: Mapping[str, Any],
    authority_receipt: Mapping[str, Any] | None = None,
    authority_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    evidence_receipts: Sequence[Mapping[str, Any]] | None = None,
    evidence_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    ambiguity_owner: str = "SYSTEM_MODEL",
) -> dict[str, Any]:
    """Resolve only the decision-relevant portion of OEWN sense ambiguity."""
    try:
        universe = _validate_sense_universe(sense_universe)
        checked = _validate_manifest(decision_manifest, universe=universe)
        auth = _authenticate_manifest(
            checked=checked,
            authority_receipt=authority_receipt,
            authority_verifier=authority_verifier,
        )
        if auth.get("pass") is not True:
            return _base(
                "OPEN__AUTHENTICATED_OEWN_DECISION_MANIFEST_REQUIRED",
                False,
                candidate_sense_set_complete_relative_to_oewn_release=True,
                manifest_sha256=checked["manifest_sha256"],
                candidate_sense_ids=list(universe["sense_ids"]),
                authority_result=auth,
                action="ACQUIRE_OR_VERIFY_ONLY_THE_DECISION_MANIFEST_AUTHORITY_BINDING",
            )

        observed, verified_receipts = _verified_observations(
            scope_id=checked["manifest"]["scope_id"],
            observations=checked["observations"],
            evidence_receipts=evidence_receipts,
            evidence_verifier=evidence_verifier,
        )

        surviving = list(universe["sense_ids"])
        for oid, value in observed.items():
            row = next(x for x in checked["observations"] if x["observation_id"] == oid)
            surviving = [sid for sid in surviving if row["outcomes"][sid] == value]
        if not surviving:
            return _base(
                "MODEL_FALSIFIED__AUTHENTICATED_OBSERVATION_EXCLUDES_ALL_OEWN_SENSES",
                False,
                candidate_sense_set_complete_relative_to_oewn_release=True,
                decision_manifest_authenticated=True,
                observation_evidence_authenticated=bool(verified_receipts),
                manifest_sha256=checked["manifest_sha256"],
                observed_outcomes=observed,
            )

        worlds = []
        for sid in surviving:
            binding = checked["sense_bindings_by_id"][sid]
            worlds.append(
                {
                    "world_id": sid,
                    "terminal_signature_complete": True,
                    "terminal_signature": deepcopy(binding["terminal_signature"]),
                }
            )
        remaining_observations = []
        for row in checked["observations"]:
            if row["observation_id"] in observed:
                continue
            remaining_observations.append(
                {
                    "observation_id": row["observation_id"],
                    "outcome_map_complete": True,
                    "outcomes": {sid: deepcopy(row["outcomes"][sid]) for sid in surviving},
                    "cost_units": row["cost_units"],
                }
            )

        problem = {
            "ambiguity_owner": ambiguity_owner,
            "hypothesis_set_complete": True,
            "worlds": worlds,
            "observations": remaining_observations,
        }
        decision = decide_ambiguity(problem)
        identified = len(surviving) == 1

        if decision.get("pass") is True:
            return _base(
                "PASS__OEWN_SENSE_AMBIGUITY_DECISION_SUFFICIENT",
                True,
                candidate_sense_set_complete_relative_to_oewn_release=True,
                decision_manifest_authenticated=True,
                observation_evidence_authenticated=bool(verified_receipts),
                decision_sufficient=True,
                intended_sense_identified=identified,
                identified_sense_id=surviving[0] if identified else None,
                surviving_sense_ids=surviving,
                manifest_sha256=checked["manifest_sha256"],
                observed_outcomes=observed,
                ambiguity_decision=decision,
                decision_rule=(
                    "ONE_SURVIVING_AUTHENTICATED_SENSE"
                    if identified
                    else "ALL_SURVIVING_SENSES_TERMINALLY_EQUIVALENT"
                ),
            )

        return _base(
            str(decision.get("status") or "OPEN__OEWN_SENSE_AMBIGUITY_REMAINS"),
            False,
            candidate_sense_set_complete_relative_to_oewn_release=True,
            decision_manifest_authenticated=True,
            observation_evidence_authenticated=bool(verified_receipts),
            surviving_sense_ids=surviving,
            manifest_sha256=checked["manifest_sha256"],
            observed_outcomes=observed,
            next_observation_id=decision.get("next_observation_id"),
            minimum_worst_case_cost_units=decision.get("minimum_worst_case_cost_units"),
            ask_user_required=decision.get("ask_user_required", False),
            clarification_required=decision.get("clarification_required", False),
            additional_information_required=decision.get("additional_information_required", False),
            ambiguity_decision=decision,
        )
    except Exception as exc:
        return _base(
            "FAIL_CLOSED",
            False,
            reason=type(exc).__name__ + ":" + str(exc),
        )
