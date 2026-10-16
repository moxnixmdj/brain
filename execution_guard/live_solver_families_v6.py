"""Fresh-goal EXECUTION families, wave 6 (heartbeat). Same contract as waves 2-5: fresh inputs,
one plain sentence, an oracle that judges the real artifact with the standard library.

  RESEARCH_DECOMPOSE_BROAD   research.objective.decompose.broad.v1
  RESEARCH_FOCUS_QUERY       research.query.focus.v1
  SEMANTIC_CELLS_ACCEPTANCE  python.software.request.semantic_cells.v1
"""
from __future__ import annotations

import hashlib
import json
import random
import shutil
from pathlib import Path
from typing import Any, Callable

from execution_guard.live_solver_end_to_end_measurement_v1 import Case, ROOT, _rel, _word
from execution_guard.live_solver_families_v2 import _passed

FIXED_ROLES = [
    "SOURCE_DISCOVERY",
    "EVIDENCE_ACQUISITION",
    "EVIDENCE_EXTRACTION",
    "RELATION_EVALUATION",
    "DECISION_SYNTHESIS_AND_VERIFICATION",
]
_PREFIXES = ["Determine whether", "Assess whether", "Evaluate whether", "Estimate", "Compare"]
_SUBJECTS = [
    "harbor sediment copper levels are safe",
    "night delivery drone noise harms sleep quality",
    "open canals lose more water than piped ones",
    "library rooftop solar output beats the block average",
    "upland stream phosphate load is rising year over year",
    "ferry wake erosion harms shoreline reeds",
    "market hall air quality meets the daytime standard",
]
_FOCUS_STOP = {
    "assess", "determine", "evaluate", "investigate", "estimate", "quantify", "compare",
    "analyze", "analyse", "whether",
    "the", "a", "an", "of", "to", "and", "or", "is", "are", "was", "were", "be", "being", "been",
    "that", "this", "these", "those", "in", "on", "at", "by", "for", "from", "with", "without",
    "as", "than",
}


def _objective(rng: random.Random) -> str:
    return f"{rng.choice(_PREFIXES)} {rng.choice(_SUBJECTS)}"


# ----------------------------------------------------------------- decompose

def gen_research_decompose(rng: random.Random, work: Path, i: int) -> Case:
    work.mkdir(parents=True, exist_ok=True)
    objective = _objective(rng)
    out = work / f"decomp_{i}_{_word(rng, 4)}.json"
    goal = (
        f"Decompose the broad research objective \"{objective}\" into research roles "
        f"and save to {_rel(out)}."
    )

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if not _passed(result):
            return False, "runtime did not pass: " + str(result.get("status"))
        if result.get("compiled_capability_id") != "research.objective.decompose.broad.v1":
            return False, "routed to " + str(result.get("compiled_capability_id"))
        if not out.is_file():
            return False, "decomposition output not written"
        doc = json.loads(out.read_text(encoding="utf-8"))
        if doc.get("output_verified") is not True or doc.get("status") != "DECOMPOSED":
            return False, "artifact not a verified DECOMPOSED decomposition"
        if doc.get("objective") != objective:
            return False, "objective echo mismatch"
        if doc.get("objective_sha256") != hashlib.sha256(objective.encode("utf-8")).hexdigest():
            return False, "objective sha256 mismatch"
        if [r["role"] for r in doc.get("roles", [])] != FIXED_ROLES:
            return False, "role graph is not the fixed contract"
        if doc.get("invented_source_urls") != [] or doc.get("invented_facts") != []:
            return False, "decomposition invented sources or facts"
        return True, ""

    return Case("RESEARCH_DECOMPOSE_BROAD", goal, oracle, True, [out])


# --------------------------------------------------------------------- focus

def gen_research_focus(rng: random.Random, work: Path, i: int) -> Case:
    work.mkdir(parents=True, exist_ok=True)
    objective = _objective(rng)
    out = work / f"focus_{i}_{_word(rng, 4)}.json"
    goal = f"Focus the research objective \"{objective}\" into a search query and save to {_rel(out)}."

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if not _passed(result):
            return False, "runtime did not pass: " + str(result.get("status"))
        if result.get("compiled_capability_id") != "research.query.focus.v1":
            return False, "routed to " + str(result.get("compiled_capability_id"))
        if not out.is_file():
            return False, "focus output not written"
        doc = json.loads(out.read_text(encoding="utf-8"))
        if doc.get("output_verified") is not True or doc.get("status") != "FOCUSED":
            return False, "artifact not a verified FOCUSED query"
        tokens = doc.get("tokens") or []
        if len(tokens) < 2 or doc.get("query") != " ".join(tokens):
            return False, "query/token mismatch"
        if doc.get("query_sha256") != hashlib.sha256(doc["query"].encode("utf-8")).hexdigest():
            return False, "query sha256 mismatch"
        if any(t in _FOCUS_STOP for t in tokens):
            return False, "stopword leaked into query tokens"
        decision_words = set(str(doc.get("decision_clause") or "").lower().split())
        if any(t not in decision_words for t in tokens):
            return False, "query token outside the decision clause"
        return True, ""

    return Case("RESEARCH_FOCUS_QUERY", goal, oracle, True, [out])


# --------------------------------------------------------------------- cells

def gen_semantic_cells(rng: random.Random, work: Path, i: int) -> Case:
    work.mkdir(parents=True, exist_ok=True)
    tree = work / f"cells_tree_{i}_{_word(rng, 4)}"
    if tree.exists():
        shutil.rmtree(tree)
    tree.mkdir(parents=True)
    fname = f"mod_{_word(rng, 5)}.py"
    literal = f"sentinel_{_word(rng, 6)}"
    kind = rng.choice(["FILE_CONTAINS", "FILE_NOT_CONTAINS", "FILE_EXISTS", "FILE_ABSENT"])
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
    task = work / f"task_cells_{i}_{_word(rng, 4)}.txt"
    task.write_text(spec, encoding="utf-8")
    out = work / f"cells_{i}_{_word(rng, 4)}.json"
    goal = (
        f"Evaluate semantic acceptance cells for the task file {_rel(task)} "
        f"against source tree {_rel(tree)} and save to {_rel(out)}."
    )

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if not _passed(result):
            return False, "runtime did not pass: " + str(result.get("status"))
        if result.get("compiled_capability_id") != "python.software.request.semantic_cells.v1":
            return False, "routed to " + str(result.get("compiled_capability_id"))
        if not out.is_file():
            return False, "cells verdict not written"
        doc = json.loads(out.read_text(encoding="utf-8"))
        if doc.get("output_verified") is not True:
            return False, "verdict not verified"
        if doc.get("failed_obligation_ids") != [] or doc.get("unbound_obligation_ids") != []:
            return False, "verdict carries failed or unbound obligations"
        rows = doc.get("cell_results") or []
        if len(rows) != 1 or rows[0].get("status") != "VERIFIED_PASS":
            return False, "expected exactly one VERIFIED_PASS cell"
        if rows[0].get("details", {}).get("kind") != kind:
            return False, "cell kind mismatch"
        target = tree / fname
        body = target.read_text(encoding="utf-8") if target.is_file() else None
        if kind == "FILE_CONTAINS" and (body is None or literal not in body):
            return False, "independent re-read: literal absent"
        if kind == "FILE_NOT_CONTAINS" and (body is None or literal in body):
            return False, "independent re-read: literal present"
        if kind == "FILE_EXISTS" and body is None:
            return False, "independent re-read: file missing"
        if kind == "FILE_ABSENT" and body is not None:
            return False, "independent re-read: file present"
        return True, ""

    return Case("SEMANTIC_CELLS_ACCEPTANCE", goal, oracle, True, [out])


GENERATORS_V6: dict[str, Callable[[random.Random, Path, int], Case]] = {
    "RESEARCH_DECOMPOSE_BROAD": gen_research_decompose,
    "RESEARCH_FOCUS_QUERY": gen_research_focus,
    "SEMANTIC_CELLS_ACCEPTANCE": gen_semantic_cells,
}
