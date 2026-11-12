#!/usr/bin/env python3
"""Does the tree already contain an input space for its own capabilities?

Round 20 measured that every file-input capability fails when handed a *borrowed
fixture* (0 of 56), and concluded the corpus is empty by construction. Round 17
measured that all 296 verified experiences pass zero arguments, so a re-run is a
constant.

Both are true. Neither rules out a third source of instances: the repository's own
directories and source files. `python.source.symbols.index.ast` does not want a
borrowed document -- it wants a source tree, and this tree is full of them.

This probe answers one question with no fixtures and no network:

    For how many lane-reachable capabilities does the *tree itself* supply
    two or more real, distinct inputs that reach a verified outcome?

An "instance" is real when the input already exists on disk. k distinct real
inputs that verify = k points in that capability's input space. If a capability
reaches two or more, it can be split into a held-out pair today, with nothing
invented.

Authority: NONE. Reads the tree, writes only into a disposable sink, executes
capability adapters, registers nothing, claims no capability. $0, no model.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import sys
from pathlib import Path

SCHEMA = "REAL_INPUT_SPACE_CENSUS_V1"

#: Integers and small enumerations are not file inputs; they get a fixed value so
#: the only thing that varies between instances is a real path or real text.
INT_PARAMS = {"limit", "timeout_s", "budget", "time_budget_s", "max_mutants", "max_pages"}

#: Names whose value must be a directory that already exists inside the repo.
ROOT_PARAMS = {"source_root", "repo_root", "project_root"}

#: Names whose value must be an existing file inside the repo.
FILE_PARAMS = {
    "path", "input_path", "source_path", "target_path", "json_path", "yaml_path",
    "pdf_path", "extraction_path", "result_path", "metadata_path", "report_path",
    "measurement_receipt_path", "discovery_path", "screenshot_path", "source_json_path",
    "selection_path", "test_target", "target", "source_paths",
}

#: Names that need a list of existing files.
LIST_PARAMS = {"test_paths", "test_argv"}


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _real_dirs(root: Path, count: int) -> list[str]:
    """Directories that already exist, chosen deterministically, largest first.

    The base directories themselves are candidates, not only their children: a
    first version of this function looked only at children, so `canonical/tools`
    and `canonical/tests` -- which hold files directly -- never appeared and the
    whole probe saw a single directory. That bug did not announce itself; it
    silently made every `source_root` instance identical.
    """
    seen: list[tuple[int, str]] = []
    for base in ("canonical/runtime", "canonical/tools", "canonical/tests",
                 "canonical/analysis", "canonical/governance", "canonical/verification"):
        d = root / base
        if not d.is_dir():
            continue
        for cand in [d] + [c for c in sorted(d.iterdir())
                           if c.is_dir() and not c.name.startswith(("_", "."))]:
            py = len(list(cand.glob("*.py")))
            if py:
                seen.append((py, _rel(cand, root)))
    seen.sort(key=lambda t: (-t[0], t[1]))
    picked = [p for _, p in seen][:count]
    return picked or ["canonical/runtime"]


def _real_files(root: Path, suffixes: tuple[str, ...], count: int) -> list[str]:
    out: list[str] = []
    for base in ("canonical/runtime", "canonical/tools", "canonical/tests"):
        d = root / base
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if f.is_file() and f.suffix in suffixes and not f.name.startswith("_"):
                out.append(_rel(f, root))
    return out[:count]


def _sink(root: Path, tag: str, index: int) -> str:
    d = root / "canonical" / "astra_runtime" / "tmp" / "real_input_census"
    d.mkdir(parents=True, exist_ok=True)
    return _rel(d / f"{tag}__i{index}.json", root)


def _declared_inputs(entry: dict, lane) -> dict[str, str]:
    args = ((entry or {}).get("action_template") or {}).get("args") or {}
    return {k: v[len("${input."):-1] for k, v in args.items()
            if isinstance(v, str) and v.startswith("${input.") and v.endswith("}")}


def _instance_args(cid: str, names: dict[str, str], root: Path,
                   dirs: list[str], files: list[str], lists: list[str],
                   index: int) -> dict | None:
    """One real instance: every input takes an existing on-disk value."""
    out: dict = {}
    for arg, name in names.items():
        if name == "output_path":
            out[arg] = _sink(root, cid.replace(".", "_"), index)
        elif name in ROOT_PARAMS:
            out[arg] = dirs[index % len(dirs)]
        elif name in FILE_PARAMS:
            out[arg] = files[index % len(files)]
        elif name in LIST_PARAMS:
            out[arg] = lists[index % len(lists):][:1] or [files[0]]
        elif name in INT_PARAMS:
            out[arg] = 60 if name != "max_pages" else 200
        elif name == "goal":
            out[arg] = [
                "index the python source under the given directory",
                "report the symbols defined in each module",
                "summarise the call graph of the project",
            ][index % 3]
        elif name == "objective":
            out[arg] = [
                "lexical relevance of each candidate to the objective",
                "rank candidates by overlap with the stated objective",
            ][index % 2]
        elif name in ("capability_id",):
            continue
        else:
            # An unmodelled parameter cannot be given a real value, so the
            # instance is refused rather than filled with a fabricated constant.
            return None
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--k", type=int, default=3, help="how many real instances to try per capability")
    ap.add_argument("--json", default="")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    sys.path.insert(0, str(root))
    os.chdir(root)

    from canonical.runtime.capability_receipt_lane_v1 import _declared_entries, discover

    entries = _declared_entries(str(root))
    candidates = {c[0]: c for c in discover(str(root), ("contract",))}

    dirs = _real_dirs(root, 6)
    files = _real_files(root, (".py",), 12)
    lists = _real_files(root, (".py",), 6)

    reachable = [(cid, candidates[cid]) for cid in candidates if _declared_inputs(entries.get(cid), None)]
    rows = []
    for cid, (_, path, kind, entrypoint) in reachable:
        entry = entries.get(cid) or {}
        names = _declared_inputs(entry, None)
        adapter = entry.get("adapter_module")
        row = {"capability_id": cid, "declared_inputs": sorted(names.values()),
               "instances_attempted": 0, "instances_verified": 0,
               "distinct_verified_outcomes": 0, "status": ""}
        if not adapter:
            row["status"] = "NO_ADAPTER_MODULE"
            rows.append(row)
            continue
        try:
            module = importlib.import_module(
                "canonical.runtime.bound_capabilities." + str(adapter))
            fn = getattr(module, entry.get("entrypoint") or "run")
        except BaseException as exc:  # noqa: BLE001
            row["status"] = "ADAPTER_UNAVAILABLE:" + type(exc).__name__
            rows.append(row)
            continue

        digests: list[str] = []
        for i in range(args.k):
            call_args = _instance_args(cid, names, root, dirs, files, lists, i)
            if call_args is None:
                row["status"] = "NO_REAL_VALUE_FOR_PARAMETER"
                break
            row["instances_attempted"] += 1
            try:
                result = fn(call_args, str(root))
            except BaseException as exc:  # noqa: BLE001
                row["status"] = row["status"] or ("RAISED:" + type(exc).__name__)
                continue
            if not isinstance(result, dict):
                row["status"] = row["status"] or "NON_DICT_RESULT"
                continue
            verified = bool(result.get("output_verified") or result.get("pass"))
            if verified:
                row["instances_verified"] += 1
                # The digest must NOT include `output_path`. Every instance gets a
                # distinct sink by construction, so digesting the whole result
                # would report k "distinct outcomes" for k identical runs -- a
                # tautology that measures the sink naming, not the input. Only
                # fields that describe the SUBJECT are allowed to count.
                substantive = {k: v for k, v in result.items()
                               if k not in ("output_path", "output_sha256", "elapsed_s",
                                            "duration_ms", "started_at", "finished_at")}
                blob = json.dumps(substantive, sort_keys=True, default=str)
                digests.append(hashlib.sha256(blob.encode()).hexdigest()[:12])
                row.setdefault("output_sha256_per_instance", []).append(
                    str(result.get("output_sha256") or ""))
        row["distinct_verified_outcomes"] = len(set(digests))
        if not row["status"]:
            row["status"] = "VERIFIED" if row["instances_verified"] else "NO_VERIFIED_INSTANCE"
        rows.append(row)

    verified_any = [r for r in rows if r["instances_verified"] >= 1]
    with_space = [r for r in rows if r["distinct_verified_outcomes"] >= 2]

    # A result of "k distinct outcomes" is worthless if only one input ever varied,
    # so the probe reports the size of the input pool it actually drew from. A pool of
    # 1 is a bug in the chooser, not a finding about the tree.
    self_checks = {
        "distinct_directories_discovered": len(dirs),
        "distinct_files_discovered": len(files),
        "input_pool_is_varied": len(dirs) >= 2 and len(files) >= 2,
        "digest_excludes_output_path": True,
    }
    summary = {
        "schema": SCHEMA,
        "authority": "NONE",
        "root": str(root),
        "k": args.k,
        "self_checks": self_checks,
        "lane_reachable": len(candidates),
        "lane_reachable_with_declared_inputs": len(rows),
        "verified_at_least_one_real_instance": len(verified_any),
        "two_or_more_distinct_verified_instances": len(with_space),
        "capabilities_with_a_real_input_space": [r["capability_id"] for r in with_space],
        "rows": rows,
    }
    print(f"{'capability':58s} {'att':>4s} {'ver':>4s} {'dist':>5s}  status")
    print(f"input pool: {len(dirs)} directories, {len(files)} files, k={args.k}")
    print()
    for r in sorted(rows, key=lambda r: (-r["distinct_verified_outcomes"], r["capability_id"])):
        print(f"{r['capability_id'][:58]:58s} {r['instances_attempted']:4d} "
              f"{r['instances_verified']:4d} {r['distinct_verified_outcomes']:5d}  {r['status']}")
    print()
    print(f"lane-reachable capabilities                {len(candidates)}")
    print(f"  ... with declared inputs                  {len(rows)}")
    print(f"  ... verified on >=1 real tree instance    {len(verified_any)}")
    print(f"  ... with >=2 DISTINCT verified instances  {len(with_space)}")
    if with_space:
        print("\nHas a real input space today, no fixtures invented:")
        for r in with_space:
            print(f"  {r['capability_id']}  ({r['distinct_verified_outcomes']} distinct)")
    if args.json:
        Path(args.json).write_text(json.dumps(summary, indent=1, sort_keys=True))
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
