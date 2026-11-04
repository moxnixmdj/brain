#!/usr/bin/env python3
"""Give the creature more than one thing to look at, and find out what it can predict unrun.

Log 11's organism had four hand-written worlds and learned each one separately. This builds a
world for **every capability the body declares**, mechanically, and then asks the only question
that distinguishes a model from a lookup table:

    can it predict what a capability will do when it has never run that capability?

Two halves, in this order
-------------------------
**The senses.** Before acting, and for every capability in the registry, the body can read things
that are free to read: how many arguments the declaration names, how many the adapter actually
reads, how many of those it reads without declaring, whether it imports a module this machine
does not have, whether it can reach the network, how much code it is, how much of it is guarded.
Those are eyes, not ideas. They are given.

**The world.** For each capability that declares inputs, has an adapter on disk, and cannot reach
the network or a subprocess, the world is built from the declaration alone: every declared input
becomes a value of the kind its name implies, in a fresh temporary directory, in its own process,
under a timeout. The adapter runs. What comes back is one of:

    CLAIM_CHECKED        it ran and the claim in `action_template.expect` held
    CLAIM_FALSE          it ran and the claim did not hold -- a lie about the world
    CLAIM_FIELD_ABSENT   it ran but returned nothing named in its own claim
    REFUSED_NAMED        it raised a named, deliberate refusal (a good outcome)
    CRASHED              it died in a way it did not declare

Everything a person did not supply: the input values, the directory, the timeout, the process
boundary. Everything a person did supply is listed in the artifact, so the ceiling can be argued
with rather than guessed at.

What this deliberately does NOT claim
-------------------------------------
A mechanically built world is a *shape*, not a *meaning*. "A path" is a path; whether it points
at the thing the capability is for is a judgement nobody made here. So a CRASHED verdict is
evidence about the capability's declaration, never about its intention, and this tool never
reports one as a defect. It reports the distribution and lets the model try to predict it.

Usage::

    python -m canonical.tools.capability_world_v1 --harvest
    python -m canonical.tools.capability_world_v1 --transfer
    python -m canonical.tools.capability_world_v1 --transfer --write
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_CAPABILITY_WORLD_V1"
ARTIFACT = ROOT / "canonical/verification/CAPABILITY_WORLD_V1.json"
TRANSFER_ARTIFACT = ROOT / "canonical/verification/CAPABILITY_TRANSFER_V1.json"
REGISTRY = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
ADAPTERS = ROOT / "canonical/runtime/bound_capabilities"

TIMEOUT_S = 25
# Four worlds per capability, because one world per capability cannot teach a general rule and
# cannot distinguish "this capability always fails" from "this input always fails". The variant
# is part of what the creature can see, so a rule like "malformed json is refused, not parsed"
# is learnable from several capabilities at once -- which is the only reason holding out a
# capability is a real test instead of a memory quiz.
VARIANTS = ("MINIMAL", "POPULATED", "MALFORMED", "ABSENT", "BARE_ARRAY", "EMPTY_FILE")
# A capability that reaches any of these cannot be situated without opening a hole in the
# machine. They are excluded before the world is built, not after it misbehaves.
UNSAFE = ("socket", "urllib", "http.client", "requests", "subprocess", "selenium", "playwright",
          "chromedriver", "os.system", "multiprocessing", "threading")
VERDICTS = ("CLAIM_CHECKED", "CLAIM_FALSE", "CLAIM_FIELD_ABSENT", "REFUSED_NAMED", "CRASHED",
            "NON_DICT", "TIMEOUT", "NO_OUTPUT")


def registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]


def declared_inputs(entry: dict) -> list[tuple[str, str]]:
    args = (entry.get("action_template") or {}).get("args") or {}
    return [(k, re.sub(r"\$\{input\.|\}", "", v)) for k, v in args.items()
            if isinstance(v, str) and "${input." in v]


def read_keys(source: str) -> set[str]:
    keys = set(re.findall(r"args\[\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*\]", source))
    keys |= set(re.findall(r"args\.get\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]", source))
    return keys


def _imported_roots(source: str) -> set[str]:
    roots = set()
    for m in re.finditer(r"^\s*(?:import|from)\s+([A-Za-z_][A-Za-z0-9_.]*)", source, re.M):
        roots.add(m.group(1).split(".")[0])
    return roots


def _importable(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def senses(capability_id: str, entry: dict) -> dict[str, float]:
    """Everything the body can know about a capability before running it.

    All of it is free: the declaration, the adapter's source text, and whether a module is on
    this machine. No world is built and nothing is executed to compute these.
    """
    module = entry.get("adapter_module") or ""
    path = ADAPTERS / f"{module}.py"
    source = path.read_text(encoding="utf-8") if path.is_file() else ""
    declared = declared_inputs(entry)
    reads = read_keys(source)
    undeclared = reads - {name for _, name in declared}
    imports = _imported_roots(source)
    missing = {m for m in imports if m not in sys.stdlib_module_names and not _importable(m)}
    expect = ((entry.get("action_template") or {}).get("expect") or {})
    return {
        "declared_inputs": float(len(declared)),
        "distinct_input_names": float(len({name for _, name in declared})),
        "adapter_reads": float(len(reads)),
        "undeclared_reads": float(len(undeclared)),
        "undeclared_ratio": float(len(undeclared) / len(reads)) if reads else 0.0,
        "adapter_bytes": float(len(source)),
        "adapter_lines": float(source.count("\n")),
        "adapter_defs": float(len(re.findall(r"^def\s+", source, re.M))),
        "adapter_raises": float(len(re.findall(r"\braise\b", source))),
        "adapter_try_blocks": float(len(re.findall(r"^\s*try:", source, re.M))),
        "third_party_imports": float(len(imports - set(sys.stdlib_module_names))),
        "missing_module_imports": float(len(missing)),
        "reaches_unsafe": float(any(u in source for u in UNSAFE)),
        "declared_result_fields": float(len(entry.get("result_fields") or [])),
        "expects_verified": float(expect.get("field") in ("output_verified", "verified")),
        "expects_pass": float(expect.get("field") == "pass"),
        "has_observed_effect": float(bool(
            (entry.get("verification") or {}).get("observed_effect"))),
        "source_is_python_stdlib": float(((entry.get("source") or {}).get("type")
                                          == "python_stdlib")),
    }


def world_senses(variant: str) -> dict[str, float]:
    """The four worlds are different situations, and knowing which one you are in is not
    cheating: a creature that cannot tell an empty room from a malformed one is blind."""
    return {
        "world_minimal": float(variant == "MINIMAL"),
        "world_populated": float(variant == "POPULATED"),
        "world_malformed": float(variant == "MALFORMED"),
        "world_absent": float(variant == "ABSENT"),
        "world_bare_array": float(variant == "BARE_ARRAY"),
        "world_empty_file": float(variant == "EMPTY_FILE"),
    }


# --------------------------------------------------------------------------- the world
def _json_text(variant: str) -> str:
    if variant == "EMPTY_FILE":
        return ""
    if variant == "BARE_ARRAY":
        return '[{"verification_paths": ["canonical/a.txt"]}]'
    if variant == "MALFORMED":
        return '{"records": [ this is not json\n'
    if variant == "POPULATED":
        return json.dumps({"records": [{"verification_paths": ["canonical/a.txt"]},
                                       {"verification_paths": ["canonical/b.txt"]},
                                       {"id": 1, "value": "x"}],
                           "items": [{"k": 1}, {"k": 2}]})
    return '{"records": [], "items": []}\n'


def _value_for(name: str, root: Path, variant: str = "MINIMAL") -> Any:
    if name.endswith("_root") or name in ("worktree_path", "source_root"):
        return str(root)
    if name.endswith("_s") or name == "timeout":
        return "5"
    if "json" in name:
        rel = name if name.endswith(".json") else f"{name}.json"
        if variant == "ABSENT":
            return rel                       # named, never created
        (root / rel).write_text(_json_text(variant), encoding="utf-8")
        return rel
    if "path" in name:
        rel = f"{name}.txt"
        if variant == "ABSENT":
            return rel
        body = "alpha\nbeta\nalpha beta\n" if variant == "POPULATED" else "x\n"
        (root / rel).write_text(body, encoding="utf-8")
        return rel
    if name == "goal":
        return "bundle the files in the repository"
    if name in ("module", "qualname", "label", "operation", "spec"):
        return "x"
    return "x"


def _worker(capability_id: str, module: str, out_dir: str, variant: str = "MINIMAL") -> int:
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    entry = registry()[capability_id]
    args = {key: _value_for(name, root, variant) for key, name in declared_inputs(entry)}
    result: dict[str, Any] = {"capability": capability_id, "variant": variant}
    try:
        path = ADAPTERS / f"{module}.py"
        spec = importlib.util.spec_from_file_location(f"_world_{module}", path)
        loaded = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loaded)
        returned = loaded.run(args, root)
        if not isinstance(returned, dict):
            result.update(verdict="NON_DICT", detail=type(returned).__name__)
        else:
            expect = (entry.get("action_template") or {}).get("expect") or {}
            field, want = expect.get("field"), expect.get("value")
            if field and field in returned:
                result.update(verdict="CLAIM_CHECKED" if returned[field] == want else "CLAIM_FALSE",
                              detail=f"{field}={returned[field]!r} want {want!r}")
            elif field:
                result.update(verdict="CLAIM_FIELD_ABSENT",
                              detail=f"no {field!r}; keys={sorted(returned)[:6]}")
            else:
                result.update(verdict="CLAIM_FIELD_ABSENT", detail="no claim declared")
    except TypeError as exc:
        result.update(verdict="CRASHED", detail=f"TypeError: {str(exc)[:160]}")
    except Exception as exc:                                        # noqa: BLE001
        message = str(exc)
        named = bool(message) and bool(re.fullmatch(r"[A-Z0-9_:. \-]+", message))
        result.update(verdict="REFUSED_NAMED" if named else "CRASHED",
                      detail=f"{type(exc).__name__}: {message[:160]}")
    print(json.dumps(result))
    return 0


def run_one(capability_id: str, module: str, variant: str = "MINIMAL") -> dict[str, Any]:
    directory = tempfile.mkdtemp(prefix="world_")
    try:
        done = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--worker",
             capability_id, module, directory, variant],
            capture_output=True, text=True, timeout=TIMEOUT_S, cwd=str(ROOT))
        lines = (done.stdout or "").strip().splitlines()
        if not lines:
            return {"capability": capability_id, "variant": variant, "verdict": "NO_OUTPUT",
                    "detail": (done.stderr or "")[-200:]}
        return json.loads(lines[-1])
    except subprocess.TimeoutExpired:
        return {"capability": capability_id, "variant": variant, "verdict": "TIMEOUT",
                "detail": f"{TIMEOUT_S}s"}
    finally:
        import shutil
        shutil.rmtree(directory, ignore_errors=True)


def harvest() -> dict:
    caps = registry()
    rows, skipped = [], {}
    for capability_id, entry in sorted(caps.items()):
        module = entry.get("adapter_module") or ""
        path = ADAPTERS / f"{module}.py"
        inputs = declared_inputs(entry)
        if not path.is_file():
            skipped[capability_id] = "no adapter on disk"
            continue
        # A capability that declares no inputs is still runnable: it is handed an empty
        # argument set in a fresh directory. Excluding it would have shrunk the world by 20
        # capabilities for no reason.
        source = path.read_text(encoding="utf-8")
        if any(u in source for u in UNSAFE):
            skipped[capability_id] = "reaches a subprocess, the network, or a browser"
            continue
        for variant in VARIANTS:
            row = run_one(capability_id, module, variant)
            row["senses"] = {**senses(capability_id, entry), **world_senses(variant)}
            rows.append(row)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    doc = {
        "schema": SCHEMA,
        "registry_size": len(caps),
        "situated": len(rows),
        "skipped": len(skipped),
        "skipped_reasons": _tally(skipped.values()),
        "verdict_counts": counts,
        "rows": rows,
        "supplied_by_a_person": ["input values", "the timeout", "the process boundary"],
        "supplied_by_the_machine": ["every declared input's kind and value", "a fresh directory"],
        "non_claims": [
            "A_MECHANICAL_WORLD_IS_A_SHAPE_NOT_A_MEANING",
            "CRASHED_IS_EVIDENCE_ABOUT_A_DECLARATION_NOT_AN_INTENTION",
            "NO_DEFECT_IS_CLAIMED_FROM_A_SYNTHESISED_WORLD_ALONE",
        ],
        "authority": "NO_CAPABILITY_CREDIT_MECHANICAL_WORLD_ONLY",
    }
    ARTIFACT.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return doc


def _tally(values) -> dict[str, int]:
    out: dict[str, int] = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return out


# --------------------------------------------------------------------------- the real test
def examples(doc: dict | None = None) -> list[dict]:
    doc = doc or json.loads(ARTIFACT.read_text(encoding="utf-8"))
    return [{"capability": row["capability"], "signals": row["senses"],
             "verdict": row["verdict"]} for row in doc["rows"]]


def transfer(seed: int = 20261104, write: bool = False) -> dict:
    """Hold out whole capabilities, fit on the rest, and ask about worlds never entered.

    Splitting by example would be a memory quiz: the same capability would appear on both sides,
    and a model could score well by recognising the capability rather than by understanding the
    world. The split is therefore by capability, and every held-out capability is one the model
    has never been trained on in any world.
    """
    import random
    from canonical.runtime import belief_v1

    doc = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    data = examples(doc)
    by_capability: dict[str, list[dict]] = {}
    for ex in data:
        by_capability.setdefault(ex["capability"], []).append(ex)

    capabilities = sorted(by_capability)
    random.Random(seed).shuffle(capabilities)
    cut = max(1, int(len(capabilities) * 0.6))
    train_caps, holdout_caps = capabilities[:cut], capabilities[cut:]
    inner = max(1, int(len(train_caps) * 0.75))
    fit_caps, validate_caps = train_caps[:inner], train_caps[inner:]

    fit = [ex for cap in fit_caps for ex in by_capability[cap]]
    validate = [ex for cap in validate_caps for ex in by_capability[cap]]
    holdout = [ex for cap in holdout_caps for ex in by_capability[cap]]

    model = belief_v1.blank()
    belief_v1.fit(model, fit, validate)
    for ex in fit:
        belief_v1.observe(model, ex["signals"], ex["verdict"])

    hit, answered = belief_v1.accuracy(model, holdout)
    baseline = belief_v1.majority_baseline(holdout)
    on_fit, _ = belief_v1.accuracy(model, fit)

    # log 11's organism: a table keyed on the target. A capability it has never met gets no
    # answer at all, which is a score of zero on purpose, not an error.
    table: dict[str, dict[str, int]] = {}
    for ex in fit:
        row = table.setdefault(ex["capability"], {})
        row[ex["verdict"]] = row.get(ex["verdict"], 0) + 1
    table_right = sum(1 for ex in holdout
                      if table.get(ex["capability"]) and
                      max(table[ex["capability"]].items(), key=lambda kv: kv[1])[0]
                      == ex["verdict"])

    # how far above baseline, in examples rather than in prose
    right = round(hit * answered)
    margin_right = round(baseline * answered)

    result = {
        "schema": "PROJECT_BRAIN_CAPABILITY_TRANSFER_V1",
        "question": "Can it predict what a capability will do, in a world it has never entered, "
                    "for a capability it has never run?",
        "seed": seed,
        "split": "by capability, so no held-out capability appears in training in any world",
        "world_size": len(data),
        "capabilities": len(by_capability),
        "train_capabilities": len(fit_caps),
        "validation_capabilities": len(validate_caps),
        "holdout_capabilities": len(holdout_caps),
        "train_examples": len(fit),
        "validation_examples": len(validate),
        "holdout_examples": len(holdout),
        "holdout_accuracy": round(hit, 4),
        "holdout_answered": answered,
        "holdout_right": right,
        "holdout_baseline_majority": round(baseline, 4),
        "holdout_baseline_right": margin_right,
        "lift_over_baseline": round(hit - baseline, 4),
        "lift_in_examples": right - margin_right,
        "on_training_accuracy": round(on_fit, 4),
        "identity_table_accuracy": round(table_right / len(holdout), 4) if holdout else None,
        "identity_table_right": table_right,
        "structure": belief_v1.describe(model),
        "verdict_counts": doc["verdict_counts"],
        "non_claims": [
            "HOLDOUT_ACCURACY_IS_MEANINGLESS_WITHOUT_THE_BASELINE_BESIDE_IT",
            "A_MECHANICAL_WORLD_DOES_NOT_ESTABLISH_SEMANTIC_CORRECTNESS",
            "FIFTY_EIGHT_CAPABILITIES_IS_NOT_A_LARGE_WORLD",
            "THE_SENSES_ARE_GIVEN_THE_IDEAS_OVER_THEM_ARE_GROWN",
        ],
        "authority": "NO_CAPABILITY_CREDIT_TRANSFER_MEASUREMENT_ONLY",
    }
    if write:
        TRANSFER_ARTIFACT.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n",
                                     encoding="utf-8")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", nargs=4, metavar=("CAPABILITY", "MODULE", "DIR", "VARIANT"))
    ap.add_argument("--harvest", action="store_true")
    ap.add_argument("--transfer", action="store_true")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    if args.worker:
        return _worker(*args.worker)
    if args.harvest:
        doc = harvest()
        print(f"situated {doc['situated']} of {doc['registry_size']} "
              f"(skipped {doc['skipped']})")
        for verdict, n in sorted(doc["verdict_counts"].items(), key=lambda kv: -kv[1]):
            print(f"  {n:3d}  {verdict}")
        for reason, n in sorted(doc["skipped_reasons"].items(), key=lambda kv: -kv[1]):
            print(f"  skip {n:3d}  {reason}")
        return 0
    if args.transfer:
        got = transfer(write=args.write)
        print(f"world {got['world_size']} examples over {got['capabilities']} capabilities")
        print(f"  fit {got['train_examples']} examples / {got['train_capabilities']} capabilities"
              f"   held-out {got['holdout_examples']} / {got['holdout_capabilities']}")
        print(f"  holdout accuracy        {got['holdout_accuracy']}"
              f"   ({got['holdout_right']} of {got['holdout_answered']} right)")
        print(f"  majority baseline       {got['holdout_baseline_majority']}"
              f"   ({got['holdout_baseline_right']} right)")
        print(f"  lift                    {got['lift_over_baseline']}"
              f"   ({got['lift_in_examples']} examples)")
        print(f"  on training data        {got['on_training_accuracy']}  (memory, not learning)")
        print(f"  identity table (log 11) {got['identity_table_accuracy']}"
              f"   ({got['identity_table_right']} right)")
        print(f"  distinctions accepted   {got['structure']['splits_accepted']}")
        for entry in got["structure"]["accepted"]:
            print(f"    {entry['signal']} <= {entry['threshold']:.4f}"
                  f"   validation {entry['validation_before']} -> {entry['validation_after']}")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
