#!/usr/bin/env python3
"""Narrow GDPval public-task CLI agent for Brain-owned artifact canaries.

Reads only task.json prompt/reference metadata and creates only candidate
deliverables. It does not read benchmark rubrics, gold deliverables, meta-prompts,
or evaluator outputs. Unsupported tasks fail closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from professional_archetype_brand_distribution_onboarding_v1 import select
from professional_questionnaire_pdf_stdlib_v1 import render


def _inside(child: pathlib.Path, parent: pathlib.Path) -> bool:
    child = child.resolve()
    parent = parent.resolve()
    return child == parent or parent in child.parents


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-json", required=True)
    ap.add_argument("--workspace", required=True)
    args = ap.parse_args()

    ws = pathlib.Path(args.workspace).resolve()
    task_path = pathlib.Path(args.task_json).resolve()
    if not ws.is_dir() or not task_path.is_file() or not _inside(task_path, ws):
        raise SystemExit("FAIL_CLOSED:INVALID_WORKSPACE_BINDING")

    task = json.loads(task_path.read_text(encoding="utf-8"))
    forbidden = {"rubric_json", "rubric_pretty", "deliverable_file_urls", "deliverable_file_hf_uris"}
    if forbidden.intersection(task):
        raise SystemExit("FAIL_CLOSED:FORBIDDEN_EVALUATION_OR_GOLD_FIELDS_PRESENT")

    prompt = str(task.get("prompt") or "")
    refs = [str(x) for x in (task.get("reference_files") or [])]
    selected = select(prompt, refs)
    if selected.get("status") != "SELECTED":
        print(json.dumps({
            "status": "FAIL_CLOSED__NO_OWNED_ARCHETYPE",
            "reason": selected.get("reason"),
            "task_id": task.get("task_id"),
            "model_dependency_count": 0,
        }, sort_keys=True))
        return 2

    title = str(selected["spec"]["title"])
    safe = re.sub(r"[^A-Za-z0-9 _().-]+", "", title).strip(" .") or "Brand Data Gathering"
    output = ws / (safe + ".pdf")
    result = render(selected["spec"], output)
    print(json.dumps({
        "status": "PASS__BRAIN_OWNED_ARTIFACT_CREATED",
        "task_id": task.get("task_id"),
        "archetype": selected.get("archetype"),
        "artifact_name": output.name,
        "artifact_sha256": result["output_sha256"],
        "artifact_bytes": result["output_bytes"],
        "page_count": result["page_count"],
        "question_count": result["question_count"],
        "input_prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "candidate_inputs": ["task.prompt", "task.reference_files"],
        "rubric_or_gold_input_count": 0,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
