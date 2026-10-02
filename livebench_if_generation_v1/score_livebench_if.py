#!/usr/bin/env python3
"""Score LiveBench-IF-shaped answers with LiveBench's OWN aggregator. PROVISIONAL tooling.

Why this exists
---------------
LiveBench's leaderboard does not report prompt-level loose accuracy. At the pinned upstream
commit its per-question score is ``ifbench_process_results`` -> ``score_results``:
``(1[all instructions followed] + fraction of instructions followed) / 2`` under the STRICT
check, with the answer taken from inside ``<solution>...</solution>`` when present. The
leaderboard then multiplies by 100 and averages by task. This driver CALLS that upstream
function (it does not re-implement it), refuses to run unless the upstream checkout is at the
pinned commit, and adds diagnostics so a reviewer can see how far other metrics (for example
the prompt-level loose accuracy declared in LIVEBENCH_IF_VERIFIER_BINDING_V1) would differ.

It never prints or stores prompts or responses: only ids, scores and aggregates.
It needs a LiveBench checkout (``--livebench-root``) and the packages upstream imports
(pandas, nltk, emoji, syllapy, langdetect, immutabledict, absl-py). Upstream also imports spaCy
and downloads NLTK data at import time; the project's hermetic runtime removes that (spaCy is
dead code with zero checker references): provide the same hermetic setup, or a stub spaCy plus
an ``NLTK_DATA`` folder, exactly as the integration test does.
"""
from __future__ import annotations

import argparse
import importlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

PINNED_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
SCHEMA = "PROJECT_BRAIN_LIVEBENCH_IF_SCORE_SUMMARY_V1"
_SOLUTION = re.compile(r"<solution>(.*?)</solution>", re.DOTALL)


class Blocked(Exception):
    code = 2


def load_upstream(livebench_root: Path, verify_commit: bool = True):
    root = Path(livebench_root).resolve()
    if not (root / "livebench").is_dir():
        raise Blocked("LIVEBENCH_ROOT_HAS_NO_livebench_PACKAGE")
    if verify_commit:
        head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        if head != PINNED_COMMIT:
            raise Blocked(f"LIVEBENCH_ROOT_NOT_AT_PINNED_COMMIT:{head[:12] or 'not-a-git-checkout'}")
        dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--", "livebench"], capture_output=True, text=True).stdout.strip()
        if dirty:
            raise Blocked("LIVEBENCH_CHECKOUT_HAS_LOCAL_EDITS")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    utils = importlib.import_module("livebench.process_results.instruction_following.utils")
    lib = importlib.import_module("livebench.if_runner.ifbench.evaluation_lib")
    return utils, lib


def load_questions(path: Path) -> list[dict[str, Any]]:
    text = Path(path).read_text(encoding="utf-8")
    rows = json.loads(text) if text.lstrip().startswith("[") else [json.loads(x) for x in text.splitlines() if x.strip()]
    if not isinstance(rows, list) or not rows:
        raise Blocked("QUESTIONS_EMPTY")
    seen: set[Any] = set()
    for i, q in enumerate(rows):
        for field in ("question_id", "turns", "instruction_id_list", "kwargs"):
            if field not in q:
                raise Blocked(f"QUESTION_FIELD_MISSING:{field}:{i}")
        if q["question_id"] in seen:
            raise Blocked(f"QUESTION_ID_DUPLICATE:{q['question_id']!r}")
        seen.add(q["question_id"])
        if len(q["instruction_id_list"]) != len(q["kwargs"]):
            raise Blocked(f"KWARGS_LENGTH_MISMATCH:{q['question_id']!r}")
    return rows


def _answer_text(model_answers: Mapping[str, Any], model_id: str, qid: Any) -> str:
    return model_answers[model_id][qid]["choices"][0]["turns"][0]


def _extract(text: str) -> str:
    m = _SOLUTION.search(text)
    return (m.group(1) if m else text).strip()


def score_run(questions: Sequence[Mapping[str, Any]], model_answers: Mapping[str, Any], model_id: str, utils: Any, lib: Any) -> dict[str, Any]:
    if model_id not in model_answers:
        raise Blocked("MODEL_ID_MISSING")
    q_ids = [q["question_id"] for q in questions]
    a_ids = set(model_answers[model_id])
    if a_ids != set(q_ids):
        raise Blocked(f"ID_SET_MISMATCH:missing={len(set(q_ids) - a_ids)}:extra={len(a_ids - set(q_ids))}")
    rows = []
    for q in questions:
        text = _answer_text(model_answers, model_id, q["question_id"])
        official = float(utils.ifbench_process_results(dict(q), text))  # LiveBench's own function
        inp = lib.InputExample(key=q["question_id"], instruction_id_list=q["instruction_id_list"], prompt=q["turns"][0], kwargs=q["kwargs"])
        response = _extract(text)
        try:
            strict = lib.test_instruction_following_strict(inp, response)
            loose = lib.test_instruction_following_loose(inp, response)
            diag = {
                "prompt_strict": 1.0 if strict.follow_all_instructions else 0.0,
                "prompt_loose": 1.0 if loose.follow_all_instructions else 0.0,
                "instruction_strict": sum(strict.follow_instruction_list) / len(strict.follow_instruction_list),
            }
        except Exception:
            diag = {"prompt_strict": 0.0, "prompt_loose": 0.0, "instruction_strict": 0.0}
        rows.append({"question_id": q["question_id"], "task": q.get("task", "all"), "score": official, **diag})
    by_task: dict[str, list[float]] = {}
    for r in rows:
        by_task.setdefault(r["task"], []).append(r["score"])
    task_means = {t: 100 * sum(v) / len(v) for t, v in sorted(by_task.items())}

    def mean(key: str) -> float:
        return 100 * sum(r[key] for r in rows) / len(rows)

    return {
        "schema": SCHEMA, "model_id": model_id, "upstream_commit": PINNED_COMMIT, "questions": len(rows),
        "leaderboard_style_category_score": sum(task_means.values()) / len(task_means),
        "task_means": task_means,
        "question_mean_score": mean("score"),
        "diagnostics_not_the_leaderboard_metric": {
            "prompt_level_strict_accuracy": mean("prompt_strict"),
            "prompt_level_loose_accuracy": mean("prompt_loose"),
            "instruction_level_strict_accuracy": mean("instruction_strict"),
        },
        "per_question": [{"question_id": r["question_id"], "task": r["task"], "score": r["score"]} for r in rows],
        "execution_authority": False, "promotion_authority": False, "capability_credit_delta": 0,
        "incremental_spend_usd": 0, "note": "PROVISIONAL tooling output; zero progress credit",
    }


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--questions", required=True, type=Path, help="JSONL rows with question_id, turns, instruction_id_list, kwargs (optional task)")
    ap.add_argument("--model-answers", required=True, type=Path, help="model_answers.json from generate_responses.py")
    ap.add_argument("--model-id", default="brain")
    ap.add_argument("--livebench-root", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)
    try:
        utils, lib = load_upstream(args.livebench_root)
        summary = score_run(load_questions(args.questions), json.loads(args.model_answers.read_text(encoding="utf-8")), args.model_id, utils, lib)
    except Blocked as exc:
        print(f"BLOCKED {exc}", file=sys.stderr)
        return exc.code
    args.out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("questions", "leaderboard_style_category_score", "question_mean_score")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
