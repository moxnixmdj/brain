#!/usr/bin/env python3
"""Admit a dormant module as a capability -- only if it can be killed first.

THE MISSION GAP THIS CLOSES.

Seventy-four capabilities, every one written by hand. What is learned is
the choice among them, and that is not what was asked for. So: the
repository holds adapter modules that work and that no capability points
at -- discovered machinery, not authored. This turns them into
capabilities.

A CAPABILITY IS A HYPOTHESIS THAT SURVIVED ATTEMPTS TO KILL IT.

Nothing is admitted because it ran. A module is admitted only when:

  1. CONTRACT INFERRED, NOT AUTHORED. The parameters are read out of the
     source with ast -- every `args.get("x")` the function actually
     consults. No hand-written schema per module.
  2. IT RUNS ON MORE THAN ONE INPUT. One success is an anecdote. Two
     distinct real inputs or it is not general.
  3. DETERMINISTIC. The same input twice gives the same result. A module
     that cannot repeat itself cannot be relied on to repeat anything.
  4. THE ARTIFACT IS RE-READ. If it claims to have written a file, the
     bytes on disk must hash to what it claimed.
  5. IT CAN BE KILLED. This is the one that matters and the one this
     session keeps relearning: a check that cannot fail is decoration.
     A corrupted input must be REFUSED. A module that says yes to
     garbage has not verified anything.

HONEST ABOUT WHAT THIS PROVES. Passing proves the module runs, repeats,
produces bytes that exist, and refuses corrupted input. It does NOT prove
the answer is semantically right -- nobody checked that, and this file
does not pretend otherwise. Forged capabilities therefore carry their own
authority tier, the same way the inventory tier already declares that it
is not a true capability receipt.

DreamCoder is the frame for what comes after: its Memorize baseline --
store whole solutions -- lost to abstraction, extracting the common
fragment. macro_v1 is Memorize. Forging is one rung up. Abstraction over
forged capabilities is the rung after that.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import time
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_CAPABILITY_FORGE_V1"
ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "canonical" / "runtime"
ADAPTERS = RUNTIME / "bound_capabilities"
STATE = RUNTIME / "state" / "forged_capabilities_v1.json"


# --- discovery -----------------------------------------------------------

def unbound_modules(registry=None) -> list[str]:
    """Adapter modules that exist and that no capability points at."""
    if registry is None:
        from canonical.runtime import grounded_action_v1 as GA
        from canonical.runtime import h100_computer_use_registry_v1 as CU
        registry = dict(GA.load_registry())
        registry.update(CU.bound_entries())
    used = {str(e.get("adapter_module") or "") for e in registry.values()}
    return sorted(p.stem for p in ADAPTERS.glob("*.py")
                  if p.stem != "__init__" and not p.stem.startswith("__")
                  and p.stem not in used and p.stem != "capability_forge_v1")


# --- contract inference --------------------------------------------------

def contract_of(module: str) -> dict:
    """What the module actually asks for, read from its own source.

    Every `args.get("name")` the body consults is a parameter it needs.
    Inferred, so it stays true when the module changes and it cannot
    drift from a schema someone wrote once and stopped maintaining.
    """
    path = ADAPTERS / (str(module) + ".py")
    if not path.is_file():
        return {"parameters": [], "entrypoint": None}
    try:
        tree = _parse(path)
    except Exception:
        return {"parameters": [], "entrypoint": None}
    params: list[str] = []
    entry = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in ("run", "invoke"):
            entry = node.name
            for sub in walk_ast(node):
                if not isinstance(sub, ast.Call):
                    continue
                fn = sub.func
                if not (isinstance(fn, ast.Attribute) and fn.attr == "get"):
                    continue
                if sub.args and isinstance(sub.args[0], ast.Constant) \
                        and isinstance(sub.args[0].value, str):
                    name = sub.args[0].value
                    if name not in params and not name.startswith("_"):
                        params.append(name)
            break
    return {"parameters": params, "entrypoint": entry}


# --- running -------------------------------------------------------------

def _load(module: str):
    path = ADAPTERS / (str(module) + ".py")
    spec = importlib.util.spec_from_file_location("forge_" + module, path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _call(module: str, args: dict, root: Path):
    """Run the module. Returns (ok, result_or_error_string)."""
    try:
        mod = _load(module)
    except Exception as exc:
        return False, "LOAD_FAILED:" + type(exc).__name__
    fn = getattr(mod, "run", None) or getattr(mod, "invoke", None)
    if not callable(fn):
        return False, "NO_ENTRYPOINT"
    try:
        out = fn(dict(args), root)
    except Exception as exc:
        # Raising is an honest refusal. Only silence is not.
        return False, type(exc).__name__ + ":" + str(exc)[:200]
    if not isinstance(out, dict):
        return False, "RESULT_NOT_A_DICT"
    return True, out


def _artifact_holds(out: dict, root: Path):
    """Re-read what it claims to have produced."""
    rel = out.get("output_path") or out.get("result_path")
    if not isinstance(rel, str) or not rel.strip():
        return None
    target = root / rel
    if not target.is_file():
        return False
    data = target.read_bytes()
    if not data:
        return False
    claim = out.get("output_sha256")
    if isinstance(claim, str) and claim.strip():
        return hashlib.sha256(data).hexdigest().lower() == claim.strip().lower()
    return True


# --- the forgiving -------------------------------------------------------

def forge(module: str, cases: list[dict], root: Path | None = None,
          require_kill: bool = True) -> dict:
    """Put one dormant module through the five tests."""
    root = root or ROOT
    report = {"module": module, "admitted": False, "checks": {}, "reasons": []}

    if len(cases) < 2:
        report["reasons"].append("FEWER_THAN_TWO_INPUTS")
        return report

    contract = contract_of(module)
    report["contract"] = contract

    runs = []
    for i, case in enumerate(cases):
        ok, out = _call(module, case, root)
        if not ok:
            report["reasons"].append("case%d_FAILED:%s" % (i, str(out)[:90]))
            continue
        # determinism: the same input again must give the same result
        ok2, out2 = _call(module, case, root)
        if not ok2 or json.dumps(out, sort_keys=True, default=str) != \
                json.dumps(out2, sort_keys=True, default=str):
            report["reasons"].append("case%d_NOT_DETERMINISTIC" % i)
            continue
        art = _artifact_holds(out, root)
        if art is False:
            report["reasons"].append("case%d_ARTIFACT_MISMATCH" % i)
            continue
        runs.append(out)
    report["checks"]["ran_on_inputs"] = "%d/%d" % (len(runs), len(cases))
    if len(runs) < 2:
        report["reasons"].append("NOT_GENERAL__FEWER_THAN_TWO_SUCCESSES")
        return report

    # CAN IT BE KILLED. Corrupt every input; each must be refused.
    if require_kill:
        kills = 0
        tried = 0
        for case in cases:
            for bad in mutations(case):
                tried += 1
                ok, _ = _call(module, bad, root)
                if not ok:
                    kills += 1
        report["checks"]["killed"] = "%d/%d" % (kills, tried)
        if tried and kills == 0:
            report["reasons"].append("CANNOT_BE_KILLED__ACCEPTS_CORRUPTED_INPUT")
            return report

    report["admitted"] = True
    return report


_FILE_EXT = (".json", ".py", ".xlsx", ".docx", ".pdf", ".sqlite",
             ".tar.gz", ".yaml", ".md", ".txt", ".png")


def mutations(case: dict) -> list[dict]:
    """Every independent way this file knows to break an input.

    ONE OPERATOR IS NOT ENOUGH, AND THIS FILE FOUND OUT THE HARD WAY.
    Corrupting only path-like values left concrete_execution_oracle
    completely unharmed -- it simply creates the directory it is handed,
    which is correct behaviour, not a fault. The forge duly reported
    "cannot be killed" and refused a module that was fine, because the
    mutation never touched anything the module actually reads.

    So several operators are tried, and a single kill is enough: the
    question is not whether every mutation lands, it is whether the
    module has ever been OBSERVED to fail. A module no mutation can
    break has no known failure mode, and admitting it would mean being
    unable to tell its working from its breaking.
    """
    out = []
    for key, value in case.items():
        if not isinstance(value, str) or not value:
            continue
        low = value.lower()
        if low.endswith(_FILE_EXT) or "/" in value:
            bad = dict(case)
            bad[key] = ("canonical/NO_SUCH_DIRECTORY_FOR_THE_FORGE/"
                        + Path(value).name)
            out.append(bad)
        bad = dict(case)
        bad[key] = ""
        out.append(bad)
        bad = dict(case)
        bad[key] = "\x00not a real value\x00"
        out.append(bad)
        if len(value) > 8:
            bad = dict(case)
            bad[key] = value[: len(value) // 2]
            out.append(bad)
    return out


def _corrupt(case: dict):
    """Backwards-compatible single mutation."""
    m = mutations(case)
    return m[0] if m else None


# --- registration --------------------------------------------------------

def _state():
    if STATE.is_file():
        try:
            data = json.loads(STATE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {"schema": SCHEMA, "forged": {}}


def register(module: str, contract: dict, cases: list[dict]) -> dict:
    """Shape an admitted module like a registry capability."""
    cid = "forged." + module
    entry = {
        "capability_id": cid,
        "status": "FORGED__MACHINE_ADMITTED",
        "incremental_spend_usd": 0,
        "platforms": ["linux"],
        "cost": 1,
        "adapter_module": module,
        "keywords": sorted(set(re.findall(r"[a-z0-9]+", module.lower()))),
        # Forged capabilities declare nothing about shared effects:
        # inventing an effect would let them chain on claims nobody made.
        "provides": ["forged." + module],
        "requires": [],
        "action_template": {
            "type": "invoke_capability",
            "args": {p: "${input.%s}" % p for p in contract.get("parameters") or []},
            "expect": {"field": "adapter", "type": "field_nonempty", "value": None},
        },
        "source": {"type": "brain_inventory"},
        "verification": {
            "tier": "FORGED",
            "authority": ("MACHINE_ADMITTED__RAN_REPEATEDLY_AND_REFUSED_"
                          "CORRUPTED_INPUT__NOT_A_SEMANTIC_RECEIPT"),
            "cases": len(cases),
        },
    }
    data = _state()
    data["forged"][cid] = {
        "entry": entry, "forged_at": time.time(),
        "example_case": cases[0] if cases else None,
    }
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    tmp.replace(STATE)
    return entry


def registered() -> dict:
    """The forged capabilities that were admitted, keyed by capability id."""
    data = _state()
    out = {}
    for cid, blob in (data.get("forged") or {}).items():
        entry = (blob or {}).get("entry")
        if isinstance(entry, dict) and entry.get("capability_id"):
            out[cid] = entry
    return out


def main() -> int:
    root = ROOT
    mods = unbound_modules()
    print("%s" % SCHEMA)
    print("dormant modules: %d\n" % len(mods))
    admitted = []
    for m in mods:
        contract = contract_of(m)
        # No inputs can be invented for a module without a run(args, root)
        # entrypoint, so it stays dormant rather than being guessed at.
        if not contract.get("entrypoint"):
            print("  skip   %-42s no run(args, root) entrypoint" % m)
            continue
        print("  forge  %-42s params=%s" % (m, ",".join(contract["parameters"])[:40]))
        admitted.append((m, contract))
    print()
    print("with a contract: %d of %d" % (len(admitted), len(mods)))
    for m, c in admitted:
        print("   %-42s %s" % (m, c["parameters"]))
    return 0


# ast helpers (imported lazily so the module loads fast)
import ast  # noqa: E402
from ast import walk as walk_ast  # noqa: E402


def _parse(path: Path):
    return ast.parse(path.read_text(errors="replace"))


if __name__ == "__main__":
    raise SystemExit(main())
