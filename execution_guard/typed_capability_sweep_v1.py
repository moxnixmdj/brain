"""Run every bound capability on sampled instances, through the typed interface.

V4 reports `typed-invocable: 67/67`. That means the signatures are known and total. It does
NOT mean the capabilities have ever been *executed* through that interface. This sweep is the
difference between the two numbers, measured.

Why this is the right instrument, from first principles:

- The sentence interface was the bottleneck for months (27 of 67). V4 correctly declared it the
  wrong interface and replaced it with types. But "the surface is total" is a claim about
  signatures, not about behaviour. Only running it settles behaviour.
- Instances come from `type_directed_sampler_v1`, which is judged by the surface's own
  `check()`, so a failure here cannot be blamed on bad inputs: the inputs were accepted.
- Every outcome is a receipt, including the failures. A capability that cannot execute on valid
  inputs is more valuable information than one that can, because it names the next unit of work.

Model dependency: 0. Spend: $0. Nothing here calls a model, a solver or the network.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import re
import shutil
import sys
import traceback
from typing import Any, Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import capability_type_surface_v1 as ts  # noqa: E402
from canonical.runtime import type_directed_sampler_v1 as samp  # noqa: E402
from canonical.runtime.capability_type_surface_v1 import type_of  # noqa: E402

SCHEMA = "PROJECT_BRAIN_TYPED_CAPABILITY_SWEEP_V1"
WORK = ROOT / "canonical/astra_runtime/tmp/typed_sweep"


def _substitute(template: Any, filled: Mapping[str, Any]) -> Any:
    """Fill ${input.X} placeholders inside an action_template, at any depth.

    A template value is usually a bare "${input.path}" but is sometimes embedded in a list
    (argv) or a dict, so the walk has to be recursive. Keys that are literal configuration
    -- argv, decode_callable, package_root, timeout_s -- are passed through untouched.
    """
    if isinstance(template, str):
        m = re.fullmatch(r"\$\{input\.([A-Za-z_][A-Za-z0-9_]*)\}", template.strip())
        if m:
            name = m.group(1)
            return filled[name] if name in filled else template
        out = template
        for key, val in filled.items():
            out = out.replace("${input." + key + "}", str(val))
        return out
    if isinstance(template, Mapping):
        return {k: _substitute(v, filled) for k, v in template.items()}
    if isinstance(template, list):
        return [_substitute(v, filled) for v in template]
    return template


def _load_adapter(adapter_path: str, name: str):
    path = ROOT / adapter_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError("MODULE_LOAD_FAILED:" + adapter_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sweep_one(cid: str, entry: dict, instances: int, seed: int, work: Path) -> dict:
    sig = ts.signature(entry)
    adapter_path = (entry.get("source") or {}).get("adapter_path")
    result = {
        "capability_id": cid,
        "signature": sig,
        "instances": instances,
        "executed": 0,
        "succeeded": 0,
        "failed": 0,
        "errors": {},
        "sample_error": None,
    }
    # 31 of 70 declare no source.adapter_path, but every one of them names an
    # adapter_module that exists on disk. Falling back to it is the difference between
    # "unrunnable" and "runnable" for a third of the registry -- and it matters because the
    # ones that then fail on a MISSING BINARY are failing on this sandbox, not on the
    # public runner, which has apt. Conflating those is the mistake of calling the
    # sandbox the machine.
    if not adapter_path:
        module_name = entry.get("adapter_module")
        if module_name:
            candidate = ROOT / "canonical/runtime/bound_capabilities" / f"{module_name}.py"
            if candidate.is_file():
                adapter_path = f"canonical/runtime/bound_capabilities/{module_name}.py"
    if not adapter_path:
        result["errors"]["NO_ADAPTER_RESOLVABLE"] = instances
        return result

    ws = work / cid.replace(".", "_")[:60]
    shutil.rmtree(ws, ignore_errors=True)
    ws.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    try:
        module = _load_adapter(adapter_path, "sweep_" + str(abs(hash(cid)) % 10_000))
    except Exception as exc:
        result["errors"]["ADAPTER_IMPORT_FAILED:" + type(exc).__name__] = instances
        result["sample_error"] = str(exc)[:300]
        return result

    # arguments the adapter requires that the registry never declared
    extra_slots = ts.adapter_arg_reads(entry).get("required") or []

    fn = getattr(module, (entry.get("entrypoint") or "run"), None)
    if fn is None:
        result["errors"]["NO_ENTRYPOINT"] = instances
        return result

    # The action_template IS the call. Placeholders are the inputs to fill; everything else
    # (argv, decode_callable, package_root, timeout_s) is literal configuration the adapter
    # also requires. Sampling only the placeholder-derived slots and handing those over was
    # the wrong model and produced 22 failures of the form CLI_ARGV_REQUIRED /
    # PYTHON_CODEC_CONTRACT_INCOMPLETE: adapters demanding arguments the call never carried.
    template_args = ((entry.get("action_template") or {}).get("args")) or {}

    for _ in range(instances):
        try:
            # the capability id is what lets content rules be scoped per capability;
            # without it a rule for one capability's output_path would silently not apply
            filled = samp.sample_args(sig, rng, ws, capability=cid)
            # the registry omits arguments the adapter nevertheless requires (65 of them
            # across 26 capabilities). Fill them from their names so the call is complete:
            # otherwise we are measuring our own incomplete template, not the capability.
            for key in extra_slots:
                if key not in filled:
                    filled[key] = samp.sample_args({key: type_of(key)}, rng, ws,
                                                   capability=cid)[key]
            args = _substitute(template_args, filled) if template_args else dict(filled)
        except samp.SamplingFailure as exc:
            result["errors"]["SAMPLING_FAILED:" + str(exc)] = \
                result["errors"].get("SAMPLING_FAILED:" + str(exc), 0) + 1
            continue
        result["executed"] += 1
        try:
            fn(dict(args), str(ROOT))
            result["succeeded"] += 1
        except Exception as exc:
            key = type(exc).__name__ + ":" + str(exc).split("\n")[0][:120]
            result["errors"][key] = result["errors"].get(key, 0) + 1
            if result["sample_error"] is None:
                result["sample_error"] = traceback.format_exc(limit=3)[:800]
            result["failed"] += 1
    return result


def sweep(instances: int, seed: int, only: set[str] | None = None) -> dict:
    registry = ts.load_registry()
    capabilities = registry.get("capabilities") or registry
    work = WORK
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)

    rows = []
    for cid, entry in sorted(capabilities.items()):
        if only and cid not in only:
            continue
        rows.append(sweep_one(cid, entry, instances, seed, work))

    clean = [r for r in rows if r["executed"] and r["failed"] == 0]
    partial = [r for r in rows if r["executed"] and 0 < r["failed"] < r["executed"]]
    broken = [r for r in rows if r["executed"] and r["failed"] == r["executed"]]
    unsampled = [r for r in rows if not r["executed"]]

    return {
        "schema": SCHEMA,
        "instances_per_capability": instances,
        "seed": seed,
        "model_dependency_count": 0,
        "totals": {
            "capabilities": len(rows),
            "clean_all_instances_pass": len(clean),
            "partial_some_instances_fail": len(partial),
            "broken_every_instance_fails": len(broken),
            "could_not_sample": len(unsampled),
        },
        "rows": rows,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--instances", type=int, default=10)
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--out", default=None)
    ap.add_argument("--only", default="", help="comma-separated capability ids")
    ns = ap.parse_args(argv)

    only = {x.strip() for x in ns.only.split(",") if x.strip()} or None
    receipt = sweep(ns.instances, ns.seed, only)
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if ns.out:
        Path(ns.out).write_text(text, encoding="utf-8")
    t = receipt["totals"]
    print(f"capabilities swept            : {t['capabilities']}")
    print(f"  clean (every instance passed): {t['clean_all_instances_pass']}")
    print(f"  partial (some failed)        : {t['partial_some_instances_fail']}")
    print(f"  broken (every instance failed): {t['broken_every_instance_fails']}")
    print(f"  could not sample             : {t['could_not_sample']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
