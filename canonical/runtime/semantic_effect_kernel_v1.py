"""Proof-carrying semantic dependency transport kernel V1.

This module does not infer word senses. Existing semantic controllers own that
work. It enforces a narrower systems invariant: an unresolved semantic
dependency that is still active on an input cannot silently disappear from a
derived value. Removal requires a self-verifying formal discharge certificate.

V1 supports two deterministic discharge routes:
1. terminal irrelevance, recomputed by semantic_ambiguity_control_v1; and
2. unique interpretation binding, recomputed by semantic_identifiability_gate.

Additional proof routes may be added only with their own deterministic verifier
bindings and tests.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping, Sequence

EFFECT_SCHEMA = "PROJECT_BRAIN_SEMANTIC_EFFECT_V1"
VALUE_SCHEMA = "PROJECT_BRAIN_SEMANTIC_EFFECT_VALUE_V1"
CERTIFICATE_SCHEMA = "PROJECT_BRAIN_SEMANTIC_DISCHARGE_CERTIFICATE_V1"
TRANSPORT_SCHEMA = "PROJECT_BRAIN_SEMANTIC_EFFECT_TRANSPORT_VERDICT_V1"

PROOF_AMBIGUITY_IRRELEVANT = "AMBIGUITY_TERMINALLY_IRRELEVANT_V1"


class SemanticEffectError(ValueError):
    pass


def _canon(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except Exception as exc:
        raise SemanticEffectError("VALUE_NOT_CANONICAL_JSON") from exc


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise SemanticEffectError(label + "_INVALID")
    return value.strip()


def _seq(value: Any, label: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise SemanticEffectError(label + "_NOT_SEQUENCE")
    return value


def _validate_effect(effect: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(effect, Mapping):
        raise SemanticEffectError("EFFECT_NOT_OBJECT")
    if effect.get("schema") != EFFECT_SCHEMA:
        raise SemanticEffectError("EFFECT_SCHEMA_INVALID")
    required = {
        "schema",
        "effect_id",
        "semvar_id",
        "property_name",
        "source_ref",
        "context_version",
        "proof_obligation_sha256",
        "semantic_truth_authority",
        "terminal_authority",
    }
    if set(effect) != required:
        raise SemanticEffectError("EFFECT_FIELDS_INVALID")
    out = dict(effect)
    for key in ("effect_id", "semvar_id", "property_name", "source_ref", "context_version"):
        out[key] = _token(out.get(key), key.upper())
    obligation = out.get("proof_obligation_sha256")
    if obligation is not None:
        obligation = _token(obligation, "PROOF_OBLIGATION_SHA256")
        if len(obligation) != 64:
            raise SemanticEffectError("PROOF_OBLIGATION_SHA256_INVALID")
    out["proof_obligation_sha256"] = obligation
    if out.get("semantic_truth_authority") is not False or out.get("terminal_authority") is not False:
        raise SemanticEffectError("EFFECT_MUST_NOT_GRANT_AUTHORITY")
    return out


def _effect_map(effects: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for raw in _seq(effects, "EFFECTS"):
        effect = _validate_effect(raw)
        eid = effect["effect_id"]
        if eid in out and out[eid] != effect:
            raise SemanticEffectError("EFFECT_ID_CONTENT_CONFLICT:" + eid)
        out[eid] = effect
    return out


def make_effect(
    *,
    effect_id: str,
    semvar_id: str,
    property_name: str,
    source_ref: str,
    context_version: str,
    proof_obligation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    obligation_sha = None
    if proof_obligation is not None:
        if not isinstance(proof_obligation, Mapping):
            raise SemanticEffectError("PROOF_OBLIGATION_NOT_OBJECT")
        obligation_sha = _sha(dict(proof_obligation))
    effect = {
        "schema": EFFECT_SCHEMA,
        "effect_id": _token(effect_id, "EFFECT_ID"),
        "semvar_id": _token(semvar_id, "SEMVAR_ID"),
        "property_name": _token(property_name, "PROPERTY_NAME"),
        "source_ref": _token(source_ref, "SOURCE_REF"),
        "context_version": _token(context_version, "CONTEXT_VERSION"),
        "proof_obligation_sha256": obligation_sha,
        "semantic_truth_authority": False,
        "terminal_authority": False,
    }
    return _validate_effect(effect)


def _validate_discharge_record(record: Mapping[str, Any], *, reverify: bool) -> dict[str, Any]:
    if not isinstance(record, Mapping) or set(record) != {"effect", "certificate"}:
        raise SemanticEffectError("DISCHARGE_RECORD_INVALID")
    effect = _validate_effect(record["effect"])
    cert = dict(record["certificate"]) if isinstance(record["certificate"], Mapping) else None
    if cert is None:
        raise SemanticEffectError("CERTIFICATE_NOT_OBJECT")
    if reverify:
        _verify_certificate(effect, cert)
    return {"effect": effect, "certificate": cert}


def _validate_value(value: Mapping[str, Any], *, reverify_discharges: bool = False) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SemanticEffectError("VALUE_NOT_OBJECT")
    required = {
        "schema",
        "payload",
        "context_version",
        "active_effects",
        "discharged_effects",
        "semantic_truth_authority",
        "terminal_authority",
    }
    if set(value) != required or value.get("schema") != VALUE_SCHEMA:
        raise SemanticEffectError("VALUE_SCHEMA_OR_FIELDS_INVALID")
    context = _token(value.get("context_version"), "CONTEXT_VERSION")
    active = _effect_map(_seq(value.get("active_effects"), "ACTIVE_EFFECTS"))
    for effect in active.values():
        if effect["context_version"] != context:
            raise SemanticEffectError("ACTIVE_EFFECT_CONTEXT_MISMATCH:" + effect["effect_id"])
    discharged = []
    for raw in _seq(value.get("discharged_effects"), "DISCHARGED_EFFECTS"):
        row = _validate_discharge_record(raw, reverify=reverify_discharges)
        if row["effect"]["context_version"] != context:
            raise SemanticEffectError("DISCHARGED_EFFECT_CONTEXT_MISMATCH:" + row["effect"]["effect_id"])
        discharged.append(row)
    if value.get("semantic_truth_authority") is not False or value.get("terminal_authority") is not False:
        raise SemanticEffectError("VALUE_MUST_NOT_GRANT_AUTHORITY")
    return {
        "schema": VALUE_SCHEMA,
        "payload": deepcopy(value.get("payload")),
        "context_version": context,
        "active_effects": [deepcopy(active[k]) for k in sorted(active)],
        "discharged_effects": deepcopy(discharged),
        "semantic_truth_authority": False,
        "terminal_authority": False,
    }


def make_value(
    payload: Any,
    *,
    context_version: str,
    effects: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    context = _token(context_version, "CONTEXT_VERSION")
    active = _effect_map(_seq(effects, "EFFECTS"))
    for effect in active.values():
        if effect["context_version"] != context:
            raise SemanticEffectError("EFFECT_CONTEXT_MISMATCH:" + effect["effect_id"])
    value = {
        "schema": VALUE_SCHEMA,
        "payload": deepcopy(payload),
        "context_version": context,
        "active_effects": [deepcopy(active[k]) for k in sorted(active)],
        "discharged_effects": [],
        "semantic_truth_authority": False,
        "terminal_authority": False,
    }
    return _validate_value(value)


def active_effect_ids(value: Mapping[str, Any]) -> list[str]:
    checked = _validate_value(value)
    return [e["effect_id"] for e in checked["active_effects"]]


def material_slice(
    value: Mapping[str, Any],
    *,
    required_properties: Sequence[str],
) -> list[dict[str, Any]]:
    checked = _validate_value(value)
    props = {_token(x, "REQUIRED_PROPERTY") for x in _seq(required_properties, "REQUIRED_PROPERTIES")}
    return [
        deepcopy(effect)
        for effect in checked["active_effects"]
        if effect["property_name"] in props
    ]


def _run_proof(
    proof_kind: str,
    proof_problem: Mapping[str, Any],
    *,
    effect: Mapping[str, Any],
) -> dict[str, Any]:
    kind = _token(proof_kind, "PROOF_KIND")
    if not isinstance(proof_problem, Mapping):
        raise SemanticEffectError("PROOF_PROBLEM_NOT_OBJECT")
    if kind == PROOF_AMBIGUITY_IRRELEVANT:
        from canonical.runtime.semantic_ambiguity_control_v1 import decide

        verdict = decide(dict(proof_problem))
        if (
            verdict.get("pass") is not True
            or verdict.get("status") != "PASS__AMBIGUITY_TERMINALLY_IRRELEVANT"
            or verdict.get("terminally_equivalent") is not True
            or verdict.get("action") != "CONTINUE_WITHOUT_DISAMBIGUATION"
        ):
            raise SemanticEffectError("AMBIGUITY_NOT_PROVED_TERMINALLY_IRRELEVANT")
        return dict(verdict)
    if kind == PROOF_IDENTIFIABILITY_UNIQUE:
        from canonical.runtime.semantic_identifiability_gate import adjudicate

        allowed = {
            "interpretations",
            "authorized_context_ids",
            "required_interpretation_id",
        }
        if set(proof_problem) != allowed:
            raise SemanticEffectError("IDENTIFIABILITY_PROOF_FIELDS_INVALID")
        required_id = _token(
            proof_problem.get("required_interpretation_id"),
            "REQUIRED_INTERPRETATION_ID",
        )
        expected_property = f"interpretation({effect['semvar_id']})={required_id}"
        if effect["property_name"] != expected_property:
            raise SemanticEffectError("IDENTIFIABILITY_PROPERTY_BINDING_MISMATCH")
        interpretations = proof_problem.get("interpretations")
        context_ids = proof_problem.get("authorized_context_ids")
        verdict = adjudicate(
            interpretations,
            authorized_context_ids=context_ids,
        )
        selected = verdict.get("interpretation")
        if (
            verdict.get("status") != "UNIQUE"
            or not isinstance(selected, Mapping)
            or selected.get("id") != required_id
        ):
            raise SemanticEffectError("INTERPRETATION_NOT_UNIQUELY_IDENTIFIED")
        return dict(verdict)
    raise SemanticEffectError("PROOF_KIND_UNSUPPORTED:" + kind)


def _certificate_id(effect: Mapping[str, Any], proof_kind: str, problem_sha: str, proof_digest: str) -> str:
    return "SEM-CERT-" + _sha({
        "effect_id": effect["effect_id"],
        "context_version": effect["context_version"],
        "proof_kind": proof_kind,
        "proof_problem_sha256": problem_sha,
        "proof_digest": proof_digest,
    })[:24]


def issue_discharge_certificate(
    effect: Mapping[str, Any],
    *,
    proof_kind: str,
    proof_problem: Mapping[str, Any],
) -> dict[str, Any]:
    checked = _validate_effect(effect)
    if checked["proof_obligation_sha256"] is None:
        raise SemanticEffectError("EFFECT_HAS_NO_BOUND_PROOF_OBLIGATION")
    problem = deepcopy(dict(proof_problem)) if isinstance(proof_problem, Mapping) else proof_problem
    problem_sha = _sha(problem)
    if problem_sha != checked["proof_obligation_sha256"]:
        raise SemanticEffectError("PROOF_PROBLEM_NOT_BOUND_TO_EFFECT")
    verdict = _run_proof(proof_kind, problem, effect=checked)
    proof_digest = _sha(verdict)
    cert = {
        "schema": CERTIFICATE_SCHEMA,
        "certificate_id": _certificate_id(checked, proof_kind, problem_sha, proof_digest),
        "effect_id": checked["effect_id"],
        "semvar_id": checked["semvar_id"],
        "property_name": checked["property_name"],
        "context_version": checked["context_version"],
        "guarantee": "FORMAL",
        "proof_kind": _token(proof_kind, "PROOF_KIND"),
        "proof_problem": problem,
        "proof_problem_sha256": problem_sha,
        "verifier_schema": _token(verdict.get("schema"), "VERIFIER_SCHEMA"),
        "verifier_status": _token(verdict.get("status"), "VERIFIER_STATUS"),
        "proof_digest": proof_digest,
        "semantic_truth_authority": False,
        "terminal_authority": False,
    }
    _verify_certificate(checked, cert)
    return cert


def _verify_certificate(effect: Mapping[str, Any], certificate: Mapping[str, Any]) -> None:
    checked = _validate_effect(effect)
    if not isinstance(certificate, Mapping):
        raise SemanticEffectError("CERTIFICATE_NOT_OBJECT")
    required = {
        "schema",
        "certificate_id",
        "effect_id",
        "semvar_id",
        "property_name",
        "context_version",
        "guarantee",
        "proof_kind",
        "proof_problem",
        "proof_problem_sha256",
        "verifier_schema",
        "verifier_status",
        "proof_digest",
        "semantic_truth_authority",
        "terminal_authority",
    }
    if set(certificate) != required or certificate.get("schema") != CERTIFICATE_SCHEMA:
        raise SemanticEffectError("CERTIFICATE_SCHEMA_OR_FIELDS_INVALID")
    if certificate.get("guarantee") != "FORMAL":
        raise SemanticEffectError("ONLY_FORMAL_CERTIFICATES_CAN_DISCHARGE")
    for key in ("effect_id", "semvar_id", "property_name", "context_version"):
        if certificate.get(key) != checked[key]:
            raise SemanticEffectError("CERTIFICATE_EFFECT_BINDING_MISMATCH:" + key)
    if certificate.get("semantic_truth_authority") is not False or certificate.get("terminal_authority") is not False:
        raise SemanticEffectError("CERTIFICATE_MUST_NOT_GRANT_AUTHORITY")
    problem = certificate.get("proof_problem")
    if not isinstance(problem, Mapping):
        raise SemanticEffectError("CERTIFICATE_PROOF_PROBLEM_INVALID")
    problem_sha = _sha(dict(problem))
    if certificate.get("proof_problem_sha256") != problem_sha:
        raise SemanticEffectError("CERTIFICATE_PROOF_PROBLEM_DIGEST_MISMATCH")
    if checked["proof_obligation_sha256"] != problem_sha:
        raise SemanticEffectError("CERTIFICATE_PROOF_PROBLEM_NOT_BOUND_TO_EFFECT")
    verdict = _run_proof(certificate.get("proof_kind"), dict(problem), effect=checked)
    proof_digest = _sha(verdict)
    if certificate.get("proof_digest") != proof_digest:
        raise SemanticEffectError("CERTIFICATE_PROOF_DIGEST_MISMATCH")
    if certificate.get("verifier_schema") != verdict.get("schema"):
        raise SemanticEffectError("CERTIFICATE_VERIFIER_SCHEMA_MISMATCH")
    if certificate.get("verifier_status") != verdict.get("status"):
        raise SemanticEffectError("CERTIFICATE_VERIFIER_STATUS_MISMATCH")
    expected_id = _certificate_id(checked, certificate["proof_kind"], problem_sha, proof_digest)
    if certificate.get("certificate_id") != expected_id:
        raise SemanticEffectError("CERTIFICATE_ID_MISMATCH")


def discharge_effect(
    value: Mapping[str, Any],
    effect_id: str,
    certificate: Mapping[str, Any],
) -> dict[str, Any]:
    checked = _validate_value(value)
    eid = _token(effect_id, "EFFECT_ID")
    active = {e["effect_id"]: e for e in checked["active_effects"]}
    if eid not in active:
        raise SemanticEffectError("ACTIVE_EFFECT_NOT_FOUND:" + eid)
    effect = active[eid]
    _verify_certificate(effect, certificate)
    del active[eid]
    discharged = list(checked["discharged_effects"])
    discharged.append({"effect": deepcopy(effect), "certificate": deepcopy(dict(certificate))})
    discharged.sort(key=lambda row: (row["effect"]["effect_id"], row["certificate"]["certificate_id"]))
    return {
        **checked,
        "active_effects": [deepcopy(active[k]) for k in sorted(active)],
        "discharged_effects": discharged,
    }


def invalidate_certificates(
    value: Mapping[str, Any],
    certificate_ids: Sequence[str],
) -> dict[str, Any]:
    checked = _validate_value(value)
    ids = {_token(x, "CERTIFICATE_ID") for x in _seq(certificate_ids, "CERTIFICATE_IDS")}
    active = {e["effect_id"]: e for e in checked["active_effects"]}
    kept = []
    removed_effects: dict[str, dict[str, Any]] = {}
    for row in checked["discharged_effects"]:
        cid = _token(row["certificate"].get("certificate_id"), "CERTIFICATE_ID")
        if cid in ids:
            effect = row["effect"]
            removed_effects[effect["effect_id"]] = effect
        else:
            kept.append(row)
    still_discharged_ids = {row["effect"]["effect_id"] for row in kept}
    for eid, effect in removed_effects.items():
        if eid not in still_discharged_ids:
            existing = active.get(eid)
            if existing is not None and existing != effect:
                raise SemanticEffectError("REACTIVATED_EFFECT_CONTENT_CONFLICT:" + eid)
            active[eid] = effect
    return {
        **checked,
        "active_effects": [deepcopy(active[k]) for k in sorted(active)],
        "discharged_effects": deepcopy(kept),
    }


def compose_value(
    payload: Any,
    *,
    inputs: Sequence[Mapping[str, Any]],
    introduced_effects: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    rows = [_validate_value(x, reverify_discharges=True) for x in _seq(inputs, "INPUTS")]
    if not rows:
        raise SemanticEffectError("AT_LEAST_ONE_INPUT_REQUIRED")
    contexts = {x["context_version"] for x in rows}
    if len(contexts) != 1:
        raise SemanticEffectError("INPUT_CONTEXT_VERSION_MISMATCH")
    context = next(iter(contexts))
    active: dict[str, dict[str, Any]] = {}
    discharged_by_cert: dict[str, dict[str, Any]] = {}
    for value in rows:
        for effect in value["active_effects"]:
            prior = active.get(effect["effect_id"])
            if prior is not None and prior != effect:
                raise SemanticEffectError("EFFECT_ID_CONTENT_CONFLICT:" + effect["effect_id"])
            active[effect["effect_id"]] = effect
        for record in value["discharged_effects"]:
            cid = record["certificate"]["certificate_id"]
            discharged_by_cert[cid] = record
    for effect in _effect_map(_seq(introduced_effects, "INTRODUCED_EFFECTS")).values():
        if effect["context_version"] != context:
            raise SemanticEffectError("INTRODUCED_EFFECT_CONTEXT_MISMATCH:" + effect["effect_id"])
        prior = active.get(effect["effect_id"])
        if prior is not None and prior != effect:
            raise SemanticEffectError("EFFECT_ID_CONTENT_CONFLICT:" + effect["effect_id"])
        active[effect["effect_id"]] = effect
    if active:
        discharged_by_cert = {
            cid: row
            for cid, row in discharged_by_cert.items()
            if row["effect"]["effect_id"] not in active
        }
    return {
        "schema": VALUE_SCHEMA,
        "payload": deepcopy(payload),
        "context_version": context,
        "active_effects": [deepcopy(active[k]) for k in sorted(active)],
        "discharged_effects": [
            deepcopy(discharged_by_cert[k]) for k in sorted(discharged_by_cert)
        ],
        "semantic_truth_authority": False,
        "terminal_authority": False,
    }


def verify_transport(
    *,
    inputs: Sequence[Mapping[str, Any]],
    output: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        in_rows = [
            _validate_value(x, reverify_discharges=True)
            for x in _seq(inputs, "INPUTS")
        ]
        out = _validate_value(output, reverify_discharges=True)
    except SemanticEffectError as exc:
        return {
            "schema": TRANSPORT_SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__INVALID_DISCHARGE_HISTORY",
            "reason": str(exc),
            "missing_effect_ids": [],
            "missing_discharge_history_certificate_ids": [],
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }
    if not in_rows:
        raise SemanticEffectError("AT_LEAST_ONE_INPUT_REQUIRED")
    contexts = {x["context_version"] for x in in_rows} | {out["context_version"]}
    if len(contexts) != 1:
        return {
            "schema": TRANSPORT_SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__CONTEXT_VERSION_MISMATCH",
            "missing_effect_ids": [],
            "missing_discharge_history_certificate_ids": [],
            "terminal_authority": False,
        }

    required_active: dict[str, dict[str, Any]] = {}
    required_history: dict[str, dict[str, Any]] = {}
    for value in in_rows:
        for effect in value["active_effects"]:
            required_active[effect["effect_id"]] = effect
        for row in value["discharged_effects"]:
            required_history[row["certificate"]["certificate_id"]] = row

    out_active = {e["effect_id"]: e for e in out["active_effects"]}
    out_history_by_effect: dict[str, list[dict[str, Any]]] = {}
    out_history_by_cert: dict[str, dict[str, Any]] = {}
    for row in out["discharged_effects"]:
        out_history_by_effect.setdefault(row["effect"]["effect_id"], []).append(row)
        out_history_by_cert[row["certificate"]["certificate_id"]] = row

    missing = []
    for eid, effect in sorted(required_active.items()):
        if out_active.get(eid) == effect:
            continue
        valid_discharge = False
        for row in out_history_by_effect.get(eid, []):
            try:
                _verify_certificate(effect, row["certificate"])
                valid_discharge = True
                break
            except SemanticEffectError:
                continue
        if not valid_discharge:
            missing.append(eid)

    missing_history = []
    for cid, row in sorted(required_history.items()):
        eid = row["effect"]["effect_id"]
        if eid in out_active:
            continue
        if cid not in out_history_by_cert:
            missing_history.append(cid)

    passed = not missing and not missing_history
    return {
        "schema": TRANSPORT_SCHEMA,
        "pass": passed,
        "status": (
            "PASS__NO_SILENT_SEMANTIC_EFFECT_LOSS"
            if passed
            else "FAIL_CLOSED__SEMANTIC_EFFECT_OR_HISTORY_LOSS"
        ),
        "missing_effect_ids": missing,
        "missing_discharge_history_certificate_ids": missing_history,
        "semantic_truth_authority": False,
        "terminal_authority": False,
    }
