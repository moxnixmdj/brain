"""What can this brain actually do? Measured, not counted.

The premise this answers: *"we have tremendous hidden capabilities under non-obvious names, and they
need to be at the unified model."* That is a claim about coverage, and coverage has three layers
that had never been measured together:

1. **Reachable** -- will the unified model's import closure even load the module?
2. **Sayable** -- does the routing index contain the words a person would use to ask for it?
3. **Routable** -- given a sentence, does the model send it to that module?

Measured 2026-11-24 on this repository: 2,247 runtime modules, 580 reachable (26%), and the largest
ones are reachable but not sayable. `computer_env_v1.py` (138 KB, "the computer itself, as an
environment the learner can act in") is reachable, and the router has **zero** postings for the word
`computer` -- so "act on the computer as an environment" routes to `shell.command.run`.

The three layers are separate gates. A module that fails layer 2 is not a missing capability; it is
an unread one.

Run: ``python3 -m canonical.tools.capability_concept_coverage_v1``
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys
from typing import Any

CLAUSE = (
    "A capability is present only if it is installable, reachable, sayable, and routable -- in that "
    "order. Layer 0 is the environment: a capability whose source cannot import is not a capability. "
    "Layer 1 is the import graph, layer 2 is the vocabulary a person can ask in, layer 3 is whether a "
    "sentence lands. Only the fourth is a capability."
)

# Concepts the mechanisms in this repository actually implement, in the words their own authors
# used. If the router cannot act on one of these, a request phrased with it cannot reach the code.
MECHANISM_CONCEPTS = (
    "route", "routing", "compile", "compiler", "bind", "binding", "derive", "derivation",
    "environment", "computer", "organ", "self-improvement", "acceptance", "admission",
    "verify", "trace", "ledger", "repair", "localize", "policy", "metamorphic", "oracle",
    "bisimulation", "continual", "forget", "transfer", "curriculum", "attention",
)


def _first_sentence(path: pathlib.Path) -> str:
    try:
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8", errors="replace")))
    except SyntaxError:
        return ""
    if not doc:
        return ""
    flat = " ".join(doc.split())
    return " ".join(flat.split(". ")[0].split())


def _installability(base: pathlib.Path, model: Any) -> dict[str, Any]:
    """Layer 0: can a BOUND capability's own source file import at all in this environment?

    This is separate from reachability on purpose. A module can sit in the unified model's import
    closure -- byte-current, pinned, indexed -- and still fail to load because one third-party
    package is absent. Measured 2026-11-24: 153 bound capabilities, 101 with a resolvable
    source_path, 92 load, and the 9 failures are all `ModuleNotFoundError: PIL`. Pillow was in
    neither requirements manifest. The lesson is the layer, not the package: a capability that
    cannot import is not a capability, and nothing in the model's index knew that.
    """
    import collections
    import importlib.util

    bound = {
        cid: rec for cid, rec in model.capabilities.items()
        if rec.get("kind") == "BOUND_CAPABILITY"
    }
    missing: collections.Counter[str] = collections.Counter()
    other: collections.Counter[str] = collections.Counter()
    with_path = loaded = 0
    for cid, record in bound.items():
        path = (record.get("provenance") or {}).get("source_path")
        if not path or not (base / path).is_file():
            continue
        with_path += 1
        try:
            spec = importlib.util.spec_from_file_location("coverage_probe", base / path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore[union-attr]
            loaded += 1
        except ModuleNotFoundError as exc:
            missing[(exc.name or "?").split(".")[0]] += 1
        except BaseException as exc:  # noqa: BLE001 - report, never crash the report
            other[type(exc).__name__] += 1
    return {
        "bound": len(bound),
        "with_resolvable_source_path": with_path,
        "loaded": loaded,
        "fail_missing_module": dict(missing.most_common()),
        "fail_other": dict(other.most_common()),
        "unresolvable_source_path": len(bound) - with_path,
    }


def _speed(base: pathlib.Path, model: Any, *, calls: int = 40) -> dict[str, Any]:
    """The standing law: everything must be insanely fast. Measure, never assert.

    Two different questions, two orders of magnitude apart in cost:

    * "which capability?"   -- index lookup, sub-millisecond
    * "can it run?"         -- TODAY answered by importing and invoking with empty args,
                              which costs the module's own import plus its failure path.

    The second is the one that violates the law, and the fix that makes it fast is a
    deletion: a declared contract turns a 1.33 ms p50 try-and-fail into a 0.058 us
    dict get. Measured 2026-11-24 over all 101 loadable BOUND capabilities.
    """
    import statistics
    import time

    sentences = (
        "route this sentence to the right capability",
        "compile the goal into a deterministic plan",
        "act on the computer as an environment",
        "verify the tar archive checksum",
        "query the yaml file with yq",
    )
    samples: list[float] = []
    for _ in range(calls):
        for sentence in sentences:
            start = time.perf_counter()
            model.route(sentence)
            samples.append((time.perf_counter() - start) * 1000)
    samples.sort()

    start = time.perf_counter()
    bound = [
        cid for cid, rec in model.capabilities.items()
        if rec.get("kind") == "BOUND_CAPABILITY"
    ]
    probe = {cid: {"args": []} for cid in bound}
    rounds = 2000
    for _ in range(rounds):
        for cid in bound:
            probe.get(cid)
    contract_us = ((time.perf_counter() - start) / (rounds * max(len(bound), 1))) * 1e6

    def pct(q: float) -> float:
        return samples[max(int(len(samples) * q) - 1, 0)]

    return {
        "route_p50_ms": round(pct(0.50), 4),
        "route_p90_ms": round(pct(0.90), 4),
        "route_p99_ms": round(pct(0.99), 4),
        "route_mean_ms": round(statistics.mean(samples), 4),
        "declared_contract_lookup_us": round(contract_us, 4),
        "note": "route() answers 'which capability' in the sub-millisecond regime; the "
                "slow path is discovering by crashing, which a declared contract deletes",
    }


def coverage(root: str | pathlib.Path = ".", *, large_only_bytes: int = 50_000) -> dict[str, Any]:
    base = pathlib.Path(root).resolve()
    sys.path.insert(0, str(base))
    from canonical.runtime.brain_owned_python_closure_census_v1 import census
    from canonical.runtime.brain_unified_model_v1 import open_model, tokenize

    closure = census(str(base), ["canonical/runtime/brain_unified_model_v1.py"])
    reachable = {row["path"] for row in closure["brain_owned_transitive_files"] if isinstance(row, dict)}

    model = open_model(root=str(base))
    index_tokens = set(model.index)
    askable_modules: set[str] = set()
    for capability_id, record in model.capabilities.items():
        if record.get("kind") != "BOUND_CAPABILITY":
            continue
        provenance = record.get("provenance") or {}
        path = provenance.get("source_path")
        if not path and str(capability_id).startswith("canonical/"):
            path = str(capability_id).split(".auto.v1")[0]
        if path:
            askable_modules.add(str(path))

    modules: list[dict[str, Any]] = []
    for path in sorted((base / "canonical" / "runtime").glob("*.py")):
        rel = path.relative_to(base).as_posix()
        claims = _first_sentence(path)
        tokens = tokenize(claims) if claims else []
        usable = [t for t in tokens if t in index_tokens]
        modules.append({
            "module": rel,
            "bytes": path.stat().st_size,
            "reachable": rel in reachable,
            "askable": rel in askable_modules,
            "claims": claims,
            "claim_tokens": len(tokens),
            "sayable_tokens": len(usable),
            "sayable_share": round(len(usable) / len(tokens), 4) if tokens else None,
        })

    mechanisms = [row for row in modules if row["reachable"] and row["bytes"] >= large_only_bytes]
    concept_rows = []
    for concept in MECHANISM_CONCEPTS:
        concept_rows.append({
            "concept": concept,
            "in_index": concept in index_tokens,
            "postings": len(model.index.get(concept) or {}),
        })

    layer_zero = _installability(base, model)

    total_bytes = sum(row["bytes"] for row in modules)
    return {
        "schema": "PROJECT_BRAIN_CAPABILITY_CONCEPT_COVERAGE_V1",
        "clause": CLAUSE,
        "modules": len(modules),
        "total_bytes": total_bytes,
        "reachable": sum(1 for row in modules if row["reachable"]),
        "askable": sum(1 for row in modules if row["askable"]),
        "routable_note": "askable is the layer the router can send a sentence to",
        "large_mechanisms": {
            "threshold_bytes": large_only_bytes,
            "count": len(mechanisms),
            "bytes": sum(row["bytes"] for row in mechanisms),
            "sayable_share_mean": (
                round(sum(row["sayable_share"] or 0 for row in mechanisms) / len(mechanisms), 4)
                if mechanisms else None
            ),
            "rows": [
                {k: row[k] for k in ("module", "bytes", "claims", "sayable_share")}
                for row in sorted(mechanisms, key=lambda r: -r["bytes"])
            ],
        },
        "layer_zero": layer_zero,
        "speed": _speed(base, model),
        "concepts": concept_rows,
        "concepts_unusable": [row["concept"] for row in concept_rows if not row["in_index"]],
        "modules_detail": modules,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = coverage(args.root)
    if args.json:
        report.pop("modules_detail", None)
        print(json.dumps(report, indent=1))
        return 0
    print(f"  {report['clause']}\n")
    print(f"  runtime modules                   : {report['modules']}")
    print(f"  reachable from the unified model  : {report['reachable']}"
          f"  ({report['reachable'] / report['modules'] * 100:.0f}%)")
    print(f"  registered as an askable capability: {report['askable']}"
          f"  ({report['askable'] / report['modules'] * 100:.0f}%)")
    mech = report["large_mechanisms"]
    print(f"\n  reachable mechanisms >= {mech['threshold_bytes'] // 1000} KB: {mech['count']}"
          f"  ({mech['bytes'] / 1e6:.2f} MB)")
    print(f"  their claims, share of tokens the router can act on: {mech['sayable_share_mean']}")
    print(f"\n  {'module':40s} {'KB':>6s}  sayable")
    for row in mech["rows"][:10]:
        name = row["module"].split("/")[-1]
        print(f"  {name[:40]:40s} {row['bytes'] // 1024:6d}  {row['sayable_share']}")
    lz = report["layer_zero"]
    sp = report["speed"]
    print(f"\n  SPEED (the standing law) route p50 {sp['route_p50_ms']} ms  p99 {sp['route_p99_ms']} ms")
    print(f"    declared-contract lookup {sp['declared_contract_lookup_us']} us")
    print(f"\n  LAYER 0 -- installability of BOUND capabilities: {lz['loaded']}/{lz['with_resolvable_source_path']} load")
    if lz["fail_missing_module"]:
        print(f"    missing modules: {lz['fail_missing_module']}")
    print(f"    no resolvable source_path: {lz['unresolvable_source_path']} of {lz['bound']}")
    print(f"\n  concepts a request cannot use (no posting in the router index):")
    print(f"    {', '.join(report['concepts_unusable']) or '(none)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
