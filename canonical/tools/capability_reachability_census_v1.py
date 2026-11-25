"""Is a capability in the repository, or is it in the system?

`brain_owned_python_closure_census_v1` answers "how many files does the front door
transitively import?" That is a *source* census. It does not answer the question that
decides whether a capability can ever run: **can anything reach it from an entry point?**

This module answers that, and refuses to be optimistic about it:

  * the reachable set is computed by AST walk (`census`), not by regex, so a
    `from x import y` that resolves to a module counts and a string mention does not;
  * a module counts as REACHED only if it is an ancestor or descendant of an entry
    point through real imports -- co-residence in a directory counts for nothing;
  * `test_*` modules are NOT entry points for the runtime. Tests prove a capability
    works; they do not deliver it. Counting a test as reach means counting a
    capability we can demonstrate and cannot use. That is the exact confusion this
    file exists to make impossible.
  * a declaration registry (`CAPABILITY_REGISTRY_V1.json`) is an *additional* entry
    path: a module named in it is reachable by name even if nothing imports it,
    because the runtime resolves it by id. Declarations are therefore a way to
    unfreeze a module without editing the import graph -- but only for modules that
    actually exist, and only when their verifier also exists.

The output is a census, not a verdict. It does not claim an orphaned module is
worthless; a great many of them are the receipts' own helpers, generated snapshots, or
superseded copies. It claims one narrow, checkable thing: THIS FILE CANNOT BE INVOKED
FROM THE FRONT DOOR OR FROM ANY DECLARED CAPABILITY.

Authority: NONE. This is a measurement of the tree, not a capability claim.
"""
from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime.brain_owned_python_closure_census_v1 import census

SCHEMA = "PROJECT_BRAIN_CAPABILITY_REACHABILITY_CENSUS_V1"
REGISTRY_SCHEMA = "PROJECT_BRAIN_CAPABILITY_DECLARATION_REGISTRY_V1"

FRONT_DOOR = "canonical/runtime/brain_unified_model_v1.py"
FABRIC = "canonical/runtime/unified_cognitive_fabric_v1.py"
RUNTIME_DIR = "canonical/runtime"

# Concept probes are for REPORTING ONLY. Nothing here decides reachability; they
# exist so a human can see which kinds of capability are stranded. A module matching
# none of these is still counted in the population.
CONCEPT_PROBES: Mapping[str, str] = {
    "instant_learning": r"instant|one_shot|one_shot|single_experience|first_demonstration|version_space|skill_induc|program_induc",
    "generalization": r"generaliz|transfer|abstraction|analog|induction|metamorph|invariant",
    "memory": r"memory|store|retriev|episod|skill|recall|consolidat",
    "computer_use": r"gui|click|browser|dom|actuator|perceiv|ground|screen|osworld|miniwob|pixel",
    "coding": r"patch|repair|swe|synthes|localiz|fault|cegis|sygus",
    "verification": r"verif|oracle|critic|audit|prove|refut|falsif|sound",
    "world_model": r"world|simulat|mental_model|predict|tomograph",
    "meta_control": r"meta|control|polic|route|dispatch|budget|schedul|allocat",
    "self_improvement": r"self_improv|self_model|bootstrap|lift|upgrade|evolve|abduct",
}


class ReachabilityError(ValueError):
    """Raised when the census cannot be computed honestly."""


def _is_test_module(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    return name.startswith("test_") or name.endswith("_test.py") or "/tests/" in rel


def _runtime_population(repo_root: pathlib.Path) -> list[str]:
    d = repo_root / RUNTIME_DIR
    if not d.is_dir():
        raise ReachabilityError("RUNTIME_DIRECTORY_MISSING:" + RUNTIME_DIR)
    return sorted(p.relative_to(repo_root).as_posix() for p in d.glob("*.py"))


def load_declared(repo_root: pathlib.Path, registry: str | pathlib.Path | None) -> dict[str, dict]:
    """Read the declaration registry. A missing registry is an empty registry, not an error.

    Every declared module must exist and must carry a verifier id; an entry that names
    a file which is not there is reported as a defect rather than silently dropped,
    because a declaration pointing at nothing is precisely the failure mode that makes
    a registry untrustworthy.
    """
    if registry is None:
        return {}
    p = pathlib.Path(registry)
    if not p.is_absolute():
        p = repo_root / p
    if not p.is_file():
        return {}
    raw = json.loads(p.read_text(encoding="utf-8"))
    caps = raw.get("capabilities")
    if not isinstance(caps, dict):
        raise ReachabilityError("REGISTRY_HAS_NO_CAPABILITIES_OBJECT")
    out: dict[str, dict] = {}
    for cap_id, entry in caps.items():
        if not isinstance(entry, dict):
            raise ReachabilityError("REGISTRY_ENTRY_NOT_OBJECT:" + str(cap_id))
        module = str(entry.get("module") or "")
        verifier = str(entry.get("verifier") or "")
        out[str(cap_id)] = {
            "module": module,
            "verifier": verifier,
            "preconditions": list(entry.get("preconditions") or []),
            "effects": list(entry.get("effects") or []),
            "exists": bool(module) and (repo_root / module).is_file(),
            "verifier_exists": bool(verifier) and (repo_root / verifier).is_file(),
        }
    return out


def census_reachability(
    repo_root: str | pathlib.Path,
    *,
    front_doors: Sequence[str] = (FRONT_DOOR, FABRIC),
    registry: str | pathlib.Path | None = "canonical/runtime/CAPABILITY_REGISTRY_V1.json",
) -> dict[str, Any]:
    """Compute which runtime modules any entry point can reach."""
    root = pathlib.Path(repo_root).resolve()
    for fd in front_doors:
        if not (root / fd).is_file():
            raise ReachabilityError("FRONT_DOOR_MISSING:" + fd)

    closure = census(root, list(front_doors))
    reachable_files = {row["path"] for row in closure["brain_owned_transitive_files"]}
    reachable_runtime = {p for p in reachable_files if p.startswith(RUNTIME_DIR + "/")}

    declared = load_declared(root, registry)
    declared_reachable = {
        cap_id: e for cap_id, e in declared.items() if e["exists"] and e["verifier_exists"]
    }
    declared_defective = {
        cap_id: e for cap_id, e in declared.items() if not (e["exists"] and e["verifier_exists"])
    }
    reachable_runtime |= {e["module"] for e in declared_reachable.values()}

    population = _runtime_population(root)
    orphaned = sorted(set(population) - reachable_runtime)

    def _size(rel: str) -> int:
        try:
            return (root / rel).stat().st_size
        except OSError:
            return 0

    pop_bytes = sum(_size(p) for p in population)
    reach_bytes = sum(_size(p) for p in reachable_runtime if p in set(population))
    orphan_bytes = sum(_size(p) for p in orphaned)

    import re as _re

    concepts: dict[str, dict[str, Any]] = {}
    for name, pattern in CONCEPT_PROBES.items():
        rx = _re.compile(pattern, _re.I)
        hits = [p for p in population if rx.search(p.rsplit("/", 1)[-1])]
        str_hits = [p for p in orphaned if rx.search(p.rsplit("/", 1)[-1])]
        concepts[name] = {
            "modules": len(hits),
            "reachable": len(hits) - len(str_hits),
            "orphaned": len(str_hits),
            "orphaned_modules": str_hits[:40],
            "note": "CONCEPT_PROBE_IS_A_REPORT_FILTER_NOT_A_CLAIM_ABOUT_THE_MODULE",
        }

    return {
        "schema": SCHEMA,
        "authority": "NONE__MEASUREMENT_OF_THE_TREE",
        "front_doors": list(front_doors),
        "reachable_files_total": len(reachable_files),
        "reachable_runtime_modules": len(reachable_runtime),
        "runtime_modules_total": len(population),
        "orphaned_runtime_modules_count": len(orphaned),
        "reachable_fraction": round(len(reachable_runtime) / len(population), 6) if population else 0.0,
        "runtime_source_bytes_total": pop_bytes,
        "reachable_runtime_source_bytes": reach_bytes,
        "orphaned_runtime_source_bytes": orphan_bytes,
        "declared_capabilities": len(declared),
        "declared_and_usable": len(declared_reachable),
        "declared_but_defective": declared_defective,
        "concepts": concepts,
        "orphaned_runtime_modules": orphaned,
        "what_this_is_not": [
            "not a claim that an orphaned module is worthless -- many are superseded copies or receipt helpers",
            "not a score: no benchmark, no capability credit, no terminal credit",
            "not a count of test modules as reachable -- a test proves a capability, it does not deliver one",
        ],
    }


def orphaned_modules(repo_root: str | pathlib.Path, **kwargs: Any) -> list[str]:
    """Convenience: just the list of runtime modules nothing can reach."""
    return census_reachability(repo_root, **kwargs)["orphaned_runtime_modules"]


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Capability reachability census")
    ap.add_argument("--root", default=".")
    ap.add_argument("--registry", default="canonical/runtime/CAPABILITY_REGISTRY_V1.json")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--top", type=int, default=3)
    args = ap.parse_args(list(argv) if argv is not None else None)

    result = census_reachability(args.root, registry=args.registry)
    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"{result['reachable_runtime_modules']} / {result['runtime_modules_total']} "
          f"runtime modules reachable ({100 * result['reachable_fraction']:.1f}%)")
    print(f"orphaned: {result['orphaned_runtime_modules_count']} "
          f"({result['orphaned_runtime_source_bytes']:,} bytes)")
    print(f"declared capabilities usable: {result['declared_and_usable']} "
          f"(defective: {len(result['declared_but_defective'])})")
    for name, row in result["concepts"].items():
        print(f"  {name:18} total={row['modules']:4} reachable={row['reachable']:4} orphaned={row['orphaned']:4}")
    if args.top:
        print("\nlargest orphaned modules:")
        root = pathlib.Path(args.root)
        rows = sorted(((root / p).stat().st_size, p) for p in result["orphaned_runtime_modules"]
                      if (root / p).is_file())
        for size, p in rows[-args.top:][::-1]:
            print(f"  {size:8,}  {p}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
