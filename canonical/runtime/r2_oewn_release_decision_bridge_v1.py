"""One-call OEWN 2025 release enumeration plus authenticated decision-sense control.

This bridge composes two already-verified R2 mechanisms:
1. exact content-addressed OEWN 2025 release-relative sense enumeration; and
2. authenticated decision-relative sense ambiguity control.

It deliberately does not infer an intended sense from definitions, examples,
similarity, rankings, or model judgment.  The release enumerator owns only the
candidate universe relative to the exact pinned archive bytes.  Terminal
signatures and observation outcomes remain authority/verifier owned.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Mapping

from canonical.runtime import oewn_release_sense_universe_v1 as release
from canonical.runtime import oewn_decision_sense_control_v1 as decision

SCHEMA = "PROJECT_BRAIN_R2_OEWN_RELEASE_DECISION_BRIDGE_V1"
ROOT = Path(__file__).resolve().parents[2]

_ALLOWED = frozenset(
    {
        "oewn_release_archive_path",
        "lemma",
        "part_of_speech",
        "decision_manifest",
        "authority_receipt",
        "evidence_receipts",
        "ambiguity_owner",
    }
)


def _base(status: str, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "candidate_sense_set_complete_relative_to_oewn_release": False,
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


def _archive_path(root: Path, raw: Any) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("OEWN_RELEASE_ARCHIVE_PATH_REQUIRED")
    rel = Path(raw.strip())
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("OEWN_RELEASE_ARCHIVE_PATH_MUST_BE_REPOSITORY_RELATIVE")
    full = (root / rel).resolve()
    root_resolved = root.resolve()
    try:
        full.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError("OEWN_RELEASE_ARCHIVE_PATH_ESCAPES_REPOSITORY") from exc
    if not full.is_file() or full.is_symlink():
        raise ValueError("OEWN_RELEASE_ARCHIVE_FILE_INVALID")
    return full


def resolve(
    payload: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
    authority_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    evidence_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else ROOT
    try:
        if not isinstance(payload, Mapping):
            return _base("FAIL_CLOSED", reason="PAYLOAD_NOT_OBJECT")
        extra = set(payload) - _ALLOWED
        if extra:
            return _base(
                "FAIL_CLOSED",
                reason="UNMODELED_FIELDS:" + ",".join(sorted(str(x) for x in extra)),
            )

        lemma = payload.get("lemma")
        if not isinstance(lemma, str) or not lemma.strip():
            return _base("FAIL_CLOSED", reason="LEMMA_REQUIRED")
        manifest = payload.get("decision_manifest")
        if not isinstance(manifest, Mapping):
            return _base("FAIL_CLOSED", reason="DECISION_MANIFEST_REQUIRED")

        archive_path = _archive_path(root, payload.get("oewn_release_archive_path"))
        universe = release.enumerate_senses(
            archive_path,
            lemma,
            part_of_speech=payload.get("part_of_speech"),
        )
        if not isinstance(universe, Mapping):
            return _base(
                "FAIL_CLOSED",
                reason="OEWN_RELEASE_ENUMERATOR_RETURNED_NO_OBJECT",
            )
        universe = deepcopy(dict(universe))
        if universe.get("pass") is not True:
            return _base(
                str(universe.get("status") or "FAIL_CLOSED__OEWN_RELEASE_ENUMERATION"),
                release_enumeration=universe,
                archive_path=str(Path(payload["oewn_release_archive_path"])),
            )
        if universe.get("candidate_set_complete_relative_to_release") is not True:
            return _base(
                "FAIL_CLOSED__OEWN_RELEASE_ENUMERATION_WITHOUT_COMPLETENESS",
                release_enumeration=universe,
            )
        if universe.get("open_world_english_sense_completeness_claimed") is not False:
            return _base(
                "FAIL_CLOSED__OEWN_RELEASE_ENUMERATOR_OVERCLAIMED_OPEN_WORLD_COMPLETENESS",
                release_enumeration=universe,
            )

        if int(universe.get("sense_count") or 0) == 0:
            return _base(
                "OPEN__LEMMA_OR_POS_ABSENT_FROM_EXACT_OEWN_2025_RELEASE",
                candidate_sense_set_complete_relative_to_oewn_release=True,
                release_enumeration=universe,
                release_relative_absence=True,
                next_required_edge=(
                    "NON_OEWN_OR_STRONGER_DOMAIN_SEMANTIC_AUTHORITY_REQUIRED"
                ),
            )

        controlled = decision.resolve(
            sense_universe=universe,
            decision_manifest=manifest,
            authority_receipt=payload.get("authority_receipt"),
            authority_verifier=authority_verifier,
            evidence_receipts=payload.get("evidence_receipts"),
            evidence_verifier=evidence_verifier,
            ambiguity_owner=str(payload.get("ambiguity_owner") or "SYSTEM_MODEL"),
        )
        if not isinstance(controlled, Mapping):
            return _base(
                "FAIL_CLOSED",
                reason="OEWN_DECISION_SENSE_CONTROLLER_RETURNED_NO_OBJECT",
                release_enumeration=universe,
            )
        controlled = deepcopy(dict(controlled))
        return {
            "schema": SCHEMA,
            "status": (
                "PASS__OEWN_RELEASE_ENUMERATION_AND_DECISION_SENSE_CONTROL"
                if controlled.get("pass") is True
                else str(controlled.get("status") or "OPEN__OEWN_DECISION_SENSE_CONTROL")
            ),
            "pass": controlled.get("pass") is True,
            "release_id": universe.get("release_id"),
            "archive_sha256": universe.get("archive_sha256"),
            "lemma": universe.get("lemma"),
            "part_of_speech": universe.get("requested_part_of_speech"),
            "sense_count": universe.get("sense_count"),
            "candidate_sense_set_complete_relative_to_oewn_release": True,
            "release_relative_absence": False,
            "decision_control": controlled,
            "decision_sufficient": controlled.get("decision_sufficient") is True,
            "intended_sense_identified": controlled.get("intended_sense_identified") is True,
            "open_world_english_sense_completeness_claimed": False,
            "semantic_truth_authority": False,
            "execution_authority": False,
            "promotion_authority": False,
            "acceptance_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _base(
            "FAIL_CLOSED",
            reason=type(exc).__name__ + ":" + str(exc),
        )
