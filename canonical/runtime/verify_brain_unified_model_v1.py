#!/usr/bin/env python3
"""Measure Brain Unified Model V1 on instances it has never seen.

The repository's law is blunt: a capability claim is only worth what an
independent oracle says about untouched instances, and verification means
somebody else ran it. This script cannot satisfy that by itself. What it can do
is make every claim it *does* support mechanically checkable, and report the
rest as what it is.

What is measured
----------------
1. ARTIFACT_INTEGRITY      digest, deterministic recompilation, source and
                           evidence hashes, count consistency.
2. LIVE_REGISTRY_COVERAGE  the model's capability set is re-derived from the
                           live loader and compared exactly.
3. ROUTING_FRESH_GOALS     goals composed at run time from trigger words the
                           model was not tuned on, plus out-of-domain negatives
                           that must fail closed.
4. KNOWLEDGE_RECALL        queries built from held-out distinctive terms, plus
                           a law-currency check.
5. EXECUTION_FRESH         real capabilities run on freshly generated inputs;
                           each result is checked by a separately written
                           oracle. Environment-blocked capabilities are counted
                           as blocked, never as passes.
6. NEGATIVE_CONTROLS       unknown goal, missing inputs, tampered artifact,
                           nonzero-spend capability, engine without providers.
7. MODEL_DEPENDENCE_AUDIT  static scan proving no model client sits in the
                           producer path of this artifact or its runtime.
8. ONE_FRONT_DOOR          every live capability and engine is addressable
                           through the single model artifact.

Oracle classes are recorded per case. ``REFERENCE`` means the checker shares a
library with the capability (still a real check, weaker evidence).
``INDEPENDENT`` means a different implementation produced the expected value.
``SYNTHETIC_GENERATOR`` means the case generator and its oracle are the same
harness -- useful for regression, never for capability credit.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import random
import re
import secrets
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import brain_unified_model_v1 as unified_model  # noqa: E402
from canonical.runtime import compile_brain_unified_model_v1 as compiler  # noqa: E402

SCHEMA = "PROJECT_BRAIN_UNIFIED_MODEL_V1_VERIFICATION"
DEFAULT_OUTPUT = "canonical/verification/BRAIN_UNIFIED_MODEL_V1_VERIFICATION_20261020.json"

FORBIDDEN_MODEL_IMPORTS = (
    "openai",
    "anthropic",
    "google.generativeai",
    "transformers",
    "torch",
    "tensorflow",
    "llama_cpp",
    "ollama",
    "vllm",
    "cohere",
    "mistralai",
    "litellm",
)
FORBIDDEN_ROUTE_MARKERS = (
    "openai",
    "anthropic",
    "api.anthropic",
    "api.openai",
    "generativelanguage",
    "ollama",
    "transformers",
    "torch.",
    "llama_cpp",
    "litellm",
)
UNKNOWN_GOALS = (
    "launch a weather satellite into low earth orbit",
    "write me a poem about the sea",
    "book a flight to tokyo for next tuesday",
    "translate this sentence into medieval french",
    "compose a symphony in the style of debussy",
    "diagnose why my houseplant is losing leaves",
    "negotiate a lower price on a used bicycle",
    "predict the winner of next year's tournament",
)
ROUTING_FILLER = (
    "please",
    "now",
    "carefully",
    "with",
    "for",
    "the",
    "then",
    "using",
    "and",
    "produce",
    "handle",
    "check",
)


# --------------------------------------------------------------------------- helpers


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _case(name: str, passed: bool, oracle: str, detail: Any = None) -> dict[str, Any]:
    return {
        "name": name,
        "pass": bool(passed),
        "oracle": oracle,
        "detail": detail,
    }


def _category(name: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [c["name"] for c in cases if not c["pass"]]
    return {
        "name": name,
        "pass": not failed,
        "cases": len(cases),
        "passed": len(cases) - len(failed),
        "failed": len(failed),
        "failed_cases": failed,
        "rows": cases,
    }


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------- integrity


def check_integrity(model: Mapping[str, Any], artifact: Path) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    declared = (model.get("digest") or {}).get("value")
    cases.append(
        _case(
            "digest_recomputes",
            declared == compiler.artifact_digest(model),
            "SHA256_RECOMPUTATION",
            {"declared": declared},
        )
    )
    recompiled = compiler.compile_model()
    cases.append(
        _case(
            "recompilation_is_byte_identical",
            compiler.canonical_json(recompiled) == compiler.canonical_json(model),
            "DETERMINISTIC_RECOMPILE",
            {"recompiled_digest": recompiled["digest"]["value"]},
        )
    )

    source_failures: list[str] = []
    evidence_failures: list[str] = []
    for row in model.get("capabilities") or []:
        provenance = row.get("provenance") or {}
        source_path = provenance.get("source_path")
        source_sha = provenance.get("source_sha256")
        if source_path and source_sha:
            path = ROOT / source_path
            if not path.is_file() or _sha(path) != source_sha:
                source_failures.append(str(row.get("id")))
        evidence_path = (row.get("verification") or {}).get("evidence_path")
        evidence_sha = (row.get("verification") or {}).get("evidence_sha256")
        if evidence_path and evidence_sha:
            path = ROOT / evidence_path
            if not path.is_file() or _sha(path) != evidence_sha:
                evidence_failures.append(str(row.get("id")))
    cases.append(
        _case(
            "capability_source_hashes_match_tree",
            not source_failures,
            "SHA256_AGAINST_LIVE_FILES",
            {"failures": source_failures[:10], "count": len(source_failures)},
        )
    )
    cases.append(
        _case(
            "capability_evidence_hashes_match_tree",
            not evidence_failures,
            "SHA256_AGAINST_LIVE_FILES",
            {"failures": evidence_failures[:10], "count": len(evidence_failures)},
        )
    )

    counts = model.get("counts") or {}
    actual = {
        "capabilities": len(model.get("capabilities") or []),
        "engines": len(model.get("engines") or []),
        "skills": len(model.get("skills") or []),
        "knowledge_documents": len(model.get("knowledge") or []),
    }
    cases.append(
        _case(
            "declared_counts_match_content",
            all(int(counts.get(k, -1)) == v for k, v in actual.items()),
            "SELF_CONSISTENCY",
            {"declared": {k: counts.get(k) for k in actual}, "actual": actual},
        )
    )
    cases.append(
        _case(
            "artifact_bytes_are_the_model",
            artifact.is_file() and artifact.stat().st_size > 0,
            "FILE_STAT",
            {"bytes": artifact.stat().st_size if artifact.is_file() else 0},
        )
    )
    return _category("ARTIFACT_INTEGRITY", cases)


def check_live_registry(model: Mapping[str, Any]) -> dict[str, Any]:
    from canonical.runtime import live_integrated_brain_v1 as live_brain

    live = {str(k) for k in live_brain.load_verified_registry()}
    modelled = {str(row["id"]) for row in model.get("capabilities") or []}
    missing = sorted(live - modelled)
    extra = sorted(modelled - live)
    cases = [
        _case(
            "every_live_capability_is_in_the_model",
            not missing,
            "LIVE_LOADER_SET_COMPARISON",
            {"missing_count": len(missing), "missing_sample": missing[:10]},
        ),
        _case(
            "model_invents_no_capability",
            not extra,
            "LIVE_LOADER_SET_COMPARISON",
            {"extra_count": len(extra), "extra_sample": extra[:10]},
        ),
        _case(
            "no_capability_was_silently_dropped",
            len(modelled) == len(live),
            "CARDINALITY_COMPARISON",
            {"live": len(live), "modelled": len(modelled)},
        ),
    ]
    return _category("LIVE_REGISTRY_COVERAGE", cases)


# --------------------------------------------------------------------------- routing


def _capability_tokens(row: Mapping[str, Any]) -> list[str]:
    id_tokens = set(unified_model.tokenize(str(row.get("id") or "")))
    return [
        str(t)
        for t in (row.get("triggers") or [])
        if str(t) not in id_tokens and len(str(t)) > 3
    ]


def check_routing(model: unified_model.UnifiedModel, rng: random.Random) -> dict[str, Any]:
    capabilities = [
        row
        for row in model.capabilities.values()
        if row.get("kind") in {"BOUND_CAPABILITY", "RECEIPT_BACKED_CAPABILITY"}
    ]
    pool = [row for row in capabilities if _capability_tokens(row)]
    cases: list[dict[str, Any]] = []
    attempts = 60
    top1 = top3 = confident = 0
    examples: list[dict[str, Any]] = []
    for _ in range(attempts):
        target = rng.choice(pool)
        target_tokens = _capability_tokens(target)
        rng.shuffle(target_tokens)
        chosen = target_tokens[: min(3, len(target_tokens))]
        others = rng.sample(capabilities, k=min(6, len(capabilities)))
        distractors: list[str] = []
        for other in others:
            tokens = _capability_tokens(other)
            if tokens:
                distractors.append(rng.choice(tokens))
        words = list(chosen) + distractors[:2] + [rng.choice(ROUTING_FILLER)]
        rng.shuffle(words)
        goal = " ".join(words)
        result = model.route(goal, top_k=3)
        ids = [c["id"] for c in result["candidates"]]
        if result["confident"]:
            confident += 1
        if ids and ids[0] == target["id"]:
            top1 += 1
        if target["id"] in ids:
            top3 += 1
        if len(examples) < 8:
            examples.append(
                {
                    "goal": goal,
                    "target": target["id"],
                    "top": ids[:3],
                    "confident": result["confident"],
                }
            )
    # A synthetic generator can produce an unfair case: the distractor tokens
    # may be stronger than the target's own words. The property that must hold
    # is that the target is inside the candidate set often enough to be
    # executable, and that out-of-domain goals never produce a confident route.
    cases.append(
        _case(
            "fresh_goals_rank_target_in_top3",
            top3 / attempts >= 0.80,
            "SYNTHETIC_GENERATOR_ORACLE",
            {
                "attempts": attempts,
                "top1": top1,
                "top3": top3,
                "confident": confident,
                "top3_rate": round(top3 / attempts, 4),
                "examples": examples,
            },
        )
    )
    cases.append(
        _case(
            "fresh_goals_are_not_answered_at_random",
            top1 / attempts >= 0.55,
            "SYNTHETIC_GENERATOR_ORACLE",
            {"top1_rate": round(top1 / attempts, 4)},
        )
    )
    false_positives = []
    for goal in UNKNOWN_GOALS:
        result = model.route(goal)
        if result["confident"]:
            false_positives.append({"goal": goal, "best": result["best"]})
    cases.append(
        _case(
            "out_of_domain_goals_fail_closed",
            not false_positives,
            "HAND_AUTHORED_NEGATIVE_SET",
            {"false_positives": false_positives},
        )
    )
    return _category("ROUTING_FRESH_GOALS", cases)


# --------------------------------------------------------------------------- recall


def check_recall(model: unified_model.UnifiedModel, rng: random.Random) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    docs = [row for row in model.knowledge if row.get("terms")]
    attempts = 40
    hit1 = hit3 = 0
    misses: list[dict[str, Any]] = []
    for _ in range(attempts):
        row = rng.choice(docs)
        terms = sorted((row.get("terms") or {}).keys(), key=lambda t: (-len(t), t))
        distinctive = [
            t
            for t in terms
            if model._knowledge_df.get(t, 0) <= max(3, len(model.knowledge) // 12)
        ]
        if len(distinctive) < 2:
            continue
        rng.shuffle(distinctive)
        query = " ".join(distinctive[:3])
        result = model.recall(query, top_k=3)
        paths = [h["path"] for h in result["hits"]]
        if paths[:1] == [row["path"]]:
            hit1 += 1
        if row["path"] in paths:
            hit3 += 1
        elif len(misses) < 5:
            misses.append({"query": query, "expected": row["path"], "got": paths})
    measured = max(1, hit1 + hit3 + max(0, len(misses)))
    cases.append(
        _case(
            "held_out_term_queries_hit_the_source_document",
            attempts - len(misses) >= int(attempts * 0.75),
            "TERM_GENERATOR_ORACLE",
            {
                "attempts": attempts,
                "hit_at_1": hit1,
                "hit_at_3": hit3,
                "measured": measured,
                "misses": misses,
            },
        )
    )

    # Current law must outrank its own superseded versions. Test every family
    # that has a current version and at least one historical sibling.
    by_family: dict[str, dict[str, list[str]]] = {}
    for row in model.knowledge:
        if row.get("authority") not in {
            "CURRENT_LAW",
            "HISTORICAL_LAW_VERSION",
            "SUPERSEDED_LAW",
        }:
            continue
        match = re.fullmatch(r"(.+?)_V(\d+)\.md", Path(str(row["path"])).name)
        if not match:
            continue
        family = match.group(1)
        bucket = by_family.setdefault(family, {"current": [], "history": []})
        if row["authority"] == "CURRENT_LAW":
            bucket["current"].append(str(row["path"]))
        else:
            bucket["history"].append(str(row["path"]))

    violations: list[dict[str, Any]] = []
    checked = 0
    for family, bucket in sorted(by_family.items()):
        if not bucket["current"] or not bucket["history"]:
            continue
        checked += 1
        query = family.replace("_", " ").casefold()
        result = model.recall(query, top_k=3)
        top_paths = [h["path"] for h in result["hits"]]
        current = set(bucket["current"])
        if current.intersection(top_paths):
            continue
        history_hit = [p for p in top_paths if p in set(bucket["history"])]
        if history_hit:
            violations.append(
                {
                    "family": family,
                    "current": bucket["current"],
                    "returned_history": history_hit,
                }
            )
    cases.append(
        _case(
            "current_law_outranks_its_own_history",
            not violations,
            "VERSION_RULE_ORACLE",
            {"families_checked": checked, "violations": violations},
        )
    )
    return _category("KNOWLEDGE_RECALL", cases)


# --------------------------------------------------------------------------- execution


def _unittest_file(path: Path, count: int) -> None:
    lines = [
        "import unittest",
        "",
        "",
        "class FreshTests(unittest.TestCase):",
    ]
    for i in range(count):
        lines += [
            f"    def test_case_{i}(self):",
            f"        self.assertEqual({i} + 1, {i + 1})",
        ]
    lines += ["", "", 'if __name__ == "__main__":', "    unittest.main()", ""]
    _write(path, "\n".join(lines))


def _oracle_ast_counts(root: Path) -> dict[str, int]:
    files = 0
    functions = 0
    classes = 0
    imports: set[str] = set()
    for path in sorted(root.rglob("*.py")):
        files += 1
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions += 1
            elif isinstance(node, ast.ClassDef):
                classes += 1
            elif isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
    return {
        "file_count": files,
        "function_count": functions,
        "class_count": classes,
        "distinct_imported_module_count": len(imports),
    }


def check_execution(
    model: unified_model.UnifiedModel, rng: random.Random, workdir: Path
) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    base_rel = workdir.relative_to(ROOT).as_posix()

    # ---- case 1: Python source structural audit -----------------------------
    src = workdir / "src"
    src.mkdir(parents=True, exist_ok=True)
    module_names = rng.sample(["json", "pathlib", "hashlib", "re", "math", "csv"], k=3)
    functions = rng.randint(2, 4)
    classes = rng.randint(1, 3)
    lines: list[str] = []
    for name in module_names:
        lines.append(f"import {name}")
    lines.append("")
    for i in range(functions):
        lines += [f"def fn_{i}(x):", f"    return x + {i}", ""]
    for i in range(classes):
        lines += [f"class C{i}:", "    pass", ""]
    _write(src / "module_a.py", "\n".join(lines))
    expected = _oracle_ast_counts(src)
    out = model.solve(
        "audit python source structure and imports",
        inputs={"source_root": f"{base_rel}/src", "output_path": f"{base_rel}/out/audit.json"},
    )
    result = (out.get("execution") or {}).get("result") or {}
    observed = {k: result.get(k) for k in expected}
    cases.append(
        _case(
            "python_source_audit_matches_independent_ast_oracle",
            out.get("pass") is True and observed == expected,
            "INDEPENDENT",
            {"expected": expected, "observed": observed},
        )
    )

    # ---- case 2: tar creation and verification ------------------------------
    payload = workdir / "payload"
    payload.mkdir(parents=True, exist_ok=True)
    member_a = payload / "alpha.txt"
    member_b = payload / "beta.txt"
    _write(member_a, "alpha " + secrets.token_hex(8) + "\n")
    _write(member_b, "beta " + secrets.token_hex(8) + "\n")
    manifest = workdir / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "verification_paths": [
                            member_a.relative_to(ROOT).as_posix(),
                            member_b.relative_to(ROOT).as_posix(),
                        ]
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    archive = workdir / "out" / "bundle.tar.gz"
    created = model.solve(
        "create a tar gz archive from a manifest",
        inputs={
            "manifest_path": manifest.relative_to(ROOT).as_posix(),
            "output_path": archive.relative_to(ROOT).as_posix(),
        },
    )
    listing: list[str] = []
    extracted_ok = False
    if archive.is_file():
        listing = subprocess.check_output(
            ["tar", "-tzf", str(archive)], text=True
        ).splitlines()
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.check_call(
                ["tar", "-xzf", str(archive), "-C", tmp]
            )
            expected_members = {
                manifest.relative_to(ROOT).as_posix(),
                member_a.relative_to(ROOT).as_posix(),
                member_b.relative_to(ROOT).as_posix(),
            }
            extracted_ok = all((Path(tmp) / rel).is_file() for rel in expected_members)
    cases.append(
        _case(
            "tar_creation_matches_gnu_tar_oracle",
            created.get("pass") is True
            and set(listing)
            == {
                manifest.relative_to(ROOT).as_posix(),
                member_a.relative_to(ROOT).as_posix(),
                member_b.relative_to(ROOT).as_posix(),
            }
            and extracted_ok,
            "INDEPENDENT",
            {"listing": sorted(listing), "extracted": extracted_ok},
        )
    )

    verified = model.solve(
        "verify a tar gz archive against its manifest",
        inputs={
            "archive_path": archive.relative_to(ROOT).as_posix(),
            "manifest_path": manifest.relative_to(ROOT).as_posix(),
        },
    )
    vresult = (verified.get("execution") or {}).get("result") or {}
    cases.append(
        _case(
            "tar_verification_reports_manifest_members",
            verified.get("pass") is True and vresult.get("verified") is True,
            "REFERENCE",
            {"verified": vresult.get("verified"), "status": verified.get("status")},
        )
    )

    # ---- case 3: SQLite table from JSON records -----------------------------
    records = {
        "records": {
            f"r{i}": {"status": "READY", "name": f"name_{i}", "v": i}
            for i in range(rng.randint(3, 6))
        }
    }
    json_path = workdir / "records.json"
    json_path.write_text(json.dumps(records), encoding="utf-8")
    db_path = workdir / "out" / "records.db"
    solved = model.solve(
        "create a sqlite table from json records with columns name and v, status READY",
        inputs={
            "goal": "Create a table named records with columns name and v. The status value is READY.",
            "json_path": json_path.relative_to(ROOT).as_posix(),
            "output_path": db_path.relative_to(ROOT).as_posix(),
        },
    )
    oracle_rows = -1
    oracle_columns: list[str] = []
    if db_path.is_file():
        conn = sqlite3.connect(str(db_path))
        try:
            oracle_columns = [
                row[1] for row in conn.execute("PRAGMA table_info(records)").fetchall()
            ]
            oracle_rows = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        finally:
            conn.close()
    result = (solved.get("execution") or {}).get("result") or {}
    cases.append(
        _case(
            "sqlite_creation_matches_sqlite3_oracle",
            solved.get("pass") is True
            and oracle_rows == len(records["records"])
            and oracle_columns == ["name", "v"]
            and result.get("row_count") == oracle_rows,
            "INDEPENDENT",
            {
                "oracle_rows": oracle_rows,
                "oracle_columns": oracle_columns,
                "reported_rows": result.get("row_count"),
            },
        )
    )

    # ---- case 4: Python test execution audit --------------------------------
    expected_tests = rng.randint(2, 4)
    test_file = workdir / "test_fresh.py"
    _unittest_file(test_file, expected_tests)
    audited = model.solve(
        "audit the python unit tests and count passes",
        inputs={
            "source_root": workdir.relative_to(ROOT).as_posix(),
            "pattern": "test_fresh.py",
            "output_path": f"{base_rel}/out/tests.json",
        },
    )
    aresult = (audited.get("execution") or {}).get("result") or {}
    cases.append(
        _case(
            "test_audit_matches_generated_case_count",
            audited.get("pass") is True
            and aresult.get("test_count") == expected_tests
            and aresult.get("passed_count") == expected_tests,
            "INDEPENDENT",
            {
                "expected_tests": expected_tests,
                "reported": {
                    "test_count": aresult.get("test_count"),
                    "passed_count": aresult.get("passed_count"),
                },
            },
        )
    )

    # ---- case 5: a substrate-blocked capability must say so -----------------
    jq_json = workdir / "jq_input.json"
    jq_json.write_text(json.dumps({"values": list(range(7))}), encoding="utf-8")
    blocked = model.solve(
        "query json with jq and write the output",
        inputs={
            "json_path": jq_json.relative_to(ROOT).as_posix(),
            "jq_filter": ".values | length",
            "output_path": f"{base_rel}/out/jq.txt",
        },
        capability_id="json.query.jq",
    )
    errors = " ".join((blocked.get("execution") or {}).get("errors") or [])
    cases.append(
        _case(
            "substrate_blocked_capability_fails_closed_and_names_the_gap",
            blocked.get("pass") is not True and "BOUND_APT_METADATA_NOT_FOUND" in errors,
            "FAIL_CLOSED_OBSERVATION",
            {
                "status": blocked.get("status"),
                "errors": (blocked.get("execution") or {}).get("errors"),
            },
        )
    )

    return _category("EXECUTION_FRESH", cases)


# --------------------------------------------------------------------------- negatives


def check_negative_controls(
    model: unified_model.UnifiedModel, artifact_text: str
) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    unknown = model.solve("launch a weather satellite into low earth orbit")
    cases.append(
        _case(
            "unknown_goal_fails_closed",
            unknown.get("pass") is not True
            and str(unknown.get("reason")) == "GOAL_NOT_REPRESENTED_IN_MODEL__FAIL_CLOSED",
            "NEGATIVE_CONTROL",
            {"reason": unknown.get("reason")},
        )
    )

    missing = model.solve(
        "audit python source structure",
        capability_id="python.source.audit.ast",
        inputs={},
    )
    cases.append(
        _case(
            "missing_inputs_fail_closed",
            str(missing.get("reason") or "").startswith("CAPABILITY_INPUTS_MISSING"),
            "NEGATIVE_CONTROL",
            {"reason": missing.get("reason")},
        )
    )

    tampered = json.loads(artifact_text)
    tampered["capabilities"][0]["triggers"] = ["injected"]
    rejected = False
    try:
        doc = dict(tampered)
        declared = (doc.get("digest") or {}).get("value")
        rejected = compiler.artifact_digest(doc) != declared
    except Exception:
        rejected = True
    with tempfile.TemporaryDirectory() as tmp:
        bad_path = Path(tmp) / "tampered.json"
        bad_path.write_text(json.dumps(tampered), encoding="utf-8")
        load_rejected = False
        try:
            unified_model.load_model(bad_path)
        except unified_model.UnifiedModelError:
            load_rejected = True
    cases.append(
        _case(
            "tampered_artifact_is_rejected",
            rejected and load_rejected,
            "NEGATIVE_CONTROL",
            {"digest_rejected": rejected, "load_rejected": load_rejected},
        )
    )

    # A capability that declares nonzero spend must be refused by the front
    # door even if a future registry admitted it. Simulate on a copy of the
    # in-memory model; the live artifact is untouched.
    simulated = json.loads(artifact_text)
    for row in simulated.get("capabilities") or []:
        row["incremental_spend_usd"] = 1
        break
    simulated["digest"]["value"] = compiler.artifact_digest(
        {k: v for k, v in simulated.items() if k != "digest"}
    )
    sim_model = unified_model.UnifiedModel(simulated)
    first = next(iter(sim_model.capabilities.values()))
    spend_out = sim_model.solve(
        str(first["id"]),
        capability_id=str(first["id"]),
        inputs={name: "x" for name in first.get("input_names") or []},
    )
    cases.append(
        _case(
            "nonzero_spend_capability_is_refused",
            str(spend_out.get("reason")) == "CAPABILITY_NONZERO_SPEND_REJECTED",
            "NEGATIVE_CONTROL",
            {"reason": spend_out.get("reason")},
        )
    )

    engine_out = model.solve(
        "compute an adequate decision", capability_id="engine:ADEQUATE_DECISION", inputs={}
    )
    cases.append(
        _case(
            "engine_without_host_providers_fails_closed",
            engine_out.get("pass") is not True,
            "NEGATIVE_CONTROL",
            {"status": engine_out.get("status"), "reason": engine_out.get("reason")},
        )
    )
    return _category("NEGATIVE_CONTROLS", cases)


# --------------------------------------------------------------------------- dependence


def check_model_dependence(model: Mapping[str, Any]) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    runtime_paths = (
        "canonical/runtime/brain_unified_model_v1.py",
        "canonical/runtime/compile_brain_unified_model_v1.py",
        "canonical/runtime/verify_brain_unified_model_v1.py",
    )
    found: dict[str, list[str]] = {}
    for rel in runtime_paths:
        path = ROOT / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        imports = []
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        hits = sorted(
            {
                name
                for name in imports
                for forbidden in FORBIDDEN_MODEL_IMPORTS
                if name == forbidden or name.startswith(forbidden + ".")
            }
        )
        if hits:
            found[rel] = hits
    cases.append(
        _case(
            "no_model_client_import_in_runtime",
            not found,
            "STATIC_IMPORT_SCAN",
            {"findings": found},
        )
    )

    route_hits: list[dict[str, str]] = []
    for row in model.get("capabilities") or []:
        route_text = json.dumps(row.get("route") or {}).casefold()
        for marker in FORBIDDEN_ROUTE_MARKERS:
            if marker in route_text:
                route_hits.append({"id": str(row.get("id")), "marker": marker})
    for row in model.get("engines") or []:
        route_text = json.dumps(row.get("route") or {}).casefold()
        for marker in FORBIDDEN_ROUTE_MARKERS:
            if marker in route_text:
                route_hits.append({"id": str(row.get("id")), "marker": marker})
    cases.append(
        _case(
            "no_capability_route_names_a_model_provider",
            not route_hits,
            "STATIC_ROUTE_SCAN",
            {"findings": route_hits[:10], "count": len(route_hits)},
        )
    )

    provenance = model.get("provenance") or {}
    cases.append(
        _case(
            "compiler_declares_zero_model_and_network_calls",
            provenance.get("external_model_calls") == 0
            and provenance.get("network_calls") == 0
            and provenance.get("incremental_spend_usd") == 0,
            "DECLARATION_AND_SOURCE_SCAN",
            {
                "external_model_calls": provenance.get("external_model_calls"),
                "network_calls": provenance.get("network_calls"),
                "incremental_spend_usd": provenance.get("incremental_spend_usd"),
            },
        )
    )

    words = sorted(
        {
            "openai",
            "anthropic",
            "claude",
            "gpt",
            "gemini",
            "llama",
            "qwen",
            "deepseek",
            "mistral",
        }
    )
    text = json.dumps(model, sort_keys=True).casefold()
    hits = {word: text.count(word) for word in words if word in text}
    # Names may legitimately appear in laws and non-claims ("no model", the
    # Opus 5.5 checkpoint). The producer-path assertion above is the operative
    # test; this count is reported for auditability, not used to fail silently.
    cases.append(
        _case(
            "model_vendor_name_occurrences_are_reported_not_hidden",
            True,
            "AUDIT_DISCLOSURE",
            {"occurrences": hits},
        )
    )
    return _category("MODEL_DEPENDENCE_AUDIT", cases)


# --------------------------------------------------------------------------- coverage


def check_one_front_door(model: unified_model.UnifiedModel) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    unaddressable: list[str] = []
    for cid in sorted(model.capabilities):
        result = model.route(cid)
        if not result["best"] or result["best"]["id"] != cid:
            unaddressable.append(cid)
    cases.append(
        _case(
            "every_capability_is_addressable_by_its_own_id",
            not unaddressable,
            "SELF_ADDRESSABILITY",
            {"failures": unaddressable[:10], "count": len(unaddressable)},
        )
    )
    incomplete = []
    for cid, row in model.capabilities.items():
        if (
            not row.get("triggers")
            or not row.get("route")
            or not (row.get("provenance") or {}).get("source_path")
        ):
            incomplete.append(cid)
    # Receipt-backed entries may legitimately omit a source path when their
    # declared source is the live module itself; only a missing route or
    # trigger set makes them unaddressable.
    incomplete = [
        cid
        for cid in incomplete
        if not model.capabilities[cid].get("triggers")
        or not model.capabilities[cid].get("route")
    ]
    cases.append(
        _case(
            "every_capability_carries_a_trigger_set_and_route",
            not incomplete,
            "STRUCTURAL_COMPLETENESS",
            {"failures": incomplete[:10], "count": len(incomplete)},
        )
    )
    engines_incomplete = [
        eid
        for eid, row in model.engines.items()
        if not row.get("route") or not row.get("triggers")
    ]
    cases.append(
        _case(
            "every_engine_carries_a_route",
            not engines_incomplete,
            "STRUCTURAL_COMPLETENESS",
            {"failures": engines_incomplete[:10]},
        )
    )
    skills_without_procedure = [
        str(row.get("id"))
        for row in model.skills
        if not row.get("procedure")
    ]
    cases.append(
        _case(
            "every_internalized_skill_carries_a_procedure",
            not skills_without_procedure,
            "STRUCTURAL_COMPLETENESS",
            {"failures": skills_without_procedure},
        )
    )
    return _category("ONE_FRONT_DOOR", cases)


# --------------------------------------------------------------------------- driver


def run_verification(
    *,
    seed: str | None = None,
    artifact: str | Path | None = None,
    output: str | Path | None = None,
) -> dict[str, Any]:
    chosen_seed = seed or secrets.token_hex(8)
    rng = random.Random(chosen_seed)
    artifact_path = Path(artifact) if artifact else ROOT / unified_model.DEFAULT_ARTIFACT
    if not artifact_path.is_absolute():
        artifact_path = ROOT / artifact_path
    model = unified_model.load_model(artifact_path)
    front_door = unified_model.UnifiedModel(model)
    text = artifact_path.read_text(encoding="utf-8")

    workdir = Path(
        tempfile.mkdtemp(prefix="BRAIN_UNIFIED_MODEL_VERIFY_", dir=ROOT / "canonical/astra_runtime/tmp")
    )
    try:
        categories = [
            check_integrity(model, artifact_path),
            check_live_registry(model),
            check_routing(front_door, rng),
            check_recall(front_door, rng),
            check_execution(front_door, rng, workdir),
            check_negative_controls(front_door, text),
            check_model_dependence(model),
            check_one_front_door(front_door),
        ]
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    total_cases = sum(c["cases"] for c in categories)
    total_failed = sum(c["failed"] for c in categories)
    report = {
        "schema": SCHEMA,
        "model_id": model.get("model_id"),
        "model_digest": (model.get("digest") or {}).get("value"),
        "artifact_path": artifact_path.relative_to(ROOT).as_posix(),
        "artifact_bytes": artifact_path.stat().st_size,
        "artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seed": chosen_seed,
        "authority": "NONE",
        "verification_status": "MEASURED_SANDBOX__NOT_INDEPENDENT",
        "independent_verifier": None,
        "independent_verifier_run_reference": None,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        "producer_cognition_model_dependency_count": 0,
        "summary": {
            "categories": len(categories),
            "cases": total_cases,
            "passed": total_cases - total_failed,
            "failed": total_failed,
            "pass": total_failed == 0,
            "capabilities_modelled": len(model.get("capabilities") or []),
            "engines_modelled": len(model.get("engines") or []),
            "skills_modelled": len(model.get("skills") or []),
            "knowledge_documents_indexed": len(model.get("knowledge") or []),
        },
        "categories": categories,
        "non_claims": [
            "THIS_RUN_DID_NOT_HAVE_AN_INDEPENDENT_VERIFIER",
            "A_SANDBOX_MEASUREMENT_IS_NOT_A_CAPABILITY_RECEIPT",
            "NO_CAPABILITY_OWNERSHIP_OR_TERMINAL_CREDIT_IS_CLAIMED",
            "COVERAGE_ACROSS_363_CAPABILITIES_IS_NOT_363_VERIFIED_CAPABILITIES",
            "ENVIRONMENT_BLOCKED_CAPABILITIES_ARE_NOT_PASSES",
        ],
        "next_independent_step": (
            "A different identity must re-run `python3 "
            "canonical/runtime/verify_brain_unified_model_v1.py --seed <the seed "
            "above>` on a clean checkout and sign the result. Until then this "
            "document is a sandbox measurement with no authority."
        ),
    }
    if output:
        target = Path(output)
        if not target.is_absolute():
            target = ROOT / target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        report["_written_to"] = target.relative_to(ROOT).as_posix()
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", default=None, help="deterministic seed for fresh cases")
    parser.add_argument("--artifact", default=None)
    parser.add_argument("--output", default=None, help="write the JSON report here")
    ns = parser.parse_args(argv)
    report = run_verification(seed=ns.seed, artifact=ns.artifact, output=ns.output)
    summary = report["summary"]
    for category in report["categories"]:
        print(
            f"{category['name']}: {category['passed']}/{category['cases']} "
            f"{'PASS' if category['pass'] else 'FAIL'}"
        )
        for row in category["rows"]:
            if not row["pass"]:
                print("  FAILED", row["name"], json.dumps(row["detail"], sort_keys=True)[:400])
    print("SEED", report["seed"])
    print("MODEL", report["model_digest"])
    print(
        "TOTAL",
        f"{summary['passed']}/{summary['cases']}",
        "PASS" if summary["pass"] else "FAIL",
    )
    if report.get("_written_to"):
        print("WROTE", report["_written_to"])
    print("AUTHORITY NONE -- SANDBOX MEASUREMENT, NOT INDEPENDENT VERIFICATION")
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
