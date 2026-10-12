"""Direct end-to-end adequacy for bounded regulatory-capital contextual facts.

The route answers only a property-extraction request over repository-local source
text. It does not map those properties back to CCoB, CCyB, TLAC, or any other
concept identity.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime import source_aligned_regcap_context_proof_v1 as producer
from canonical.runtime import regcap_contextual_fact_independent_verify_v1 as independent_verify

SCHEMA = "PROJECT_BRAIN_R2_REGCAP_CONTEXTUAL_FACT_DIRECT_ADEQUACY_V1"
ROUTE_ID = "DIRECT_ADEQUACY::REGCAP_BOUNDED_CONTEXTUAL_FACT_EXTRACTION_V1"
CAPABILITY_ID = "finance.regcap.contextual_fact.extract.source_aligned"
ROOT = Path(__file__).resolve().parents[2]
PATH_RE = r"canonical/[A-Za-z0-9_./-]+"
GRAMMAR = re.compile(
    r"^Extract verified regulatory-capital contextual facts from (?P<source>"
    + PATH_RE
    + r"\.(?:txt|md)) and save them to (?P<output>"
    + PATH_RE
    + r"\.json)\.?$",
    re.IGNORECASE,
)

_KINDS = (producer.CCOB_KIND, producer.CCYB_KIND, producer.TLAC_KIND)

def _base(status: str, passed: bool = False) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "matched": False,
        "semantic_acceptance_complete": False,
        "actual_goal_satisfaction_verified": False,
        "direct_adequacy_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }

def _safe(root: Path, rel: str, *, must_exist: bool) -> Path:
    root = root.resolve()
    raw = Path(rel)
    if raw.is_absolute() or ".." in raw.parts or not rel.startswith("canonical/"):
        raise ValueError("PATH_INVALID")
    path = (root / raw).resolve(strict=False)
    if path == root or root not in path.parents or path.is_symlink():
        raise ValueError("PATH_INVALID")
    if must_exist and not path.is_file():
        raise ValueError("SOURCE_FILE_MISSING")
    return path

def _contract(goal: str) -> tuple[dict[str, Any], list[str]]:
    out = compile_contract(
        goal,
        source_id="user",
        routing_target_effects=["finance.regcap.contextual_fact.extract"],
    )
    ids = list(
        (out.get("acceptance_contract") or {}).get("required_obligation_ids") or []
    )
    if out.get("pass") is not True or not ids:
        raise ValueError("RAW_TASK_CONTRACT_INVALID")
    return out, ids

def _policy_id(goal: str) -> str:
    payload = CAPABILITY_ID + "\n" + goal
    return "GOAL_SCOPED::" + sha256(payload.encode("utf-8")).hexdigest()

def _producer_payload(
    source_text: str,
    *,
    source_id: str,
    source_path: str,
) -> dict[str, Any]:
    spans: list[tuple[int, int]] = [(0, len(source_text))]
    for m in re.finditer(r"(?:[0-9]+\.[0-9]+|[^.!?\n])+[.!?]?", source_text):
        s, e = m.span()
        while s < e and source_text[s].isspace():
            s += 1
        while e > s and source_text[e - 1].isspace():
            e -= 1
        if e > s and (s, e) not in spans:
            spans.append((s, e))
    claims = []
    idx = 0
    for s, e in spans:
        for kind in _KINDS:
            claims.append(
                {
                    "claim_id": "context-" + str(idx),
                    "kind": kind,
                    "start": s,
                    "end": e,
                }
            )
            idx += 1
    proof = producer.verify_proof(
        source_text,
        source_id=source_id,
        claims=claims,
    )
    if proof.get("status") == "FAIL_CLOSED":
        raise RuntimeError("SOURCE_CONTEXT_PROOF_FAIL_CLOSED")
    accepted = list(proof.get("accepted_claims") or [])
    if not accepted:
        raise RuntimeError("NO_BOUNDED_REGCAP_CONTEXT_FACT_RECOGNIZED")
    kinds = sorted({str(row["kind"]) for row in accepted})
    atoms = sorted(
        {
            str(atom_id)
            for row in accepted
            for atom_id in (row.get("proved_atom_ids") or [])
        }
    )
    return {
        "schema": independent_verify.OUTPUT_SCHEMA,
        "status": "VERIFIED_BOUNDED_REGCAP_CONTEXT_FACTS",
        "source_id": source_id,
        "source_path": source_path,
        "source_sha256": sha256(source_text.encode("utf-8")).hexdigest(),
        "matched_context_kinds": kinds,
        "proved_atom_ids": atoms,
        "concept_identity_claimed": False,
        "reverse_property_to_concept_classification_authorized": False,
        "open_world_semantic_closure": False,
    }

def preflight(request: Mapping[str, Any], *, repo_root=None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    if not isinstance(request, Mapping):
        return {**_base("FAIL_CLOSED"), "reason": "REQUEST_NOT_OBJECT"}
    task = str(request.get("task_id") or "").strip()
    goal = str(request.get("goal") or "").strip()
    if not task or not goal:
        return {**_base("FAIL_CLOSED"), "reason": "TASK_ID_AND_GOAL_REQUIRED"}
    match = GRAMMAR.fullmatch(goal)
    if match is None:
        return {**_base("NOT_APPLICABLE"), "matched": False}
    try:
        source_rel = match.group("source")
        output_rel = match.group("output")
        source = _safe(root, source_rel, must_exist=True)
        output = _safe(root, output_rel, must_exist=False)
        if source == output:
            raise ValueError("SOURCE_OUTPUT_COLLISION")
        source_sha = sha256(source.read_bytes()).hexdigest()
        contract, ids = _contract(goal)
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),
            "matched": True,
            "route_id": ROUTE_ID,
            "capability_id": CAPABILITY_ID,
            "task_id": task,
            "goal": goal,
            "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
            "selected_policy_id": _policy_id(goal),
            "source_path": source_rel,
            "source_sha256": source_sha,
            "output_path": output_rel,
            "raw_task_contract_sha256": contract["task_contract_sha256"],
            "raw_acceptance_obligation_ids": ids,
            "preflight_execution_authority": False,
        }
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),
            "matched": True,
            "route_id": ROUTE_ID,
            "reason": type(exc).__name__ + ":" + str(exc),
        }

def _restore(path: Path, existed: bool, original: bytes | None) -> None:
    if existed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(original or b"")
    elif path.exists():
        path.unlink()

def run(
    request: Mapping[str, Any],
    *,
    repo_root=None,
    independent_provider=None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    pf = preflight(request, repo_root=root)
    if pf.get("matched") is not True or pf.get("status") == "FAIL_CLOSED":
        return pf

    source = _safe(root, pf["source_path"], must_exist=True)
    output = _safe(root, pf["output_path"], must_exist=False)
    existed = output.is_file()
    original = output.read_bytes() if existed else None
    try:
        before = source.read_bytes()
        if sha256(before).hexdigest() != pf["source_sha256"]:
            raise RuntimeError("SOURCE_DRIFT_BEFORE_EXECUTION")
        source_text = before.decode("utf-8")
        source_id = "repo:" + pf["source_path"] + ":" + pf["source_sha256"]

        payload = _producer_payload(
            source_text,
            source_id=source_id,
            source_path=pf["source_path"],
        )
        verification = (
            independent_provider(
                source_text,
                source_id=source_id,
                source_path=pf["source_path"],
                candidate=payload,
            )
            if independent_provider
            else independent_verify.verify(
                source_text,
                source_id=source_id,
                source_path=pf["source_path"],
                candidate=payload,
            )
        )
        if (
            not isinstance(verification, Mapping)
            or verification.get("pass") is not True
            or verification.get("producer_independent") is not True
            or verification.get("semantic_acceptance_complete") is not True
        ):
            raise RuntimeError("INDEPENDENT_CONTEXT_FACT_VERIFICATION_FAILED")

        after = source.read_bytes()
        if after != before:
            raise RuntimeError("SOURCE_DRIFT_DURING_EXECUTION")

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        readback = json.loads(output.read_text(encoding="utf-8"))
        if readback != payload:
            raise RuntimeError("OUTPUT_READBACK_MISMATCH")

        _, accepted = _contract(str(request["goal"]))
        if accepted != pf["raw_acceptance_obligation_ids"]:
            raise RuntimeError("RAW_ACCEPTANCE_SET_DRIFT")

        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", True),
            "matched": True,
            "route_id": ROUTE_ID,
            "capability_id": CAPABILITY_ID,
            "selected_policy_id": pf["selected_policy_id"],
            "goal_sha256": pf["goal_sha256"],
            "source_path": pf["source_path"],
            "source_sha256": pf["source_sha256"],
            "output_path": pf["output_path"],
            "output_sha256": sha256(output.read_bytes()).hexdigest(),
            "matched_context_kinds": payload["matched_context_kinds"],
            "proved_atom_ids": payload["proved_atom_ids"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": accepted,
            "acceptance_receipt": {
                "verified": True,
                "producer_independent": True,
                "verifier": independent_verify.SCHEMA,
                "concept_identity_claimed": False,
            },
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "authority_boundary": (
                "BOUNDED_SOURCE_CONTEXT_PROPERTY_EXTRACTION_ONLY__"
                "NO_PROPERTY_TO_CONCEPT_REVERSE_CLASSIFICATION__"
                "NO_OPEN_WORLD_FINANCE_SEMANTIC_CLOSURE"
            ),
        }
    except Exception as exc:
        _restore(output, existed, original)
        rollback = (
            output.is_file()
            and existed
            and output.read_bytes() == (original or b"")
            if existed
            else not output.exists()
        )
        return {
            **_base("OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"),
            "matched": True,
            "route_id": ROUTE_ID,
            "capability_id": CAPABILITY_ID,
            "goal_sha256": pf.get("goal_sha256"),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "rollback_complete": rollback,
            "reason": type(exc).__name__ + ":" + str(exc),
        }
