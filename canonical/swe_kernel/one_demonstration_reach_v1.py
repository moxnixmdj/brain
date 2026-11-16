#!/usr/bin/env python3
"""How much of a real machine does ONE demonstration reach? Measured, not argued.

THE CLAIM UNDER TEST
--------------------
"Give the agent the most advanced action once; it has learned it permanently, everywhere."
The learned-skill bundle in this tree is that mechanism at its best: four exercisable skills, each
learned from one demonstration, each carrying a premise (`set once, read once, in the statement
that directly follows`), each proving its own edit by re-parsing and comparing ASTs before writing
a byte. If one demonstration bought an action, applying the stored skill at every eligible site in
this repository should succeed at nearly every site.

So this module asks the tree's own code -- 5,513 files, 139,438 name sites -- the only question
that decides the claim:

    of every place in a real repository where the learned action could fire,
    how many does the single demonstration actually reach?

WHAT IS MEASURED
----------------
For each family that has an exercisable skill (`inline`, `rename`), a deterministic stride sample of
real sites is executed against the skill in an isolated copy of the file, and each site lands in
exactly one box:

  * VERIFIED   the file changed, the sentence matched, and everything outside the named function is
               byte-identical (`outside_digests`);
  * REFUSED    nothing was written, and the skill named the reason it declined;
  * DAMAGED    something was written and the verdict did not hold. This box must stay empty: an
               action that fires outside its premise does not fail, it mutates the world.

Refusal reasons are normalised to *classes* (identifiers and numbers replaced by `?`), because the
class -- "read twice", "bound in a nested scope", "not a plain assignment" -- is what a second
demonstration would have to teach, and the variable's name is not. The number of distinct classes a
real repository produces is the count of demonstrations the "one experience each and we are done"
plan would need, and it is discovered from the code rather than enumerated in advance.

THE TWO NUMBERS THAT DECIDE THE CLAIM
-------------------------------------
  reach                 verified / sites sampled          (how much of a machine one action covers)
  reach_where_premise   verified / sites whose premise holds (whether it does what it says)

The first is small and the second is near one, and that pair is the whole answer: the demonstration
is *perfect inside its premise* and *absent outside it*. The premise, not the environment, is what
decides where a learned action may fire, and the premise is a property of a site that can be read
without executing anything.

Nothing in this file calls, trains, or distils a model. Model calls: 0. Spend: $0.
"""
from __future__ import annotations

import ast
import json
import pathlib
import re
import sys
import tempfile
import time
from typing import Any, Iterable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # pragma: no cover - import wiring
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import learned_skill_verdict_v1 as lv  # noqa: E402

SCHEMA = "one_demonstration_reach_v1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
FAMILIES = {"inline": "inline the variable", "rename": "rename the variable"}
DEFAULT_SAMPLE = 300
DEFAULT_PATTERN = "canonical/**/*.py"
_IDENTIFIERS = re.compile(r"[A-Za-z_][A-Za-z_0-9]*|\d+")


def family_skill(family: str) -> dict[str, Any]:
    """The bundle's own skill for a family: the best instance of one demonstration that exists."""
    prefix = FAMILIES[family]
    for skill in lv.load_skills():
        if str(skill.get("goal_skeleton") or "").startswith(prefix):
            return skill
    raise LookupError("no skill in the bundle for family %r" % family)


def request_for(family: str, path: str, function: str, variable: str) -> dict[str, str]:
    if family == "rename":
        return {"path0": path, "str2": function, "str0": variable,
                "str1": variable + "_brain_renamed"}
    return {"path0": path, "str1": function, "str0": variable}


def reason_key(reason: str, *, variable: str | None = None,
               function: str | None = None) -> str:
    """The class key: the reason with the site's names and numbers removed entirely.

    Removing the tokens (rather than substituting them) is what keeps a one-letter variable from
    splitting one class into two, which it did: `a is not a variable assigned ...` and `x is not a
    variable assigned ...` are the same class and were counted as two before this.
    """
    text = str(reason)
    if variable:
        text = re.sub(r"\b%s\b" % re.escape(variable), " ", text)
    if function:
        text = re.sub(r"\b%s\b" % re.escape(function), " ", text)
    text = re.sub(r"\b\d+\b", " ", text)
    # Articles carry no class information, and one-letter variable names collide with them: removing
    # `a` from `a is not a variable assigned in apply` leaves a sentence that differs from the same
    # sentence about `x` only by the article. Measured; hence the normalisation.
    text = re.sub(r"\b(?:a|an|the)\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:140]


def reason_class(reason: str, *, variable: str | None = None,
                 function: str | None = None) -> str:
    """The class of a refusal: the site's own names and numbers taken out, the sentence kept.

    The class is what a second demonstration would have to teach -- "read twice", "bound in a
    nested scope", "not a plain assignment". The variable's name is not part of it, and neither is
    the count.
    """
    text = str(reason)
    if variable:
        text = re.sub(r"\b%s\b" % re.escape(variable), "$NAME", text)
    if function:
        text = re.sub(r"\b%s\b" % re.escape(function), "$FUNCTION", text)
    text = re.sub(r"\b\d+\b", "N", text)
    return re.sub(r"\s+", " ", text).strip()[:140]


def _features(function_node: ast.AST, variable: str) -> dict[str, Any]:
    stores, loads = 0, 0
    direct = False
    store_at: list[int] = []
    load_at: list[int] = []
    for index, statement in enumerate(function_node.body):
        if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
                and statement.targets[0].id == variable):
            direct = True
        for inner in ast.walk(statement):
            if isinstance(inner, ast.Name) and inner.id == variable:
                if isinstance(inner.ctx, ast.Store):
                    stores += 1
                    store_at.append(index)
                elif isinstance(inner.ctx, ast.Load):
                    loads += 1
                    load_at.append(index)
    adjacent = bool(store_at and load_at and min(load_at) == max(store_at) + 1)
    return {"stores": stores, "loads": loads, "direct": direct, "adjacent": adjacent}


def sites_in_file(path: str, *, repo: pathlib.Path = ROOT) -> list[dict[str, Any]]:
    """Every place in one file where a name is bound in a top-level function."""
    try:
        source = (repo / path).read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, SyntaxError, UnicodeDecodeError):
        return []
    sites: list[dict[str, Any]] = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        seen: set[str] = set()
        for statement in node.body:
            for inner in ast.walk(statement):
                if (isinstance(inner, ast.Name) and isinstance(inner.ctx, ast.Store)
                        and inner.id not in seen):
                    seen.add(inner.id)
                    sites.append({"path": path, "function": node.name, "variable": inner.id,
                                  **_features(node, inner.id)})
    return sites


def all_sites(*, repo: pathlib.Path = ROOT,
              pattern: str = DEFAULT_PATTERN) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    started = time.time()
    files = sorted(p for p in repo.glob(pattern) if p.is_file())
    sites: list[dict[str, Any]] = []
    files_with_sites = 0
    for file in files:
        found = sites_in_file(str(file.relative_to(repo)), repo=repo)
        if found:
            files_with_sites += 1
            sites.extend(found)
    return sites, {"files": len(files), "files_with_sites": files_with_sites,
                   "scan_seconds": round(time.time() - started, 2)}


def sample(sites: Sequence[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    """Deterministic stride over the whole site list: coverage of the tree, not of one corner."""
    if count <= 0 or not sites:
        return []
    if count >= len(sites):
        return list(sites)
    stride = len(sites) / float(count)
    return [sites[min(len(sites) - 1, int(index * stride))] for index in range(count)]


def _refusal_reason(stdout: str, stderr: str) -> str:
    for line in (stdout or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("REFUSED:"):
            return stripped[len("REFUSED:"):].strip()
        if stripped.startswith("REFUSED"):
            return stripped
    tail = (stderr or "").strip().splitlines()
    return ("CRASH: " + tail[-1][:120]) if tail else "NO_REASON_GIVEN"


def run_site(skill: Mapping[str, Any], site: Mapping[str, Any], *,
             repo: pathlib.Path = ROOT, python_executable: str | None = None,
             timeout_s: float = 120.0) -> dict[str, Any]:
    """Apply the learned action at one real site and say which box it lands in."""
    function_key, _variable_key = lv.claim_roles(skill)
    family = "rename" if function_key == "str2" else "inline"
    request = request_for(family, str(site["path"]), str(site["function"]),
                          str(site["variable"]))
    with tempfile.TemporaryDirectory(prefix="brain_reach_") as scratch:
        workdir = pathlib.Path(scratch)
        before = lv._copy_target(request["path0"], workdir, repo)
        run = lv.run_program(lv.source_with_request(skill, request), workdir=workdir,
                            timeout_s=timeout_s, python_executable=python_executable)
        after = lv._read_back(request["path0"], workdir)
        world = lv.judge(lv.witness_postcondition(skill, request, before), workdir=workdir, run=run)
        claim = lv.judge(lv.concrete_postcondition(skill, request), workdir=workdir, run=run)
    if world["accepted"] and claim["accepted"]:
        outcome, reason = "VERIFIED", claim["why"]
    elif after == before:
        outcome, reason = "REFUSED", _refusal_reason(str(run.get("stdout") or ""),
                                                     str(run.get("stderr") or ""))
    else:
        outcome, reason = "DAMAGED", world["why"] + "/" + claim["why"]
    return {"outcome": outcome, "reason": str(reason),
            "reason_class": reason_class(str(reason), variable=str(site["variable"]),
                                     function=str(site["function"])),
            "reason_key": reason_key(str(reason), variable=str(site["variable"]),
                                     function=str(site["function"])),
            "site": dict(site), "request": request, "returncode": run.get("returncode"),
            "file_changed": after != before}


def _premise_holds(site: Mapping[str, Any]) -> bool:
    """The stated premise, read off the site: a plain binding, set once, read once, right after."""
    return (bool(site.get("direct")) and site.get("stores") == 1 and site.get("loads") == 1
            and bool(site.get("adjacent")))


def measure(family: str, *, count: int = DEFAULT_SAMPLE, repo: pathlib.Path = ROOT,
            python_executable: str | None = None,
            sites: Sequence[dict[str, Any]] | None = None) -> dict[str, Any]:
    skill = family_skill(family)
    if sites is None:
        sites, scan = all_sites(repo=repo)
    else:
        scan = {"files": 0, "files_with_sites": 0, "scan_seconds": 0.0}
    chosen = sample(list(sites), count)
    started = time.time()
    rows = [run_site(skill, site, repo=repo, python_executable=python_executable)
            for site in chosen]
    verified = [row for row in rows if row["outcome"] == "VERIFIED"]
    refused = [row for row in rows if row["outcome"] == "REFUSED"]
    damaged = [row for row in rows if row["outcome"] == "DAMAGED"]
    held = [row for row in rows if _premise_holds(row["site"])]
    verified_in_premise = [row for row in verified if _premise_holds(row["site"])]
    residual: dict[str, int] = {}
    for row in held:
        if row["outcome"] == "VERIFIED":
            continue
        residual[row["reason_key"]] = residual.get(row["reason_key"], 0) + 1
    classes: dict[str, dict[str, Any]] = {}
    for row in refused:
        key = row["reason_key"]
        entry = classes.setdefault(key, {"count": 0, "example": row["reason_class"]})
        entry["count"] += 1
    return {
        "family": family,
        "skill_id": skill.get("skill_id"),
        "goal": skill.get("goal_skeleton"),
        "sampled": len(rows),
        "verified": len(verified),
        "refused": len(refused),
        "damaged": len(damaged),
        "damaged_sites": [row["request"] for row in damaged],
        "reach": round(len(verified) / len(rows), 4) if rows else None,
        # The documented premise has four conditions; three of them are mechanical enough to read
        # off a site (`plain binding`, `set once`, `read once`, `in the statement that directly
        # follows`). The fourth -- `the first thing the next statement computes, exactly once` --
        # is deliberately left to the skill. So this column is a PROXY, and every site inside the
        # proxy that still declined is listed by class instead of being smoothed away.
        "premise_proxy_sites": len(held),
        "premise_proxy_verified": len(verified_in_premise),
        "reach_where_premise_proxy": (round(len(verified_in_premise) / len(held), 4)
                                      if held else None),
        "premise_proxy_residual_classes": dict(sorted(residual.items(),
                                                      key=lambda item: (-item[1], item[0]))),
        "verified_outside_premise_proxy": len(verified) - len(verified_in_premise),
        "class_count": len(classes),
        "classes": dict(sorted(classes.items(),
                               key=lambda item: (-item[1]["count"], item[0]))),
        "seconds": round(time.time() - started, 2),
        "rows": rows,
    }


def measure_all(*, count: int = DEFAULT_SAMPLE, repo: pathlib.Path = ROOT,
                pattern: str = DEFAULT_PATTERN,
                python_executable: str | None = None) -> dict[str, Any]:
    sites, scan = all_sites(repo=repo, pattern=pattern)
    families = {family: measure(family, count=count, repo=repo,
                                python_executable=python_executable, sites=sites)
                for family in FAMILIES}
    sampled = sum(row["sampled"] for row in families.values())
    verified = sum(row["verified"] for row in families.values())
    damaged = sum(row["damaged"] for row in families.values())
    all_classes = sorted({klass for row in families.values() for klass in row["classes"]})
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "incremental_spend_usd": 0,
        "network_calls": 0,
        "tree": {"sites": len(sites), "direct_sites":
                 sum(1 for site in sites if site["direct"]), **scan},
        "families": families,
        "sampled": sampled,
        "verified": verified,
        "damaged": damaged,
        "reach": round(verified / sampled, 4) if sampled else None,
        "class_count": len(all_classes),
        "classes": all_classes,
        "one_demonstration_buys": (
            "%d of %d sampled sites (%.1f%%) reached by the stored demonstration; %d classes of "
            "site it declines; %d damaged"
            % (verified, sampled, 100.0 * verified / sampled if sampled else 0.0,
               len(all_classes), damaged)),
    }


def summarize(report: Mapping[str, Any]) -> str:
    lines = ["one demonstration, measured against %d real sites in %d files (%d bound directly "
             "in a function body)" % (report["tree"]["sites"], report["tree"]["files"],
                                      report["tree"]["direct_sites"]),
             "  scan: %.2fs" % report["tree"]["scan_seconds"]]
    for family, row in report["families"].items():
        where = row["reach_where_premise_proxy"]
        lines.append("  %-7s reach %.1f%% (%d/%d) | inside premise proxy %.1f%% (%d sites) | "
                     "declined %d in %d classes | damaged %d  [%.1fs]"
                     % (family, 100.0 * (row["reach"] or 0.0), row["verified"], row["sampled"],
                        100.0 * (where or 0.0), row["premise_proxy_sites"], row["refused"],
                        row["class_count"], row["damaged"], row["seconds"]))
        for _key, entry in list(row["classes"].items())[:6]:
            lines.append("        %4d  %s" % (entry["count"], entry["example"][:96]))
    lines.append("  distinct classes of site the demonstration does not cover: %d"
                 % report["class_count"])
    lines.append("  " + report["one_demonstration_buys"])
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Measure how far one learned demonstration reaches in a real repository.")
    parser.add_argument("--json", dest="json_path", default=None)
    parser.add_argument("--sample", type=int, default=DEFAULT_SAMPLE)
    parser.add_argument("--pattern", default=DEFAULT_PATTERN)
    ns = parser.parse_args(argv)
    report = measure_all(count=ns.sample, pattern=ns.pattern)
    print(summarize(report))
    if ns.json_path:
        target = pathlib.Path(ns.json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("\nwritten:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
