#!/usr/bin/env python3
"""Measure the live Brain end to end on goals it has never seen.

Law: canonical/laws/TRUE_CAPABILITY_TEST_LAW_V1.md (fresh instances, independent oracle,
zero model).  This is a measurement of the whole path plain goal -> compiler -> planner ->
controller -> bound tool -> artifact, through the public entry points:

  OLD  canonical.runtime.live_integrated_brain_v1.run_raw_goal
  NEW  canonical.runtime.live_brain_route_admission_v1.solve   (fail-closed admission)

Three measurements, all seeded from os.urandom unless --seed is given (a seeded run is a
replay and is labelled as such):

  1. tool liveness   - for each of the bound capabilities: adapter present, imports,
                       declared external dependency present on THIS machine.
  2. in-scope goals  - fresh goals from families the compiler is documented to handle,
                       each checked by an independent stdlib oracle on the real artifact
                       (tarfile members and bytes, json content, exact literal).
  3. out-of-scope    - fresh goals no bound tool can serve (translation, proofs,
                       summaries, finance, prose).  The only correct answer is
                       pass=False with no artifact written.  A PASS is a fail-open.

Writes one JSON receipt. Authority: NONE. Credit: 0. Nothing here changes a scoreboard.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import os
import random
import shutil
import string
import subprocess
import sys
import tarfile
import time
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_LIVE_SOLVER_END_TO_END_MEASUREMENT_V1"
REGISTRY = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
ADAPTERS = ROOT / "canonical/runtime/bound_capabilities"
WORK = "canonical/astra_runtime/tmp/live_solver_e2e"

# apt/npm packages -> the executable or python module that proves presence on this machine
_APT_PROBE = {
    "jq": ("bin", "jq"), "yq": ("bin", "yq"), "pandoc": ("bin", "pandoc"), "weasyprint": ("bin", "weasyprint"),
    "tesseract-ocr": ("bin", "tesseract"), "qrencode": ("bin", "qrencode"), "zbar-tools": ("bin", "zbarimg"),
    "chromium-chromedriver": ("bin", "chromedriver"), "chromium-driver": ("bin", "chromedriver"), "sqlite3": ("bin", "sqlite3"),
    "zint": ("bin", "zint"), "tar": ("bin", "tar"), "python3-docx": ("py", "docx"), "python3-openpyxl": ("py", "openpyxl"),
    "python3-xlsxwriter": ("py", "xlsxwriter"), "python3-sympy": ("py", "sympy"), "python3-pypdf": ("py", "pypdf"),
    "python3-pil": ("py", "PIL"), "python3-yaml": ("py", "yaml"), "python3-msgpack": ("py", "msgpack"), "python3-bson": ("py", "bson"),
}


def _present(kind: str, name: str) -> bool:
    if kind == "bin":
        return shutil.which(name) is not None
    return importlib.util.find_spec(name) is not None


def tool_liveness() -> dict[str, Any]:
    doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
    rows = []
    for cid, entry in doc["capabilities"].items():
        adapter = str(entry.get("adapter_module") or "")
        native = adapter == "runtime_native_action" or (entry.get("source") or {}).get("type") == "runtime_native"
        adapter_path = ADAPTERS / (adapter + ".py") if adapter and not native else None
        declared_path = (entry.get("source") or {}).get("adapter_path")
        if adapter_path is not None and not adapter_path.is_file() and declared_path:
            adapter_path = ROOT / str(declared_path)  # some adapters live outside bound_capabilities/
        imports_ok, import_error = None, None
        if adapter_path is not None and adapter_path.is_file():
            try:
                spec = importlib.util.spec_from_file_location("probe_" + adapter, adapter_path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[union-attr]
                imports_ok = hasattr(mod, str(entry.get("entrypoint") or "run"))
            except Exception as exc:  # noqa: BLE001 - liveness probe
                imports_ok, import_error = False, type(exc).__name__ + ":" + str(exc)[:120]
        source = entry.get("source") or {}
        deps = []
        for pkg in source.get("packages") or []:
            name = str(pkg.get("name") or "")
            probe = _APT_PROBE.get(name)
            if source.get("type") == "pypi":
                probe = ("py", name.replace("-", "_"))
            deps.append({"package": name, "type": source.get("type"), "present_here": _present(*probe) if probe else None})
        placeholders = sorted(_placeholders(entry.get("action_template") or {}))
        rows.append({
            "capability_id": cid,
            "adapter_module": adapter or None,
            "runtime_native_action": native,
            "adapter_present": True if native else bool(adapter_path and adapter_path.is_file()),
            "adapter_imports": imports_ok,
            "import_error": import_error,
            "external_dependencies": deps,
            "all_dependencies_present_here": all(d["present_here"] is not False for d in deps) if deps else True,
            "takes_input_from_goal": bool(placeholders),
            "input_keys": placeholders,
            "platforms": entry.get("platforms"),
        })
    return {
        "capabilities_total": len(rows),
        "adapter_missing": sorted(r["capability_id"] for r in rows if not r["adapter_present"]),
        "adapter_import_failed": sorted(r["capability_id"] for r in rows if r["adapter_imports"] is False),
        "external_dependency_missing_here": sorted(r["capability_id"] for r in rows if not r["all_dependencies_present_here"]),
        "zero_input_capabilities": sorted(r["capability_id"] for r in rows if not r["takes_input_from_goal"]),
        "rows": rows,
    }


def _placeholders(value: Any) -> set[str]:
    import re
    found: set[str] = set()
    def walk(v: Any) -> None:
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, str):
            found.update(re.findall(r"\$\{input\.([A-Za-z0-9_]+)\}", v))
    walk(value)
    return found


# ----------------------------------------------------------------------------- fresh goals

def _word(rng: random.Random, n: int = 6) -> str:
    return "".join(rng.choice(string.ascii_lowercase) for _ in range(n))


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


class Case:
    def __init__(self, family: str, goal: str, oracle: Callable[[dict[str, Any]], tuple[bool, str]], expect_pass: bool, artifacts: list[Path]):
        self.family, self.goal, self.oracle, self.expect_pass, self.artifacts = family, goal, oracle, expect_pass, artifacts


def gen_archive(rng: random.Random, work: Path, i: int) -> Case:
    d = work / f"archive_{i}"
    d.mkdir(parents=True, exist_ok=True)
    files = {}
    for k in range(rng.randint(1, 4)):
        p = d / f"{_word(rng)}_{k}.txt"
        content = (_word(rng, rng.randint(1, 40)) + "\n") * rng.randint(1, 5)
        p.write_text(content, encoding="utf-8")
        files[_rel(p)] = content.encode("utf-8")
    manifest = d / "manifest.json"
    manifest.write_text(json.dumps({"records": [{"verification_paths": sorted(files)}]}), encoding="utf-8")
    out = d / f"{_word(rng)}.tar.gz"
    phr = rng.choice([
        "Create a tar.gz archive from the manifest {m}, including all its verification_paths files, and save it to {o}.",
        "Create a tar.gz archive from {m} and save it to {o}.",
        "Build a tar.gz archive from the manifest {m} and write it to {o}.",
    ])
    goal = phr.format(m=_rel(manifest), o=_rel(out))

    def oracle(_: dict[str, Any]) -> tuple[bool, str]:
        if not out.is_file():
            return False, "archive not written"
        with tarfile.open(out, "r:gz") as tf:
            got = {}
            for m in tf.getmembers():
                if m.isfile():
                    got[m.name.lstrip("./")] = tf.extractfile(m).read()  # type: ignore[union-attr]
        expected = {k: v for k, v in files.items()}
        missing = [k for k in expected if not any(name.endswith(k) for name in got)]
        if missing:
            return False, "members missing: " + ",".join(missing)
        for k, v in expected.items():
            name = next(n for n in got if n.endswith(k))
            if got[name] != v:
                return False, "bytes differ for " + k
        return True, "all members present with identical bytes"
    return Case("ARCHIVE_TAR_GZ_FROM_MANIFEST", goal, oracle, True, [out])


def gen_literal_json(rng: random.Random, work: Path, i: int) -> Case:
    d = work / f"literal_{i}"
    d.mkdir(parents=True, exist_ok=True)
    out = d / f"{_word(rng)}.json"
    n = rng.randint(1, 3)
    fields = rng.sample(["id", "name", "value", "code", "label", "count"], 2)
    records = []
    for _ in range(n):
        a = _word(rng, rng.randint(2, 8))
        b = rng.randint(0, 999)
        records.append({fields[0]: a, fields[1]: b})
    count_word = {1: "one", 2: "two", 3: "three"}[n]
    body = "; ".join(f"{r[fields[0]]} {r[fields[1]]}" for r in records)
    terminal = rng.choice([".", ""])  # a natural sentence ends with a period; both forms are legitimate goals
    goal = f"Create {_rel(out)} containing exactly {count_word} record{'s' if n > 1 else ''} with fields {fields[0]} and {fields[1]}: {body}{terminal}"

    def oracle(_: dict[str, Any]) -> tuple[bool, str]:
        if not out.is_file():
            return False, "json not written"
        got = json.loads(out.read_text(encoding="utf-8"))
        return (got == records), f"expected {records} got {got}"
    return Case("LITERAL_JSON_RECORDS", goal, oracle, True, [out])


def gen_compound_literal(rng: random.Random, work: Path, i: int) -> Case:
    d = work / f"compound_{i}"
    d.mkdir(parents=True, exist_ok=True)
    a, b = d / f"{_word(rng)}.json", d / f"{_word(rng)}.json"
    ra = {"id": _word(rng, 4), "value": rng.randint(0, 99)}
    rb = {"id": _word(rng, 4), "value": rng.randint(0, 99)}
    goal = (f"Create {_rel(a)} containing exactly one record with fields id and value: {ra['id']} {ra['value']}. "
            f"Then create {_rel(b)} containing exactly one record with fields id and value: {rb['id']} {rb['value']}.")

    def oracle(_: dict[str, Any]) -> tuple[bool, str]:
        for p, r in ((a, ra), (b, rb)):
            if not p.is_file():
                return False, f"{p.name} not written"
            if json.loads(p.read_text(encoding="utf-8")) != [r]:
                return False, f"{p.name} content differs"
        return True, "both records exact"
    return Case("COMPOUND_TWO_STEP_LITERAL_JSON", goal, oracle, True, [a, b])


def gen_exact_literal(rng: random.Random, work: Path, i: int) -> Case:
    literal = " ".join(_word(rng, rng.randint(2, 7)) for _ in range(rng.randint(1, 5))) + " " + str(rng.randint(0, 9999))
    verb = rng.choice(["Respond", "Reply"])
    goal = f'{verb} with exactly "{literal}".'

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        ctl = result.get("controller_execution") or {}
        got = ctl.get("final_summary") if isinstance(ctl, dict) else None
        return (got == literal), f"expected {literal!r} got {got!r}"
    return Case("EXACT_LITERAL_RESPONSE", goal, oracle, True, [])


_OOS_TEMPLATES = [
    "Translate the sentence '{s}' into {lang} and save it to {o}.",
    "Write a short poem about {thing} and save it to {o}.",
    "Summarize the file {src} into three sentences and save the summary to {o}.",
    "Prove that the square root of {n} is irrational and save the proof to {o}.",
    "Compute the SA-CCR add-on for a {n},000,000 notional interest-rate swap and save it to {o}.",
    "Explain how the Python runtime allocates memory and save the explanation to {o}.",
    "Write a Python tutorial about {thing} for beginners and save it to {o}.",
    "Book a flight from {city} to Rome for next Monday and save the confirmation to {o}.",
    "Draft an email to {name} declining the meeting and save it to {o}.",
    "Count the number of vowels in the file {src} and save the count to {o}.",
    "Sort the lines of {src} alphabetically and save them to {o}.",
    "Convert {n} degrees Celsius to Fahrenheit and save the result to {o}.",
    "Find the capital of {country} and save it to {o}.",
    "Generate a secure password of {n} characters and save it to {o}.",
]


def gen_out_of_scope(rng: random.Random, work: Path, i: int) -> Case:
    d = work / f"oos_{i}"
    d.mkdir(parents=True, exist_ok=True)
    src = d / f"{_word(rng)}.txt"
    src.write_text("\n".join(_word(rng, rng.randint(3, 9)) for _ in range(rng.randint(3, 12))) + "\n", encoding="utf-8")
    out = d / f"{_word(rng)}.{rng.choice(['txt', 'md', 'json'])}"
    tpl = rng.choice(_OOS_TEMPLATES)
    goal = tpl.format(s=" ".join(_word(rng, 5) for _ in range(3)), lang=rng.choice(["French", "Arabic", "German"]),
                      o=_rel(out), src=_rel(src), thing=_word(rng, 7), n=rng.randint(2, 97), city=_word(rng, 6).title(),
                      name=_word(rng, 5).title(), country=_word(rng, 8).title())

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if result.get("pass") is True:
            return False, "FAIL_OPEN: reported PASS via " + str(result.get("compiled_capability_id"))
        if out.exists():
            return False, "FAIL_OPEN_SIDE_EFFECT: wrote " + out.name + " while failing"
        return True, str(result.get("failure_class"))
    return Case("OUT_OF_SCOPE_MUST_FAIL_CLOSED", goal, oracle, False, [out])


GENERATORS: dict[str, Callable[[random.Random, Path, int], Case]] = {
    "ARCHIVE_TAR_GZ_FROM_MANIFEST": gen_archive,
    "LITERAL_JSON_RECORDS": gen_literal_json,
    "COMPOUND_TWO_STEP_LITERAL_JSON": gen_compound_literal,
    "EXACT_LITERAL_RESPONSE": gen_exact_literal,
    "OUT_OF_SCOPE_MUST_FAIL_CLOSED": gen_out_of_scope,
}

# Families the compiler advertises but that need binaries / packages this machine lacks, or
# a goal grammar not yet reproduced here.  Listed so the denominator is honest.
NOT_MEASURED_HERE = {
    "DOCX_CREATE": "python3-docx package (apt) not installed here",
    "XLSX_CREATE_VERIFY": "xlsxwriter/openpyxl (apt) not installed here",
    "SQLITE_CREATE_VERIFY": "sqlite3 CLI verifier (apt) not installed here",
    "MARKDOWN_TO_PDF": "pandoc + weasyprint (apt) not installed here",
    "PDF_TEXT_OCR": "tesseract-ocr / pypdf (apt) not installed here",
    "QR_BARCODE_GENERATE_DECODE": "qrencode / zbar-tools / zint (apt) not installed here",
    "BROWSER_CAPTURE": "chromedriver (apt) not installed here",
    "HTTP_JSON_FETCH__PYPI_AUDIT__WEB_RELEASE": "network egress blocked in this sandbox",
    "YAML_TO_JSON": "yq (apt) not installed here",
    "NUMERIC_EXPRESSION_SYMPY": "python3-sympy (apt) not installed here",
    "CHART_RASTER_READERS": "PIL (apt) not installed here",
    "PYTHON_REPAIR_LOOPS__FAULT_LOCALIZATION": "stdlib-only; fresh-bug generator not yet written (next measurement)",
    "PYTHON_SOURCE_TEST_AUDIT": "stdlib-only; goal grammar needs context manifests; not yet generated",
    "KNOWLEDGE_FETCH_ASSESS_ASSERT": "network egress blocked in this sandbox",
    "SOURCE_RANKING_BM25__EVIDENCE_EXTRACT__DECISION_SYNTHESIS": "stdlib-only; compound goal grammar not yet generated",
}


def _entry(name: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    if name == "old":
        from canonical.runtime.live_integrated_brain_v1 import run_raw_goal
        return run_raw_goal
    from canonical.runtime.live_brain_route_admission_v1 import solve
    return solve


def run(seed: int | None, per_family: int, oos_count: int, entries: list[str], keep: bool) -> dict[str, Any]:
    replay = seed is not None
    if seed is None:
        seed = int.from_bytes(os.urandom(8), "big")
    work = ROOT / WORK
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    kstar_artifact = ROOT / "canonical/astra_runtime/artifacts/TERMINAL_KSTAR_RESULT_20261007_V1.json"
    kstar_existed = kstar_artifact.exists()
    run_tag = "E2E_" + hashlib.sha256(f"{seed}:{os.urandom(8).hex()}".encode()).hexdigest()[:10]
    results: dict[str, Any] = {}
    for entry_name in entries:
        fn = _entry(entry_name)
        rng = random.Random(seed)
        families: dict[str, dict[str, Any]] = {}
        failures: list[dict[str, Any]] = []
        for family, gen in GENERATORS.items():
            n = oos_count if family == "OUT_OF_SCOPE_MUST_FAIL_CLOSED" else per_family
            ok = 0
            elapsed = 0
            caps: dict[str, int] = {}
            for i in range(n):
                case = gen(rng, work / entry_name, i)
                for a in case.artifacts:
                    if a.exists():
                        a.unlink()
                t0 = time.perf_counter_ns()
                try:
                    # task ids must be unique: the live controller checkpoints per task id and
                    # refuses to re-run a finished id (MODEL_INDEPENDENT_CONTROLLER_PLAN_WITHOUT_FINISH)
                    result = fn({"task_id": f"{run_tag}_{entry_name}_{family}_{i}", "goal": case.goal})
                except Exception as exc:  # noqa: BLE001 - an exception leak is itself a finding
                    result = {"pass": None, "status": "EXCEPTION_LEAK", "failure_class": type(exc).__name__ + ":" + str(exc)[:200]}
                elapsed += time.perf_counter_ns() - t0
                cap = str(result.get("compiled_capability_id") or result.get("compiler_mode") or "-")
                caps[cap] = caps.get(cap, 0) + 1
                good, why = case.oracle(result)
                if good:
                    ok += 1
                elif len(failures) < 60:
                    failures.append({"family": family, "goal": case.goal[:220], "why": why[:300],
                                     "status": str(result.get("status"))[:120], "capability": cap,
                                     "admission_rule": ((result.get("route_admission") or {}).get("rule") if isinstance(result.get("route_admission"), dict) else None)})
            families[family] = {"instances": n, "oracle_pass": ok, "pass_rate": round(ok / n, 4) if n else None,
                                "mean_ms": round(elapsed / n / 1e6, 2) if n else None, "routes_taken": caps,
                                "expected": "all PASS with exact artifact" if family != "OUT_OF_SCOPE_MUST_FAIL_CLOSED" else "all FAIL closed, no artifact"}
        in_scope = [f for f in families if f != "OUT_OF_SCOPE_MUST_FAIL_CLOSED"]
        results[entry_name] = {
            "entry": "canonical.runtime.live_integrated_brain_v1.run_raw_goal" if entry_name == "old" else "canonical.runtime.live_brain_route_admission_v1.solve",
            "families": families,
            "in_scope_families_measured": len(in_scope),
            "in_scope_families_all_pass": sum(1 for f in in_scope if families[f]["oracle_pass"] == families[f]["instances"]),
            "in_scope_instance_pass_rate": round(sum(families[f]["oracle_pass"] for f in in_scope) / max(1, sum(families[f]["instances"] for f in in_scope)), 4),
            "out_of_scope_fail_closed_rate": families["OUT_OF_SCOPE_MUST_FAIL_CLOSED"]["pass_rate"],
            "failures_sample": failures,
        }
    if not keep and work.exists():
        shutil.rmtree(work)
    # remove the controller checkpoints this run created (state dir is not a measurement artifact)
    state = ROOT / "canonical/astra_runtime/state"
    removed = 0
    if state.is_dir():
        for p in state.glob(run_tag + "_*"):
            p.unlink()
            removed += 1
    if not kstar_existed and kstar_artifact.exists():
        kstar_artifact.unlink()  # written by the catch-all tool during fail-open runs of the old entry
    liveness = tool_liveness()
    return {
        "schema": SCHEMA,
        "authority": "NONE",
        "credit": 0,
        "incremental_spend_usd": 0,
        "model_dependency_count": 0,
        "replay": replay,
        "seed": seed,
        "run_tag": run_tag,
        "controller_checkpoints_removed": removed,
        "python": sys.version.split()[0],
        "machine": {"platform": sys.platform, "network_egress": "allowlisted hosts only"},
        "tool_liveness": liveness,
        "families_not_measured_here": NOT_MEASURED_HERE,
        "measurements": results,
        "how_to_read": [
            "in_scope_instance_pass_rate is over FRESH goals the compiler has never seen, judged on the real artifact by stdlib oracles.",
            "out_of_scope_fail_closed_rate must be 1.0: every goal no tool can serve must come back pass=False with nothing written.",
            "Families in families_not_measured_here are not failures and not passes; they are unmeasured on this machine.",
            "Nothing here is a capability credit. Authority NONE.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=None, help="replay seed (labels the run as a replay)")
    ap.add_argument("--per-family", type=int, default=50)
    ap.add_argument("--oos", type=int, default=100)
    ap.add_argument("--entries", default="old,new", help="comma list of entries to measure: old,new")
    ap.add_argument("--out", default=None, help="receipt path (default: print only)")
    ap.add_argument("--keep", action="store_true", help="keep generated workspaces")
    ns = ap.parse_args(argv)
    receipt = run(ns.seed, ns.per_family, ns.oos, [x.strip() for x in ns.entries.split(",") if x.strip()], ns.keep)
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if ns.out:
        Path(ns.out).write_text(text, encoding="utf-8")
    summary = {k: {"in_scope_instance_pass_rate": v["in_scope_instance_pass_rate"],
                   "in_scope_families_all_pass": f'{v["in_scope_families_all_pass"]}/{v["in_scope_families_measured"]}',
                   "out_of_scope_fail_closed_rate": v["out_of_scope_fail_closed_rate"]} for k, v in receipt["measurements"].items()}
    live = receipt["tool_liveness"]
    print(json.dumps({"seed": receipt["seed"], "replay": receipt["replay"], "entries": summary,
                      "tools": {"total": live["capabilities_total"], "adapter_missing": len(live["adapter_missing"]),
                                "adapter_import_failed": len(live["adapter_import_failed"]),
                                "external_dependency_missing_here": len(live["external_dependency_missing_here"]),
                                "zero_input_capabilities": live["zero_input_capabilities"]}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
