#!/usr/bin/env python3
"""Play 3 — Induction With an Abstain Option (`abstain_gated_skill_induction_v1`).

Implements Play 3 of `canonical/verification/FRONTIER_LEAPFROG_PLAN_20261125_V1.md`
(selective procedural abstraction with abstention as the admission gate) over a
deterministic 40-episode induction benchmark built from the 181 real OSS commits in
`canonical/corpus/single_line_fix_candidates_20261123_V1.json` (15 repositories).

Mechanism:
  - Each episode teaches on ONE real commit `(old_line -> new_line)` and induces a
    structural AST/skeleton transformation rule `(precondition_guard, transform_family)`.
  - Admission rule (the unusual move): a candidate skill is admitted ONLY if it
    explicitly abstains (`ABSTAIN_PRECONDITION_UNMET`) on EVERY stored negative
    (already-repaired code and safe neighbor lines across the bank).
  - Each episode then evaluates on THREE unseen test probes (120 probes total):
      1. Unseen in-family positive variant
      2. Unseen cross-repository / cross-family transfer candidate
      3. Unseen negative (repaired / safe code where firing is a wrong edit)
  - Compares Abstain-Gated Induction against an Ungated Similarity-Retrieval baseline.

Kill criterion (from `FRONTIER_LEAPFROG_PLAN_20261125_V1.md`):
  - `cross_family_transfer_hits == 0` AND `precision <= 0.50` with abstention.

Authority: NONE. Zero model calls (`K3 = 0`), `$0` spend, deterministic execution.
"""
from __future__ import annotations

import ast
import hashlib
import json
import pathlib
import sys
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.gradient_free_law_consolidation_v1 import (  # noqa: E402
    ast_alpha_skeleton,
    parse_single_line_stmt,
)

SCHEMA = "PROJECT_BRAIN_ABSTAIN_GATED_SKILL_INDUCTION_V1"
CANDIDATES_181_REL = "canonical/corpus/single_line_fix_candidates_20261123_V1.json"
HELDOUT_UNSEEN_REL = "canonical/corpus/heldout_unseen_repos_20261124_V1.json"
EPISODE_COUNT = 40
PRECISION_FLOOR = 0.50


def classify_structural_edit_family(old_line: str, new_line: str) -> dict[str, Any]:
    """Extract an AST-structural transformation family + negative-space guard."""
    old_stmt = parse_single_line_stmt(old_line)
    new_stmt = parse_single_line_stmt(new_line)
    if old_stmt is None or new_stmt is None:
        return {
            "family": "UNPARSED_TOKEN_FALLBACK",
            "precondition_head": old_line.strip().split()[0] if old_line.strip() else "EMPTY",
            "specific_guard": False,
            "old_skel": old_line.strip(),
            "new_skel": new_line.strip(),
        }

    old_skel = ast_alpha_skeleton(old_stmt)
    new_skel = ast_alpha_skeleton(new_stmt)
    old_type = type(old_stmt).__name__
    new_type = type(new_stmt).__name__

    # Family 1: Guard conjunction refinement: `if P:` -> `if P and Q:` (where old has no BoolOp And or fewer conjuncts)
    if isinstance(old_stmt, ast.If) and isinstance(new_stmt, ast.If):
        old_and = len(old_stmt.test.values) if isinstance(old_stmt.test, ast.BoolOp) and isinstance(old_stmt.test.op, ast.And) else 1
        new_and = len(new_stmt.test.values) if isinstance(new_stmt.test, ast.BoolOp) and isinstance(new_stmt.test.op, ast.And) else 1
        if new_and > old_and:
            test_kind = type(old_stmt.test).__name__
            return {
                "family": f"IF_GUARD_CONJUNCT_STRENGTHEN:{test_kind}:{old_and}_TO_{new_and}",
                "precondition_head": f"If:{test_kind}:and={old_and}",
                "specific_guard": True,
                "old_skel": old_skel,
                "new_skel": new_skel,
            }
        old_or = len(old_stmt.test.values) if isinstance(old_stmt.test, ast.BoolOp) and isinstance(old_stmt.test.op, ast.Or) else 1
        new_or = len(new_stmt.test.values) if isinstance(new_stmt.test, ast.BoolOp) and isinstance(new_stmt.test.op, ast.Or) else 1
        if new_or > old_or:
            test_kind = type(old_stmt.test).__name__
            return {
                "family": f"IF_GUARD_DISJUNCT_WIDEN:{test_kind}:{old_or}_TO_{new_or}",
                "precondition_head": f"If:{test_kind}:or={old_or}",
                "specific_guard": True,
                "old_skel": old_skel,
                "new_skel": new_skel,
            }

    # Family 2: Single inequality/equality widened to tuple membership (`x != a` -> `x not in (a, b)` or `x == a` -> `x in (a, b)`)
    old_cmps = [n for n in ast.walk(old_stmt) if isinstance(n, ast.Compare) and len(n.ops) == 1]
    new_cmps = [n for n in ast.walk(new_stmt) if isinstance(n, ast.Compare) and len(n.ops) == 1]
    if old_cmps and new_cmps:
        o_op = type(old_cmps[0].ops[0]).__name__
        n_op = type(new_cmps[0].ops[0]).__name__
        if (o_op, n_op) in (("Eq", "In"), ("NotEq", "NotIn")):
            return {
                "family": f"SCALAR_CMP_TO_MEMBERSHIP:{old_type}:{o_op}_TO_{n_op}",
                "precondition_head": f"{old_type}:Cmp:{o_op}",
                "specific_guard": True,
                "old_skel": old_skel,
                "new_skel": new_skel,
            }
        if o_op != n_op:
            return {
                "family": f"RELATIONAL_OP_REPAIR:{old_type}:{o_op}_TO_{n_op}",
                "precondition_head": f"{old_type}:Cmp:{o_op}",
                "specific_guard": True,
                "old_skel": old_skel,
                "new_skel": new_skel,
            }

    # Family 3: Unconditional expression wrapped in ternary conditional (`x = E` -> `x = E if C else D` or `return E` -> `return E if C else D`)
    old_has_ifexp = any(isinstance(n, ast.IfExp) for n in ast.walk(old_stmt))
    new_has_ifexp = any(isinstance(n, ast.IfExp) for n in ast.walk(new_stmt))
    if (not old_has_ifexp) and new_has_ifexp and old_type == new_type:
        return {
            "family": f"TERNARY_NONE_EMPTY_GUARD_WRAP:{old_type}",
            "precondition_head": f"{old_type}:no_ifexp:{old_skel[:36]}",
            "specific_guard": True,
            "old_skel": old_skel,
            "new_skel": new_skel,
        }

    # Family 4: Plain string literal upgraded to f-string diagnostic formatting
    old_has_fstr = any(isinstance(n, ast.JoinedStr) for n in ast.walk(old_stmt))
    new_has_fstr = any(isinstance(n, ast.JoinedStr) for n in ast.walk(new_stmt))
    if (not old_has_fstr) and new_has_fstr and old_type == new_type:
        return {
            "family": f"STATIC_STR_TO_FSTRING_DIAGNOSTIC:{old_type}",
            "precondition_head": f"{old_type}:plain_str_msg",
            "specific_guard": True,
            "old_skel": old_skel,
            "new_skel": new_skel,
        }

    # Family 5: Collection / wrapper constructor normalization (`x = f(...)` -> `x = tuple(f(...))` / `list(...)` / unwrap `cast(T, x) -> x`)
    if isinstance(old_stmt, (ast.Assign, ast.Return)) and type(old_stmt) is type(new_stmt):
        o_val = old_stmt.value
        n_val = new_stmt.value
        if isinstance(n_val, ast.Call) and isinstance(n_val.func, ast.Name) and n_val.func.id in ("tuple", "list", "set", "str", "bool", "int"):
            if not (isinstance(o_val, ast.Call) and isinstance(o_val.func, ast.Name) and o_val.func.id == n_val.func.id):
                return {
                    "family": f"COERCE_WRAPPER_CALL:{old_type}:{n_val.func.id}",
                    "precondition_head": f"{old_type}:unwrapped_for_{n_val.func.id}:{old_skel[:32]}",
                    "specific_guard": True,
                    "old_skel": old_skel,
                    "new_skel": new_skel,
                }
        if isinstance(o_val, ast.Call) and isinstance(o_val.func, ast.Name) and o_val.func.id == "cast" and not isinstance(n_val, ast.Call):
            return {
                "family": f"UNWRAP_TYPING_CAST:{old_type}",
                "precondition_head": f"{old_type}:cast_call",
                "specific_guard": True,
                "old_skel": old_skel,
                "new_skel": new_skel,
            }

    # Fallback: generic statement-head induction without a separating structural invariant.
    # An ungated similarity learner admits this and misfires on repaired code; the abstain gate catches it!
    return {
        "family": f"OVERBROAD_STMT_HEAD:{old_type}_TO_{new_type}",
        "precondition_head": f"BROAD_HEAD:{old_type}",
        "specific_guard": False,
        "old_skel": old_skel,
        "new_skel": new_skel,
    }


def probe_statement_features(line: str) -> dict[str, Any]:
    stmt = parse_single_line_stmt(line)
    if stmt is None:
        return {"parsed": False, "stmt_type": "UNPARSED", "skel": line.strip()}
    skel = ast_alpha_skeleton(stmt)
    stmt_type = type(stmt).__name__
    cmps = [n for n in ast.walk(stmt) if isinstance(n, ast.Compare) and len(n.ops) == 1]
    cmp_op = type(cmps[0].ops[0]).__name__ if cmps else None
    and_len = (
        len(stmt.test.values)
        if isinstance(stmt, ast.If) and isinstance(stmt.test, ast.BoolOp) and isinstance(stmt.test.op, ast.And)
        else (1 if isinstance(stmt, ast.If) else 0)
    )
    or_len = (
        len(stmt.test.values)
        if isinstance(stmt, ast.If) and isinstance(stmt.test, ast.BoolOp) and isinstance(stmt.test.op, ast.Or)
        else (1 if isinstance(stmt, ast.If) else 0)
    )
    if_test_kind = type(stmt.test).__name__ if isinstance(stmt, ast.If) else None
    has_ifexp = any(isinstance(n, ast.IfExp) for n in ast.walk(stmt))
    has_fstr = any(isinstance(n, ast.JoinedStr) for n in ast.walk(stmt))
    has_plain_str = any(isinstance(n, ast.Constant) and isinstance(n.value, str) for n in ast.walk(stmt))
    val = getattr(stmt, "value", None)
    top_call_name = (
        val.func.id
        if isinstance(val, ast.Call) and isinstance(val.func, ast.Name)
        else None
    )
    return {
        "parsed": True,
        "stmt_type": stmt_type,
        "skel": skel,
        "cmp_op": cmp_op,
        "and_len": and_len,
        "or_len": or_len,
        "if_test_kind": if_test_kind,
        "has_ifexp": has_ifexp,
        "has_fstr": has_fstr,
        "has_plain_str": has_plain_str,
        "top_call_name": top_call_name,
    }


@dataclass(frozen=True)
class InducedSkill:
    skill_id: str
    family: str
    source_repo: str
    source_commit: str
    old_skel: str
    new_skel: str
    specific_guard: bool


def skill_decision_on_line(skill: InducedSkill, line: str) -> tuple[str, str]:
    """Return `('FIRE', family)` or `('ABSTAIN', reason)` on a candidate code line."""
    feat = probe_statement_features(line)
    if not feat["parsed"]:
        return "ABSTAIN", "ABSTAIN_UNPARSED_INPUT"
    # Never fire if line already matches the post-fix skeleton!
    if feat["skel"] == skill.new_skel:
        return "ABSTAIN", "ABSTAIN_ALREADY_SATISFIES_POSTCONDITION"

    fam = skill.family
    if fam.startswith("IF_GUARD_CONJUNCT_STRENGTHEN:"):
        _, test_kind, counts = fam.split(":")
        expected_and = int(counts.split("_TO_")[0])
        if feat["stmt_type"] == "If" and feat["if_test_kind"] == test_kind and feat["and_len"] == expected_and:
            return "FIRE", fam
        return "ABSTAIN", "ABSTAIN_PRECONDITION_UNMET"

    if fam.startswith("IF_GUARD_DISJUNCT_WIDEN:"):
        _, test_kind, counts = fam.split(":")
        expected_or = int(counts.split("_TO_")[0])
        if feat["stmt_type"] == "If" and feat["if_test_kind"] == test_kind and feat["or_len"] == expected_or and feat["and_len"] == 1:
            return "FIRE", fam
        return "ABSTAIN", "ABSTAIN_PRECONDITION_UNMET"

    if fam.startswith("SCALAR_CMP_TO_MEMBERSHIP:") or fam.startswith("RELATIONAL_OP_REPAIR:"):
        _, stype, ops = fam.split(":")
        expected_op = ops.split("_TO_")[0]
        if feat["stmt_type"] == stype and feat["cmp_op"] == expected_op and feat["skel"] == skill.old_skel:
            return "FIRE", fam
        return "ABSTAIN", "ABSTAIN_PRECONDITION_UNMET"

    if fam.startswith("TERNARY_NONE_EMPTY_GUARD_WRAP:"):
        _, stype = fam.split(":")
        if feat["stmt_type"] == stype and (not feat["has_ifexp"]) and feat["skel"] == skill.old_skel:
            return "FIRE", fam
        return "ABSTAIN", "ABSTAIN_PRECONDITION_UNMET"

    if fam.startswith("STATIC_STR_TO_FSTRING_DIAGNOSTIC:"):
        _, stype = fam.split(":")
        if feat["stmt_type"] == stype and feat["has_plain_str"] and (not feat["has_fstr"]) and feat["skel"] == skill.old_skel:
            return "FIRE", fam
        return "ABSTAIN", "ABSTAIN_PRECONDITION_UNMET"

    if fam.startswith("COERCE_WRAPPER_CALL:"):
        _, stype, wrapper = fam.split(":")
        if feat["stmt_type"] == stype and feat["top_call_name"] != wrapper and feat["skel"] == skill.old_skel:
            return "FIRE", fam
        return "ABSTAIN", "ABSTAIN_PRECONDITION_UNMET"

    if fam.startswith("UNWRAP_TYPING_CAST:"):
        _, stype = fam.split(":")
        if feat["stmt_type"] == stype and feat["top_call_name"] == "cast":
            return "FIRE", fam
        return "ABSTAIN", "ABSTAIN_PRECONDITION_UNMET"

    # Overbroad fallback skill (matches any statement with the same AST head!)
    if fam.startswith("OVERBROAD_STMT_HEAD:"):
        expected_head = fam.split(":")[1].split("_TO_")[0]
        if feat["stmt_type"] == expected_head:
            return "FIRE", fam
    return "ABSTAIN", "ABSTAIN_PRECONDITION_UNMET"


def induce_skill_from_commit(idx: int, task: Mapping[str, Any]) -> InducedSkill:
    info = classify_structural_edit_family(str(task["old_line"]), str(task["new_line"]))
    sha = str(task.get("commit") or task.get("sha") or f"ep{idx}")[:10]
    return InducedSkill(
        skill_id=f"skill_{idx:02d}_{sha}",
        family=info["family"],
        source_repo=str(task.get("repo") or "unknown"),
        source_commit=sha,
        old_skel=info["old_skel"],
        new_skel=info["new_skel"],
        specific_guard=bool(info["specific_guard"]),
    )


def admit_with_abstain_gate(skill: InducedSkill, stored_negatives: Sequence[str]) -> dict[str, Any]:
    violations: list[int] = []
    for i, neg_line in enumerate(stored_negatives):
        decision, _reason = skill_decision_on_line(skill, neg_line)
        if decision != "ABSTAIN":
            violations.append(i)
    return {
        "admitted": len(violations) == 0,
        "stored_negatives_checked": len(stored_negatives),
        "negative_violations": len(violations),
        "rejection_reason": None if not violations else f"FIRED_ON_{len(violations)}_STORED_NEGATIVES",
    }


def run_40_episode_induction(root: str | pathlib.Path = ROOT) -> dict[str, Any]:
    repo_root = pathlib.Path(root).resolve()
    c181 = json.loads((repo_root / CANDIDATES_181_REL).read_text(encoding="utf-8"))["tasks"]
    h8 = json.loads((repo_root / HELDOUT_UNSEEN_REL).read_text(encoding="utf-8"))["tasks"]
    all_tasks = list(c181) + list(h8)

    # Annotate all parseable tasks with their structural family
    annotated: list[dict[str, Any]] = []
    for t in all_tasks:
        if parse_single_line_stmt(str(t["old_line"])) is None or parse_single_line_stmt(str(t["new_line"])) is None:
            continue
        info = classify_structural_edit_family(str(t["old_line"]), str(t["new_line"]))
        annotated.append({**t, "_family_info": info})

    # Group by structural family so we select a balanced 40-episode curriculum:
    # recurring specific families (enabling real cross-repo transfer checks) + overbroad traps!
    by_family: dict[str, list[dict[str, Any]]] = {}
    for item in annotated:
        by_family.setdefault(item["_family_info"]["family"], []).append(item)

    selected_episodes: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any], str]] = []
    specific_multi = sorted(
        [(fam, items) for fam, items in by_family.items() if items[0]["_family_info"]["specific_guard"] and len(items) >= 2],
        key=lambda kv: (-len(kv[1]), kv[0]),
    )
    specific_single = sorted(
        [(fam, items) for fam, items in by_family.items() if items[0]["_family_info"]["specific_guard"] and len(items) == 1],
        key=lambda kv: kv[0],
    )
    overbroad_groups = sorted(
        [(fam, items) for fam, items in by_family.items() if not items[0]["_family_info"]["specific_guard"]],
        key=lambda kv: (-len(kv[1]), kv[0]),
    )

    # Stored negative bank: 24 repaired (`new_line`) statements spanning diverse statement types
    stored_negatives = [str(item["new_line"]) for item in annotated[:24]]

    # Build 26 specific episodes + 14 overbroad episodes = 40 real-commit episodes!
    pool_order: list[tuple[str, list[dict[str, Any]]]] = []
    for fam, items in specific_multi:
        pool_order.append((fam, items))
    for fam, items in specific_single:
        pool_order.append((fam, items))

    ep_sources: list[tuple[str, dict[str, Any], list[dict[str, Any]]]] = []
    for fam, items in pool_order:
        for idx_in_fam, teach in enumerate(items):
            if len(ep_sources) >= 26:
                break
            peers = [x for j, x in enumerate(items) if j != idx_in_fam]
            ep_sources.append((fam, teach, peers))
        if len(ep_sources) >= 26:
            break

    for fam, items in overbroad_groups:
        for idx_in_fam, teach in enumerate(items):
            if len(ep_sources) >= EPISODE_COUNT:
                break
            peers = [x for j, x in enumerate(items) if j != idx_in_fam]
            ep_sources.append((fam, teach, peers))
        if len(ep_sources) >= EPISODE_COUNT:
            break

    for ep_idx, (_fam, teach, peers) in enumerate(ep_sources[:EPISODE_COUNT]):
        in_fam = peers[0] if peers else annotated[(ep_idx + 7) % len(annotated)]
        cross_repo_peers = [p for p in peers if p.get("repo") != teach.get("repo")]
        cross_target = (
            cross_repo_peers[0]
            if cross_repo_peers
            else next((a for a in annotated if a.get("repo") != teach.get("repo") and a["_family_info"]["family"] == _fam),
                      annotated[(ep_idx + 19) % len(annotated)])
        )
        unseen_neg = str(annotated[(ep_idx + 31) % len(annotated)]["new_line"])
        selected_episodes.append((teach, in_fam, cross_target, unseen_neg))

    # Evaluate BOTH Abstain-Gated Induction and Ungated Baseline across all 40 episodes (120 probes)
    admitted_count = 0
    rejected_on_negatives = 0

    gated_tp = 0
    gated_fp = 0
    gated_fn = 0
    gated_abstain_on_unseen_neg = 0
    cross_repo_transfer_hits = 0
    cross_repo_transfer_opportunities = 0

    ungated_tp = 0
    ungated_fp = 0

    for ep_idx, (teach, in_fam, cross_target, unseen_neg) in enumerate(selected_episodes):
        skill = induce_skill_from_commit(ep_idx, teach)
        gate = admit_with_abstain_gate(skill, [str(teach["new_line"]), *stored_negatives])
        admitted = gate["admitted"]
        if admitted:
            admitted_count += 1
        else:
            rejected_on_negatives += 1

        in_fam_same_true_class = (
            in_fam["_family_info"]["specific_guard"]
            and in_fam["_family_info"]["family"] == skill.family
        )
        cross_is_diff_repo = cross_target.get("repo") != teach.get("repo")
        cross_same_true_class = (
            cross_is_diff_repo
            and cross_target["_family_info"]["specific_guard"]
            and cross_target["_family_info"]["family"] == skill.family
        )
        if cross_is_diff_repo:
            cross_repo_transfer_opportunities += 1

        # Probe 1: in-family variant
        d1, _ = skill_decision_on_line(skill, str(in_fam["old_line"]))
        if d1 == "FIRE":
            if in_fam_same_true_class:
                ungated_tp += 1
            else:
                ungated_fp += 1
        if admitted and d1 == "FIRE":
            if in_fam_same_true_class:
                gated_tp += 1
            else:
                gated_fp += 1
        elif in_fam_same_true_class:
            gated_fn += 1

        # Probe 2: cross-repository transfer variant
        d2, _ = skill_decision_on_line(skill, str(cross_target["old_line"]))
        if d2 == "FIRE":
            if cross_same_true_class:
                ungated_tp += 1
            else:
                ungated_fp += 1
        if admitted and d2 == "FIRE":
            if cross_same_true_class:
                gated_tp += 1
                cross_repo_transfer_hits += 1
            else:
                gated_fp += 1
        elif cross_same_true_class:
            gated_fn += 1

        # Probe 3: unseen negative (repaired line — firing is ALWAYS a false positive!)
        d3, _ = skill_decision_on_line(skill, unseen_neg)
        if d3 == "FIRE":
            ungated_fp += 1
        if (not admitted) or d3 == "ABSTAIN":
            gated_abstain_on_unseen_neg += 1
        else:
            gated_fp += 1

    gated_precision = round(gated_tp / max(gated_tp + gated_fp, 1), 4)
    gated_recall = round(gated_tp / max(gated_tp + gated_fn, 1), 4)
    ungated_precision = round(ungated_tp / max(ungated_tp + ungated_fp, 1), 4)
    unseen_neg_refusal_rate = round(gated_abstain_on_unseen_neg / max(len(selected_episodes), 1), 4)

    kill_triggered = (cross_repo_transfer_hits == 0) and (gated_precision <= PRECISION_FLOOR)

    summary_digest = hashlib.sha256(
        json.dumps(
            {
                "episodes": len(selected_episodes),
                "admitted": admitted_count,
                "tp": gated_tp,
                "fp": gated_fp,
                "transfer": cross_repo_transfer_hits,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    return {
        "schema": SCHEMA,
        "play_id": "PLAY_3_ABSTAIN_GATED_SKILL_INDUCTION",
        "status": "KILLED" if kill_triggered else "ESTABLISHED_ON_40_EPISODE_REAL_COMMIT_SET",
        "output_verified": not kill_triggered,
        "corpus_sources": [CANDIDATES_181_REL, HELDOUT_UNSEEN_REL],
        "episodes_total": len(selected_episodes),
        "test_probes_total": len(selected_episodes) * 3,
        "skills_admitted": admitted_count,
        "skills_rejected_by_abstain_gate": rejected_on_negatives,
        "precision": gated_precision,
        "recall": gated_recall,
        "ungated_baseline_precision": ungated_precision,
        "precision_lift_over_ungated": round(gated_precision - ungated_precision, 4),
        "unseen_negative_refusal_rate": unseen_neg_refusal_rate,
        "cross_family_transfer_hits": cross_repo_transfer_hits,
        "cross_family_transfer_opportunities": cross_repo_transfer_opportunities,
        "prior_literal_baseline_transfer": "0/36",
        "true_positives": gated_tp,
        "false_positives": gated_fp,
        "false_negatives": gated_fn,
        "kill_criterion": {
            "min_precision_if_zero_transfer": PRECISION_FLOOR,
            "kill_if_zero_transfer_and_low_precision": True,
            "kill_triggered": kill_triggered,
        },
        "summary_sha256": summary_digest,
        "model_dependency_count": 0,
    }


def run(args: Mapping[str, Any] | None, root: str | pathlib.Path = ROOT) -> dict[str, Any]:
    req = dict(args or {})
    if req.get("action") == "induce_single" and isinstance(req.get("task"), Mapping):
        skill = induce_skill_from_commit(0, req["task"])
        negs = list(req.get("stored_negatives") or [str(req["task"].get("new_line") or "")])
        gate = admit_with_abstain_gate(skill, negs)
        return {
            "schema": SCHEMA,
            "status": "ADMITTED" if gate["admitted"] else "REFUSED_BY_ABSTAIN_GATE",
            "output_verified": True,
            "skill_family": skill.family,
            "gate": gate,
        }
    return run_40_episode_induction(root)


if __name__ == "__main__":
    print(json.dumps(run({}, ROOT), indent=2, sort_keys=True))
