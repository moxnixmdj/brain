"""Source-bound identity proof for "loss-absorbing cushion" -> CCoB.

This module proves only one exact source-context relation. It does not declare
"loss-absorbing cushion" a global synonym for the capital conservation buffer.

The proof requires:
1. the exact content-addressed projection pack;
2. live HTTPS authentication of both short source fragments;
3. the CCoB-identifying fragment to precede the loss-cushion fragment;
4. both fragments to remain within a tight locality bound.

No policy, execution, acceptance, promotion, or terminal authority is granted.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.https_source_fragment_projection_authority_v2 import (
    verify_projection_pack,
)
from canonical.runtime.regcap_necessary_property_authority_v1 import CCOB

SCHEMA = "PROJECT_BRAIN_NYFED_LOSS_CUSHION_CCOB_SOURCE_IDENTITY_V1"
PACK_PATH = (
    "canonical/evidence/"
    "NYFED_2010_LOSS_ABSORBING_CUSHION_CCOB_SOURCE_V1.json"
)
PACK_GIT_BLOB_SHA = "a602ebb7639899c300a2558dc05967b1fd06b249"
SOURCE_ID = "NYFED_DUDLEY_BASEL_2010_10_10"
EXACT_SURFACE = "loss-absorbing cushion"
IDENTITY_FRAGMENT_ID = "CCOB_IDENTIFYING_FRAGMENT"
LOSS_CUSHION_FRAGMENT_ID = "LOSS_CUSHION_FRAGMENT"
MAX_RELATION_GAP_CHARS = 512
ROOT = Path(__file__).resolve().parents[2]


def _git_blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "mapped_concept_id": None,
        "source_context_identity_authority": False,
        "semantic_identity_authority": False,
        "semantic_truth_authority": False,
        "global_phrase_identity_authority": False,
        "open_world_ontology_complete": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def load_pack(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    path = (root / PACK_PATH).resolve(strict=True)
    path.relative_to(root)
    if not path.is_file() or path.is_symlink():
        raise ValueError("PACK_FILE_INVALID")
    raw = path.read_bytes()
    observed = _git_blob(raw)
    if observed != PACK_GIT_BLOB_SHA:
        raise ValueError("PACK_GIT_BLOB_DRIFT:" + observed)
    doc = json.loads(raw.decode("utf-8"))
    if not isinstance(doc, Mapping):
        raise ValueError("PACK_NOT_OBJECT")
    if doc.get("source_id") != SOURCE_ID:
        raise ValueError("PACK_SOURCE_ID_MISMATCH")
    return dict(doc)


def verify(
    *,
    repo_root: str | Path | None = None,
    opener: Any = None,
) -> dict[str, Any]:
    try:
        pack = load_pack(repo_root=repo_root)
        source = verify_projection_pack(pack, opener=opener)
        if source.get("pass") is not True:
            return _base(
                "FAIL_CLOSED",
                reason="SOURCE_PROJECTION_AUTHORITY_FAILED",
                source_result=source,
            )

        matched = {
            str(row.get("fragment_id") or ""): row
            for row in source.get("matched_fragments") or []
            if isinstance(row, Mapping)
        }
        if IDENTITY_FRAGMENT_ID not in matched or LOSS_CUSHION_FRAGMENT_ID not in matched:
            return _base(
                "FAIL_CLOSED",
                reason="REQUIRED_SOURCE_FRAGMENT_MISSING_FROM_RECEIPT",
                source_result=source,
            )

        identity = matched[IDENTITY_FRAGMENT_ID]
        cushion = matched[LOSS_CUSHION_FRAGMENT_ID]
        identity_index = int(identity.get("fragment_index"))
        cushion_index = int(cushion.get("fragment_index"))
        gap = cushion_index - identity_index
        if gap <= 0 or gap > MAX_RELATION_GAP_CHARS:
            return _base(
                "OPEN__SOURCE_FRAGMENTS_NOT_IN_ADMITTED_RELATION_SHAPE",
                source_result=source,
                relation_gap_chars=gap,
                required_order=[
                    IDENTITY_FRAGMENT_ID,
                    LOSS_CUSHION_FRAGMENT_ID,
                ],
                max_relation_gap_chars=MAX_RELATION_GAP_CHARS,
            )

        if identity.get("section_anchor") != cushion.get("section_anchor"):
            return _base(
                "OPEN__SOURCE_FRAGMENTS_NOT_IN_SAME_AUTHENTICATED_SECTION",
                source_result=source,
            )

        return _base(
            "PASS__SOURCE_BOUND_LOSS_ABSORBING_CUSHION_MAPS_TO_CCOB",
            passed=True,
            mapped_concept_id=CCOB,
            source_context_identity_authority=True,
            semantic_identity_authority=True,
            semantic_truth_authority=True,
            global_phrase_identity_authority=False,
            exact_surface=EXACT_SURFACE,
            source_id=SOURCE_ID,
            source_url=source.get("url"),
            source_receipt_sha256=(
                (source.get("receipt") or {}).get("receipt_sha256")
                if isinstance(source.get("receipt"), Mapping)
                else None
            ),
            relation_gap_chars=gap,
            relation=(
                "EXACT_SOURCE_CONTEXT_IDENTIFIES_THE_2_5_PERCENT_CAPITAL_"
                "CONSERVATION_BUFFER_THEN_DESCRIBES_IT_AS_CREATING_A_"
                "LOSS_ABSORBING_CUSHION"
            ),
            boundary=(
                "SOURCE_SPECIFIC_IDENTITY_ONLY__NO_GLOBAL_SYNONYMY__"
                "NO_REVERSE_INFERENCE_FROM_LOSS_ABSORPTION_PROPERTY__"
                "NO_OPEN_WORLD_ONTOLOGY_POLICY_OR_TERMINAL_AUTHORITY"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))
