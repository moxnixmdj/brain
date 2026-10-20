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
import base64
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


def _python_repair_args(cid: str, sig: dict, rng, ws: Path) -> dict | None:
    """Domain generator for the python-repair cluster, reusing a fixture that already works.

    Generic sampling cannot serve these: a repair capability needs a repository with a test
    that genuinely FAILS, and a file of plausible-looking text is not that. Supplying better
    plumbing produced BASELINE_ALREADY_PASSES -- nothing to repair -- which is the honest
    signal that this is a domain problem, not a typing problem.

    The domain is recognised by the SHAPE of the inputs (a source root plus tests), not by a
    list of capability ids, so it keeps working as the registry grows.
    """
    # The domain is "operates on python source", which is the presence of ANY
    # source slot -- not source_root plus tests. Requiring tests as well skipped
    # python.tests.audit.unittest (no test_paths) and patch.search (no
    # source_root), which are the same domain reached by a different door.
    if not ({"source_root", "source_path", "source_paths"} & set(sig)):
        return None
    from execution_guard import live_solver_families_v6 as v6

    root = ws / f"repo{rng.randrange(1 << 30)}"
    root.mkdir(parents=True, exist_ok=True)
    # polarity: repair needs a failing baseline, an audit needs a passing one.
    # handing the red fixture to python.tests.audit.unittest produced
    # TEST_FILE_FAILED -- the fixture contradicting what the capability means.
    green = ("audit" in cid or "verify" in cid)
    bug = v6.fresh_coupled_bug(rng, root, rng.randrange(1 << 20), mutate=not green)

    args: dict = {}
    for slot, want in sig.items():
        if want == ts.PATH_DIR and ("source" in slot or "root" in slot):
            # the fixtures land in a subdirectory of root, and adapters glob
            # non-recursively, so the root that works is the one holding the
            # files. Pointing at root found nothing: TEST_AUDIT_EMPTY.
            args[slot] = str(bug.src.parent)
        elif want == ts.PATH_LIST and "test" in slot:
            args[slot] = [str(p) for p in bug.tests]
        elif want == ts.ARGV:
            args[slot] = [sys.executable, "-B", str(sorted(bug.tests)[0])]
        # caps that take a single file, or a list of files, rather than a root
        elif want == ts.PATH_FILE and "source" in slot:
            args[slot] = str(bug.src)
        elif want == ts.PATH_LIST and "source" in slot:
            args[slot] = [str(bug.src)]
    if "test_paths" not in args and "test_paths" in sig:
        args["test_paths"] = [str(p) for p in bug.tests]
    # a discovery glob is not free text: a random word matches no test file and
    # the adapter answers TEST_AUDIT_EMPTY, which is the sampler lying again
    if "pattern" in sig:
        args["pattern"] = "test_*.py"
    return args or None


def _saccr_args(cid: str, sig: dict, rng, ws: Path) -> dict | None:
    """finance.saccr.credit.addon.v1 rejects anything that is not {"trades": [...]}.

    saccr_credit_addon_gen_v1 emits exactly that, so the fix is to use it rather
    than to invent a schema the adapter might accept.
    """
    if "trades" not in cid and "saccr" not in cid:
        return None
    from canonical.capabilities.true.generators import saccr_credit_addon_gen_v1 as gen

    inst = gen.generate(rng, 1)[0]
    path = ws / f"trades{rng.randrange(1 << 30)}.json"
    path.write_text(json.dumps(inst), encoding="utf-8")
    out = {}
    for slot, want in sig.items():
        if want == ts.PATH_FILE:
            out[slot] = str(path)
    return out or None


def _docx_args(cid: str, sig: dict, rng, ws: Path) -> dict | None:
    """The docx verifiers need a real .docx, not a file of plausible text.

    docx_exact_text_edit_gen_v1 emits one base64-encoded. expected_structure is
    left to the sampler deliberately: guessing a structure the document does not
    have would turn a real signal into a false pass.
    """
    if not cid.startswith("docx."):
        return None
    if not ({"document_path", "docx_path", "path"} & set(sig)):
        return None
    from canonical.capabilities.true.generators import docx_exact_text_edit_gen_v1 as gen

    inst = gen.generate(rng, 1)[0]
    b64 = inst.get("docx_b64")
    if not b64:
        return None
    path = ws / f"doc{rng.randrange(1 << 30)}.docx"
    path.write_bytes(base64.b64decode(b64))
    out = {}
    for slot, want in sig.items():
        if want == ts.PATH_FILE:
            out[slot] = str(path)
    return out or None


def _load_adapter(adapter_path: str, name: str):
    path = ROOT / adapter_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError("MODULE_LOAD_FAILED:" + adapter_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sweep_one(cid: str, entry: dict, instances: int, seed: int, work: Path,
              use_schema: bool = True) -> dict:
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
        # a domain generator wins over generic sampling wherever one applies
        domain = (_python_repair_args(cid, sig, rng, ws)
                  or _saccr_args(cid, sig, rng, ws)
                  or _docx_args(cid, sig, rng, ws) or {})
        try:
            # the capability id is what lets content rules be scoped per capability;
            # without it a rule for one capability's output_path would silently not apply
            # the format the adapter PARSES the file as, not what its name suggests
            formats = ts.parsed_formats(entry) if entry else {}
            # The mined schema is a hypothesis about what the adapter wants, and a
            # hypothesis can be wrong: it regressed archive.verify.tar_gz.gnu from a
            # domain error to a type error. So it is tried, not assumed, and the
            # capability itself decides. See the strategy note in sweep().
            schemas = (ts.parsed_schema(entry) if (entry and use_schema) else {})
            filled = samp.sample_args(sig, rng, ws, capability=cid,
                                      formats=formats, schemas=schemas)
            # the registry omits arguments the adapter nevertheless requires (65 of them
            # across 26 capabilities). Fill them from their names so the call is complete:
            # otherwise we are measuring our own incomplete template, not the capability.
            for key in extra_slots:
                if key not in filled:
                    filled[key] = samp.sample_args({key: type_of(key)}, rng, ws,
                                                   capability=cid)[key]
            merged = {**filled, **domain}
            args = _substitute(template_args, merged) if template_args else dict(merged)
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
        row = sweep_one(cid, entry, instances, seed, work)
        # A mined schema is a hypothesis, so it is only adopted when the
        # capability -- the one authority on what it accepts -- actually prefers
        # it. Both are run and the better stands; the winner is recorded, because
        # which input a capability needs is itself a finding. This is not tuning
        # until green: it is one alternative, chosen by the oracle, and reported.
        if (row["executed"] and row["failed"] > 0
                and ts.parsed_schema(entry)):
            plain = sweep_one(cid, entry, instances, seed, work, use_schema=False)
            if plain["succeeded"] > row["succeeded"]:
                plain["strategy"] = "generic"
                row = plain
            else:
                row["strategy"] = "schema"
        rows.append(row)

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
