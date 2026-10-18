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
        if is_vacuous(out):
            report["reasons"].append("case%d_VACUOUS__FOUND_NOTHING" % i)
            continue
        if self_reported_failure(out):
            report["reasons"].append("case%d_SELF_REPORTED_FAILURE" % i)
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


_VACUOUS_STATUS = ("no_", "none", "empty", "skipped", "not_found",
                   "unresolved", "n/a", "nothing")


def is_vacuous(result: dict) -> bool:
    """Did it actually do anything, or just report that it found nothing?

    VACUOUS TRUTH, AND THE FORGE WALKED STRAIGHT INTO IT.

    concrete_execution_oracle returned

        {"status": "NO_POSTCONDITION_PARSED", "checked": 0, "violations": []}

    for every input. Well-formed, honest, and empty. The forge ran it
    three times, saw a dict come back each time, and admitted it as a
    capability -- a capability whose entire demonstrated behaviour is
    "found nothing". A result can be truthful and still be evidence of
    nothing, which is the same failure as a check that cannot fail, one
    level up.

    So: a status announcing that nothing was found is vacuous; every
    count being zero is vacuous; a non-empty artifact or a real value is
    not.
    """
    if not isinstance(result, dict):
        return True
    status = str(result.get("status") or "").strip().lower()
    if status and any(status.startswith(p) or status == p
                      for p in _VACUOUS_STATUS):
        return True
    counts = [v for v in result.values() if isinstance(v, (int, float))
              and not isinstance(v, bool)]
    lists = [v for v in result.values() if isinstance(v, list)]
    if counts and all(v == 0 for v in counts):
        return True
    if lists and all(len(v) == 0 for v in lists):
        return True
    return False


def self_reported_failure(result: dict) -> bool:
    """Did the module say, in its own result, that it did not succeed?

    THE SECOND HOLE, FOUND IMMEDIATELY AFTER THE FIRST. python_request_
    semantic_acceptance_cells_v1 returned a busy, non-vacuous result on
    every input -- and every one of them said pass=false. It had been
    handed hashes I invented, so refusing was correct, but a run that
    reports failure is not evidence the module can do the work. A forge
    that counts failures as successes would happily admit a module whose
    entire demonstrated behaviour is saying no.
    """
    if not isinstance(result, dict):
        return True
    for key in ("pass", "ok", "verified", "output_verified", "success"):
        if key in result and result.get(key) is False:
            return True
    status = str(result.get("status") or "").strip().upper()
    if status and (status.startswith("FAIL") or status.startswith("ERROR")
                   or status in ("REJECTED", "UNRESOLVED")):
        return True
    if isinstance(result.get("errors"), list) and result.get("errors"):
        return True
    return False


def observe_roles(module: str, case: dict, root: Path | None = None) -> dict:
    """Which parameters are destinations and which are sources -- observed.

    The binder decides this from the NAME: it treats a parameter as a
    destination only when "output" appears in it. `target_path` names no
    output and is therefore searched for in a world where it does not
    exist yet, so the capability is unbindable and the forged capability
    was unreachable for a reason that had nothing to do with the module.

    So ask the machine instead of reading the name. Point each path-like
    parameter at a scratch path that does not exist, run the module, and
    look: a file that appeared is a destination, one that was already
    there is a source. Same rule as the feature probe -- the machine
    knows, the name only guesses.
    """
    root = root or ROOT
    roles: dict[str, str] = {}
    for key, value in (case or {}).items():
        if not isinstance(value, str) or not value.strip():
            continue
        if not ("/" in value or value.lower().endswith(_FILE_EXT)):
            continue
        scratch = "canonical/astra_runtime/tmp/forge_probe_%s_%s" % (
            hashlib.sha256((module + key).encode("utf-8")).hexdigest()[:10],
            Path(value).name)
        target = root / scratch
        existed_before = target.exists()
        probe = dict(case)
        probe[key] = scratch
        try:
            ok, _ = _call(module, probe, root)
        except Exception:
            ok = False
        appeared = (not existed_before) and target.is_file()
        roles[key] = "output" if (ok and appeared) else "input"
        if appeared:
            try:
                target.unlink()
            except Exception:
                pass
    return roles


# --- forging from the inventory -----------------------------------------

_PATHY = ("path", "file", "dir", "root", "src", "dst", "source", "target",
          "input", "output", "filename", "folder")
_VOCAB = ("canonical/runtime", "hello", "test", "1,2,3", "a b c", "42")


def _path_pool(root: Path, hint: str | None = None) -> list[str]:
    """Real files to hand a path-shaped parameter, by the kind it names."""
    try:
        from canonical.runtime.world_binding_v1 import _EXT_BY_TOKEN
    except Exception:
        _EXT_BY_TOKEN = {}
    ext = None
    if hint:
        ext = _EXT_BY_TOKEN.get(hint)
    out = []
    for base in ("canonical/runtime", "canonical/astra_runtime/tmp",
                 "canonical/tests"):
        d = root / base
        if not d.is_dir():
            continue
        try:
            names = sorted(d.iterdir())
        except Exception:
            continue
        for p in names:
            if not p.is_file():
                continue
            if ext and not p.name.lower().endswith(ext):
                continue
            rel = str(p.relative_to(root))
            out.append(rel)
            if len(out) >= 6:
                return out
    return out or ["canonical/runtime/grounded_action_v1.py"]


def signature_of(source_rel: str, function: str, root: Path) -> dict:
    """Each parameter's declared type, read from the function's own source.

    Type-blind input generation is not generation, it is noise: `generate
    (rng, n)` was handed a string for `n` and refused with a TypeError,
    which says nothing about the function and everything about the guess.
    The annotation is right there in the file, so it is read rather than
    inferred from the parameter's name.
    """
    path = root / str(source_rel or "")
    if not path.is_file():
        return {}
    try:
        tree = ast.parse(path.read_text(errors="replace"))
    except Exception:
        return {}
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function:
            for arg in list(node.args.args) + list(node.args.kwonlyargs):
                ann = ""
                if arg.annotation is not None:
                    try:
                        ann = ast.unparse(arg.annotation)
                    except Exception:
                        ann = ""
                out[arg.arg] = ann
            break
    return out


def _values_for(param: str, ann: str, root: Path, count: int) -> list:
    """A few plausible values of the declared type."""
    low = str(param).lower()
    a = str(ann or "").lower()
    pathy = any(t in low for t in _PATHY)
    if pathy and not any(t in a for t in ("int", "float", "bool")):
        hint = next((t for t in _EXT_BY_TOKEN_WORDS if t in low), None)
        return _path_pool(root, hint)[:count]
    if "int" in a:
        return [1, 2, 3][:count]
    if "float" in a:
        return [1.0, 2.5, 3.0][:count]
    if "bool" in a:
        return [True, False][:count]
    if "list" in a or "sequence" in a or "tuple" in a:
        return [["a"], ["a", "b"], ["a", "b", "c"]][:count]
    if "dict" in a or "mapping" in a:
        return [{"a": 1}, {"a": 1, "b": 2}][:count]
    return list(_VOCAB)[:count]


def candidate_inputs(params, root: Path, count: int = 3,
                     annotations: dict | None = None,
                     source_rel: str = "", function: str = "") -> list[dict]:
    """Plausible inputs for a function the forge was never told about.

    Invented inputs are an unverifiable act, so these are not invented:
    path-shaped parameters get real files of the kind their name asks
    for, and the rest get short ordinary strings. Nothing here has to be
    right -- a wrong input simply fails a case, and two successes are
    required before anything is admitted.
    """
    params = [str(p) for p in (params or [])]
    if annotations is None and source_rel and function:
        annotations = signature_of(source_rel, function, root)
    annotations = annotations or {}
    pools: dict[str, list] = {}
    for name in params:
        pools[name] = _values_for(name, annotations.get(name, ""), root, count) \
            or list(_VOCAB)
    cases = []
    for i in range(count):
        case = {}
        for name, pool in pools.items():
            case[name] = pool[i % len(pool)]
        cases.append(case)
    # make the cases actually differ
    for i, case in enumerate(cases):
        for name, pool in pools.items():
            if len(pool) > 1:
                case[name] = pool[(i + list(pools).index(name)) % len(pool)]
    return cases


_EXT_BY_TOKEN_WORDS = ("json", "yaml", "pdf", "docx", "xlsx", "sqlite",
                       "csv", "markdown", "md", "png", "html", "tar",
                       "archive", "db", "database", "sheet", "workbook")


def forge_function(entry: dict, root: Path | None = None,
                   require_kill: bool = True) -> dict:
    """Put one inventoried function through the same six tests.

    The 5,221 inventoried functions are pure Python already in this
    repository: no binary to install, no network to reach. They are the
    seam the dormant modules turned out not to be. The inventory calls
    them a measurement of existing tests and not a capability receipt;
    surviving determinism, non-vacuity, honest success and attempted
    killing is a stronger claim than that, and it is the claim that
    admits one.
    """
    root = root or ROOT
    from canonical.runtime import module_bridge_v1 as MB
    name = str(entry.get("function") or "")
    cid = "forged.fn." + re.sub(r"[^a-z0-9]+", "_",
                                str(entry.get("source_rel") or "").lower()) \
        + "." + name
    report = {"capability_id": cid[:150], "function": name,
              "source_rel": entry.get("source_rel"), "admitted": False,
              "checks": {}, "reasons": []}

    params = [p for p in (entry.get("params") or []) if not str(p).startswith("_")]
    required = [str(p) for p in (entry.get("required") or [])]
    if not required:
        required = params[:1]

    def call(case):
        try:
            out = MB.invoke(entry, case, root)
        except Exception as exc:
            return False, type(exc).__name__ + ":" + str(exc)[:160]
        if not isinstance(out, dict):
            return False, "RESULT_NOT_A_DICT"
        return True, out

    cases = candidate_inputs(required, root,
                            annotations=signature_of(
                                str(entry.get("source_rel") or ""), name, root),
                            source_rel=str(entry.get("source_rel") or ""),
                            function=name)
    runs = []
    for i, case in enumerate(cases):
        ok, out = call(case)
        if not ok:
            report["reasons"].append("case%d_FAILED:%s" % (i, str(out)[:80]))
            continue
        ok2, out2 = call(case)
        if not ok2 or json.dumps(out, sort_keys=True, default=str) != \
                json.dumps(out2, sort_keys=True, default=str):
            report["reasons"].append("case%d_NOT_DETERMINISTIC" % i)
            continue
        if is_vacuous(out):
            report["reasons"].append("case%d_VACUOUS" % i)
            continue
        if self_reported_failure(out):
            report["reasons"].append("case%d_SELF_REPORTED_FAILURE" % i)
            continue
        runs.append((case, out))
    report["checks"]["ran"] = "%d/%d" % (len(runs), len(cases))
    if len(runs) < 2:
        report["reasons"].append("NOT_GENERAL")
        return report

    if require_kill:
        kills = 0
        tried = 0
        for case, _ in runs:
            for bad in mutations(case):
                tried += 1
                ok, _ = call(bad)
                if not ok:
                    kills += 1
        report["checks"]["killed"] = "%d/%d" % (kills, tried)
        if kills == 0:
            report["reasons"].append(
                "NO_MUTATION_COULD_KILL_IT" if tried
                else "NO_MUTATION_WAS_POSSIBLE__UNEVIDENCED")
            return report

    report["admitted"] = True
    return report


def sweep_inventory(limit: int = 60, root: Path | None = None,
                    min_passing_cases: int = 1) -> dict:
    """Try to forge from the inventory. Most will fail; that is the point."""
    root = root or ROOT
    from canonical.runtime import module_bridge_v1 as MB
    entries = (MB._index() or {}).get("entries") or []
    pool = [e for e in entries
            if int(e.get("passing_cases") or 0) >= min_passing_cases
            and str(e.get("tier") or "") == "TEST_EVIDENCED"]
    tried, admitted = 0, []
    for e in pool[:limit]:
        tried += 1
        r = forge_function(e, root)
        if r.get("admitted"):
            admitted.append(r)
    return {"tried": tried, "admitted": len(admitted), "results": admitted}


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
