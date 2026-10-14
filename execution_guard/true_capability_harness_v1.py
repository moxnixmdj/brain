#!/usr/bin/env python3
"""True-capability harness (stdlib only).

Implements canonical/laws/TRUE_CAPABILITY_TEST_LAW_V1.md:

  * UNSEEN INSTANCES  - instances are generated at run time from a seed the
    author cannot choose (GitHub run id + attempt + commit on Actions, random
    bytes elsewhere).  A fixed seed is allowed only for replaying a receipt and
    is marked REPLAY (never crediting).
  * INDEPENDENT ORACLES - every instance is judged by oracle functions that
    live in a different file from the solver; the spec declares each oracle's
    class (PUBLISHED_CANARY, DIFFERENTIAL_EXTERNAL, ANALYTIC_CLOSED_FORM,
    METAMORPHIC, PROPERTY).  At least one oracle must not share the solver's
    lineage (the spec says which).
  * ZERO MODEL - the solver runs with the network disabled and the harness
    fails the run if a model/LLM library is imported.
  * SEPARATION - the generator and the oracles may not import the solver
    module (checked on source), so a solver cannot be tuned to its own tests.

The receipt it writes is a MEASUREMENT with `authority: NONE`.  It proves
nothing by itself; credit is granted only by the referee on a public runner.

Usage
  python3 execution_guard/true_capability_harness_v1.py run --spec SPEC.json
        [--instances N] [--seed HEX] [--receipt-dir DIR] [--ledger PATH]
  python3 execution_guard/true_capability_harness_v1.py self-test
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import platform
import random
import re
import socket
import sys
import tempfile
import time
import traceback
from typing import Any, Callable

SCHEMA_SPEC = "TRUE_CAPABILITY_SPEC_V1"
SCHEMA_RECEIPT = "TRUE_CAPABILITY_RECEIPT_V1"
SCHEMA_LEDGER = "TRUE_CAPABILITY_LEDGER_V1"
ORACLE_CLASSES = {
    "PUBLISHED_CANARY",      # fixed inputs with outputs published by a third party
    "DIFFERENTIAL_EXTERNAL",  # an implementation written by someone else
    "ANALYTIC_CLOSED_FORM",   # closed-form truth derived from the governing standard
    "METAMORPHIC",            # relations between outputs of related inputs
    "PROPERTY",               # invariants every valid output must satisfy
}
BANNED_MODULE_PREFIXES = (
    "torch", "transformers", "tensorflow", "jax", "onnxruntime", "llama_cpp",
    "vllm", "openai", "anthropic", "google.generativeai", "cohere", "mistralai",
    "sklearn", "xgboost", "lightgbm", "sentence_transformers", "litellm",
)
ROOT = pathlib.Path(__file__).resolve().parents[1]


class HarnessError(Exception):
    pass


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------

def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_sha(path: pathlib.Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def load_module(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise HarnessError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def derive_seed(explicit: str | None) -> tuple[str, str, bool]:
    """Return (seed_hex, seed_source, replay)."""
    if explicit:
        if not re.fullmatch(r"[0-9a-f]{16,64}", explicit):
            raise HarnessError("explicit seed must be 16-64 hex chars")
        return explicit, "EXPLICIT_REPLAY", True
    run_id = os.environ.get("GITHUB_RUN_ID")
    sha = os.environ.get("GITHUB_SHA")
    if run_id and sha:
        attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
        material = f"{run_id}:{attempt}:{sha}".encode()
        return hashlib.sha256(material).hexdigest(), "GITHUB_RUN_ID_ATTEMPT_SHA", False
    return os.urandom(32).hex(), "OS_URANDOM", False


def carrier_name() -> str:
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return "GITHUB_ACTIONS:" + os.environ.get("GITHUB_REPOSITORY", "?")
    return "SANDBOX"


def source_imports(path: pathlib.Path) -> set[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    names: set[str] = set()
    for m in re.finditer(r"^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))", text, re.M):
        names.add((m.group(1) or m.group(2)).split(".")[-1])
        names.add(m.group(1) or m.group(2))
    for m in re.finditer(r"spec_from_file_location\([^)]*?([\w/\.\-]+\.py)", text):
        names.add(pathlib.Path(m.group(1)).stem)
    return names


class NetworkBlocked(RuntimeError):
    pass


_NETWORK_AUDIT_EVENTS = frozenset({
    "socket.connect", "socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr",
    "socket.getnameinfo", "socket.sendto", "socket.sendmsg", "socket.bind",
})
_network_block_installed = False


def _network_audit_hook(event: str, args: tuple) -> None:
    if event in _NETWORK_AUDIT_EVENTS:
        raise NetworkBlocked("network access is disabled inside the true-capability harness (" + event + ")")


def block_network() -> None:
    """Deny every network operation for the rest of this process via PEP 578 audit hooks.

    This is the interpreter's own mechanism (sys.addaudithook): nothing in the
    standard library is replaced, and the hook cannot be removed once installed,
    which is exactly the property a measurement process needs.
    """
    global _network_block_installed
    if not _network_block_installed:
        sys.addaudithook(_network_audit_hook)
        _network_block_installed = True


def banned_modules_loaded() -> list[str]:
    hits = []
    for name in list(sys.modules):
        for pref in BANNED_MODULE_PREFIXES:
            if name == pref or name.startswith(pref + "."):
                hits.append(name)
                break
    return sorted(set(hits))


# ----------------------------------------------------------------------------
# core run
# ----------------------------------------------------------------------------

def load_spec(spec_path: pathlib.Path) -> dict[str, Any]:
    spec = json.loads(spec_path.read_text())
    if spec.get("schema") != SCHEMA_SPEC:
        raise HarnessError("spec schema must be " + SCHEMA_SPEC)
    for key in ("capability_id", "claim", "input_class", "scope_limits", "solver",
                "generator", "oracles", "min_instances", "pass_threshold",
                "independent_oracle_ids", "falsification_condition"):
        if key not in spec:
            raise HarnessError("spec missing " + key)
    if not spec["independent_oracle_ids"]:
        raise HarnessError("spec must name at least one oracle that does not share the solver's lineage")
    return spec


def resolve(root: pathlib.Path, rel: str) -> pathlib.Path:
    p = (root / rel).resolve()
    if not p.exists():
        raise HarnessError("missing file " + rel)
    return p


def run_spec(spec_path: pathlib.Path, *, root: pathlib.Path, instances: int | None,
             seed: str | None, receipt_dir: pathlib.Path | None, ledger: pathlib.Path | None,
             quiet: bool = False) -> dict[str, Any]:
    spec = load_spec(spec_path)
    cap = spec["capability_id"]
    solver_path = resolve(root, spec["solver"]["module"])
    gen_path = resolve(root, spec["generator"]["module"])
    oracle_path = resolve(root, spec["oracles"]["module"])
    if len({solver_path, gen_path, oracle_path}) != 3:
        raise HarnessError("solver, generator and oracle module must be three different files")
    solver_stem = solver_path.stem
    for label, path in (("generator", gen_path), ("oracle", oracle_path)):
        imps = source_imports(path)
        if solver_stem in imps or any(i.endswith("." + solver_stem) for i in imps):
            raise HarnessError(f"{label} module imports the solver module ({solver_stem}); separation violated")

    n = int(instances or spec["min_instances"])
    if n < int(spec["min_instances"]):
        raise HarnessError("instances below spec minimum")
    seed_hex, seed_source, replay = derive_seed(seed)
    rng = random.Random(int(seed_hex[:32], 16))

    block_network()
    t0 = time.time()
    solver_mod = load_module(solver_path, "tc_solver_" + cap.lower())
    gen_mod = load_module(gen_path, "tc_gen_" + cap.lower())
    oracle_mod = load_module(oracle_path, "tc_oracle_" + cap.lower())
    solve: Callable[[dict[str, Any]], dict[str, Any]] = getattr(solver_mod, spec["solver"]["entry"])
    generate = getattr(gen_mod, spec["generator"].get("entry", "generate"))
    oracles = getattr(oracle_mod, spec["oracles"].get("entry", "oracles"))()
    declared = {o["id"]: o for o in spec["oracles"]["declared"]}
    for o in oracles:
        if o["id"] not in declared:
            raise HarnessError("oracle not declared in spec: " + o["id"])
        if declared[o["id"]]["class"] not in ORACLE_CLASSES:
            raise HarnessError("unknown oracle class for " + o["id"])
    missing = set(declared) - {o["id"] for o in oracles}
    if missing:
        raise HarnessError("declared oracles not implemented: " + ",".join(sorted(missing)))
    for oid in spec["independent_oracle_ids"]:
        if oid not in declared:
            raise HarnessError("independent oracle id not declared: " + oid)

    inst_list = list(generate(rng, n))
    if len(inst_list) != n:
        raise HarnessError("generator returned wrong instance count")

    per_oracle = {o["id"]: {"pass": 0, "fail": 0, "error": 0} for o in oracles}
    failures: list[dict[str, Any]] = []
    solver_errors = 0
    instance_pass = 0
    canary_results: list[dict[str, Any]] = []
    for idx, inst in enumerate(inst_list):
        try:
            out = solve(inst)
        except Exception as exc:  # solver crash = failure on this instance
            solver_errors += 1
            if len(failures) < 8:
                failures.append({"instance_index": idx, "instance": inst, "solver_error": repr(exc)})
            continue
        ok_all = True
        for o in oracles:
            try:
                ok, detail = o["check"](inst, out, solve)
            except Exception as exc:
                ok, detail = False, "ORACLE_ERROR:" + repr(exc)
                per_oracle[o["id"]]["error"] += 1
            if ok:
                per_oracle[o["id"]]["pass"] += 1
            else:
                per_oracle[o["id"]]["fail"] += 1
                ok_all = False
                if len(failures) < 8:
                    failures.append({"instance_index": idx, "oracle": o["id"], "instance": inst,
                                     "output": out, "detail": str(detail)[:400]})
        if ok_all:
            instance_pass += 1

    # published canaries: fixed third-party inputs/outputs, run in addition to fresh instances
    canaries = getattr(oracle_mod, "canaries", lambda: [])()
    canary_pass = 0
    for c in canaries:
        try:
            out = solve(c["instance"])
            ok, detail = c["check"](out)
        except Exception as exc:
            ok, detail = False, repr(exc)
        canary_results.append({"id": c["id"], "source": c["source"], "pass": bool(ok), "detail": str(detail)[:300]})
        canary_pass += int(bool(ok))

    banned = banned_modules_loaded()
    pass_rate = instance_pass / n
    threshold = float(spec["pass_threshold"])
    verdict = "PASS" if (pass_rate >= threshold and canary_pass == len(canaries) and not banned) else "FAIL"
    if replay:
        verdict += "__REPLAY_NOT_CREDITING"
    receipt = {
        "schema": SCHEMA_RECEIPT,
        "authority": "NONE",
        "kind": "FRESH_INSTANCE_MEASUREMENT",
        "capability_id": cap,
        "claim": spec["claim"],
        "scope_limits": spec["scope_limits"],
        "spec_path": str(spec_path.relative_to(root)) if spec_path.is_relative_to(root) else str(spec_path),
        "spec_sha256": sha256_file(spec_path),
        "carrier": carrier_name(),
        "github": {k: os.environ.get(k) for k in ("GITHUB_REPOSITORY", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA", "GITHUB_REF")},
        "seed": seed_hex,
        "seed_source": seed_source,
        "replay": replay,
        "instances": n,
        "instance_pass": instance_pass,
        "fresh_pass_rate": round(pass_rate, 6),
        "pass_threshold": threshold,
        "solver_errors": solver_errors,
        "per_oracle": per_oracle,
        "oracle_classes": {oid: declared[oid]["class"] for oid in declared},
        "independent_oracle_ids": spec["independent_oracle_ids"],
        "canaries": canary_results,
        "canary_pass": f"{canary_pass}/{len(canaries)}",
        "banned_modules_detected": banned,
        "network_blocked": True,
        "nonstdlib_modules_loaded": sorted(_nonstdlib_loaded()),
        "blobs": {
            "solver": {"path": str(solver_path.relative_to(root)), "git_blob_sha": git_blob_sha(solver_path), "sha256": sha256_file(solver_path)},
            "generator": {"path": str(gen_path.relative_to(root)), "git_blob_sha": git_blob_sha(gen_path), "sha256": sha256_file(gen_path)},
            "oracles": {"path": str(oracle_path.relative_to(root)), "git_blob_sha": git_blob_sha(oracle_path), "sha256": sha256_file(oracle_path)},
        },
        "python": platform.python_version(),
        "wall_seconds": round(time.time() - t0, 3),
        "failures_sample": failures,
        "verdict": verdict,
        "self_description": "Measurement of a solver on instances generated after the solver was frozen, judged by oracles in separate files. authority NONE: it records what was observed on this carrier and grants no credit; only a referee-signed run on a public runner may be cited.",
    }
    if receipt_dir is not None:
        receipt_dir.mkdir(parents=True, exist_ok=True)
        out_path = receipt_dir / f"{cap}__{seed_hex[:16]}.json"
        out_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        receipt["receipt_path"] = str(out_path.relative_to(root)) if out_path.is_relative_to(root) else str(out_path)
    if ledger is not None:
        update_ledger(ledger, receipt, root)
    if not quiet:
        print(f"TRUE_CAPABILITY_{verdict} {cap} fresh_pass_rate={pass_rate:.4f} ({instance_pass}/{n}) canaries={canary_pass}/{len(canaries)} seed={seed_hex[:16]} source={seed_source} carrier={receipt['carrier']}")
        for oid, c in per_oracle.items():
            print(f"  oracle {oid:40s} {declared[oid]['class']:22s} pass={c['pass']} fail={c['fail']} error={c['error']}")
        if banned:
            print("  BANNED_MODULES:", ",".join(banned))
        for f in failures[:3]:
            print("  failure:", json.dumps(f)[:300])
    return receipt


def _nonstdlib_loaded() -> set[str]:
    std = set(getattr(sys, "stdlib_module_names", set()))
    out = set()
    for name, mod in list(sys.modules.items()):
        top = name.split(".")[0]
        if top in std or top.startswith("_") or top.startswith("tc_"):
            continue
        f = getattr(mod, "__file__", None) or ""
        if "site-packages" in f or "dist-packages" in f:
            out.add(top)
    return out


def update_ledger(ledger_path: pathlib.Path, receipt: dict[str, Any], root: pathlib.Path) -> None:
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text())
    else:
        ledger = {"schema": SCHEMA_LEDGER, "authority": "NONE", "rows": {},
                  "rule": "Rows are written only by execution_guard/true_capability_harness_v1.py from a receipt. A row is a measurement, not a claim; status MEASURED_SANDBOX never counts; status MEASURED_PUBLIC_RUNNER counts only when the receipt is referee-signed."}
    rows = ledger.setdefault("rows", {})
    status = "MEASURED_PUBLIC_RUNNER" if receipt["carrier"].startswith("GITHUB_ACTIONS") else "MEASURED_SANDBOX"
    if receipt["replay"]:
        status = "REPLAY_NOT_CREDITING"
    rows[receipt["capability_id"]] = {
        "claim": receipt["claim"],
        "scope_limits": receipt["scope_limits"],
        "spec_path": receipt["spec_path"],
        "latest_receipt": receipt.get("receipt_path"),
        "fresh_pass_rate": receipt["fresh_pass_rate"],
        "instances": receipt["instances"],
        "canary_pass": receipt["canary_pass"],
        "verdict": receipt["verdict"],
        "status": status,
        "carrier": receipt["carrier"],
        "seed_source": receipt["seed_source"],
        "solver_git_blob_sha": receipt["blobs"]["solver"]["git_blob_sha"],
        "oracle_classes": receipt["oracle_classes"],
        "independent_oracle_ids": receipt["independent_oracle_ids"],
        "measured_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")


# ----------------------------------------------------------------------------
# self-test: the harness must be able to fail
# ----------------------------------------------------------------------------

_SELFTEST_FILES = {
    "solver_ok.py": "def solve(inst):\n    return {'sum': inst['a'] + inst['b']}\n",
    "solver_bad.py": "def solve(inst):\n    return {'sum': inst['a'] + inst['b'] + (1 if inst['a'] % 3 == 0 else 0)}\n",
    "solver_imports_torch.py": (
        "import os, sys\n"
        "sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fake_site'))\n"
        "import torch  # a real (fixture) module named torch, found on sys.path\n"
        "def solve(inst):\n    return {'sum': inst['a'] + inst['b']}\n"
    ),
    "fake_site/torch.py": "FIXTURE = 'stands in for a model framework in the harness self-test only'\n",
    "gen.py": "def generate(rng, n):\n    return [{'a': rng.randint(-1000, 1000), 'b': rng.randint(-1000, 1000)} for _ in range(n)]\n",
    "gen_cheat.py": "import solver_ok\ndef generate(rng, n):\n    return [{'a': 1, 'b': 1} for _ in range(n)]\n",
    "oracle.py": (
        "def oracles():\n"
        "    def closed_form(inst, out, solve):\n"
        "        return out['sum'] == inst['a'] + inst['b'], 'expected %d' % (inst['a'] + inst['b'])\n"
        "    def commutative(inst, out, solve):\n"
        "        other = solve({'a': inst['b'], 'b': inst['a']})\n"
        "        return other['sum'] == out['sum'], 'commutativity'\n"
        "    return [{'id': 'CLOSED_FORM', 'check': closed_form}, {'id': 'COMMUTATIVE', 'check': commutative}]\n"
        "def canaries():\n"
        "    return [{'id': 'TWO_PLUS_TWO', 'source': 'arithmetic', 'instance': {'a': 2, 'b': 2}, 'check': lambda out: (out['sum'] == 4, out)}]\n"
    ),
}


def _write_selftest_spec(d: pathlib.Path, solver: str, gen: str) -> pathlib.Path:
    spec = {
        "schema": SCHEMA_SPEC, "capability_id": "SELFTEST_INT_ADD", "claim": "integer addition",
        "input_class": "pairs of ints in [-1000,1000]", "scope_limits": ["ints only"],
        "solver": {"module": solver, "entry": "solve"}, "generator": {"module": gen},
        "oracles": {"module": "oracle.py", "declared": [{"id": "CLOSED_FORM", "class": "ANALYTIC_CLOSED_FORM"}, {"id": "COMMUTATIVE", "class": "METAMORPHIC"}]},
        "independent_oracle_ids": ["CLOSED_FORM"], "min_instances": 50, "pass_threshold": 1.0,
        "falsification_condition": "any pair whose sum is wrong",
    }
    p = d / f"spec_{pathlib.Path(solver).stem}_{pathlib.Path(gen).stem}.json"
    p.write_text(json.dumps(spec))
    return p


def self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        d = pathlib.Path(td)
        for name, body in _SELFTEST_FILES.items():
            (d / name).parent.mkdir(parents=True, exist_ok=True)
            (d / name).write_text(body)
        results = []
        ok = run_spec(_write_selftest_spec(d, "solver_ok.py", "gen.py"), root=d, instances=200, seed=None, receipt_dir=None, ledger=None, quiet=True)
        results.append(("correct solver passes", ok["verdict"] == "PASS" and ok["fresh_pass_rate"] == 1.0))
        bad = run_spec(_write_selftest_spec(d, "solver_bad.py", "gen.py"), root=d, instances=200, seed=None, receipt_dir=None, ledger=None, quiet=True)
        results.append(("wrong solver fails", bad["verdict"] == "FAIL" and bad["fresh_pass_rate"] < 1.0))
        try:
            run_spec(_write_selftest_spec(d, "solver_ok.py", "gen_cheat.py"), root=d, instances=50, seed=None, receipt_dir=None, ledger=None, quiet=True)
            results.append(("generator importing solver rejected", False))
        except HarnessError as exc:
            results.append(("generator importing solver rejected", "separation" in str(exc)))
        rep = run_spec(_write_selftest_spec(d, "solver_ok.py", "gen.py"), root=d, instances=50, seed="deadbeefdeadbeef", receipt_dir=None, ledger=None, quiet=True)
        results.append(("explicit seed marked replay", rep["replay"] and "REPLAY" in rep["verdict"]))
        try:
            b = run_spec(_write_selftest_spec(d, "solver_imports_torch.py", "gen.py"), root=d, instances=50, seed=None, receipt_dir=None, ledger=None, quiet=True)
            results.append(("banned module makes the run fail", b["verdict"] == "FAIL" and "torch" in b["banned_modules_detected"]))
        finally:
            sys.modules.pop("torch", None)
            if str(d / "fake_site") in sys.path:
                sys.path.remove(str(d / "fake_site"))
        try:
            socket.create_connection(("127.0.0.1", 9), timeout=0.2)
            results.append(("network blocked", False))
        except NetworkBlocked:
            results.append(("network blocked", True))
        except OSError:
            results.append(("network blocked", False))
    allok = all(r[1] for r in results)
    for name, res in results:
        print(("PASS " if res else "FAIL ") + name)
    print("TRUE_CAPABILITY_HARNESS_SELF_TEST_" + ("PASS" if allok else "FAIL"))
    return 0 if allok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--spec", required=True)
    r.add_argument("--instances", type=int)
    r.add_argument("--seed")
    r.add_argument("--receipt-dir")
    r.add_argument("--ledger")
    r.add_argument("--root", default=str(ROOT))
    sub.add_parser("self-test")
    ns = ap.parse_args(argv)
    if ns.cmd == "self-test":
        return self_test()
    root = pathlib.Path(ns.root).resolve()
    try:
        rec = run_spec(pathlib.Path(ns.spec).resolve(), root=root, instances=ns.instances, seed=ns.seed,
                       receipt_dir=pathlib.Path(ns.receipt_dir).resolve() if ns.receipt_dir else None,
                       ledger=pathlib.Path(ns.ledger).resolve() if ns.ledger else None)
    except HarnessError as exc:
        print("TRUE_CAPABILITY_HARNESS_ERROR", exc)
        return 2
    except Exception:
        traceback.print_exc()
        return 2
    return 0 if rec["verdict"].startswith("PASS") else 1


if __name__ == "__main__":
    sys.exit(main())
