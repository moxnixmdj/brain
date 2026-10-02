"""Exact target-literal to witness-source crosswalk.

Discovery only. This module searches frozen target source literals inside only the
content-addressed source files explicitly declared by each normalized Brain witness.

A literal hit is a candidate pointer, not semantic proof. This module never infers
atom equivalence, metric equivalence, scope coverage, acceptance, capability, family,
execution, or promotion credit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TYPED_WITNESS_TARGET_LITERAL_CROSSWALK_V1"
ROOT = Path(__file__).resolve().parents[2]


def _blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "target_count": 0,
        "witness_count": 0,
        "pair_count": 0,
        "pairs_with_literal_hits": 0,
        "pairs": [],
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def _target_literals(target: Mapping[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for atom_row in target.get("atom_sources", []):
        if not isinstance(atom_row, Mapping):
            continue
        atom = atom_row.get("atom")
        if not isinstance(atom, str) or not atom:
            continue
        for src in atom_row.get("sources", []):
            if isinstance(src, Mapping) and isinstance(src.get("literal"), str) and src["literal"]:
                rows.append({"kind": "ATOM", "name": atom, "literal": src["literal"]})
    for metric_row in target.get("metric_requirement_sources", []):
        if not isinstance(metric_row, Mapping):
            continue
        metric = metric_row.get("metric")
        if not isinstance(metric, str) or not metric:
            continue
        for src in metric_row.get("sources", []):
            if isinstance(src, Mapping) and isinstance(src.get("literal"), str) and src["literal"]:
                rows.append({"kind": "METRIC", "name": metric, "literal": src["literal"]})

    unique: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in rows:
        unique[(row["kind"], row["name"], row["literal"])] = row
    return [unique[k] for k in sorted(unique)]


def _witness_sources(witness: Mapping[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    p = witness.get("source_path")
    sha = witness.get("source_sha")
    if isinstance(p, str) and p and isinstance(sha, str) and sha:
        rows.append({"path": p, "git_blob_sha": sha, "role": "PRIMARY"})
    for src in witness.get("supporting_sources", []):
        if not isinstance(src, Mapping):
            continue
        p = src.get("path")
        sha = src.get("sha")
        if isinstance(p, str) and p and isinstance(sha, str) and sha:
            rows.append({"path": p, "git_blob_sha": sha, "role": "SUPPORTING"})

    unique: dict[str, dict[str, str]] = {}
    for row in rows:
        prior = unique.get(row["path"])
        if prior is not None and prior["git_blob_sha"] != row["git_blob_sha"]:
            raise ValueError(f"WITNESS_SOURCE_SHA_CONFLICT:{row['path']}")
        unique[row["path"]] = row
    return [unique[k] for k in sorted(unique)]


def build_crosswalk(
    target_doc: Mapping[str, Any],
    witness_doc: Mapping[str, Any],
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    targets = target_doc.get("targets")
    witnesses = witness_doc.get("witnesses")
    if not isinstance(targets, list) or not targets:
        return _fail("TARGETS_INVALID")
    if not isinstance(witnesses, list) or not witnesses:
        return _fail("WITNESSES_INVALID")

    errors: list[str] = []
    normalized_targets: list[tuple[str, list[dict[str, str]]]] = []
    for i, target in enumerate(targets):
        if not isinstance(target, Mapping):
            errors.append(f"TARGET_{i}_INVALID")
            continue
        pid = target.get("predicate_id")
        if not isinstance(pid, str) or not pid:
            errors.append(f"TARGET_{i}_PREDICATE_ID_INVALID")
            continue
        literals = _target_literals(target)
        if not literals:
            errors.append(f"TARGET_NO_SOURCE_LITERALS:{pid}")
            continue
        normalized_targets.append((pid, literals))

    normalized_witnesses: list[tuple[str, list[dict[str, str]], list[dict[str, Any]]]] = []
    for i, witness in enumerate(witnesses):
        if not isinstance(witness, Mapping):
            errors.append(f"WITNESS_{i}_INVALID")
            continue
        wid = witness.get("witness_id")
        if not isinstance(wid, str) or not wid:
            errors.append(f"WITNESS_{i}_ID_INVALID")
            continue
        if witness.get("independent_or_objective") is not True:
            errors.append(f"WITNESS_NOT_INDEPENDENT_OR_OBJECTIVE:{wid}")
            continue
        try:
            refs = _witness_sources(witness)
        except ValueError as e:
            errors.append(str(e))
            continue
        if not refs:
            errors.append(f"WITNESS_NO_CONTENT_ADDRESSED_SOURCES:{wid}")
            continue

        loaded: list[dict[str, Any]] = []
        for ref in refs:
            path = root / ref["path"]
            if not path.exists() or not path.is_file():
                errors.append(f"WITNESS_SOURCE_MISSING:{wid}:{ref['path']}")
                continue
            try:
                data = path.read_bytes()
                text = data.decode("utf-8")
            except (OSError, UnicodeDecodeError):
                errors.append(f"WITNESS_SOURCE_UNREADABLE:{wid}:{ref['path']}")
                continue
            actual = _blob_sha(data)
            if actual != ref["git_blob_sha"]:
                errors.append(f"WITNESS_SOURCE_BLOB_MISMATCH:{wid}:{ref['path']}")
                continue
            loaded.append({
                "path": ref["path"],
                "git_blob_sha": actual,
                "role": ref["role"],
                "text": text,
            })
        if len(loaded) != len(refs):
            continue
        normalized_witnesses.append((wid, refs, loaded))

    if errors:
        return _fail(*errors)

    pairs: list[dict[str, Any]] = []
    pairs_with_hits = 0
    literal_hit_total = 0

    for pid, literals in normalized_targets:
        for wid, refs, loaded in normalized_witnesses:
            hits: list[dict[str, Any]] = []
            hit_keys: set[tuple[str, str, str]] = set()
            atom_names_hit: set[str] = set()
            metric_names_hit: set[str] = set()

            for literal_row in literals:
                literal = literal_row["literal"]
                for source in loaded:
                    line_numbers = [
                        n for n, line in enumerate(source["text"].splitlines(), start=1)
                        if literal in line
                    ]
                    if not line_numbers:
                        continue
                    key = (literal_row["kind"], literal_row["name"], literal)
                    hit_keys.add(key)
                    if literal_row["kind"] == "ATOM":
                        atom_names_hit.add(literal_row["name"])
                    else:
                        metric_names_hit.add(literal_row["name"])
                    hits.append({
                        "kind": literal_row["kind"],
                        "name": literal_row["name"],
                        "literal": literal,
                        "path": source["path"],
                        "git_blob_sha": source["git_blob_sha"],
                        "source_role": source["role"],
                        "line_numbers": line_numbers[:16],
                    })

            distinct_literal_count = len({
                (x["kind"], x["name"], x["literal"]) for x in literals
            })
            exact_literal_hit_count = len(hit_keys)
            if exact_literal_hit_count:
                pairs_with_hits += 1
                literal_hit_total += exact_literal_hit_count

            pairs.append({
                "target_predicate_id": pid,
                "witness_id": wid,
                "target_source_literal_count": distinct_literal_count,
                "exact_target_literal_hit_count": exact_literal_hit_count,
                "target_literal_coverage_fraction": (
                    exact_literal_hit_count / distinct_literal_count
                    if distinct_literal_count else 0.0
                ),
                "atom_names_with_exact_literal_hits": sorted(atom_names_hit),
                "metric_names_with_exact_literal_hits": sorted(metric_names_hit),
                "candidate_hits": sorted(
                    hits,
                    key=lambda x: (x["kind"], x["name"], x["literal"], x["path"])
                ),
                "candidate_only": True,
                "semantic_binding_verified": False,
                "scope_relation_verified": False,
            })

    pairs.sort(key=lambda x: (
        -x["exact_target_literal_hit_count"],
        x["target_predicate_id"],
        x["witness_id"],
    ))

    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_TARGET_LITERAL_WITNESS_SOURCE_CROSSWALK_COMPUTED__ZERO_CREDIT",
        "errors": [],
        "target_count": len(normalized_targets),
        "witness_count": len(normalized_witnesses),
        "pair_count": len(pairs),
        "pairs_with_literal_hits": pairs_with_hits,
        "pairs_without_literal_hits": len(pairs) - pairs_with_hits,
        "distinct_literal_hits_across_pairs": literal_hit_total,
        "pairs": pairs,
        "rule": (
            "SEARCH_ONLY_EXACT_FROZEN_TARGET_SOURCE_LITERALS_INSIDE_DECLARED_CONTENT_ADDRESSED_WITNESS_SOURCES__"
            "LITERAL_HIT_IS_CANDIDATE_POINTER_ONLY__"
            "NO_SEMANTIC_EQUIVALENCE_METRIC_EQUIVALENCE_SCOPE_RELATION_ACCEPTANCE_CAPABILITY_FAMILY_EXECUTION_OR_PROMOTION_CREDIT"
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    target_doc = json.loads(
        (ROOT / "canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V1.json").read_text(
            encoding="utf-8"
        )
    )
    witness_doc = json.loads(
        (ROOT / "canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json").read_text(
            encoding="utf-8"
        )
    )
    out = build_crosswalk(target_doc, witness_doc)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if str(out.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
