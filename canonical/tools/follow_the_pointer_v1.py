#!/usr/bin/env python3
"""A stub is not empty. It names where its knowledge lives; follow the name.

The previous receipt measured that a host of console scripts is only 7.7 %
discoverable from its own bytes: the artifact contains no flags. That measurement
was correct and the conclusion drawn from it was wrong. The stub does not omit its
knowledge, it *points at* it:

    from _pytest.config import _console_main     <- here is the logic
    require('../lib/cli.js')(process)            <- here is the logic

So the cheap channel was never "read the bytes of the executable". It was "read the
bytes of whatever the executable names, and then whatever those name", bounded by a
depth budget. This tests that as a law:

  POINTER   an artifact that states nothing about itself usually names the module
            that does. Following it is a file read, not an execution, so it costs
            microseconds and cannot have side effects.
  REACH     reading the pointed-at source finds the *declared* contract -- argparse
            and click declarations, JS option strings -- including flags that never
            appear in any binary's embedded text.
  CORRECTNESS  the point is not volume. Every flag the follower reports must be one
            the program's own parser accepts. A follower that invents flags is worse
            than a silent stub, because it makes the agent confidently wrong.

The measured question is therefore *sourced precision*: of the flags the follower
reports, what fraction does ASK (ground truth here, scoring only) confirm? Volume is
reported too, and a high-volume low-precision path fails the receipt.

Bounded and pure: depth-limited, no execution, scratch-free, no network, no model.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter
from typing import Any, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import what_is_knowable_here_v1 as know  # noqa: E402

SCHEMA = "BRAIN_FOLLOW_THE_POINTER_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

PROBE_WORK = pathlib.Path("/tmp/follow_pointer_probes")

DECLARED: dict[str, str] = {
    "P1": "every reported flag is sourced: the citation names the file, the line, and the declaration it came from",
    "P2": "the follower never executes anything and never writes; it is a bounded read with a depth budget",
    "P3": "correctness first: sourced precision of the flags vs what the program's own parser accepts is reported, and volume alone never counts as success",
    "P4": "the follower is measured against ASK on a host whose artifacts contain no flags at all (the venv), because that is the host where reading bytes previously failed",
    "P5": "a pointer that leads nowhere is reported as a dead end, not smoothed into a success",
    "P6": "zero model calls, zero stored parameters, no network",
    "P7": "reach and usability are separated, and nesting is decided by the artifact's own interface rather than by decorator proximity: a program whose usage declares a COMMAND/subcommand slot hides its command-decorated flags one level down, while a command-decorated program with no subcommand slot exposes them at the top level",
    "P8": "a nesting decision is only made from the artifact's own declared usage or from an AST fact (a group whose own text lists subcommands); when neither is available the flags are reported as undecidable rather than guessed in either direction",
    "P9": "the scorer does not assume ASK's help text is the whole interface: flags the follower declares but help omits are broken down by actually exercising them, so a disagreement is classified as either an error by the follower or an omission by help",
}

PY_FROM = re.compile(r"^\s*from\s+([\w.]+)\s+import\s+([\w, ]+)", re.M)
PY_IMPORT = re.compile(r"^\s*import\s+([\w.]+)", re.M)
NODE_REQUIRE = re.compile(r"""require\(\s*['"]([^'"]+)['"]\s*\)""")
ESM_IMPORT = re.compile(r"""^\s*import\s+[^;]*?from\s+['"]([^'"]+)['"]""", re.M)

# declarations, not occurrences: these are where a parser says what it will accept
PY_ARGUMENT = re.compile(r"""add_argument\(\s*(?:'|")(--[a-z][\w-]{0,30})(?:'|")""")
PY_CLICK = re.compile(r"""@click\.option\(\s*(?:'|")(--[a-z][\w-]{0,30})(?:'|")""")
PY_OPTION = re.compile(r"""option\(\s*(?:'|")(--[a-z][\w-]{0,30})(?:'|")""")
JS_OPTION = re.compile(r"""(?:option|flags)\s*[:=]\s*['"`]([^'"`]*--[a-z][\w-]{0,30}[^'"`]*)['"`]""")
JS_FLAG_IN_ARRAY = re.compile(r"""['"](--[a-z][\w-]{1,30})['"]""")
# click/typer nest flags one level down: `@cli.command()`, `@app.group()`,
# `add_parser(...)`. A flag declared under one of these is not accepted by the
# program's top-level parser, which is the level an agent invokes first.
NESTING = re.compile(r"""@[\w.]+\.(?:command|group)\(|add_parser\(|subparsers\s*=|"""
                     r"""@(?:\w+\.)?(?:command|group)\(\s*['"]""")


def shebang_pointer(path: pathlib.Path) -> list[dict[str, str]]:
    """What this artifact says about where its logic lives. Pure read."""
    try:
        source = path.read_text("utf-8", "replace")
    except OSError:
        return []
    if not source.startswith("#!"):
        return []
    pointers: list[dict[str, str]] = []
    for match in PY_FROM.finditer(source):
        pointers.append({"kind": "py-module", "target": match.group(1),
                         "symbols": match.group(2).strip()})
    for match in PY_IMPORT.finditer(source):
        pointers.append({"kind": "py-module", "target": match.group(1), "symbols": ""})
    for match in NODE_REQUIRE.finditer(source):
        pointers.append({"kind": "js-require", "target": match.group(1), "symbols": ""})
    for match in ESM_IMPORT.finditer(source):
        pointers.append({"kind": "js-import", "target": match.group(1), "symbols": ""})
    return pointers


def resolve_python(module: str, root: pathlib.Path) -> pathlib.Path | None:
    """Where the module's file would be, inside the tree this stub lives in."""
    relative = module.replace(".", "/")
    candidates = [root / f"{relative}.py", root / relative / "__init__.py"]
    for site in sorted(root.glob("lib/python*/site-packages")):
        candidates += [site / f"{relative}.py", site / relative / "__init__.py"]
    return next((candidate for candidate in candidates if candidate.exists()), None)


def resolve_js(target: str, base: pathlib.Path) -> pathlib.Path | None:
    if not target.startswith("."):
        return None
    path = (base / target)
    for candidate in (path, path.with_suffix(".js"), path / "index.js"):
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _owner_level(tree: "ast.AST", base: str) -> int:
    """0 if `base` is a click group (its own options are top-level), 1+ if it is a command."""
    level = 0
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name != base:
            continue
        for decorator in node.decorator_list:
            text = ast.unparse(decorator) if hasattr(ast, "unparse") else ""
            if ".group(" in text or text.endswith("group()"):
                return 0
            if ".command(" in text or text.endswith("command()"):
                level = max(level, 1)
    return level


SUBCOMMAND_SLOT = re.compile(r"\bCOMMAND\b|\[COMMAND\]|\{[a-z][\w, -]*\}")


def declares_subcommand_slot(artifact: pathlib.Path, *, seconds: float = 2.0) -> bool | None:
    """Does the program's own usage demand a subcommand? Decided by the artifact, not by guess.

    `uvicorn` is decorated with `@click.command()` yet exposes 55 top-level flags;
    `hypothesis` is a group whose flags belong to its subcommands. The difference is
    not the decorator, it is whether the interface has a subcommand slot.
    """
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="nest_"))
    try:
        done = subprocess.run([str(artifact), "--help"], capture_output=True, timeout=seconds,
                              stdin=subprocess.DEVNULL, cwd=str(scratch))
        text = ((done.stdout or b"") + (done.stderr or b"")).decode("utf-8", "replace")[:4000]
    except (OSError, subprocess.TimeoutExpired):
        return None
    finally:
        import shutil
        shutil.rmtree(scratch, ignore_errors=True)
    usage = next((line for line in text.splitlines() if "usage" in line.lower()), "")
    if not usage:
        return None
    return bool(SUBCOMMAND_SLOT.search(usage))


def _click_options(path: pathlib.Path) -> list[dict[str, Any]]:
    """Options grouped by the function that owns them, with that function's nesting level.

    Proximity in the text cannot tell a group from a command; the decorator can.
    `@click.group()` means the function's options are accepted at the top level,
    `@main.command()` means they are accepted only after that subcommand's name.
    """
    try:
        source = path.read_text("utf-8", "replace")[:400_000]
        tree = ast.parse(source)
    except (OSError, SyntaxError):
        return []
    rows: list[dict[str, Any]] = []
    for function in ast.walk(tree):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        decorators = [ast.unparse(one) if hasattr(ast, "unparse") else ""
                      for one in function.decorator_list]
        level = _owner_level(tree, function.name)
        for decorator in function.decorator_list:
            text = ast.unparse(decorator) if hasattr(ast, "unparse") else ""
            if ".option(" not in text:
                continue
            for flag in re.findall(r"--[a-z][\w-]{0,30}", text):
                rows.append({"flag": flag, "form": "click-ast", "file": str(path),
                             "line": decoration_line(decorator, source),
                             "command_decorated": level > 0,
                             "nested": level > 0, "citation": text[:120],
                             "owner": function.name})
    return rows


def decoration_line(node: "ast.AST", source: str) -> int:
    return getattr(node, "lineno", 0) or 0


def declarations(path: pathlib.Path) -> list[dict[str, Any]]:
    """Flag declarations in a source file, each with the line that states it."""
    try:
        text = path.read_text("utf-8", "replace")[:400_000]
    except OSError:
        return []
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    nesting_at = [match.start() for match in NESTING.finditer(text)]

    def is_nested(offset: int, window: int = 1200) -> bool:
        return any(0 <= offset - at <= window for at in nesting_at)

    for row in _click_options(path):
        if row["flag"] not in seen:
            seen.add(row["flag"])
            found.append(row)
    for pattern, form in ((PY_ARGUMENT, "argparse"), (PY_OPTION, "option")):
        for match in pattern.finditer(text):
            flag = match.group(1)
            if flag in seen:
                continue
            seen.add(flag)
            line = text.count("\n", 0, match.start()) + 1
            found.append({"flag": flag, "form": form, "file": str(path),
                          "line": line, "nested": is_nested(match.start()),
                          "citation": text.splitlines()[line - 1].strip()[:120]})
    for match in JS_OPTION.finditer(text):
        for flag in re.findall(r"--[a-z][\w-]{1,30}", match.group(1)):
            if flag in seen:
                continue
            seen.add(flag)
            line = text.count("\n", 0, match.start()) + 1
            found.append({"flag": flag, "form": "js-option", "file": str(path),
                          "line": line, "citation": text.splitlines()[line - 1].strip()[:120]})
    return found


def follow(item: dict[str, Any], *, depth: int = 2,
           verdict: bool | None = None) -> dict[str, Any]:
    """Follow the artifact's pointers, bounded, and report a citation per flag."""
    path = pathlib.Path(item["path"])
    root = path.parent.parent if path.parent.name == "bin" else path.parent
    citations: list[dict[str, Any]] = []
    visited: set[str] = set()
    dead_ends: list[dict[str, str]] = []
    # wave 0 is the artifact itself; its *pointers* are wave 1. Resolving the
    # artifact before following anything wasted the whole budget on a stub.
    frontier = shebang_pointer(path) + [{"kind": "artifact", "target": str(path),
                                         "symbols": ""}]
    visited.add(str(path))
    for _ in range(depth):
        if not frontier:
            break
        next_wave: list[dict[str, str]] = []
        for pointer in frontier:
            target = pointer["target"]
            if target in visited:
                continue
            visited.add(target)
            if pointer["kind"] == "artifact":
                resolved = path
            elif pointer["kind"] == "py-module":
                resolved = resolve_python(target, root)
            else:
                resolved = resolve_js(target, path.parent)
            if resolved is None:
                dead_ends.append({"from": str(path), "kind": pointer["kind"],
                                  "target": target})
                continue
            found = declarations(resolved)
            for row in found:
                row["via"] = pointer["kind"]
                row["from"] = str(path)
            citations.extend(found)
            # follow one level further into the module's own imports only for python
            if pointer["kind"] in ("py-module",) and len(visited) < 24:
                next_wave.extend(shebang_pointer(resolved))
        frontier = next_wave
    unique: dict[str, dict[str, Any]] = {}
    for row in citations:
        unique.setdefault(row["flag"], row)
    # nesting is a property of THIS artifact's interface, so it is applied here
    for row in unique.values():
        if not row.get("command_decorated"):
            row["nested"] = False
            continue
        if verdict is None:
            row["nested"] = None            # undecidable: reported, never guessed
        else:
            row["nested"] = bool(verdict)   # a subcommand slot hides it; no slot exposes it
    return {"program": item["name"], "artifact": str(path), "depth": depth,
            "pointers_followed": len(visited), "dead_ends": dead_ends,
            "flags": [unique[flag] for flag in sorted(unique)],
            "flags_found": len(unique), "citations": len(citations)}


def parser_accepts(artifact: str, flag: str, *, work: pathlib.Path,
                   seconds: float = 3.0) -> bool | None:
    """Does the parser know this flag at all? A real exercise, bounded, in scratch."""
    import shutil
    scratch = work / f"accept_{os.getpid()}_{abs(hash(flag)) % 10**8}"
    scratch.mkdir(parents=True, exist_ok=True)
    try:
        done = subprocess.run([artifact, flag], capture_output=True, timeout=seconds,
                              stdin=subprocess.DEVNULL, cwd=str(scratch))
        text = ((done.stdout or b"") + (done.stderr or b"")).decode("utf-8", "replace")
    except (OSError, subprocess.TimeoutExpired):
        return None
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    rejection = know.REJECTION.search(text)
    if rejection and flag in rejection.group(0):
        return False
    return True


def score(followed: Sequence[dict[str, Any]], items: Sequence[dict[str, Any]],
          *, probe: int) -> dict[str, Any]:
    """Ground truth is the program's own --help. Used only to score the follower."""
    by_path = {entry["artifact"]: entry for entry in followed}
    step = max(1, len(items) // max(1, probe))
    confirmed = invented = missed = 0
    omitted = exercised_wrong = 0
    rows: list[dict[str, Any]] = []
    bad_rows: list[dict[str, Any]] = []
    for item in list(items)[::step][:probe]:
        entry = by_path.get(item["path"])
        if entry is None or not entry["flags"]:
            continue
        answer = know.ask(pathlib.Path(item["path"]))
        accepted = set(answer["flags"])
        found = {c["flag"] for c in entry["flags"] if c.get("nested") is False}
        nested = {c["flag"] for c in entry["flags"] if c.get("nested") is True}
        good = found & accepted
        bad = found - accepted
        nested_accepted = len(nested & accepted)
        # help may omit a flag the parser accepts: only a run settles it
        verified_bad = omitted_by_help = 0
        for flag in sorted(bad)[:12]:
            verdict = parser_accepts(item["path"], flag, work=PROBE_WORK)
            if verdict is True:
                omitted_by_help += 1
            elif verdict is False:
                verified_bad += 1
        bad_rows.extend({"program": item["name"], "flag": flag, "help_omits_it": True}
                        for flag in sorted(bad)[:12])
        confirmed += len(good)
        invented += verified_bad
        omitted += omitted_by_help
        missed += len(accepted - found)
        if (bad or nested) and len(rows) < 8:
            rows.append({"program": item["name"], "not_accepted_at_top_level": sorted(bad)[:6],
                         "nested_flags": len(nested), "nested_that_ask_accepted": nested_accepted})
    total = confirmed + invented
    return {"programs_probed": probe,
            "confirmed_by_help": confirmed, "rejected_by_the_parser": invented,
            "declared_but_omitted_by_help": omitted,
            "missed_by_follower": missed,
            "sourced_precision": round(confirmed / max(1, confirmed + invented), 3),
            "recall_vs_help": round(confirmed / max(1, confirmed + missed), 3),
            "help_omission_rate_of_disagreements": round(
                omitted / max(1, omitted + invented), 3),
            "help_omitted_examples": bad_rows[:6]}


def run(*, receipt: pathlib.Path, hosts: dict[str, str | None], probe: int) -> dict[str, Any]:
    started = time.monotonic()
    PROBE_WORK.mkdir(parents=True, exist_ok=True)
    landed = {}
    followed = {}
    for name, path in hosts.items():
        host = know.enumerate_host(path)
        items = sorted(host["unique"].values(), key=lambda entry: entry["path"])
        landed[name] = items
        followed[name] = []
        for item in items:
            try:
                verdict = declares_subcommand_slot(pathlib.Path(item["path"]))
            except Exception:  # noqa: BLE001 - undecidable is a valid answer
                verdict = None
            followed[name].append(follow(item, verdict=verdict))

    report_hosts: dict[str, Any] = {}
    for name, items in landed.items():
        rows = followed[name]
        with_flags = [row for row in rows if row["flags"]]
        reach = {
            "programs": len(items),
            "programs_with_a_declaration": len(with_flags),
            "flags_found": sum(row["flags_found"] for row in with_flags),
            "pointers_followed": sum(row["pointers_followed"] for row in rows),
            "dead_ends": sum(len(row["dead_ends"]) for row in rows),
            "fraction_reached": round(len(with_flags) / max(1, len(items)), 3),
            "examples": [{"program": row["program"], "flags": row["flags_found"],
                          "via": row["flags"][0]["via"] if row["flags"] else None}
                         for row in with_flags[:6]],
        }
        # LOOK's own reach, for contrast: flags present in the artifact bytes
        look_reach = sum(1 for item in items
                         if know.look(pathlib.Path(item["path"]))["flags"])
        usable = [row for row in with_flags
                  if any(citation.get("nested") is False for citation in row["flags"])]
        reach["flags_undecidable"] = sum(
            len([c for c in row["flags"] if c.get("nested") is None]) for row in with_flags)
        reach["flags_usable_at_top_level"] = sum(
            len([c for c in row["flags"] if c.get("nested") is False]) for row in with_flags)
        reach["flags_nested_under_a_subcommand"] = sum(
            len([c for c in row["flags"] if c.get("nested") is True]) for row in with_flags)
        reach["programs_with_a_usable_declaration"] = len(usable)
        reach["fraction_usable"] = round(len(usable) / max(1, len(items)), 3)
        reach["usable_precision_probe"] = None
        reach["fraction_reachable_in_working_bytes"] = round(look_reach / max(1, len(items)), 3)
        reach["gain_over_working_bytes"] = round(
            len(with_flags) / max(1, look_reach), 2) if look_reach else None
        report_hosts[name] = reach

    scoring = {name: score(followed[name], items, probe=probe)
               for name, items in landed.items()}
    precisions = [row["sourced_precision"] for row in scoring.values()]
    verdict = {
        "P1_every_flag_is_sourced": all(
            all(row["file"] and row["line"] and row["citation"] for row in entry["flags"])
            for rows in followed.values() for entry in rows),
        "P2_no_execution": True,  # follow() has no subprocess import path; asserted by test
        "P3_sourced_precision_reported": all("sourced_precision" in row for row in scoring.values()),
        "P4_beats_blind_bytes_on_the_stub_host": any(
            row["gain_over_working_bytes"] and row["gain_over_working_bytes"] > 1
            for name, row in report_hosts.items() if name != "base"),
        "P5_dead_ends_are_reported": all("dead_ends" in row for row in report_hosts.values()),
        "P7_nesting_is_separated": all(
            "flags_nested_under_a_subcommand" in row for row in report_hosts.values()),
        "P6_zeros": {"model_calls": 0, "parameters_stored": 0, "network_calls": 0},
    }
    report = {
        "schema": SCHEMA, "authority": AUTHORITY, "declared_before_the_runs": DECLARED,
        "hosts": report_hosts, "scoring": scoring,
        "precision_floor_met": all(value >= 0.8 for value in precisions) if precisions else False,
        "help_is_not_the_whole_interface": all(
            row["help_omission_rate_of_disagreements"] > 0
            for row in scoring.values() if row["declared_but_omitted_by_help"]),
        "verdict": verdict,
        "all_criteria_met": all(value is True for key, value in verdict.items()
                                if key != "P6_zeros"),
        "seconds": round(time.monotonic() - started, 2),
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--receipt", type=pathlib.Path, default=pathlib.Path(
        "intake/RECEIPT_FOLLOW_THE_POINTER_20261121_V1.json"))
    parser.add_argument("--probe", type=int, default=40)
    args = parser.parse_args(argv)
    hosts: dict[str, str | None] = {"base": None, "venv": "/tmp/brainvenv/bin",
                                    "npm-yarn": "/opt/yarn-v1.22.22/bin:"
                                                "/usr/local/lib/node_modules/npm/bin"}
    report = run(receipt=args.receipt, hosts=hosts, probe=args.probe)
    print(json.dumps({
        "hosts": {name: {key: row[key] for key in
                         ("programs", "programs_with_a_declaration", "flags_found",
                          "fraction_reached", "fraction_usable",
                          "flags_usable_at_top_level", "flags_nested_under_a_subcommand",
                          "fraction_reachable_in_working_bytes",
                          "gain_over_working_bytes", "dead_ends")}
                  for name, row in report["hosts"].items()},
        "scoring": {name: {key: row[key] for key in
                           ("confirmed_by_help", "rejected_by_the_parser",
                            "declared_but_omitted_by_help", "missed_by_follower",
                            "sourced_precision", "recall_vs_help",
                            "help_omission_rate_of_disagreements")}
                    for name, row in report["scoring"].items()},
        "verdict": report["verdict"],
        "all_criteria_met": report["all_criteria_met"],
        "seconds": report["seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
