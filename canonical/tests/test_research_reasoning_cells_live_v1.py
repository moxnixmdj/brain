"""Three owned reasoning mechanisms through the one mouth.

Live bindings (no new kernels, no models, no spend, no network):
  research.objective.decompose.broad.v1  (broad objective -> fixed research-role graph)
  research.query.focus.v1                (broad objective -> bounded search query)
  python.software.request.semantic_cells.v1 (task file + source tree -> acceptance verdict)

Every test runs a plain sentence through ``live_brain_route_admission_v1.solve``
and judges the real artifact with an independent stdlib oracle. Quoted objectives
carry plain words only: the sentence binder cannot transport quote characters
inside quotes, so objectives with inner quotes are out of scope by construction
(the binding fails closed on them instead of guessing).
"""
from __future__ import annotations

import hashlib
import json
import random
import shutil
import string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as adm  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_research_reasoning_cells"
REL = "canonical/astra_runtime/tmp/test_research_reasoning_cells"
STATE = ROOT / "canonical/astra_runtime/state"

FIXED_ROLES = [
    "SOURCE_DISCOVERY",
    "EVIDENCE_ACQUISITION",
    "EVIDENCE_EXTRACTION",
    "RELATION_EVALUATION",
    "DECISION_SYNTHESIS_AND_VERIFICATION",
]
BROAD_PREFIXES = ["Determine whether", "Assess whether", "Evaluate whether", "Estimate", "Compare"]
SUBJECTS = [
    "city tap water nitrate levels are safe",
    "night freight rail noise harms sleep quality",
    "open reservoirs lose more water than covered ones",
    "rooftop solar output beats the street average",
    "river sediment load is rising year over year",
]
FOCUS_STOPWORDS = {
    "assess", "determine", "evaluate", "investigate", "estimate", "quantify", "compare",
    "analyze", "analyse", "whether",
    "the", "a", "an", "of", "to", "and", "or", "is", "are", "was", "were", "be", "being", "been",
    "that", "this", "these", "those", "in", "on", "at", "by", "for", "from", "with", "without",
    "as", "than",
}


def setup_module(_module=None):
    WORK.mkdir(parents=True, exist_ok=True)


def teardown_module(_module=None):
    if WORK.exists():
        shutil.rmtree(WORK)


def _cleanup(task_id: str) -> None:
    for p in STATE.glob(task_id + "__*"):
        p.unlink()


def _solve(task_id: str, goal: str):
    try:
        return adm.solve({"task_id": task_id, "goal": goal})
    finally:
        _cleanup(task_id)


def _word(rng: random.Random, n: int) -> str:
    return "".join(rng.choice(string.ascii_lowercase) for _ in range(n))


def _fresh_objective(rng: random.Random) -> str:
    return f"{rng.choice(BROAD_PREFIXES)} {rng.choice(SUBJECTS)}"


def test_decompose_fresh_objectives_match_the_fixed_role_contract():
    for seed in (3, 11, 27, 64, 101):
        rng = random.Random(seed)
        objective = _fresh_objective(rng)
        out = WORK / f"decomp_{seed}.json"
        if out.exists():
            out.unlink()
        goal = (
            f"Decompose the broad research objective \"{objective}\" into research roles "
            f"and save to {REL}/decomp_{seed}.json."
        )
        res = _solve(f"TEST_RRC_DECOMP_{seed}", goal)
        assert res["pass"] is True, (seed, res.get("status"), res.get("failure_class"), res.get("reason"))
        assert res["compiled_capability_id"] == "research.objective.decompose.broad.v1"
        assert res.get("model_dependency_count") == 0
        assert res.get("incremental_spend_usd") == 0
        assert out.is_file()
        doc = json.loads(out.read_text(encoding="utf-8"))
        assert doc["output_verified"] is True
        assert doc["status"] == "DECOMPOSED"
        assert doc["objective"] == objective
        assert doc["objective_sha256"] == hashlib.sha256(objective.encode("utf-8")).hexdigest()
        assert [r["role"] for r in doc["roles"]] == FIXED_ROLES
        assert all(r["status"] == "REQUIRES_GROUNDING" for r in doc["roles"])
        assert doc["invented_source_urls"] == [] and doc["invented_facts"] == []
        assert doc["model_dependency_count"] == 0


def test_focus_fresh_objectives_yield_auditable_queries():
    for seed in (5, 17, 42, 88, 130):
        rng = random.Random(seed)
        objective = _fresh_objective(rng)
        out = WORK / f"focus_{seed}.json"
        if out.exists():
            out.unlink()
        goal = (
            f"Focus the research objective \"{objective}\" into a search query "
            f"and save to {REL}/focus_{seed}.json."
        )
        res = _solve(f"TEST_RRC_FOCUS_{seed}", goal)
        assert res["pass"] is True, (seed, res.get("status"), res.get("failure_class"), res.get("reason"))
        assert res["compiled_capability_id"] == "research.query.focus.v1"
        assert res.get("model_dependency_count") == 0
        assert out.is_file()
        doc = json.loads(out.read_text(encoding="utf-8"))
        assert doc["output_verified"] is True
        assert doc["status"] == "FOCUSED"
        assert doc["query"] == " ".join(doc["tokens"])
        assert doc["query_sha256"] == hashlib.sha256(doc["query"].encode("utf-8")).hexdigest()
        assert len(doc["tokens"]) >= 2
        assert not any(t in FOCUS_STOPWORDS for t in doc["tokens"])
        decision_words = set(doc["decision_clause"].lower().split())
        assert all(t in decision_words for t in doc["tokens"]), doc["tokens"]
        assert doc["semantic_entailment_status"] == "UNVERIFIED"
        assert doc["factual_correctness_status"] == "UNVERIFIED"


def test_cells_acceptance_verdict_on_fresh_trees():
    kinds = ("FILE_CONTAINS", "FILE_NOT_CONTAINS", "FILE_EXISTS", "FILE_ABSENT")
    for seed in (7, 21, 55, 77):
        rng = random.Random(seed)
        kind = kinds[seed % len(kinds)]
        tree = WORK / f"cells_tree_{seed}"
        if tree.exists():
            shutil.rmtree(tree)
        tree.mkdir(parents=True)
        fname = f"mod_{_word(rng, 5)}.py"
        literal = f"sentinel_{_word(rng, 6)}"
        if kind == "FILE_CONTAINS":
            (tree / fname).write_text(f"def f():\n    return \"{literal}\"\n", encoding="utf-8")
            spec = f"The file \"{fname}\" must contain \"{literal}\"."
        elif kind == "FILE_NOT_CONTAINS":
            (tree / fname).write_text("def f():\n    return 1\n", encoding="utf-8")
            spec = f"The file \"{fname}\" must not contain \"{literal}\"."
        elif kind == "FILE_EXISTS":
            (tree / fname).write_text("x = 1\n", encoding="utf-8")
            spec = f"The file \"{fname}\" must exist."
        else:
            (tree / "other.py").write_text("x = 1\n", encoding="utf-8")
            spec = f"The file \"{fname}\" must not exist."
        task = WORK / f"task_cells_{seed}.txt"
        task.write_text(spec, encoding="utf-8")
        out = WORK / f"cells_{seed}.json"
        if out.exists():
            out.unlink()
        goal = (
            f"Evaluate semantic acceptance cells for the task file {REL}/task_cells_{seed}.txt "
            f"against source tree {REL}/cells_tree_{seed} and save to {REL}/cells_{seed}.json."
        )
        res = _solve(f"TEST_RRC_CELLS_{seed}", goal)
        assert res["pass"] is True, (seed, kind, res.get("status"), res.get("failure_class"), res.get("reason"))
        assert res["compiled_capability_id"] == "python.software.request.semantic_cells.v1"
        assert out.is_file()
        doc = json.loads(out.read_text(encoding="utf-8"))
        assert doc["output_verified"] is True
        assert doc["failed_obligation_ids"] == [] and doc["unbound_obligation_ids"] == []
        assert len(doc["cell_results"]) == 1
        cell = doc["cell_results"][0]
        assert cell["status"] == "VERIFIED_PASS" and cell["pass"] is True
        assert cell["details"]["kind"] == kind
        # independent check: read the tree ourselves, trust no verdict blindly
        if kind == "FILE_CONTAINS":
            assert literal in (tree / fname).read_text(encoding="utf-8")
        elif kind == "FILE_NOT_CONTAINS":
            assert literal not in (tree / fname).read_text(encoding="utf-8")
        elif kind == "FILE_EXISTS":
            assert (tree / fname).is_file()
        else:
            assert not (tree / fname).exists()


def test_narrow_objective_fails_closed_and_writes_nothing():
    out = WORK / "decomp_narrow.json"
    if out.exists():
        out.unlink()
    goal = (
        "Decompose the broad research objective \"Rank local restaurants by price\" into research roles "
        f"and save to {REL}/decomp_narrow.json."
    )
    res = _solve("TEST_RRC_NARROW", goal)
    assert res["pass"] is False
    assert not out.exists()


def test_unbound_cells_spec_fails_closed_and_writes_nothing():
    tree = WORK / "cells_tree_bad"
    if tree.exists():
        shutil.rmtree(tree)
    tree.mkdir(parents=True)
    (tree / "a.py").write_text("x = 1\n", encoding="utf-8")
    task = WORK / "task_cells_bad.txt"
    task.write_text("The file ", encoding="utf-8")
    out = WORK / "cells_bad.json"
    if out.exists():
        out.unlink()
    goal = (
        f"Evaluate semantic acceptance cells for the task file {REL}/task_cells_bad.txt "
        f"against source tree {REL}/cells_tree_bad and save to {REL}/cells_bad.json."
    )
    res = _solve("TEST_RRC_CELLS_BAD", goal)
    assert res["pass"] is False, res.get("status")
    assert not out.exists()


def test_out_of_scope_sentences_still_fail_closed():
    probes = [
        "Translate the poem into French and save it to {REL}/oos_fr.txt.",
        "Prove that every even number is the sum of two primes and save to {REL}/oos_proof.txt.",
        "Summarize the quarterly report and save to {REL}/oos_summary.txt.",
    ]
    for i, template in enumerate(probes):
        goal = template.format(REL=REL)
        res = _solve(f"TEST_RRC_OOS_{i}", goal)
        assert res["pass"] is False, (goal, res.get("status"))
