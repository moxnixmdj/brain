"""Local appositive identity authority for bounded regulatory-capital concepts.

V1 recognizes only exact local apposition of an authenticated official concept
surface followed by the descriptor "loss-absorbing cushion", e.g.

    "TLAC, a loss-absorbing cushion, ..."

The result is LOCAL referential equivalence for that source span only. It does
not create a global synonym, alias, ontology identity, or terminal authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Callable, Mapping

from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime.https_source_fragment_projection_authority_v2 import (
    verify_projection_pack,
)
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    EVIDENCE_SCHEMA as DAG_EVIDENCE_SCHEMA,
    RECEIPT_SCHEMA as EDGE_RECEIPT_SCHEMA,
    evidence_sha256 as dag_evidence_sha256,
    prove as prove_dag,
)

SCHEMA = "PROJECT_BRAIN_REGCAP_LOCAL_APPOSITIVE_IDENTITY_V1"
EDGE_EVIDENCE_SCHEMA = "PROJECT_BRAIN_REGCAP_LOCAL_APPOSITIVE_EDGE_EVIDENCE_V1"

DESCRIPTOR = "loss-absorbing cushion"

_SURFACES = {
    regcap.CCOB: {
        "capital conservation buffer": (
            "BIS_BASEL_RBC30_2023_11_08_EFFECTIVE_2027_01_01",
            "CCOB_CET1_ABOVE_MINIMUM",
        ),
    },
    regcap.CCYB: {
        "countercyclical buffer": (
            "BIS_BASEL_RBC30_2023_11_08_EFFECTIVE_2027_01_01",
            "CCYB_MACRO_FINANCIAL",
        ),
    },
    regcap.TLAC: {
        "total loss-absorbing capacity": (
            "FSB_TLAC_2015_11_09",
            "TLAC_GSIB_SCOPE",
        ),
        "tlac": (
            "FSB_TLAC_2015_11_09",
            "TLAC_GSIB_SCOPE",
        ),
    },
}

_WS = re.compile(r"\s+")


def _norm(value: Any) -> str:
    return _WS.sub(" ", str(value or "").strip()).casefold()


def _sha(value: Any) -> str:
    if isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    return sha256(raw).hexdigest()


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "local_identity_authority": False,
        "global_alias_authority": False,
        "semantic_truth_authority": False,
        "source_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _mention_id(source_id: str, local_scope_id: str, descriptor_start: int, descriptor_end: int) -> str:
    return "MENTION:" + _sha({
        "source_id": source_id,
        "scope_id": local_scope_id,
        "descriptor_span": [descriptor_start, descriptor_end],
    })


def _validate_span(text: str, start: Any, end: Any, label: str) -> tuple[int, int]:
    if (
        isinstance(start, bool)
        or not isinstance(start, int)
        or isinstance(end, bool)
        or not isinstance(end, int)
        or start < 0
        or end <= start
        or end > len(text)
    ):
        raise ValueError(label + "_SPAN_INVALID")
    return start, end


def _surface_authority(
    concept_id: str,
    surface: str,
    *,
    repo_root: str | Path | None,
    projection_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any]] = verify_projection_pack,
) -> dict[str, Any]:
    rules = _SURFACES.get(concept_id)
    if not isinstance(rules, Mapping):
        raise ValueError("CONCEPT_OUTSIDE_BOUND_REGCAP_APPOSITIVE_SCOPE")
    binding = rules.get(_norm(surface))
    if binding is None:
        raise ValueError("CONCEPT_SURFACE_NOT_AUTHENTICATED")
    source_id, fragment_id = binding
    checked = regcap.load_pack(repo_root=repo_root)
    source_pack = checked["sources_by_id"].get(source_id)
    if not isinstance(source_pack, Mapping):
        raise ValueError("SURFACE_SOURCE_PACK_MISSING")
    result = projection_verifier(deepcopy(dict(source_pack)))
    if not isinstance(result, Mapping) or result.get("pass") is not True:
        raise ValueError("OFFICIAL_SURFACE_SOURCE_AUTHORITY_FAILED")
    fragment_ids = set(result.get("receipt", {}).get("fragment_ids", []))
    if fragment_id not in fragment_ids:
        raise ValueError("OFFICIAL_SURFACE_FRAGMENT_NOT_AUTHENTICATED")
    return {
        "concept_id": concept_id,
        "surface": surface,
        "source_id": source_id,
        "fragment_id": fragment_id,
        "source_receipt_sha256": result["receipt"]["receipt_sha256"],
        "pack_git_blob_sha": checked["pack_git_blob_sha"],
    }


def evaluate_edge_evidence(
    payload: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
    projection_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any]] = verify_projection_pack,
) -> dict[str, Any]:
    try:
        if not isinstance(payload, Mapping) or payload.get("schema") != EDGE_EVIDENCE_SCHEMA:
            return _base("FAIL_CLOSED", reason="EDGE_EVIDENCE_SCHEMA_INVALID")
        allowed = {
            "schema",
            "source_id",
            "source_text",
            "concept_id",
            "concept_start",
            "concept_end",
            "descriptor_start",
            "descriptor_end",
            "direction",
        }
        extra = set(payload) - allowed
        if extra:
            return _base(
                "FAIL_CLOSED",
                reason="UNMODELED_EDGE_EVIDENCE_FIELDS:"
                + ",".join(sorted(str(x) for x in extra)),
            )

        source_id = str(payload.get("source_id") or "").strip()
        source_text = payload.get("source_text")
        concept_id = str(payload.get("concept_id") or "").strip()
        direction = str(payload.get("direction") or "").strip().upper()
        if not source_id or not isinstance(source_text, str) or not source_text:
            return _base("FAIL_CLOSED", reason="SOURCE_ID_OR_TEXT_INVALID")
        if direction not in {"DESCRIPTOR_TO_CONCEPT", "CONCEPT_TO_DESCRIPTOR"}:
            return _base("FAIL_CLOSED", reason="DIRECTION_INVALID")

        cs, ce = _validate_span(
            source_text,
            payload.get("concept_start"),
            payload.get("concept_end"),
            "CONCEPT",
        )
        ds, de = _validate_span(
            source_text,
            payload.get("descriptor_start"),
            payload.get("descriptor_end"),
            "DESCRIPTOR",
        )
        if ce >= ds:
            return _base("FAIL_CLOSED", reason="SPAN_ORDER_INVALID")

        concept_surface = source_text[cs:ce]
        descriptor_surface = source_text[ds:de]
        if _norm(descriptor_surface) != DESCRIPTOR:
            return _base(
                "UNRESOLVED__DESCRIPTOR_OUTSIDE_BOUND_SCOPE",
                descriptor_surface=descriptor_surface,
            )

        bridge = source_text[ce:ds]
        if re.fullmatch(r"\s*,\s*(?:a|an|the)\s+", bridge, flags=re.I) is None:
            return _base(
                "UNRESOLVED__APPOSITIVE_BRIDGE_NOT_CERTIFIED",
                bridge=bridge,
            )
        suffix = source_text[de:]
        next_nonspace = suffix.lstrip()[:1]
        if next_nonspace not in {",", "."}:
            return _base(
                "UNRESOLVED__APPOSITIVE_CLOSURE_NOT_CERTIFIED",
                next_character=next_nonspace or None,
            )

        surface_auth = _surface_authority(
            concept_id,
            concept_surface,
            repo_root=repo_root,
            projection_verifier=projection_verifier,
        )

        source_sha = _sha(source_text)
        scope_id = "REGCAP_LOCAL_APPOSITIVE:" + _sha({
            "source_id": source_id,
            "source_text_sha256": source_sha,
        })[:32]
        mention_id = _mention_id(source_id, scope_id, ds, de)

        if direction == "DESCRIPTOR_TO_CONCEPT":
            edge_source, edge_target = mention_id, concept_id
        else:
            edge_source, edge_target = concept_id, mention_id

        evidence_material = {
            "source_id": source_id,
            "source_text_sha256": source_sha,
            "scope_id": scope_id,
            "concept_id": concept_id,
            "concept_surface": concept_surface,
            "concept_span": [cs, ce],
            "descriptor_surface": descriptor_surface,
            "descriptor_span": [ds, de],
            "direction": direction,
            "surface_authority": surface_auth,
            "relation": "LOCAL_APPOSITIVE_COREFERENCE",
        }
        edge_core = {
            "pass": True,
            "schema": EDGE_RECEIPT_SCHEMA,
            "scope_id": scope_id,
            "source_id": edge_source,
            "target_id": edge_target,
            "relation": "ENTAILS",
            "source_semantics_authenticated": True,
            "target_semantics_authenticated": True,
            "relation_semantics_authenticated": True,
            "verification_authority_mutated": False,
            "evidence_sha256": _sha(evidence_material),
        }
        edge = dict(edge_core)
        edge["receipt_sha256"] = _sha(edge_core)

        return _base(
            "PASS__LOCAL_APPOSITIVE_EDGE_AUTHENTICATED",
            passed=True,
            local_identity_authority=True,
            semantic_truth_authority=True,
            source_authority=True,
            local_scope_id=scope_id,
            mention_id=mention_id,
            concept_id=concept_id,
            direction=direction,
            edge_receipt=edge,
            source_text_sha256=source_sha,
            surface_authority=surface_auth,
            boundary=(
                "EXACT_LOCAL_APPOSITION_ONLY__LOCAL_REFERENT_IDENTITY_DOES_NOT_CREATE_"
                "GLOBAL_SYNONYMY_OR_ALIAS__BOUND_DESCRIPTOR_IS_loss-absorbing_cushion_ONLY"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))


def verify_edge_evidence(
    payload: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
    projection_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any]] = verify_projection_pack,
) -> Mapping[str, Any] | None:
    out = evaluate_edge_evidence(
        payload,
        repo_root=repo_root,
        projection_verifier=projection_verifier,
    )
    receipt = out.get("edge_receipt")
    if out.get("pass") is not True or not isinstance(receipt, Mapping):
        return None
    return deepcopy(dict(receipt))


def prove_local_equivalence(
    *,
    source_id: str,
    source_text: str,
    concept_id: str,
    concept_start: int,
    concept_end: int,
    descriptor_start: int,
    descriptor_end: int,
    repo_root: str | Path | None = None,
    projection_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any]] = verify_projection_pack,
) -> dict[str, Any]:
    base = {
        "schema": EDGE_EVIDENCE_SCHEMA,
        "source_id": source_id,
        "source_text": source_text,
        "concept_id": concept_id,
        "concept_start": concept_start,
        "concept_end": concept_end,
        "descriptor_start": descriptor_start,
        "descriptor_end": descriptor_end,
    }
    forward = {**base, "direction": "DESCRIPTOR_TO_CONCEPT"}
    reverse = {**base, "direction": "CONCEPT_TO_DESCRIPTOR"}

    forward_out = evaluate_edge_evidence(
        forward,
        repo_root=repo_root,
        projection_verifier=projection_verifier,
    )
    if forward_out.get("pass") is not True:
        return forward_out
    reverse_out = evaluate_edge_evidence(
        reverse,
        repo_root=repo_root,
        projection_verifier=projection_verifier,
    )
    if reverse_out.get("pass") is not True:
        return reverse_out

    scope_id = forward_out["local_scope_id"]
    mention_id = forward_out["mention_id"]
    dag_evidence = {
        "schema": DAG_EVIDENCE_SCHEMA,
        "scope_id": scope_id,
        "left_id": mention_id,
        "right_id": concept_id,
        "entailment_receipts": [forward, reverse],
        "counterexample_receipts": [],
    }
    expected_sha = dag_evidence_sha256(dag_evidence)

    def verifier(raw: Mapping[str, Any]) -> Mapping[str, Any] | None:
        return verify_edge_evidence(
            raw,
            repo_root=repo_root,
            projection_verifier=projection_verifier,
        )

    dag = prove_dag(
        dag_evidence,
        expected_evidence_sha256=expected_sha,
        relation_verifier=verifier,
    )
    if dag.get("pass") is not True or dag.get("logical_equivalence_in_scope") is not True:
        return _base(
            "FAIL_CLOSED",
            reason="LOCAL_APPOSITIVE_DAG_EQUIVALENCE_NOT_PROVED",
            dag_result=dag,
        )

    return _base(
        "PASS__LOCAL_APPOSITIVE_IDENTITY_PROVED",
        passed=True,
        local_identity_authority=True,
        semantic_truth_authority=True,
        source_authority=True,
        local_scope_id=scope_id,
        mention_id=mention_id,
        concept_id=concept_id,
        relation="LOGICAL_EQUIVALENCE_IN_SCOPE",
        dag_evidence=dag_evidence,
        expected_dag_evidence_sha256=expected_sha,
        dag_result=dag,
        global_alias_authority=False,
        boundary=(
            "LOCAL_SOURCE_SPAN_REFERENTIAL_EQUIVALENCE_ONLY__NO_GLOBAL_ALIAS_"
            "PROMOTION_OR_CROSS_DOCUMENT_SCOPE_LEAKAGE"
        ),
    )
