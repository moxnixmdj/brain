"""Zero-learned candidate for the frozen Unknown-Domain direct interface V1.

The candidate consumes only the evaluator-defined visible packet and transcript.
It does not import the hidden scorer, hidden generator, hidden records, or any
learned model. Transfer is solved by reusing the visible exact Domain-A receipt,
requesting one allowed Domain-B probe, and exhaustively identifying the unique
role mapping that satisfies all visible observations. Abstention decisions use
only visible hypothesis consequences and probe schemas.
"""
from __future__ import annotations

import itertools
import math
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_H100_ZERO_LEARNED_UNKNOWN_DOMAIN_DIRECT_CANDIDATE_V1"
TRANSFER = "CROSS_DOMAIN_TRANSFER_OUTSIDE_MYSTERYMECHANISM_TASK_STRUCTURE"
ABSTAIN = "CALIBRATED_UNKNOWN_OR_ABSTENTION_ON_NONIDENTIFIABLE_OR_UNDERSPECIFIED_VARIANTS"


class CandidateError(ValueError):
    pass


def _eval_program(program: Mapping[str, Any], role_values: Mapping[str, float]) -> float:
    if program.get("dsl") != "UDIR_V1":
        raise CandidateError("PROGRAM_DSL_UNSUPPORTED")
    op = str(program.get("op") or "")
    p = program.get("params")
    if not isinstance(p, Mapping):
        raise CandidateError("PROGRAM_PARAMS_INVALID")
    x = float(role_values.get("r0", 0.0))
    if op == "AFFINE_POS":
        return float(p["bias"]) + float(p["gain"]) * x
    if op == "SIGN":
        return -1.0 if x < 0 else 1.0
    if op == "COMPLEMENT":
        return float(p["total"]) - x
    if op == "SAT_MONO":
        return float(p["bias"]) + float(p["gain"]) * (x / (1.0 + abs(x)))
    if op == "ADD2":
        return float(p["bias"]) + float(role_values["r0"]) + float(role_values["r1"])
    if op == "STEP":
        return float(p["high"]) if x >= float(p["threshold"]) else float(p["low"])
    raise CandidateError("PROGRAM_OP_UNSUPPORTED")


def _same_number(a: Any, b: Any) -> bool:
    try:
        return math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=1e-12)
    except (TypeError, ValueError):
        return False


def _receipt(case: Mapping[str, Any]) -> Mapping[str, Any]:
    receipts = case.get("domain_a", {}).get("earned_receipts", [])
    if not isinstance(receipts, Sequence) or isinstance(receipts, (str, bytes)) or len(receipts) != 1:
        raise CandidateError("EXACTLY_ONE_DOMAIN_A_RECEIPT_REQUIRED")
    r = receipts[0]
    if not isinstance(r, Mapping):
        raise CandidateError("DOMAIN_A_RECEIPT_INVALID")
    if r.get("independent_verified") is not True or r.get("exact_byte_bound") is not True:
        raise CandidateError("DOMAIN_A_RECEIPT_NOT_VERIFIED")
    if str(r.get("conclusion") or "") != "success":
        raise CandidateError("DOMAIN_A_RECEIPT_NOT_SUCCESS")
    return r


def _all_domain_b_features(case: Mapping[str, Any], transcript: Sequence[Mapping[str, Any]]) -> list[str]:
    rows = list(case.get("domain_b", {}).get("tasks", []))
    if transcript:
        rows += [x.get("probe_result", {}) for x in transcript]
    query = case.get("domain_b", {}).get("query_inputs", {})
    features = set(query) if isinstance(query, Mapping) else set()
    for row in rows:
        inputs = row.get("inputs", {}) if isinstance(row, Mapping) else {}
        if isinstance(inputs, Mapping):
            features.update(map(str, inputs.keys()))
    if not features:
        raise CandidateError("NO_DOMAIN_B_FEATURES")
    return sorted(features)


def _fit_role_mapping(
    case: Mapping[str, Any],
    transcript: Sequence[Mapping[str, Any]],
    program: Mapping[str, Any],
) -> dict[str, str]:
    roles = program.get("roles")
    if not isinstance(roles, Sequence) or isinstance(roles, (str, bytes)) or not roles:
        raise CandidateError("PROGRAM_ROLES_INVALID")
    roles = [str(x) for x in roles]
    features = _all_domain_b_features(case, transcript)
    if len(features) < len(roles):
        raise CandidateError("INSUFFICIENT_FEATURES")

    observations = list(case.get("domain_b", {}).get("tasks", []))
    for t in transcript:
        if isinstance(t, Mapping) and isinstance(t.get("probe_result"), Mapping):
            observations.append(t["probe_result"])
    if not observations:
        raise CandidateError("NO_DOMAIN_B_OBSERVATIONS")

    fits = []
    for chosen in itertools.permutations(features, len(roles)):
        mapping = dict(zip(roles, chosen))
        ok = True
        for obs in observations:
            if not isinstance(obs, Mapping) or not isinstance(obs.get("inputs"), Mapping):
                ok = False
                break
            vals = obs["inputs"]
            try:
                rv = {role: float(vals[fid]) for role, fid in mapping.items()}
                pred = _eval_program(program, rv)
            except (KeyError, TypeError, ValueError, CandidateError):
                ok = False
                break
            if not _same_number(pred, obs.get("terminal_consequence")):
                ok = False
                break
        if ok:
            fits.append(mapping)

    # The transfer claim requires an identified support set, not merely a lucky
    # prediction. Refuse ambiguity rather than smuggling label memorization in.
    support_sets = {tuple(sorted(m.values())) for m in fits}
    if len(support_sets) != 1:
        raise CandidateError(f"ROLE_MAPPING_SUPPORT_NOT_IDENTIFIED:{len(support_sets)}")
    # Multiple role permutations with the same support could matter for ADD2 only,
    # whose role order is symmetric. Pick deterministically after support identity.
    return sorted(fits, key=lambda m: tuple(m[r] for r in roles))[0]


def _transfer_step(case: Mapping[str, Any], transcript: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    r = _receipt(case)
    program = r.get("normalized_primitive_program")
    if not isinstance(program, Mapping):
        raise CandidateError("RECEIPT_PROGRAM_INVALID")

    if not transcript:
        probes = case.get("domain_b", {}).get("allowed_probes", [])
        if not isinstance(probes, Sequence) or isinstance(probes, (str, bytes)) or not probes:
            raise CandidateError("TRANSFER_PROBE_REQUIRED_BUT_UNAVAILABLE")
        # Frozen evaluator orders the safe precommitted probes by cost; choose
        # minimum cost with deterministic probe-id tie break.
        p = min(
            (x for x in probes if isinstance(x, Mapping)),
            key=lambda x: (float(x.get("cost", math.inf)), str(x.get("probe_id") or "")),
        )
        pid = str(p.get("probe_id") or "").strip()
        if not pid:
            raise CandidateError("PROBE_ID_INVALID")
        return {"type": "REQUEST_PROBE", "probe_id": pid}

    mapping = _fit_role_mapping(case, transcript, program)
    query = case.get("domain_b", {}).get("query_inputs")
    if not isinstance(query, Mapping):
        raise CandidateError("QUERY_INPUTS_INVALID")
    rv = {role: float(query[fid]) for role, fid in mapping.items()}
    consequence = _eval_program(program, rv)

    support = sorted(set(mapping.values()))
    all_features = _all_domain_b_features(case, transcript)
    rejected = sorted(set(all_features) - set(support))
    rid = str(r.get("receipt_id") or "").strip()
    fingerprint = str(r.get("primitive_fingerprint") or "").strip()
    if not rid or not fingerprint:
        raise CandidateError("RECEIPT_ID_OR_FINGERPRINT_MISSING")

    provenance = [{"evidence_id": rid, "source": "DOMAIN_A_RECEIPT", "receipt": fingerprint}]
    provenance += [
        {"evidence_id": fid, "source": "DOMAIN_B_VISIBLE_OR_PROBE", "receipt": "OBSERVED_FEATURE"}
        for fid in sorted(set(support) | set(rejected))
    ]
    return {
        "type": "CONCLUDE",
        "terminal_consequence": consequence,
        "domain_a_source_receipt_ids": [rid],
        "transferred_primitive_fingerprint": fingerprint,
        "support_feature_ids": support,
        "negative_transfer_rejected_feature_ids": rejected,
        "mapping_basis": "FORMAL_REDUCTION",
        "evidence_provenance": provenance,
    }


def _abstention_step(case: Mapping[str, Any]) -> dict[str, Any]:
    hypotheses = case.get("hypotheses")
    if not isinstance(hypotheses, Sequence) or isinstance(hypotheses, (str, bytes)) or not hypotheses:
        raise CandidateError("HYPOTHESES_REQUIRED")
    plausible = [h for h in hypotheses if isinstance(h, Mapping) and h.get("plausible") is True]
    if not plausible:
        raise CandidateError("NO_PLAUSIBLE_HYPOTHESIS")
    consequences = {str(h.get("terminal_consequence")) for h in plausible}
    if len(consequences) == 1:
        return {"type": "CONCLUDE", "terminal_consequence": next(iter(consequences))}

    probes = case.get("allowed_probes", [])
    if not isinstance(probes, Sequence) or isinstance(probes, (str, bytes)):
        raise CandidateError("ALLOWED_PROBES_INVALID")
    discriminators = [
        p for p in probes
        if isinstance(p, Mapping)
        and isinstance(p.get("argument_schema"), Mapping)
        and str(p["argument_schema"].get("type") or "") == "SAFE_BINARY_DISCRIMINATOR"
    ]
    if discriminators:
        p = min(
            discriminators,
            key=lambda x: (float(x.get("cost", math.inf)), str(x.get("probe_id") or "")),
        )
        return {"type": "REQUEST_DISCRIMINATOR", "discriminator": str(p["probe_id"])}

    return {
        "type": "ABSTAIN",
        "nonidentifiability_witness": (
            "Multiple plausible hypotheses imply decision-distinct terminal consequences, "
            "and no visible allowed probe is declared as a safe discriminator."
        ),
    }


def step(case_visible: Mapping[str, Any], transcript: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not isinstance(case_visible, Mapping):
        raise CandidateError("CASE_INVALID")
    if not isinstance(transcript, Sequence) or isinstance(transcript, (str, bytes)):
        raise CandidateError("TRANSCRIPT_INVALID")
    leaf = case_visible.get("leaf_id")
    if leaf == TRANSFER:
        return _transfer_step(case_visible, transcript)
    if leaf == ABSTAIN:
        return _abstention_step(case_visible)
    raise CandidateError("LEAF_UNSUPPORTED")
