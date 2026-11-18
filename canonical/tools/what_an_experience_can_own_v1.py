"""What one experience can own: does the most invariant form of it reach an unseen program?

THE QUESTION
------------
*"Give the model the actions once, let it experience each, and it owns them permanently -- so it
solves everything on a computer."* The tree has measured this three times for EDIT CLASSES (1-3 of
819 pairs; 3 of 40 programs; precision 0.0 on held-out repositories) and once as an information law
(one demonstration buys at most log2|Y| bits, whatever the hypothesis space is).

Never measured: the most INVARIANT form an experience can take. A repair can be stored as the text
that was edited (a spelling: destroyed by a rename, measured 8/10 -> 1/10), as an edit class (a
shape: 1-3 of 819), or as an ANGELIC PAIR -- *this shape of site, with this value demanded, is
answered by this expression* -- which names no program, no variable and no spelling. If any form of
experience is permanent and transferable, it is that one.

So this tool takes the three angelic pairs this tree proved with the corpus's own pytest
(`force_the_value_and_see_v1`, receipt THE_FAILURE_ALREADY_SAYS_WHAT_TO_WRITE_20261118_V1) and asks
the only question that decides the claim:

    addressability  does the site's invariant shape even occur in a program never experienced?
    efficacy        when it does, does the stored expression fix that program, judged by the
                    corpus's own pytest on a fresh copy, with the answer key absent?

WHAT THE ANSWER IS WORTH
------------------------
Addressability bounds every possible memory of this kind: a shape that never recurs cannot be
recalled, whatever is stored. Efficacy then says whether the stored expression is the meaning or an
accident of the program it came from. Both are counted; neither is asserted.

Authority NONE, producer-run, zero model calls, zero network calls at run time.
"""
from __future__ import annotations

import argparse
import ast
import copy
import json
import pathlib
import random
import re
import shutil
import sys
import tempfile
import time
from typing import Any, Iterator, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import grammar_closed_repair_v1 as gen  # noqa: E402
from expressions_from_a_site_v1 import SAFE_BUILTINS  # noqa: E402

SCHEMA = "BRAIN_WHAT_AN_EXPERIENCE_CAN_OWN_V1"
UPSTREAM = "https://github.com/jkoppel/QuixBugs"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
PAIRS_RECEIPT = REPO / "canonical/verification/THE_FAILURE_ALREADY_SAYS_WHAT_TO_WRITE_20261118_V1.json"
DONOR_COUNTS = (1, 2, 4, 8, 16, 24)
SEEDS = (0, 1, 2, 3, 4)


# -------------------------------------------------------------------------------------------------- #
# 1. the invariant form: a shape names no program, no variable and no spelling
# -------------------------------------------------------------------------------------------------- #

def _free_names(text: str) -> list[str]:
    """The names the site mentions, in the order it first mentions them.

    A builtin is an OPERATION and stays literal: `len`, `max`, `sorted` mean the same thing in every
    program, and abstracting them away would make `__S0__(__S1__)` of every two-argument call. A name
    a program defines is DATA and becomes a slot: it means nothing outside the program that wrote it.
    """
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError:
        return []
    seen: list[str] = []
    for node in ast.walk(tree):  # document order is not guaranteed for every node kind
        if isinstance(node, ast.Name) and node.id not in seen and node.id not in SAFE_BUILTINS:
            seen.append(node.id)
    # ast.walk is breadth-first; re-sort by position so the slots are a property of the text alone.
    def lineno(node: ast.AST) -> tuple[int, int]:
        return (getattr(node, "lineno", 0), getattr(node, "col_offset", 0))
    order: dict[str, tuple[int, int]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id not in order and node.id not in SAFE_BUILTINS:
            order[node.id] = lineno(node)
    return sorted(seen, key=lambda name: order[name])


def shape_of(text: str) -> tuple[str, list[str]]:
    """The site's text with every free name replaced by a positional slot: `arr[0]` -> `__S0__[0]`."""
    names = _free_names(text)
    shape = text
    for index, name in enumerate(names):
        shape = re.sub(rf"(?<![A-Za-z0-9_.]){re.escape(name)}(?![A-Za-z0-9_])",
                       f"__S{index}__", shape)
    return shape, names


def templated(expression: str, names: Sequence[str]) -> str:
    """The expression with the site's names replaced by the same slots, so it can be re-pointed."""
    shape = expression
    for index, name in enumerate(names):
        shape = re.sub(rf"(?<![A-Za-z0-9_.]){re.escape(name)}(?![A-Za-z0-9_])",
                       f"__S{index}__", shape)
    return shape


def instantiate(template: str, names: Sequence[str]) -> str:
    for index, name in enumerate(names):
        template = template.replace(f"__S{index}__", name)
    return template


# -------------------------------------------------------------------------------------------------- #
# 2. every place a program makes a decision worth remembering
# -------------------------------------------------------------------------------------------------- #

def sites_of(source: str) -> list[dict[str, Any]]:
    """The same statement-level expressions the forcing instrument asks about, with their paths."""
    tree = ast.parse(source)
    function = next((node for node in tree.body if isinstance(node, ast.FunctionDef)), None)
    if function is None:
        return []
    out: list[dict[str, Any]] = []
    for path, node in gen._paths(function):  # noqa: SLF001
        targets: list[tuple[str, int | None]] = []
        if isinstance(node, (ast.Return, ast.Expr)) and getattr(node, "value", None) is not None:
            targets = [("value", None)]
        elif isinstance(node, (ast.If, ast.While)):
            targets = [("test", None)]
        elif isinstance(node, ast.Assign):
            targets = [("value", None)]
        elif isinstance(node, ast.For):
            targets = [("iter", None)]
        elif isinstance(node, ast.Call):
            targets = [("args", index) for index, _ in enumerate(node.args)]
        for field, index in targets:
            original = getattr(node, field) if index is None else node.args[index]
            if not isinstance(original, ast.expr):
                continue
            text = ast.unparse(original)
            shape, names = shape_of(text)
            out.append({"path": path + ((field, index),), "text": text, "shape": shape,
                        "names": names, "lineno": getattr(original, "lineno", 0)})
    return out


# -------------------------------------------------------------------------------------------------- #
# 3. the pairs this tree already proved
# -------------------------------------------------------------------------------------------------- #

def pairs_from_receipt(path: pathlib.Path = PAIRS_RECEIPT) -> list[dict[str, Any]]:
    """The angelic pairs, exactly as the corpus's own pytest certified them."""
    if not path.is_file():
        return []
    receipt = json.loads(path.read_text())
    pairs: list[dict[str, Any]] = []
    for row in receipt.get("rows", []):
        for attempt in row.get("attempts") or []:
            if not attempt.get("corpus_test_passes"):
                continue
            site_text = attempt.get("site")
            expression = attempt.get("expression")
            if not isinstance(site_text, str) or not isinstance(expression, str):
                continue
            shape, names = shape_of(site_text)
            pairs.append({"donor": row["task"], "site_text": site_text, "shape": shape,
                          "names": names, "expression": expression,
                          "template": templated(expression, names),
                          "questions_the_search_needed": row.get("questions_asked")})
    return pairs


# -------------------------------------------------------------------------------------------------- #
# 4. addressability: can a shape repeat in a program nobody experienced?
# -------------------------------------------------------------------------------------------------- #

def addressability(programs: dict[str, str], donor_counts: Sequence[int] = DONOR_COUNTS,
                   seeds: Sequence[int] = SEEDS) -> dict[str, Any]:
    sites = {name: sites_of(source) for name, source in programs.items()}
    names = sorted(sites)
    keys = {name: [site["shape"] for site in sites[name]] for name in names}
    rows: list[dict[str, Any]] = []
    for count in donor_counts:
        for seed in seeds:
            rng = random.Random(seed)
            if count >= len(names):
                continue   # no program left unseen: nothing to transfer to, and 0.0 would read as a failure
            donors = rng.sample(names, count)
            targets = [name for name in names if name not in donors]
            pool: set[str] = set()
            for donor in donors:
                pool.update(keys[donor])
            total = sum(len(keys[name]) for name in targets)
            hit = sum(1 for name in targets for key in keys[name] if key in pool)
            programs_reached = sum(1 for name in targets if any(key in pool for key in keys[name]))
            rows.append({"donors": count, "seed": seed,
                         "target_sites": total,
                         "target_sites_the_donors_address": hit,
                         "share": round(hit / total, 4) if total else 0.0,
                         "target_programs_with_at_least_one_addressable_site": programs_reached,
                         "target_programs": len(targets)})
    grid = {}
    for row in rows:
        grid.setdefault(row["donors"], []).append(row["share"])
    return {
        "programs": len(names),
        "shape_multiplicity": sorted(
            ({"shape": shape, "sites": sum(1 for name in names for key in keys[name] if key == shape)}
             for shape in {key for name in names for key in keys[name]}),
            key=lambda row: -row["sites"])[:12],
        "sites_per_program": {name: len(keys[name]) for name in names},
        "distinct_shapes": len({key for name in names for key in keys[name]}),
        "sites_total": sum(len(keys[name]) for name in names),
        "curve_mean_share_addressable": {count: round(sum(values) / len(values), 4)
                                         for count, values in grid.items()},
        "rows": rows,
    }


# -------------------------------------------------------------------------------------------------- #
# 5. efficacy: does the stored expression fix a program nobody experienced?
# -------------------------------------------------------------------------------------------------- #

def patched_source(source: str, site: dict[str, Any], expression: str) -> str:
    tree = ast.parse(source)
    function = next((node for node in tree.body if isinstance(node, ast.FunctionDef)), None)
    if function is None:
        raise ValueError("NO_FUNCTION")
    replacement = ast.parse(expression, mode="eval").body
    cloned = gen.replace_at(function, site["path"], replacement)  # noqa: SLF001
    tree.body = [cloned if node is function else node for node in tree.body]
    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + "\n"


def judged_by_the_corpus(root: pathlib.Path, name: str, source: str, timeout: int) -> dict[str, Any]:
    """The corpus's own pytest, on a fresh copy, with no answer key anywhere in the directory."""
    where = pathlib.Path(tempfile.mkdtemp(prefix=f"own-{name}-"))
    try:
        task = gen.build_task(root, name, where)
        (where / "python_programs" / f"{name}.py").write_text(source)
        verdict = gen.verify_with_corpus_test(where, task["test_path"], timeout)
        return {"returncode": verdict["returncode"], "timed_out": verdict["timed_out"],
                "passes": verdict["returncode"] == 0, "tail": verdict["tail"],
                "answer_key_in_task_dir": task["answer_key_in_task_dir"]}
    finally:
        shutil.rmtree(where, ignore_errors=True)


def efficacy(root: pathlib.Path, programs: dict[str, str], pairs: Sequence[dict[str, Any]],
             timeout: int, limit: int | None = None) -> dict[str, Any]:
    attempted: list[dict[str, Any]] = []
    for pair in pairs:
        control = None
        donor_source = programs.get(pair["donor"])
        if donor_source is not None:
            # The control: at the donor's own site the pair must pass, or the harness is broken
            # rather than the transfer.
            same = [site for site in sites_of(donor_source) if site["shape"] == pair["shape"]
                    and site["text"] == pair["site_text"]]
            if same:
                control = judged_by_the_corpus(root, pair["donor"],
                                               patched_source(donor_source, same[0],
                                                              pair["expression"]), timeout)
        attempts = 0
        for name, source in sorted(programs.items()):
            if name == pair["donor"]:
                continue
            for site in sites_of(source):
                if site["shape"] != pair["shape"]:
                    continue
                if limit is not None and attempts >= limit:
                    break
                attempts += 1
                expression = instantiate(pair["template"], site["names"])
                try:
                    patched = patched_source(source, site, expression)
                except Exception as error:  # noqa: BLE001
                    attempted.append({"pair": pair["site_text"], "donor": pair["donor"],
                                      "target": name, "site": site["text"],
                                      "expression": expression, "stage": "PATCH_RAISED",
                                      "error": repr(error)[:200]})
                    continue
                verdict = judged_by_the_corpus(root, name, patched, timeout)
                attempted.append({"pair": pair["site_text"], "donor": pair["donor"],
                                  "target": name, "site": site["text"],
                                  "expression": expression,
                                  "stage": "VERIFIED_BY_THE_CORPUS" if verdict["passes"]
                                           else "THE_CORPUS_REFUSED",
                                  "returncode": verdict["returncode"],
                                  "timed_out": verdict["timed_out"]})
        pair_record = {"donor": pair["donor"], "site": pair["site_text"],
                       "shape": pair["shape"], "expression": pair["expression"],
                       "template": pair["template"], "control_on_the_donor": control,
                       "attempts": attempts}
        attempted.append({"pair_record": pair_record})
    per_pair = [row["pair_record"] for row in attempted if "pair_record" in row]
    for record in per_pair:
        fixed = {row["target"] for row in attempted
                 if row.get("pair") == record["site"] and row.get("donor") == record["donor"]
                 and row.get("stage") == "VERIFIED_BY_THE_CORPUS"}
        record["unseen_programs_it_fixed"] = sorted(fixed)
        record["precision_per_attempt"] = round(len(fixed) / record["attempts"], 4) \
            if record["attempts"] else None
    transfers = [row for row in attempted if row.get("stage") == "VERIFIED_BY_THE_CORPUS"]
    return {
        "pairs": per_pair,
        "attempts_total": sum(record["attempts"] for record in per_pair),
        "addressability_and_information_by_pair": [
            {"site": record["site"], "template": record["template"],
             "sites_that_match": record["attempts"],
             "unseen_programs_it_fixed": record["unseen_programs_it_fixed"],
             "precision_per_attempt": record["precision_per_attempt"]}
            for record in per_pair],
        "programs_a_stored_expression_fixed": sorted({row["target"] for row in transfers}),
        "transfers": transfers,
        "every_attempt": [row for row in attempted if "pair_record" not in row],
        "controls_passed": sum(1 for record in per_pair
                               if (record.get("control_on_the_donor") or {}).get("passes")),
    }


# -------------------------------------------------------------------------------------------------- #
# 6. what a lookup costs against what a search costs
# -------------------------------------------------------------------------------------------------- #

def cost(programs: dict[str, str], pairs: Sequence[dict[str, Any]]) -> dict[str, Any]:
    shapes: dict[str, dict[str, Any]] = {pair["shape"]: pair for pair in pairs}
    started = time.perf_counter()
    lookups = 0
    addressed = 0
    for source in programs.values():
        for site in sites_of(source):
            lookups += 1
            if site["shape"] in shapes:
                addressed += 1
    elapsed = time.perf_counter() - started
    questions_saved = sum(pair.get("questions_the_search_needed") or 0 for pair in pairs)
    return {"lookups": lookups, "addressed": addressed,
            "seconds_for_every_lookup_in_the_corpus": round(elapsed, 4),
            "microseconds_per_lookup": round(1e6 * elapsed / max(lookups, 1), 1),
            "questions_the_search_needed_to_learn_these_pairs": questions_saved,
            "measured_cost_of_one_question_ms": 7.69}


# -------------------------------------------------------------------------------------------------- #
# 7. one run
# -------------------------------------------------------------------------------------------------- #

def collect(root: pathlib.Path) -> dict[str, str]:
    programs = {}
    for path in sorted((root / "python_programs").glob("*.py")):
        if path.name.startswith(("node", "load_", "conftest")):
            continue
        if not (root / "json_testcases" / f"{path.stem}.json").is_file():
            continue
        programs[path.stem] = path.read_text()
    return programs


def summarise(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "pairs_available": len(result["efficacy"]["pairs"]),
        "controls_passed": result["efficacy"]["controls_passed"],
        "attempts_in_unseen_programs": result["efficacy"]["attempts_total"],
        "unseen_programs_a_stored_expression_fixed": len(
            result["efficacy"]["programs_a_stored_expression_fixed"]),
        "which": result["efficacy"]["programs_a_stored_expression_fixed"],
        "addressable_share_by_donor_count": result["addressability"]["curve_mean_share_addressable"],
        "distinct_shapes_over_sites": f"{result['addressability']['distinct_shapes']}/"
                                      f"{result['addressability']['sites_total']}",
        "microseconds_per_lookup": result["cost"]["microseconds_per_lookup"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--quixbugs", type=pathlib.Path, default=pathlib.Path("/tmp/QuixBugs"))
    parser.add_argument("--receipt", type=pathlib.Path, default=None)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--limit-per-pair", type=int, default=None)
    args = parser.parse_args(argv)

    started = time.time()
    programs = collect(args.quixbugs)
    pairs = pairs_from_receipt()
    result = {
        "schema": SCHEMA, "authority": AUTHORITY, "upstream": UPSTREAM,
        "corpus_commit": (args.quixbugs / ".git").exists() and
                         (gen.subprocess.run(["git", "-C", str(args.quixbugs), "rev-parse", "HEAD"],
                                             capture_output=True, text=True).stdout.strip()),
        "tool": "canonical/tools/what_an_experience_can_own_v1.py",
        "pairs_source": str(PAIRS_RECEIPT.relative_to(REPO)),
        "model_dependency_count": 0, "external_capability_provider_count": 0,
        "network_calls_at_run_time": 0,
        "programs": len(programs),
        "addressability": addressability(programs),
        "efficacy": efficacy(args.quixbugs, programs, pairs, args.timeout, args.limit_per_pair),
        "cost": cost(programs, pairs),
        "seconds": round(time.time() - started, 1),
    }
    result["summary"] = summarise(result)
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(result, indent=1, default=str) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("efficacy",)}, indent=1,
                     default=str)[:2600])
    print(json.dumps(result["efficacy"]["pairs"], indent=1, default=str)[:1600])
    print("TRANSFERS", json.dumps(result["efficacy"]["transfers"], indent=1, default=str)[:800])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
