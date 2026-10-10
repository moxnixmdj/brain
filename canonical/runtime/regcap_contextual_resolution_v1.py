"""Safe contextual resolver over the bounded regcap discriminator matrix.

Selection is authorized only when an independent verifier certifies that the
caller-supplied candidate set is complete for the current task scope.  Matrix
completeness by itself never supplies hypothesis-set completeness.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import re
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.regcap_contextual_observation_compiler_v1 import compile_span
from canonical.runtime.regcap_contrastive_discriminator_matrix_v1 import (
    DOMAIN,
    verify_matrix,
)
from canonical.runtime import regcap_bounded_rival_registry_authority_v1 as regcap_registry

SCHEMA = "PROJECT_BRAIN_REGCAP_CONTEXTUAL_RESOLUTION_V1"
COMPLETENESS_SCHEMA = "PROJECT_BRAIN_TASK_CANDIDATE_SET_COMPLETENESS_RECEIPT_V1"
_SHA = re.compile(r"^[0-9a-f]{64}$")


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


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_truth_authority": False,
        "concept_identity_authority": False,
        "candidate_universe_complete": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _verify_completeness(
    raw: Any,
    verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None,
    *,
    scope_id: str,
    candidate_ids: Sequence[str],
) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(raw, Mapping) or not callable(verifier):
        return None, "CANDIDATE_COMPLETENESS_RECEIPT_AND_VERIFIER_REQUIRED"
    out = verifier(deepcopy(dict(raw)))
    if not isinstance(out, Mapping):
        return None, "CANDIDATE_COMPLETENESS_VERIFIER_RETURNED_NO_RESULT"
    out = deepcopy(dict(out))
    expected = {
        "pass": True,
        "schema": COMPLETENESS_SCHEMA,
        "scope_id": scope_id,
        "candidate_set_complete": True,
        "verification_authority_mutated": False,
    }
    bad = [k for k, v in expected.items() if out.get(k) != v]
    observed_ids = out.get("candidate_ids")
    if not isinstance(observed_ids, Sequence) or isinstance(observed_ids, (str, bytes)):
        bad.append("candidate_ids")
    elif list(observed_ids) != list(candidate_ids):
        bad.append("candidate_ids")
    if _SHA.fullmatch(str(out.get("receipt_sha256") or "")) is None:
        bad.append("receipt_sha256")
    if bad:
        return out, "CANDIDATE_COMPLETENESS_BINDING_INVALID:" + ",".join(sorted(set(bad)))
    return out, None


def resolve(
    source_text: str,
    *,
    start: int,
    end: int,
    task_scope_id: str,
    candidate_ids: Sequence[str],
    candidate_completeness_receipt: Mapping[str, Any] | None = None,
    candidate_completeness_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    projection_verifier=None,
    repo_root=None,
) -> dict[str, Any]:
    observation = compile_span(source_text, start=start, end=end)
    if observation.get("pass") is not True:
        return _base(
            observation.get("status") or "UNRESOLVED",
            observation=observation,
        )

    if (
        not isinstance(candidate_ids, Sequence)
        or isinstance(candidate_ids, (str, bytes))
        or not candidate_ids
    ):
        return _base("FAIL_CLOSED", reason="CANDIDATE_IDS_REQUIRED", observation=observation)
    candidates = [str(x) for x in candidate_ids]
    if len(candidates) != len(set(candidates)):
        return _base("FAIL_CLOSED", reason="CANDIDATE_IDS_DUPLICATE", observation=observation)
    if not set(candidates).issubset(set(DOMAIN)):
        return _base("FAIL_CLOSED", reason="CANDIDATE_OUTSIDE_MATRIX_DOMAIN", observation=observation)
    if not isinstance(task_scope_id, str) or not task_scope_id.strip():
        return _base("FAIL_CLOSED", reason="TASK_SCOPE_ID_REQUIRED", observation=observation)
    task_scope_id = task_scope_id.strip()

    matrix = verify_matrix(
        repo_root=repo_root,
        projection_verifier=projection_verifier,
    ) if projection_verifier is not None else verify_matrix(repo_root=repo_root)
    if matrix.get("pass") is not True:
        return _base(
            "FAIL_CLOSED",
            reason="CONTRASTIVE_MATRIX_AUTHORITY_FAILED",
            observation=observation,
            matrix_result=matrix,
        )

    row = next(
        (
            x for x in matrix.get("observations", [])
            if x.get("observation_id") == observation.get("observation_id")
        ),
        None,
    )
    if not isinstance(row, Mapping):
        return _base(
            "FAIL_CLOSED",
            reason="OBSERVATION_NOT_IN_AUTHENTICATED_MATRIX",
            observation=observation,
            matrix_result=matrix,
        )

    matches = [
        cid for cid in candidates
        if row.get("outcomes", {}).get(cid) == observation.get("outcome")
    ]

    complete, error = _verify_completeness(
        candidate_completeness_receipt,
        candidate_completeness_verifier,
        scope_id=task_scope_id,
        candidate_ids=candidates,
    )
    if error is not None:
        return _base(
            "OPEN__CANDIDATE_SET_COMPLETENESS_REQUIRED",
            observation=observation,
            matching_candidates=matches,
            candidate_ids=candidates,
            matrix_sha256=matrix.get("matrix_sha256"),
            candidate_completeness_error=error,
            candidate_completeness_result=complete,
        )

    if len(matches) == 1:
        selected = matches[0]
        proof_material = {
            "task_scope_id": task_scope_id,
            "candidate_ids": candidates,
            "candidate_completeness_receipt_sha256": complete["receipt_sha256"],
            "matrix_sha256": matrix["matrix_sha256"],
            "observation_id": observation["observation_id"],
            "outcome": observation["outcome"],
            "selected_concept_id": selected,
            "source_text_sha256": observation["source_text_sha256"],
            "source_span": observation["source_span"],
        }
        return _base(
            "PASS__CONTEXTUAL_CONCEPT_RESOLVED_WITH_COMPLETE_CANDIDATE_SET",
            passed=True,
            semantic_truth_authority=True,
            concept_identity_authority=True,
            candidate_universe_complete=True,
            selected_concept_id=selected,
            observation=observation,
            candidate_ids=candidates,
            matching_candidates=matches,
            candidate_completeness_result=complete,
            matrix_sha256=matrix["matrix_sha256"],
            proof_sha256=_sha(proof_material),
            boundary=(
                "CONCEPT_SELECTION_ONLY_RELATIVE_TO_INDEPENDENTLY_AUTHENTICATED_"
                "TASK_CANDIDATE_SET_COMPLETENESS_AND_AUTHENTICATED_MATRIX_OUTCOME__"
                "NO_GLOBAL_ONTOLOGY_COMPLETENESS_OR_TERMINAL_AUTHORITY"
            ),
        )

    return _base(
        "UNRESOLVED__AUTHENTICATED_OBSERVATION_NOT_UNIQUE_WITHIN_COMPLETE_CANDIDATE_SET",
        observation=observation,
        candidate_ids=candidates,
        matching_candidates=matches,
        candidate_universe_complete=True,
        candidate_completeness_result=complete,
        matrix_sha256=matrix["matrix_sha256"],
    )


def resolve_authenticated_regcap_scope(
    source_text: str,
    *,
    start: int,
    end: int,
    task_scope_id: str,
    candidate_ids: Sequence[str],
    repo_root=None,
    projection_verifier=None,
) -> dict[str, Any]:
    """Resolve direct bounded reg-cap context without requiring descriptor text.

    Authority comes only from the existing authenticated three-rival registry.
    The supplied candidate ids must exactly match that bounded registry.
    """
    if task_scope_id != regcap_registry.SCOPE_ID:
        return _base(
            "NOT_APPLICABLE__OUTSIDE_AUTHENTICATED_REGCAP_SCOPE",
            candidate_ids=list(candidate_ids) if isinstance(candidate_ids, Sequence) else [],
        )

    universe = (
        regcap_registry.resolve_authenticated_registry(
            repo_root=repo_root,
            projection_verifier=projection_verifier,
        )
        if projection_verifier is not None
        else regcap_registry.resolve_authenticated_registry(repo_root=repo_root)
    )
    if universe.get("status") == "FAIL_CLOSED":
        return _base(
            "FAIL_CLOSED",
            reason="REGCAP_BOUNDED_REGISTRY_AUTHORITY_FAILED",
            registry_result=universe,
        )
    if (
        universe.get("authenticated_scope_completeness") is not True
        or universe.get("hypothesis_set_complete") is not True
    ):
        return _base(
            "FAIL_CLOSED",
            reason="REGCAP_BOUNDED_REGISTRY_COMPLETENESS_UNPROVED",
            registry_result=universe,
        )

    registry_ids = sorted(str(x) for x in universe.get("candidate_concept_ids") or [])
    supplied_ids = [str(x) for x in candidate_ids]
    if sorted(supplied_ids) != registry_ids:
        return _base(
            "FAIL_CLOSED",
            reason="CANDIDATES_DO_NOT_MATCH_AUTHENTICATED_REGISTRY",
            registry_candidate_ids=registry_ids,
            supplied_candidate_ids=sorted(supplied_ids),
            registry_result=universe,
        )

    observation = compile_span(source_text, start=start, end=end)
    if observation.get("pass") is not True:
        return _base(
            observation.get("status") or "UNRESOLVED",
            observation=observation,
            registry_result=universe,
        )

    authority = universe.get("authority_result")
    matrix_result = (
        authority.get("matrix_result")
        if isinstance(authority, Mapping)
        else None
    )
    if not isinstance(matrix_result, Mapping) or matrix_result.get("pass") is not True:
        return _base(
            "FAIL_CLOSED",
            reason="AUTHENTICATED_MATRIX_RESULT_MISSING",
            registry_result=universe,
        )

    row = next(
        (
            x for x in matrix_result.get("observations", [])
            if isinstance(x, Mapping)
            and x.get("observation_id") == observation.get("observation_id")
        ),
        None,
    )
    if not isinstance(row, Mapping):
        return _base(
            "FAIL_CLOSED",
            reason="OBSERVATION_NOT_IN_AUTHENTICATED_MATRIX",
            observation=observation,
            registry_result=universe,
        )

    matches = [
        cid for cid in registry_ids
        if row.get("outcomes", {}).get(cid) == observation.get("outcome")
    ]
    if len(matches) != 1:
        return _base(
            "UNRESOLVED__AUTHENTICATED_OBSERVATION_NOT_UNIQUE_IN_BOUND_REGISTRY",
            observation=observation,
            matching_candidates=matches,
            candidate_ids=registry_ids,
            candidate_universe_complete=True,
            registry_result=universe,
        )

    selected = matches[0]
    proof_material = {
        "task_scope_id": task_scope_id,
        "candidate_ids": registry_ids,
        "matrix_sha256": matrix_result.get("matrix_sha256"),
        "observation_id": observation["observation_id"],
        "outcome": observation["outcome"],
        "selected_concept_id": selected,
        "source_text_sha256": observation["source_text_sha256"],
        "source_span": observation["source_span"],
    }
    return _base(
        "PASS__AUTHENTICATED_REGCAP_CONTEXT_RESOLVED_WITHOUT_DESCRIPTOR",
        passed=True,
        semantic_truth_authority=True,
        concept_identity_authority=True,
        candidate_universe_complete=True,
        selected_concept_id=selected,
        observation=observation,
        candidate_ids=registry_ids,
        matching_candidates=matches,
        registry_result=universe,
        matrix_sha256=matrix_result.get("matrix_sha256"),
        proof_sha256=_sha(proof_material),
        boundary=(
            "EXACT_AUTHENTICATED_THREE_RIVAL_TASK_SCOPE_ONLY__"
            "NO_LITERAL_DESCRIPTOR_REQUIRED__NO_GLOBAL_ONTOLOGY_COMPLETENESS__"
            "NO_SEMANTIC_IDENTITY_OUTSIDE_THIS_BOUNDED_SCOPE_OR_TERMINAL_AUTHORITY"
        ),
    )
