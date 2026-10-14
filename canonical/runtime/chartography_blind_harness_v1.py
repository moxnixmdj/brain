#!/usr/bin/env python3
"""Chartography blind harness V1 — held-out scoring for the zero-model chart solver.

Pipeline (every stage content-addressed, zero credit):

  build-pack   parquet (surgeai/chartography data.parquet, runner only)  ->  pack/
               pack/tasks.jsonl keeps every original column; images written to pack/images/.
  build-views  pack/  ->  views/solver_view (id, image, prompt ONLY) + views/scorer_view (everything else)
               Fail-closed split: any column not explicitly solver-visible is held out.
  run          solver_view -> results.jsonl, each task in a scrubbed subprocess; scorer_view chmod 000
               for the duration; the solver never receives a path to it.
  score        results + scorer_view -> receipt (pass/abstain/fail per task, taxonomy census,
               scorer-semantics label).  Gold values are never written into the receipt.

The scorer semantics are ASSUMED (explicit range if present, else 5 % relative tolerance, else
normalized exact match) until the official Chartography grading is bound; the receipt says so.
Nothing here grants acceptance, capability, ownership, or terminal credit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

SCHEMA = "PROJECT_BRAIN_CHARTOGRAPHY_BLIND_HARNESS_V1"
REPO_ROOT = Path(__file__).resolve().parents[2]

ID_COLUMNS = ("id", "task_id", "uid", "example_id", "index", "idx")
PROMPT_COLUMNS = ("prompt", "question", "query", "instruction", "input", "text")
IMAGE_COLUMNS = ("image", "img", "chart", "figure", "image_path", "image_url", "chart_image")
ANSWER_KEY_RE = re.compile(
    r"(answer|label|gold|solution|target|accepted|range|tolerance|expected|ground_truth|\bgt\b|rubric|correct)",
    re.I,
)
SECRET_ENV_RE = re.compile(r"(TOKEN|SECRET|KEY|PASSWORD|CREDENTIAL|HF_|HUGGING)", re.I)

QUESTION_TYPES: list[tuple[str, re.Pattern[str]]] = [
    ("CAGR", re.compile(r"\b(cagr|compound annual)\b", re.I)),
    ("PERCENT_CHANGE", re.compile(r"(percent(age)?\s+(change|increase|decrease|growth)|grow(th|n)? by what percent|by what percent)", re.I)),
    ("RATIO", re.compile(r"\b(ratio|how many times|fold|share of|proportion|percent of|fraction of)\b", re.I)),
    ("DIFFERENCE", re.compile(r"\b(difference|how much (more|less|higher|lower|greater)|gap between|exceed|increase from|decrease from)\b", re.I)),
    ("EXTREMA", re.compile(r"\b(highest|lowest|maximum|minimum|largest|smallest|peak|max|min|most|least|greatest)\b", re.I)),
    ("AGGREGATE", re.compile(r"\b(total|sum|average|mean|median|combined|overall)\b", re.I)),
    ("TREND_RATE", re.compile(r"\b(trend|slope|rate of|per (year|month|day|unit)|gradient)\b", re.I)),
    ("THRESHOLD_INTERSECTION", re.compile(r"\b(how long|when (does|will|did)|at what (x|time|year|point|value|temperature|depth)|reach(es)?|cross(es)?|intersect)\b", re.I)),
    ("COUNT", re.compile(r"\b(how many (categories|series|bars|points|countries|years|items))\b", re.I)),
    ("LOOKUP", re.compile(r"\b(what (is|was|are|were) the value|value of|how (many|much)|what (is|was) the)\b", re.I)),
]


# ----------------------------------------------------------------------------- utilities
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_tree(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(x for x in root.rglob("*") if x.is_file()):
        h.update(str(p.relative_to(root)).encode())
        h.update(sha256_file(p).encode())
    return h.hexdigest()


def classify_question(prompt: str) -> str:
    for name, rx in QUESTION_TYPES:
        if rx.search(prompt or ""):
            return name
    return "UNCLASSIFIED"


def _pick(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    low = {c.lower(): c for c in columns}
    for cand in candidates:
        if cand in low:
            return low[cand]
    for c in columns:  # loose containment, e.g. "chart_image_png"
        if any(cand in c.lower() for cand in candidates):
            return c
    return None


# ----------------------------------------------------------------------------- build-pack (runner only)
def build_pack_from_parquet(parquet_path: Path, pack_dir: Path) -> dict[str, Any]:
    import pyarrow.parquet as pq  # runner dependency; absent in the authoring sandbox

    table = pq.read_table(str(parquet_path))
    columns = list(table.column_names)
    image_col = _pick(columns, IMAGE_COLUMNS)
    if image_col is None:
        raise SystemExit(f"FAIL_CLOSED__NO_IMAGE_COLUMN__columns={columns}")
    pack_dir.mkdir(parents=True, exist_ok=True)
    (pack_dir / "images").mkdir(exist_ok=True)
    rows = table.to_pylist()
    with open(pack_dir / "tasks.jsonl", "w", encoding="utf-8") as out:
        for i, row in enumerate(rows):
            img = row.pop(image_col)
            data: bytes | None = None
            if isinstance(img, dict) and isinstance(img.get("bytes"), (bytes, bytearray)):
                data = bytes(img["bytes"])
            elif isinstance(img, (bytes, bytearray)):
                data = bytes(img)
            if data is None:
                raise SystemExit("FAIL_CLOSED__IMAGE_COLUMN_NOT_EMBEDDED_BYTES__REMOTE_URL_FETCH_NOT_IMPLEMENTED")
            name = f"{i:04d}.png"
            (pack_dir / "images" / name).write_bytes(data)
            row["__image_file"] = f"images/{name}"
            row["__row_index"] = i
            out.write(json.dumps(row, default=str) + "\n")
    return {"rows": len(rows), "columns": columns, "image_column": image_col,
            "parquet_sha256": sha256_file(parquet_path)}


# ----------------------------------------------------------------------------- build-views
def build_views(pack_dir: Path, views_dir: Path) -> dict[str, Any]:
    tasks_path = pack_dir / "tasks.jsonl"
    rows = [json.loads(l) for l in tasks_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not rows:
        raise SystemExit("FAIL_CLOSED__EMPTY_PACK")
    columns = sorted({k for r in rows for k in r.keys()})
    id_col = _pick(columns, ID_COLUMNS)
    prompt_col = _pick(columns, PROMPT_COLUMNS)
    image_col = "__image_file" if "__image_file" in columns else _pick(columns, IMAGE_COLUMNS)
    if prompt_col is None or image_col is None:
        raise SystemExit(f"FAIL_CLOSED__SOLVER_VISIBLE_COLUMNS_UNRESOLVED__columns={columns}")
    held_out = [c for c in columns if c not in {id_col, prompt_col, image_col, "__row_index"}]
    answer_like = [c for c in held_out if ANSWER_KEY_RE.search(c)]
    if not answer_like:
        raise SystemExit(f"FAIL_CLOSED__NO_ANSWER_LIKE_COLUMN_AMONG_HELD_OUT__held_out={held_out}")

    solver_dir = views_dir / "solver_view"
    scorer_dir = views_dir / "scorer_view"
    (solver_dir / "images").mkdir(parents=True, exist_ok=True)
    scorer_dir.mkdir(parents=True, exist_ok=True)
    with open(solver_dir / "tasks.jsonl", "w", encoding="utf-8") as s_out, \
            open(scorer_dir / "answers.jsonl", "w", encoding="utf-8") as a_out:
        for i, r in enumerate(rows):
            tid = str(r.get(id_col, r.get("__row_index", i))) if id_col else str(r.get("__row_index", i))
            src_img = pack_dir / str(r[image_col])
            dst_img = solver_dir / "images" / src_img.name
            dst_img.write_bytes(src_img.read_bytes())
            s_out.write(json.dumps({"id": tid, "image": f"images/{src_img.name}", "prompt": str(r[prompt_col])}) + "\n")
            a_out.write(json.dumps({"id": tid, **{c: r.get(c) for c in held_out}}, default=str) + "\n")

    manifest = {
        "schema": SCHEMA + "__VIEWS",
        "columns": columns,
        "solver_visible_columns": [c for c in (id_col, prompt_col, image_col) if c],
        "held_out_columns": held_out,
        "answer_like_columns": answer_like,
        "task_count": len(rows),
        "pack_sha256": sha256_tree(pack_dir),
        "solver_view_sha256": sha256_tree(solver_dir),
        "scorer_view_sha256": sha256_tree(scorer_dir),
        "leakage_check": leakage_check(solver_dir),
    }
    (views_dir / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    return manifest


def leakage_check(solver_dir: Path) -> dict[str, Any]:
    tasks = [json.loads(l) for l in (solver_dir / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    offending = sorted({k for t in tasks for k in t.keys() if k not in {"id", "image", "prompt"}})
    answerish = sorted({k for k in offending if ANSWER_KEY_RE.search(k)})
    extra_files = sorted(str(p.relative_to(solver_dir)) for p in solver_dir.rglob("*")
                         if p.is_file() and not (p.name == "tasks.jsonl" or p.parent.name == "images"))
    return {"pass": not offending and not extra_files, "non_solver_keys": offending,
            "answer_like_keys": answerish, "unexpected_files": extra_files}


# ----------------------------------------------------------------------------- run
def _scrubbed_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not SECRET_ENV_RE.search(k)}
    env["CHARTOGRAPHY_BLIND_MODE"] = "1"
    return env


def solve_one(image: Path, prompt: str) -> dict[str, Any]:
    """Stage 1: the professional solver's two exact grammars. Stage 2: the
    kernel-backed general extractor (typed queries over bar/line/pie tables).
    Both are zero-model; abstention is a first-class, non-credited outcome."""
    from canonical.runtime import chartography_deterministic_professional_solver_v1 as solver
    stage1_reason = None
    try:
        out = solver.solve(image, prompt)
        return {"status": str(out.get("status") or "PASS"), "route": out.get("route") or "PROFESSIONAL_GRAMMAR",
                "answer": out.get("answer"), "raw_value": out.get("raw_value"),
                "bounded_learned_components": out.get("bounded_learned_components"),
                "general_purpose_model_dependency_count": out.get("general_purpose_model_dependency_count")}
    except Exception as exc:
        stage1_reason = f"{type(exc).__name__}__{str(exc)[:80]}"
    try:
        from canonical.runtime import chartography_general_extractor_v1 as general
        res = general.solve(image, prompt)
    except Exception as exc:  # missing numpy / unexpected failure: still an abstention
        return {"status": f"ABSTAIN__GENERAL_{type(exc).__name__}__{str(exc)[:80]}", "route": None,
                "answer": None, "raw_value": None, "stage1": stage1_reason}
    if res.get("status") == "ANSWER":
        return {"status": "PASS", "route": f"GENERAL_{res.get('chart_kind')}_{res.get('type')}",
                "answer": res.get("answer"), "raw_value": res.get("answer_numeric"),
                "certified": res.get("certified"), "certificate": res.get("certificate"),
                "bounded_learned_components": ["tesseract_ocr"], "general_purpose_model_dependency_count": 0,
                "stage1": stage1_reason}
    return {"status": str(res.get("status")), "route": None, "answer": None, "raw_value": None,
            "stage1": stage1_reason}


def run_solver(views_dir: Path, results_path: Path, solver: Callable[[Path, str], dict[str, Any]] | None = None,
               timeout_s: int = 180) -> dict[str, Any]:
    solver_dir = views_dir / "solver_view"
    scorer_dir = views_dir / "scorer_view"
    tasks = [json.loads(l) for l in (solver_dir / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    lc = leakage_check(solver_dir)
    if not lc["pass"]:
        raise SystemExit(f"FAIL_CLOSED__LEAKAGE_CHECK__{lc}")
    sealed = False
    try:
        if scorer_dir.exists():
            os.chmod(scorer_dir, 0)
            sealed = True
        with open(results_path, "w", encoding="utf-8") as out:
            for t in tasks:
                image = solver_dir / t["image"]
                if solver is not None:
                    res = solver(image, t["prompt"])
                else:
                    cmd = [sys.executable, "-m", "canonical.runtime.chartography_blind_harness_v1", "solve-one",
                           "--image", str(image), "--prompt", t["prompt"]]
                    try:
                        proc = subprocess.run(cmd, cwd=str(REPO_ROOT), env=_scrubbed_env(), capture_output=True,
                                              text=True, timeout=timeout_s)
                        res = json.loads(proc.stdout.strip().splitlines()[-1]) if proc.stdout.strip() else \
                            {"status": f"ABSTAIN__NO_OUTPUT__rc={proc.returncode}", "answer": None, "raw_value": None}
                    except subprocess.TimeoutExpired:
                        res = {"status": "ABSTAIN__TIMEOUT", "answer": None, "raw_value": None}
                    except Exception as exc:
                        res = {"status": f"ABSTAIN__{type(exc).__name__}", "answer": None, "raw_value": None}
                res.update({"id": t["id"], "question_type": classify_question(t["prompt"])})
                out.write(json.dumps(res, default=str) + "\n")
    finally:
        if sealed:
            os.chmod(scorer_dir, stat.S_IRWXU)
    return {"tasks": len(tasks), "results_sha256": sha256_file(results_path), "scorer_view_sealed_during_run": sealed,
            "isolation": "SUBPROCESS_SCRUBBED_ENV" if solver is None else "IN_PROCESS_CALLABLE"}


# ----------------------------------------------------------------------------- score
_NUM_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def _to_float(v: Any) -> float | None:
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        m = _NUM_RE.search(v.replace(",", ""))
        return float(m.group(0)) if m else None
    return None


def _normalize(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s)).strip().casefold().rstrip(".")


def _gold_from_row(row: dict[str, Any]) -> tuple[str, Any, tuple[float, float] | None]:
    """Return (semantics, gold, range)."""
    keys = {k.lower(): k for k in row.keys() if k != "id"}
    rng = None
    for a, b in (("min", "max"), ("lower", "upper"), ("low", "high"), ("accepted_min", "accepted_max")):
        if a in keys and b in keys:
            lo, hi = _to_float(row[keys[a]]), _to_float(row[keys[b]])
            if lo is not None and hi is not None:
                rng = (lo, hi)
    for k in keys:
        if "range" in k or "accepted" in k or "tolerance" in k:
            v = row[keys[k]]
            if isinstance(v, (list, tuple)) and len(v) == 2 and all(_to_float(x) is not None for x in v):
                rng = (_to_float(v[0]), _to_float(v[1]))
            elif isinstance(v, str) and v.count(",") == 1 and all(_to_float(x) is not None for x in v.strip("[]() ").split(",")):
                a, b = v.strip("[]() ").split(",")
                rng = (_to_float(a), _to_float(b))
    gold_key = None
    for cand in ("answer", "gold", "label", "solution", "target", "expected", "ground_truth", "correct_answer"):
        for k in keys:
            if cand in k and "range" not in k and "tolerance" not in k:
                gold_key = keys[k]
                break
        if gold_key:
            break
    gold = row.get(gold_key) if gold_key else None
    if rng is not None:
        return "EXPLICIT_RANGE", gold, rng
    if _to_float(gold) is not None:
        return "NUMERIC_REL_TOL_5PCT__ASSUMED_NOT_OFFICIAL", gold, None
    if gold is not None:
        return "NORMALIZED_EXACT_MATCH__ASSUMED_NOT_OFFICIAL", gold, None
    return "NO_GOLD_RESOLVED__FAIL_CLOSED", None, None


def score(results_path: Path, views_dir: Path, rel_tol: float = 0.05) -> dict[str, Any]:
    answers = {str(json.loads(l)["id"]): json.loads(l) for l in (views_dir / "scorer_view" / "answers.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    results = [json.loads(l) for l in results_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    per_task, semantics_counter, taxonomy = [], {}, {}
    n_pass = n_attempt = n_abstain = 0
    for r in results:
        gold_row = answers.get(str(r["id"]))
        if gold_row is None:
            raise SystemExit(f"FAIL_CLOSED__RESULT_WITHOUT_GOLD_ROW__{r['id']}")
        semantics, gold, rng = _gold_from_row(gold_row)
        semantics_counter[semantics] = semantics_counter.get(semantics, 0) + 1
        attempted = not str(r.get("status", "")).startswith("ABSTAIN")
        value = _to_float(r.get("raw_value")) if r.get("raw_value") is not None else _to_float(r.get("answer"))
        passed = False
        if attempted and semantics != "NO_GOLD_RESOLVED__FAIL_CLOSED":
            if rng is not None:
                passed = value is not None and rng[0] <= value <= rng[1]
            elif semantics.startswith("NUMERIC"):
                g = _to_float(gold)
                passed = value is not None and g is not None and abs(value - g) <= max(1e-9, rel_tol * abs(g))
            else:
                passed = _normalize(r.get("answer")) == _normalize(gold)
        n_attempt += int(attempted)
        n_abstain += int(not attempted)
        n_pass += int(passed)
        qt = r.get("question_type", "UNCLASSIFIED")
        cell = taxonomy.setdefault(qt, {"tasks": 0, "attempted": 0, "pass": 0})
        cell["tasks"] += 1
        cell["attempted"] += int(attempted)
        cell["pass"] += int(passed)
        per_task.append({"id": r["id"], "question_type": qt, "status": r.get("status"), "route": r.get("route"),
                         "attempted": attempted, "pass": passed, "semantics": semantics})
    n = len(results)
    return {
        "schema": SCHEMA + "__RECEIPT",
        "task_count": n,
        "attempted": n_attempt,
        "abstained": n_abstain,
        "passed": n_pass,
        "score_percent": round(100.0 * n_pass / n, 3) if n else None,
        "target_percent": 89.0,
        "meets_target_under_assumed_semantics": bool(n and 100.0 * n_pass / n >= 89.0),
        "scorer_semantics_used": semantics_counter,
        "scorer_semantics_label": "ASSUMED__NOT_THE_OFFICIAL_CHARTOGRAPHY_GRADER__BIND_OFFICIAL_SEMANTICS_BEFORE_ANY_CLAIM",
        "taxonomy_census": taxonomy,
        "per_task": per_task,
        "gold_values_in_receipt": False,
        "accounting": {"incremental_spend_usd": 0, "acceptance_credit_delta": 0, "capability_credit_delta": 0,
                       "ownership_credit_delta": 0, "terminal_credit_delta": 0},
        "hard_nonclaims": ["NOT_AN_OFFICIAL_CHARTOGRAPHY_SCORE", "NO_FAMILY_OR_ATOM_PROMOTION",
                           "NO_GENERAL_PURPOSE_MODEL_COGNITION_IN_SOLVER_PATH__BOUNDED_OCR_ONLY"],
    }


# ----------------------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("build-pack"); p.add_argument("--parquet", required=True); p.add_argument("--pack", required=True)
    p = sub.add_parser("build-views"); p.add_argument("--pack", required=True); p.add_argument("--views", required=True)
    p = sub.add_parser("run"); p.add_argument("--views", required=True); p.add_argument("--results", required=True)
    p = sub.add_parser("score"); p.add_argument("--views", required=True); p.add_argument("--results", required=True); p.add_argument("--receipt", required=True)
    p = sub.add_parser("solve-one"); p.add_argument("--image", required=True); p.add_argument("--prompt", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "build-pack":
        print(json.dumps(build_pack_from_parquet(Path(a.parquet), Path(a.pack)), indent=1))
    elif a.cmd == "build-views":
        m = build_views(Path(a.pack), Path(a.views))
        print(json.dumps({k: v for k, v in m.items() if k != "columns"} | {"columns": m["columns"]}, indent=1))
    elif a.cmd == "run":
        print(json.dumps(run_solver(Path(a.views), Path(a.results)), indent=1))
    elif a.cmd == "score":
        rec = score(Path(a.results), Path(a.views))
        Path(a.receipt).write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({k: rec[k] for k in ("task_count", "attempted", "abstained", "passed", "score_percent",
                                              "meets_target_under_assumed_semantics", "scorer_semantics_used")}, indent=1))
    elif a.cmd == "solve-one":
        print(json.dumps(solve_one(Path(a.image), a.prompt), default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
