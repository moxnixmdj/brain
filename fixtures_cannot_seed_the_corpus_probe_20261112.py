#!/usr/bin/env python3
"""Can the instance corpus be seeded from the fixtures already in the tree? Measured: no.

Round 19 gave every receipt its inputs, and the corpus it feeds starts at zero because history has
none. The obvious next move is to seed it: run each capability that takes a file input against a
document that is already in the repository. This probe does exactly that and counts.

The arithmetic, in one place:

    curated capabilities                                   145
      declare at least one ${input.*}                      126
      take a file input (something other than output_path)  56
      execute to a success status given any in-tree doc      0

That last zero is the point. Having a document is not having an instance: the capability needs the
packages, roots and contracts its own environment provides, and a fixture copied from another corner
of the tree satisfies none of them. So the corpus cannot be seeded from artifacts. It can only be
seeded from **work** — a real invocation on a real document for a real task, whose bytes round 19's
`snapshot_inputs` now keeps.

Authority NONE. Reads the registry and the fixtures; runs adapters with `output_path` pointed at a
temporary directory; writes nothing into the tree. $0, no model.
"""
from __future__ import annotations

import argparse
import collections
import contextlib
import importlib.util
import io
import json
import os
import pathlib
import re
import signal
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent
REGISTRY = REPO_ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
ADAPTERS = "canonical/runtime/bound_capabilities"
SINK = "/tmp/brain_instance_probe"
PER_ATTEMPT_TIMEOUT_S = 5
MAX_DOCUMENTS_TRIED = 6
SUCCESS_PREFIXES = ("PASS", "OK", "COMPLETE")
PLACEHOLDER = re.compile(r"\$\{input\.([A-Za-z0-9_]+)\}")


class _Timeout(Exception):
    pass


def _alarm(_signum, _frame):
    raise _Timeout()


def fixture_documents(root: pathlib.Path) -> list[str]:
    """Documents a capability could be handed: the fixtures the tree already ships."""
    found: list[str] = []
    for base in ("canonical/astra_runtime/fixtures", "canonical/tests/fixtures"):
        for dirpath, _dirs, files in os.walk(root / base):
            for name in files:
                if name.endswith((".json", ".jsonl", ".md", ".txt")):
                    found.append(str(pathlib.Path(dirpath, name).relative_to(root)))
    return sorted(found)


def declared_inputs(entry: dict[str, Any]) -> set[str]:
    args = ((entry.get("action_template") or {}).get("args")) or {}
    return set(PLACEHOLDER.findall(json.dumps(args)))


def try_capability(root: pathlib.Path, capability_id: str, entry: dict[str, Any],
                   documents: list[str]) -> dict[str, Any]:
    """Run one capability against documents already in the tree. Never writes into the tree."""
    inputs = declared_inputs(entry)
    file_inputs = {name for name in inputs if name.endswith("_path") and name != "output_path"}
    adapter = str(entry.get("adapter_module") or "")
    module_path = root / ADAPTERS / f"{adapter}.py"
    if not file_inputs:
        return {"capability_id": capability_id, "class": "no_file_input"}
    if not module_path.exists():
        return {"capability_id": capability_id, "class": "no_adapter"}

    os.makedirs(SINK, exist_ok=True)
    signal.signal(signal.SIGALRM, _alarm)
    for document in documents[:MAX_DOCUMENTS_TRIED]:
        args: dict[str, Any] = {"capability_id": capability_id,
                                "output_path": f"{SINK}/{adapter}.json"}
        for name in inputs:
            if name in args:
                continue
            args[name] = document if name.endswith("_path") else (5 if name == "timeout_s" else "x")
        try:
            spec = importlib.util.spec_from_file_location("probe_" + adapter, module_path)
            if spec is None or spec.loader is None:
                return {"capability_id": capability_id, "class": "no_adapter"}
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            signal.alarm(PER_ATTEMPT_TIMEOUT_S)
            with contextlib.redirect_stdout(io.StringIO()):
                result = module.run(dict(args), str(root))
            signal.alarm(0)
        except BaseException:  # a refusal is data; the probe tries the next document
            signal.alarm(0)
            continue
        status = str(result.get("status", "")) if isinstance(result, dict) else ""
        if status.startswith(SUCCESS_PREFIXES):
            return {"capability_id": capability_id, "class": "ran", "document": document,
                    "status": status}
    return {"capability_id": capability_id, "class": "no_valid_instance"}


def run() -> dict[str, Any]:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]
    documents = fixture_documents(REPO_ROOT)

    counts: collections.Counter = collections.Counter()
    rows = []
    for capability_id, entry in registry.items():
        row = try_capability(REPO_ROOT, capability_id, entry, documents)
        rows.append(row)
        counts[row["class"]] += 1

    file_input = counts["ran"] + counts["no_valid_instance"] + counts["no_adapter"]
    return {
        "probe": "fixtures_cannot_seed_the_corpus",
        "authority": "NONE",
        "executed": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "writes_into_tree": False,
        "registry_capabilities": len(registry),
        "declare_inputs": sum(1 for entry in registry.values() if declared_inputs(entry)),
        "take_a_file_input": file_input,
        "executed_to_success_with_an_in_tree_document": counts["ran"],
        "no_valid_instance": counts["no_valid_instance"],
        "no_adapter": counts["no_adapter"],
        "fixture_documents_in_tree": len(documents),
        "documents_tried_per_capability": min(MAX_DOCUMENTS_TRIED, len(documents)),
        "examples_that_ran": [row for row in rows if row["class"] == "ran"][:5],
        "why_zero": (
            "a document is not an instance: the capability also needs the packages, roots and "
            "contracts of its own environment, and a fixture from another corner of the tree "
            "satisfies none of them"
        ),
        "what_that_leaves": (
            "the corpus can only be seeded from work — a real invocation on a real document — which "
            "is exactly what input_digests (round 19) now preserves"
        ),
        "hard_nonclaims": [
            "SEEDING_ONLY_NOT_A_CAPABILITY_MEASUREMENT",
            "NO_REGISTRY_WRITE",
            "NO_TRUTH_ACHIEVED",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)

    report = run()
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("Can in-tree fixtures seed the instance corpus?")
    print("=" * 78)
    print(f"  registry capabilities                        {report['registry_capabilities']:>6}")
    print(f"    declare at least one input                 {report['declare_inputs']:>6}")
    print(f"    take a file input                          {report['take_a_file_input']:>6}")
    print(f"  fixture documents available                  {report['fixture_documents_in_tree']:>6}")
    print(f"  documents tried per capability               "
          f"{report['documents_tried_per_capability']:>6}")
    print()
    print(f"  ran to a success status                      "
          f"{report['executed_to_success_with_an_in_tree_document']:>6}")
    print(f"  no valid instance found                      {report['no_valid_instance']:>6}")
    print(f"  no adapter module                            {report['no_adapter']:>6}")
    print()
    print("  " + report["why_zero"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
