"""Canonical cross-runner memory for verified reusable R3 skills.

Only independently reauthenticatable skill records and rebuilt Pareto-frontier
metadata are persisted here. Observations, retry capsules, failures, and pending
work are intentionally excluded.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.executable_skill_verification_authenticator_v1 import (
    reauthenticate_record,
)

SCHEMA = "PROJECT_BRAIN_R3_VERIFIED_SKILL_MEMORY_V1"
DEFAULT_MEMORY_RELATIVE = "canonical/state/R3_VERIFIED_SKILL_MEMORY_V1.json"
SUPERSET_SCOPE_PREDICATE = "STRUCTURAL_MATCH_V1"


class SkillMemoryError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False, default=str,
    )


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _s(value: Any) -> str:
    return " ".join(str(value or "").split())


def _items(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return sorted({_s(x) for x in value if _s(x)})


def _skill_id(skill: Mapping[str, Any]) -> str:
    digest = _s(skill.get("candidate_sha256"))
    if not digest:
        raise SkillMemoryError("VERIFIED_SKILL_DIGEST_MISSING")
    return "skill:" + digest.replace("sha256:", "")


def _family_id(skill: Mapping[str, Any]) -> str:
    post = _items(skill.get("postconditions"))
    if not post:
        raise SkillMemoryError("VERIFIED_SKILL_POSTCONDITIONS_EMPTY")
    return "family:" + _sha({"postconditions": post})


def _pareto_row(skill_id: str, skill: Mapping[str, Any]) -> dict[str, Any]:
    steps = skill.get("steps")
    if not isinstance(steps, Sequence) or isinstance(steps, (str, bytes)) or not steps:
        raise SkillMemoryError("VERIFIED_SKILL_STEPS_INVALID")
    relation = _s(skill.get("scope_relation"))
    if relation not in {"EXACT", "PROVEN_SUPERSET"}:
        raise SkillMemoryError("VERIFIED_SKILL_SCOPE_RELATION_INVALID")
    io_width = 0
    for step in steps:
        if not isinstance(step, Mapping):
            raise SkillMemoryError("VERIFIED_SKILL_STEP_INVALID")
        io_width += len(_items(step.get("inputs"))) + len(_items(step.get("outputs")))
    generalized = (
        relation == "PROVEN_SUPERSET"
        and _s(skill.get("scope_predicate")) == SUPERSET_SCOPE_PREDICATE
    )
    return {
        "capability_id": skill_id,
        "reusable_capability": True,
        "independently_verified": True,
        "capability": len(_items(skill.get("postconditions"))),
        "generalization": 2 if generalized else 1,
        "reliability": len(_items(skill.get("source_episode_ids"))),
        "latency": len(steps),
        "compute": len(steps),
        "memory": io_width,
        "incremental_spend_usd": 0,
    }


def _record(
    skill_id: str,
    raw: Mapping[str, Any],
    *,
    repo_root: str | Path,
    reject_invalid: bool,
) -> dict[str, Any] | None:
    if not isinstance(raw, Mapping) or not isinstance(raw.get("skill"), Mapping):
        if reject_invalid:
            raise SkillMemoryError("SKILL_MEMORY_RECORD_INVALID:" + str(skill_id))
        return None
    verdict = reauthenticate_record(raw["skill"], repo_root=repo_root)
    skill = verdict.get("verified_skill")
    if verdict.get("pass") is not True or not isinstance(skill, Mapping):
        if reject_invalid or raw.get("active") is True:
            raise SkillMemoryError(
                "SKILL_MEMORY_REAUTHENTICATION_FAILED:" + str(skill_id)
            )
        return None
    sid = _skill_id(skill)
    family = _family_id(skill)
    if sid != str(skill_id):
        raise SkillMemoryError("SKILL_MEMORY_ID_MISMATCH:" + str(skill_id))
    stored_family = _s(raw.get("family_id"))
    if stored_family and stored_family != family:
        raise SkillMemoryError("SKILL_MEMORY_FAMILY_MISMATCH:" + str(skill_id))

    quarantined = raw.get("quarantined") is True
    out = {
        "skill": deepcopy(dict(skill)),
        "family_id": family,
        "pareto_metrics": _pareto_row(sid, skill),
        "active": raw.get("active") is True and not quarantined,
        "dominated_by": _s(raw.get("dominated_by")) or None,
        "compression": {
            "source_episode_count": len(_items(skill.get("source_episode_ids"))),
            "stored_program_step_count": len(list(skill.get("steps") or [])),
            "repeated_program_copies_eliminated": max(
                0, len(_items(skill.get("source_episode_ids"))) - 1
            ),
        },
    }
    if quarantined:
        out["quarantined"] = True
        out["quarantine_reason"] = (
            _s(raw.get("quarantine_reason"))
            or "VERIFIED_REUSE_ROUTE_COUNTEREXAMPLE"
        )
    scopes = _items(raw.get("generalization_counterexample_scopes"))
    if scopes:
        out["generalization_counterexample_scopes"] = scopes
    if raw.get("generalization_repromotion_blocked") is True:
        out["generalization_repromotion_blocked"] = True
    if raw.get("recovered_from_quarantine_by_scope_contraction") is True:
        out["recovered_from_quarantine_by_scope_contraction"] = True
    return out


def _frontiers(skills: Mapping[str, Any]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for sid, rec in skills.items():
        if not isinstance(rec, Mapping) or rec.get("active") is not True:
            continue
        family = _s(rec.get("family_id"))
        if not family:
            raise SkillMemoryError("ACTIVE_SKILL_FAMILY_MISSING:" + str(sid))
        out.setdefault(family, []).append(str(sid))
    return {k: sorted(set(v)) for k, v in sorted(out.items())}


def document_from_state(
    state: Mapping[str, Any], *, repo_root: str | Path
) -> dict[str, Any]:
    raw_skills = state.get("skills", {})
    if not isinstance(raw_skills, Mapping):
        raise SkillMemoryError("SOURCE_SKILLS_INVALID")
    skills: dict[str, Any] = {}
    for sid, raw in sorted(raw_skills.items(), key=lambda x: str(x[0])):
        rec = _record(str(sid), raw, repo_root=repo_root, reject_invalid=False)
        if rec is not None:
            skills[str(sid)] = rec
    body = {
        "schema": SCHEMA,
        "version": 1,
        "skills": skills,
        "pareto_frontiers": _frontiers(skills),
    }
    return {**body, "memory_sha256": _sha(body)}


def validate_document(
    doc: Mapping[str, Any], *, repo_root: str | Path
) -> dict[str, Any]:
    if not isinstance(doc, Mapping) or doc.get("schema") != SCHEMA:
        raise SkillMemoryError("SCHEMA_INVALID")
    if doc.get("version") != 1:
        raise SkillMemoryError("VERSION_INVALID")
    raw_skills = doc.get("skills")
    raw_frontiers = doc.get("pareto_frontiers")
    if not isinstance(raw_skills, Mapping) or not isinstance(raw_frontiers, Mapping):
        raise SkillMemoryError("SHAPE_INVALID")
    body = {
        "schema": SCHEMA,
        "version": 1,
        "skills": deepcopy(dict(raw_skills)),
        "pareto_frontiers": deepcopy(dict(raw_frontiers)),
    }
    if _s(doc.get("memory_sha256")) != _sha(body):
        raise SkillMemoryError("DIGEST_MISMATCH")

    skills: dict[str, Any] = {}
    for sid, raw in sorted(raw_skills.items(), key=lambda x: str(x[0])):
        rec = _record(str(sid), raw, repo_root=repo_root, reject_invalid=True)
        if rec is None or _canon(rec) != _canon(raw):
            raise SkillMemoryError("NONCANONICAL_RECORD:" + str(sid))
        skills[str(sid)] = rec
    expected = _frontiers(skills)
    normalized = {
        str(k): sorted({_s(x) for x in v if _s(x)})
        for k, v in raw_frontiers.items()
        if isinstance(v, Sequence) and not isinstance(v, (str, bytes))
    }
    if normalized != expected:
        raise SkillMemoryError("FRONTIER_MISMATCH")
    return {**body, "skills": skills, "pareto_frontiers": expected}


def merge_file(
    state: Mapping[str, Any],
    *,
    memory_path: str | Path,
    repo_root: str | Path,
) -> dict[str, Any]:
    merged = deepcopy(dict(state))
    p = Path(memory_path)
    if not p.exists():
        return merged
    memory = validate_document(
        json.loads(p.read_text(encoding="utf-8")),
        repo_root=repo_root,
    )
    skills = deepcopy(dict(memory["skills"]))
    local = merged.get("skills", {})
    if not isinstance(local, Mapping):
        raise SkillMemoryError("LOCAL_SKILLS_INVALID")
    for sid, raw in local.items():
        rec = _record(str(sid), raw, repo_root=repo_root, reject_invalid=False)
        if rec is not None:
            skills[str(sid)] = rec
    merged["skills"] = skills
    merged["pareto_frontiers"] = _frontiers(skills)
    return merged


def write_file(
    state: Mapping[str, Any],
    *,
    memory_path: str | Path,
    repo_root: str | Path,
) -> None:
    doc = document_from_state(state, repo_root=repo_root)
    payload = json.dumps(doc, indent=2, sort_keys=True) + "\n"
    p = Path(memory_path)
    if p.exists() and p.read_text(encoding="utf-8") == payload:
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(p)
