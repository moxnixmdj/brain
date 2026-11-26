#!/usr/bin/env python3
"""The fixes are inside coverage. So is the failure ordering, vocabulary, or something else?

THE MEASUREMENT THAT ENDS THE GUESSING
--------------------------------------
Five rounds have ended with "0 solved" and a plausible story attached to it. This tool
replaces the story with a taxonomy of the exact reason each task cannot be solved by the
current generator, computed at the level of individual *sites* rather than whole diffs.

For each task, for each line the real fix changes that lies inside coverage:

  UNDISCOVERED   the line never executes under the failing test, so no coverage-keyed
                 generator can consider it. The channel, not the grammar, failed.
  SITE_REACHED   the line executes and the generator puts a candidate on that exact line.
                 It screened the right place and the edit was wrong.
  NO_VOCABULARY  the line executes but the change is not a substitution of something
                 already on that line -- it adds statements, changes a signature, or
                 introduces a new function. No site-local substitution form can produce it.

The third class is the one worth knowing. If it dominates, then adding forms to the
substitution family cannot help, because the fixes are not substitutions, and the ceiling
for that entire family is measurable today rather than after another failed round.

Each class is also split by the operation the diff performed (ADD, DELETE, REPLACE) and by
whether the changed token appears elsewhere in the file. Those splits are what tell you
what a generator would have to be able to build.

INTEGRITY: offline corpus characterisation. The diff scores the generator; it never feeds it.
No solve claimed. Zero model calls, no stored parameters, no network at run time.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import time
from typing import Any, Sequence

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.tools import coverage_selector_measurement_v1 as COV  # noqa: E402
from canonical.tools import site_edit_space_measurement_v1 as SES  # noqa: E402

SCHEMA = "BRAIN_FIX_VOCABULARY_TAXONOMY_V1"
WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")


IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
STR_RE = re.compile(r"""(?:[rbuf]{0,2})(['\"]).*?\1""")


def shape_of(text: str) -> str:
    """A statement's shape with identifiers and literals replaced by holes.

    This is the anti-unification key. Two statements with the same shape differ only in the
    names they mention, so a repository that already contains one contains a *template* for
    the other. If the added statements in this corpus match a shape that already exists in the
    same file, an addition generator has something to instantiate. If they do not, the added
    text is genuinely new and no recombination of the file can produce it.
    """
    shaped = STR_RE.sub("<S>", text)
    shaped = IDENT_RE.sub("<I>", shaped)
    shaped = re.sub(r"\s+", " ", shaped).strip()
    return shaped


def file_shapes(text: str) -> set[str]:
    shapes: set[str] = set()
    for line in text.splitlines():
        st = line.strip()
        if len(st) >= 4:
            shapes.add(shape_of(st))
    return shapes


def op_of(old: str, new: str) -> str:
    if old and new:
        return "REPLACE"
    if new:
        return "ADD"
    return "DELETE"


def changed_tokens(old: str, new: str) -> list[str]:
    """Identifiers/words on the new side that are absent from the old side."""
    before = set(WORD_RE.findall(old))
    return [t for t in WORD_RE.findall(new) if t not in before]


def classify_task(task: dict[str, Any], plugin_dir: pathlib.Path) -> dict[str, Any]:
    root = SES.CHECKOUTS.get(task["repo"])
    if not root or not pathlib.Path(root).exists():
        return {"sha": task["sha"][:8], "status": "NO_CHECKOUT"}
    co = pathlib.Path(root)
    SES.git(co, "checkout", "-q", "--force", task["parent"])
    SES.git(co, "clean", "-qfd")
    if SES.git(co, "checkout", task["sha"], "--", task["test"]).returncode != 0:
        return {"sha": task["sha"][:8], "status": "TEST_NOT_APPLICABLE"}

    roots = SES.import_roots(task["source_files"], co)
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(plugin_dir), *roots, str(co)]),
           "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    node = task["failed_nodes"][0]
    base = SES.run_pytest(co, env, node)
    if base.returncode == 0:
        return {"sha": task["sha"][:8], "status": "NOT_FAIL_TO_PASS"}

    originals = {s: (co / s).read_text(errors="replace") for s in task["source_files"] if (co / s).exists()}
    hits = COV.run_with_coverage(co, env, node, list(originals), plugin_dir)
    covered: dict[str, set[int]] = {}
    for bucket in ("test_time", "import_time"):
        for src, lns in hits.get(bucket, {}).items():
            covered.setdefault(src, set()).update(lns)

    SES.git(co, "checkout", "-q", "--force", task["parent"])
    SES.git(co, "clean", "-qfd")
    SES.git(co, "checkout", task["sha"], "--", *task["source_files"])
    fixed = {s: (co / s).read_text(errors="replace") for s in task["source_files"] if (co / s).exists()}
    SES.git(co, "checkout", "-q", "--force", task["parent"])
    SES.git(co, "clean", "-qfd")

    sites: list[dict[str, Any]] = []
    for src, ptext in originals.items():
        ftext = fixed.get(src, ptext)
        if ptext == ftext:
            continue
        file_words = set(WORD_RE.findall(ptext))
        for ln, old, new in SES.changed_lines(ptext, ftext):
            if not (old or new):
                continue
            executes = ln in covered.get(src, set())
            tokens = changed_tokens(old, new)
            known = [t for t in tokens if t in file_words]
            op = op_of(old, new)
            if not executes:
                klass = "UNDISCOVERED"
            elif op == "REPLACE" and (old.strip() and new.strip()) and len(tokens) == 0:
                # same identifiers on both sides: a token/operator edit on one line is exactly
                # what the site-local forms emit.
                klass = "SITE_REACHED_SUBSTITUTABLE"
            elif op == "REPLACE" and tokens and len(known) == len(tokens):
                klass = "SITE_REACHED_SUBSTITUTABLE"
            else:
                klass = "NO_VOCABULARY"
            shapes_in_file = file_shapes(ptext)
            added = new.strip()
            shape_known = bool(added) and len(added) >= 6 and shape_of(added) in shapes_in_file
            sites.append({"file": src, "line": ln, "op": op, "executes": executes,
                          "class": klass, "tokens_absent_from_file": [t for t in tokens if t not in file_words][:6],
                          "new_len": len(added),
                          "added_shape_already_in_file": shape_known if op != "DELETE" else None,
                          "added_shape": shape_of(added)[:120] if added else None})

    classes: dict[str, int] = {}
    for s in sites:
        classes[s["class"]] = classes.get(s["class"], 0) + 1
    return {"sha": task["sha"][:8], "repo": task["repo"], "status": "MEASURED",
            "sites": sites, "site_classes": classes,
            "truth_sites": len(sites),
            "has_source_frame": bool(SES.traced_frames(base.stdout + base.stderr, task["source_files"]))}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ns = ap.parse_args(argv)
    started = time.time()
    plugin_dir = pathlib.Path("/tmp/brain_cover_plugin")

    tasks = json.loads(SES.CORPUS.read_text())["tasks"]
    rows = [classify_task(t, plugin_dir) for t in tasks]
    measured = [r for r in rows if r.get("status") == "MEASURED"]

    classes: dict[str, int] = {}
    ops: dict[str, int] = {}
    shape_known = shape_total = 0
    for r in measured:
        for site in r["sites"]:
            if site.get("added_shape_already_in_file") is not None:
                shape_total += 1
                shape_known += bool(site["added_shape_already_in_file"])
    for r in measured:
        for k, v in r["site_classes"].items():
            classes[k] = classes.get(k, 0) + v
        for s in r["sites"]:
            ops[s["op"]] = ops.get(s["op"], 0) + 1
    total = sum(classes.values())

    # A task is within the substitution family iff EVERY one of its changed sites is
    # substitutable. One inexpressible site and the task is out of reach, not almost reachable.
    reachable = [r for r in measured if r["sites"] and all(
        s["class"] == "SITE_REACHED_SUBSTITUTABLE" for s in r["sites"])]
    # The family this project actually ships emits ONE edit at a time. A task needing two
    # coordinated substitutions is out of reach of it even when every site is substitutable,
    # so the single-edit ceiling must be reported separately or the number flatters the tool.
    single_edit = [r for r in measured
                   if len(r["sites"]) == 1 and r["sites"][0]["class"] == "SITE_REACHED_SUBSTITUTABLE"]
    per_task = {
        "tasks_all_sites_substitutable": len(reachable),
        "tasks_reachable_by_a_single_substitution": len(single_edit),
        "tasks_with_at_least_one_substitutable_site": sum(
            1 for r in measured if any(s["class"] == "SITE_REACHED_SUBSTITUTABLE" for s in r["sites"])),
        "tasks_with_at_least_one_discovered_site": sum(
            1 for r in measured if any(s["class"] != "UNDISCOVERED" for s in r["sites"])),
        "tasks_whose_only_change_line_never_executes": sum(
            1 for r in measured if r["sites"] and all(s["class"] == "UNDISCOVERED" for s in r["sites"])),
    }

    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 1)},
        "question": "Why does a coverage-seeded generator solve 0 of 28? Per site: undiscovered, substitutable, or inexpressible?",
        "measured_tasks": len(measured),
        "changed_sites": total,
        "site_classes": classes,
        "operations": ops,
        "per_task": per_task,
        "addition_shapes": {
            "added_statements": shape_total,
            "whose_shape_already_occurs_in_the_same_file": shape_known,
            "share": round(shape_known / shape_total, 3) if shape_total else None,
            "reading": ("A shape that already occurs in the file is a template the repo supplies; "
                        "a shape that does not is text no recombination of the file can produce. "
                        "This decides whether an addition generator is worth building at all."),
        },
        "ceiling_for_the_substitution_family": (
            round(len(reachable) / len(measured), 3) if measured else None),
        "ceiling_for_a_single_edit": (
            round(len(single_edit) / len(measured), 3) if measured else None),
        "reading": ("ceiling_for_the_substitution_family is the share of tasks every one of whose "
                    "changed lines is a single-line substitution of tokens the file already has. "
                    "No amount of ranking or budget can push a substitution-only generator past it."),
        "rows": rows,
        "authority": "NONE -- offline corpus measurement; no solve claimed, no benchmark row",
    }
    pathlib.Path(ns.out).write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in
                      ("measured_tasks", "changed_sites", "site_classes", "operations", "per_task",
                       "ceiling_for_the_substitution_family", "ceiling_for_a_single_edit")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
