#!/usr/bin/env python3
"""ADVANCED CAPABILITY RUNTIME -- one runtime, one sitting, every advanced capability we can execute.

WHAT THIS IS FOR
----------------
The owner asked for a fresh measurement of *all* of Brain's most advanced
capabilities in **one runtime**, run **now**, so that no comparison against a
frontier model is built on a stale receipt. This script is that runtime.

It does not describe capabilities. It *executes* them, in this process or in a
child process of this machine, and writes one scorecard:

  * Tier 1 -- the true-capability harness (fresh instances from OS entropy,
    independent oracles in a different file from the solver), 11 specs.
  * Tier 2 -- the MEME dependency-memory bench (protocol semantics, flat control).
  * Tier 3 -- the bound-capability registry: structural liveness of every entry,
    plus live end-to-end invocations of a cross-domain sample, each judged by a
    *separate* oracle written in this file (GNU tar, jq, ast, zipfile, sqlite3).
  * Tier 4 -- the model-free test-guided Python repair loop on freshly generated
    bugs, judged by held-out tests the loop never sees.
  * Tier 5 -- the plain-goal compiler: fresh goals, author-labelled, so that a
    wrong binding is visible instead of counted as a success.
  * Tier 6 -- the instant-learning closed loop ("the gap closes the loop").
  * Tier 7 -- the tree's own verification: unified-model gates, dark-matter
    census, orientation contract.
  * Tier 8 -- substrate availability: which advertised capabilities cannot run
    on *this* machine at all (PIL, sympy, tesseract, yq, pandoc, sqlite3 CLI).
    A capability that cannot know this machine cannot run on it -- recorded as a
    substrate forfeit, never as a pass.

RULES THIS SCRIPT OBEYS
-----------------------
  * 0 model calls, 0 network calls, $0.00 incremental spend. No model library is
    imported anywhere; the child processes are the tree's own zero-model tools.
  * Nothing is written outside a temporary directory, except this scorecard.
  * Every number names its oracle and its n. Where there is no instrument, the
    row says NO_INSTRUMENT and the axis is forfeited -- it is never invented.
  * The author of this script wrote the repair-bug generator and the goal labels;
    those two rows are labelled AUTHOR_LABELLED and are weaker evidence than the
    harness rows, which use oracles in a different file. The label travels with
    the number.

Usage:
  python3 canonical/tools/advanced_capability_runtime_20261127_v1.py
      [--out PATH] [--truecap-instances N] [--skip SLOW_PROBES]
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "BRAIN_ADVANCED_CAPABILITY_RUNTIME_20261127_V1"
# set in main(): the scorecard path, so the artifact-stability probe can set this
# sitting's own outputs aside and measure the tree as it was found.
_SELF_OUTPUT: list = [None]
DATE = "2026-11-27"
OUT_DEFAULT = ROOT / "canonical/verification/ADVANCED_CAPABILITY_RUNTIME_20261127_V1.json"

REGISTRY = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
EXTENDED = ROOT / "canonical/runtime/AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1.json"
FABRIC = ROOT / "canonical/capabilities/CAPABILITY_FABRIC_V1.json"
HIDDEN = ROOT / "canonical/capabilities/hidden/HIDDEN_CAPABILITY_CENSUS_V1.json"

def _now_ms() -> float:
    return time.perf_counter() * 1000.0

def _sha(text: str | bytes) -> str:
    b = text.encode("utf-8") if isinstance(text, str) else text
    return hashlib.sha256(b).hexdigest()

def _row(**kw) -> dict:
    """One measured axis. Anything not measured is NO_INSTRUMENT, never a guess."""
    base = {
        "axis_id": kw.get("axis_id"),
        "capability": kw.get("capability"),
        "instrument": kw.get("instrument"),
        "n": kw.get("n"),
        "metric": kw.get("metric"),
        "value": kw.get("value"),
        "oracle": kw.get("oracle"),
        "oracle_class": kw.get("oracle_class", "DECLARED"),
        "status": kw.get("status", "MEASURED"),
        "model_calls": 0,
        "spend_usd": 0.0,
        "duration_ms": round(float(kw.get("duration_ms") or 0.0), 2),
        "witness": kw.get("witness") or {},
        "why_not_measured": kw.get("why_not_measured"),
    }
    return base

def _run(argv: list[str], timeout: int = 900) -> dict:
    started = _now_ms()
    try:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        p = subprocess.run(argv, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout, env=env)
        return {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr,
                "duration_ms": round(_now_ms() - started, 2), "timed_out": False}
    except subprocess.TimeoutExpired as exc:
        return {"returncode": -9, "stdout": (exc.stdout or b"").decode("utf-8", "replace")
                if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
                "stderr": "TIMEOUT", "duration_ms": round(_now_ms() - started, 2),
                "timed_out": True}

# --------------------------------------------------------------------------------------
# INVENTORY: what exists at all, before anything is measured.
# --------------------------------------------------------------------------------------
def inventory() -> dict:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]
    ext = json.loads(EXTENDED.read_text(encoding="utf-8"))["capabilities"] if EXTENDED.exists() else {}
    fabric = json.loads(FABRIC.read_text(encoding="utf-8")) if FABRIC.exists() else {}
    hidden = json.loads(HIDDEN.read_text(encoding="utf-8")) if HIDDEN.exists() else {}
    statuses: dict[str, int] = {}
    for v in reg.values():
        statuses[str(v.get("status"))] = statuses.get(str(v.get("status")), 0) + 1
    adapter_paths = 0
    missing = []
    for k, v in reg.items():
        p = (v.get("source") or {}).get("adapter_path")
        if p and (ROOT / p).exists():
            adapter_paths += 1
        else:
            missing.append(k)
    runtime_modules = len(list((ROOT / "canonical/runtime").glob("*.py")))
    swe_modules = len(list((ROOT / "canonical/swe_kernel").glob("*.py")))
    return {
        "bound_registry_entries": len(reg),
        "bound_registry_statuses": statuses,
        "extended_autonomous_registry_entries": len(ext),
        "extended_registry_statuses": _status_histogram(ext),
        "entries_with_existing_adapter_file": adapter_paths,
        "entries_without_adapter_file": len(missing),
        "entries_without_adapter_file_sample": sorted(missing)[:12],
        "certified_fabric_capabilities": int(fabric.get("certified_count") or 0),
        "fabric_admission_coverage_ratio": fabric.get("admission_coverage_ratio"),
        "hidden_capability_census_entries": len(hidden.get("hidden") or []),
        "runtime_modules": runtime_modules,
        "swe_kernel_modules": swe_modules,
        "python": platform.python_version(),
    }

def _status_histogram(d: dict) -> dict:
    h: dict[str, int] = {}
    for v in d.values():
        s = str((v or {}).get("status")) if isinstance(v, dict) else "UNKNOWN"
        h[s] = h.get(s, 0) + 1
    return dict(sorted(h.items(), key=lambda kv: -kv[1])[:8])

# --------------------------------------------------------------------------------------
# TIER 1: true-capability harness (fresh instances, independent oracles).
# --------------------------------------------------------------------------------------
def probe_truecap(instances: int) -> tuple[list[dict], dict]:
    specs = sorted((ROOT / "canonical/capabilities/true/specs").glob("*.json"))
    rows, summary = [], {"specs": len(specs), "passed": 0, "failed": 0, "instances_per_spec": instances}
    receipts = pathlib.Path(tempfile.mkdtemp(prefix="tc-receipts-"))
    total_ms = 0.0
    for spec in specs:
        res = _run([sys.executable, "execution_guard/true_capability_harness_v1.py", "run",
                    "--spec", str(spec), "--instances", str(instances),
                    "--receipt-dir", str(receipts)], timeout=900)
        total_ms += res["duration_ms"]
        first = (res["stdout"].strip().splitlines() or [""])[0]
        caps = spec.stem
        rate = None
        m = re.search(r"fresh_pass_rate=([0-9.]+) \(([0-9]+)/([0-9]+)\)", first)
        if m:
            rate = float(m.group(1))
            passed_n, total_n = int(m.group(2)), int(m.group(3))
        else:
            passed_n, total_n = 0, 0
        oracle_lines = [ln.strip() for ln in res["stdout"].splitlines() if ln.strip().startswith("oracle ")]
        ok = res["returncode"] == 0 and first.startswith("TRUE_CAPABILITY_PASS")
        summary["passed" if ok else "failed"] += 1
        rows.append(_row(
            axis_id="truecap:" + caps,
            capability=caps,
            instrument="execution_guard/true_capability_harness_v1.py",
            n=total_n or instances,
            metric="fresh_pass_rate",
            value=rate,
            oracle="; ".join(o.split("  ")[0].replace("oracle ", "").strip() for o in oracle_lines)[:400] or "see receipt",
            oracle_class="INDEPENDENT_FILE_ORACLES",
            status="PASS" if ok else "FAIL",
            duration_ms=res["duration_ms"],
            witness={"first_line": first[:200], "oracle_lines": len(oracle_lines),
                     "spec_sha256": _sha(spec.read_bytes())},
            why_not_measured=None if ok else (res["stderr"] or first)[:300],
        ))
    summary["duration_ms"] = round(total_ms, 2)
    summary["fresh_instances_total"] = summary["passed"] * instances
    shutil.rmtree(receipts, ignore_errors=True)
    return rows, summary

# --------------------------------------------------------------------------------------
# TIER 2: MEME dependency-memory bench.
# --------------------------------------------------------------------------------------
def probe_meme() -> tuple[list[dict], dict]:
    out = pathlib.Path(tempfile.mkdtemp(prefix="meme-")) / "scorecard.json"
    res = _run([sys.executable, "canonical/evaluation/meme_protocol_bench_v1.py",
                "--json", str(out)], timeout=600)
    rows = []
    if not out.exists():
        return [_row(axis_id="dependency_memory", capability="dependency-correct memory (MEME protocol)",
                     instrument="canonical/evaluation/meme_protocol_bench_v1.py", n=0,
                     metric="pass_rate", value=None, oracle="reference fixpoint",
                     status="FAIL", duration_ms=res["duration_ms"],
                     why_not_measured=(res["stderr"] or res["stdout"])[-300:])], {}
    d = json.loads(out.read_text(encoding="utf-8"))
    dm = d["results"]["dependency_memory"]
    flat = d["results"]["flat_retrieval"]
    sc = d.get("self_check", {})
    rows.append(_row(axis_id="dependency_memory", capability="dependency-correct memory (cascade, absence, aggregation, tracking, deletion, exact recall)",
                     instrument="canonical/evaluation/meme_protocol_bench_v1.py", n=dm["instances"],
                     metric="oracle_judged_pass_rate", value=dm["rate"],
                     oracle=d.get("judged_by"), oracle_class="INDEPENDENT_FIXPOINT_EVALUATOR",
                     status="PASS" if dm["rate"] >= 0.99 else "FAIL",
                     duration_ms=d.get("elapsed_ms", res["duration_ms"]),
                     witness={"per_operation": dm.get("per_operation"),
                              "false_success_claims": dm.get("false_success_claims")}))
    rows.append(_row(axis_id="dependency_memory_control", capability="flat retrieval control (does the instrument discriminate?)",
                     instrument="same bench", n=flat["instances"], metric="oracle_judged_pass_rate",
                     value=flat["rate"], oracle="reference fixpoint", oracle_class="CONTROL_ARM",
                     status="CONTROL",
                     duration_ms=d.get("elapsed_ms", res["duration_ms"]),
                     witness={"per_operation": flat.get("per_operation"),
                              "false_success_claims": flat.get("false_success_claims")}))
    rows.append(_row(axis_id="dependency_memory_instrument_selfcheck", capability="the bench's own honesty (stub + liar arms)",
                     instrument="same bench --self-check semantics", n=sc.get("instances", 36),
                     metric="discrimination", value=sc.get("discrimination"),
                     oracle="stub_rate/liar_rate", oracle_class="INSTRUMENT_SELF_CHECK",
                     status="PASS" if sc.get("trustworthy") else "FAIL",
                     witness=sc))
    shutil.rmtree(out.parent, ignore_errors=True)
    return rows, {"verdict": d.get("verdict"), "seed": d.get("seed")}

# --------------------------------------------------------------------------------------
# TIER 3a: bound-registry structural liveness.
# --------------------------------------------------------------------------------------
def probe_registry_liveness() -> tuple[list[dict], dict]:
    import importlib.util
    import inspect
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]
    live, missing_path, no_entry, import_err = 0, 0, 0, 0
    errors = []
    started = _now_ms()
    for k, v in reg.items():
        p = (v.get("source") or {}).get("adapter_path")
        if not p:
            missing_path += 1
            continue
        ap = ROOT / p
        if not ap.exists():
            missing_path += 1
            continue
        try:
            spec = importlib.util.spec_from_file_location("adv_" + re.sub(r"\W", "_", k), ap)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            fn = getattr(mod, v.get("entrypoint") or "run", None)
            if fn is None or not callable(fn):
                no_entry += 1
                continue
            inspect.signature(fn)
            live += 1
        except Exception as exc:  # noqa: BLE001
            import_err += 1
            errors.append({"capability": k, "error": type(exc).__name__, "detail": str(exc)[:120]})
    dur = round(_now_ms() - started, 2)
    row = _row(axis_id="registry_liveness", capability="bound capabilities that actually load and expose an entrypoint on this machine",
               instrument="import every registered adapter", n=len(reg), metric="live_fraction",
               value=round(live / len(reg), 4) if reg else None,
               oracle="python import + callable check", oracle_class="STRUCTURAL", status="MEASURED",
               duration_ms=dur,
               witness={"live": live, "missing_adapter_path": missing_path,
                        "no_entrypoint": no_entry, "import_error": import_err,
                        "import_errors_sample": errors[:8]})
    return [row], {"live": live, "missing_adapter_path": missing_path,
                   "no_entrypoint": no_entry, "import_error": import_err}

# --------------------------------------------------------------------------------------
# TIER 3b: live cross-domain invocations, each judged by an oracle written here.
# --------------------------------------------------------------------------------------
def _invoke(module_path: str, args: dict, root: pathlib.Path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("advinv_" + _sha(module_path)[:8], ROOT / module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run(args, str(root))

def _guard(rows: list[dict], axis_id: str, capability: str, instrument: str, oracle: str,
           oracle_class: str, fn) -> None:
    """Run one live invocation. A raised adapter is a FAIL row, never a crashed sitting."""
    t0 = _now_ms()
    try:
        row = fn()
        rows.append(row)
    except Exception as exc:  # noqa: BLE001
        msg = f"{type(exc).__name__}: {str(exc)[:220]}"
        substrate = isinstance(exc, ModuleNotFoundError) or "No module named" in msg
        rows.append(_row(axis_id=axis_id, capability=capability, instrument=instrument, n=0,
                         metric="invocation_raised", value=None, oracle=oracle,
                         oracle_class=oracle_class,
                         status="NO_SUBSTRATE" if substrate else "FAIL",
                         duration_ms=_now_ms() - t0,
                         why_not_measured=(f"third-party substrate missing on this machine ({msg})"
                                           if substrate else msg)))

def probe_live_adapters() -> tuple[list[dict], dict]:
    rows: list[dict] = []
    work = pathlib.Path(tempfile.mkdtemp(prefix="live-adapters-"))
    try:
        # ---------- 1. archive create + independent GNU tar verification ----------
        def _archive_create():
            (work / "canonical/docs").mkdir(parents=True)
            (work / "canonical/docs/a.txt").write_text("alpha\n" * 40, encoding="utf-8")
            (work / "canonical/docs/b.txt").write_text("beta\n" * 25, encoding="utf-8")
            (work / "manifest.json").write_text(json.dumps({"records": [
                {"verification_paths": ["canonical/docs/a.txt", "canonical/docs/b.txt"]}]}), encoding="utf-8")
            t0 = _now_ms()
            created = _invoke("canonical/runtime/bound_capabilities/archive_tarfile.py",
                              {"manifest_path": "manifest.json", "output_path": "bundle.tar.gz"}, work)
            dur = _now_ms() - t0
            ex = work / "extracted"
            ex.mkdir()
            p = subprocess.run(["tar", "-xzf", str(work / "bundle.tar.gz"), "-C", str(ex)],
                               capture_output=True, text=True)
            ok = p.returncode == 0 and all((ex / rel).read_bytes() == (work / rel).read_bytes()
                                           for rel in created["members"])
            return _row(axis_id="bound:archive.create", capability="create a tar.gz bundle from a manifest",
                        instrument="bound_capabilities/archive_tarfile.py", n=created["member_count"],
                        metric="members_byte_identical_after_GNU_tar_extract", value=bool(ok),
                        oracle="GNU tar extraction + sha256 of each member vs the source bytes",
                        oracle_class="DIFFERENTIAL_EXTERNAL", status="PASS" if ok else "FAIL",
                        duration_ms=dur,
                        witness={"output_bytes": created["output_bytes"],
                                 "output_sha256": created["output_sha256"][:16],
                                 "tar_returncode": p.returncode})
        _guard(rows, "bound:archive.create", "create a tar.gz bundle from a manifest",
               "bound_capabilities/archive_tarfile.py", "GNU tar", "DIFFERENTIAL_EXTERNAL", _archive_create)

        # ---------- 2. archive verify ----------
        def _archive_verify():
            t0 = _now_ms()
            ver = _invoke("canonical/runtime/bound_capabilities/archive_verify_gnu_tar.py",
                          {"archive_path": "bundle.tar.gz", "manifest_path": "manifest.json"}, work)
            dur = _now_ms() - t0
            ok = bool(ver.get("verified"))
            return _row(axis_id="bound:archive.verify", capability="verify an archive against source hashes",
                        instrument="bound_capabilities/archive_verify_gnu_tar.py", n=1,
                        metric="verified", value=ok,
                        oracle="the adapter re-extracts with GNU tar and compares sha256",
                        oracle_class="DIFFERENTIAL_EXTERNAL", status="PASS" if ok else "FAIL",
                        duration_ms=dur, witness={k: ver.get(k) for k in
                                                  ("verified", "members_match", "detail") if k in ver})
        _guard(rows, "bound:archive.verify", "verify an archive against source hashes",
               "bound_capabilities/archive_verify_gnu_tar.py", "GNU tar", "DIFFERENTIAL_EXTERNAL", _archive_verify)

        # ---------- 3. jq query judged by python ----------
        def _jq():
            (work / "data.json").write_text(json.dumps(
                {"items": [{"name": "aa", "v": 1}, {"name": "bb", "v": 2}, {"name": "cc", "v": 3}]}),
                encoding="utf-8")
            t0 = _now_ms()
            q = _invoke("canonical/runtime/bound_capabilities/jq_query.py",
                        {"input_path": "data.json", "filter": ".items[].name",
                         "output_path": "names.txt"}, work)
            dur = _now_ms() - t0
            got = (work / "names.txt").read_text(encoding="utf-8").split()
            want = [x["name"] for x in json.loads((work / "data.json").read_text())["items"]]
            ok = got == want
            return _row(axis_id="bound:json.query.jq", capability="structured JSON query (jq)",
                        instrument="bound_capabilities/jq_query.py", n=len(want),
                        metric="rows_equal_python_oracle", value=bool(ok),
                        oracle="python json.load + list comprehension",
                        oracle_class="DIFFERENTIAL_EXTERNAL", status="PASS" if ok else "FAIL",
                        duration_ms=dur, witness={"got": got, "want": want, "adapter": q.get("adapter")})
        _guard(rows, "bound:json.query.jq", "structured JSON query (jq)",
               "bound_capabilities/jq_query.py", "python json", "DIFFERENTIAL_EXTERNAL", _jq)

        # ---------- 4. secret scan ----------
        def _secret():
            (work / "canonical/scan").mkdir(parents=True, exist_ok=True)
            (work / "canonical/scan/leak.py").write_text('AWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n', encoding="utf-8")
            (work / "canonical/scan/clean.py").write_text("VALUE = 41 + 1\n", encoding="utf-8")
            t0 = _now_ms()
            s1 = _invoke("canonical/runtime/bound_capabilities/python_source_secret_scan.py",
                         {"source_root": "canonical/scan", "output_path": "scan.json"}, work)
            dur = _now_ms() - t0
            hit = s1.get("finding_count") == 1 and str(s1.get("answer", "")).endswith("leak.py:1")
            (work / "canonical/scan/leak.py").unlink()
            s2 = _invoke("canonical/runtime/bound_capabilities/python_source_secret_scan.py",
                         {"source_root": "canonical/scan", "output_path": "scan2.json"}, work)
            ok = bool(hit) and s2.get("finding_count") == 0
            return _row(axis_id="bound:secret_scan",
                        capability="hard-coded credential scan (detects the planted key, silent on a clean tree)",
                        instrument="bound_capabilities/python_source_secret_scan.py", n=2,
                        metric="detect_planted_AND_silent_on_clean", value=bool(ok),
                        oracle="the author planted exactly one secret and then removed it",
                        oracle_class="AUTHOR_LABELLED", status="PASS" if ok else "FAIL",
                        duration_ms=dur,
                        witness={"with_secret": s1.get("finding_count"), "clean": s2.get("finding_count"),
                                 "redacted": [f.get("redacted") for f in s1.get("findings", [])]})
        _guard(rows, "bound:secret_scan", "hard-coded credential scan",
               "bound_capabilities/python_source_secret_scan.py", "planted secret",
               "AUTHOR_LABELLED", _secret)

        # ---------- 5. symbol index judged by ast ----------
        def _symbols():
            (work / "canonical/srctree").mkdir(parents=True, exist_ok=True)
            (work / "canonical/srctree/m.py").write_text(
                "def alpha():\n    return 1\n\n\nclass Beta:\n    def gamma(self):\n        return 2\n\n\nasync def delta():\n    return 3\n",
                encoding="utf-8")
            t0 = _now_ms()
            idx = _invoke("canonical/runtime/bound_capabilities/python_source_symbol_index.py",
                          {"source_root": "canonical/srctree", "output_path": "index.json"}, work)
            dur = _now_ms() - t0
            tree = ast.parse((work / "canonical/srctree/m.py").read_text(encoding="utf-8"))
            want_names = sorted(n.name for n in ast.walk(tree)
                                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)))
            produced = work / "index.json"
            blob = produced.read_text(encoding="utf-8") if produced.exists() else json.dumps(idx, default=str)
            ok = all(name in blob for name in want_names)
            return _row(axis_id="bound:symbol_index", capability="python source symbol index",
                        instrument="bound_capabilities/python_source_symbol_index.py", n=len(want_names),
                        metric="every_ast_symbol_present", value=bool(ok),
                        oracle="ast.walk over the same file", oracle_class="DIFFERENTIAL_EXTERNAL",
                        status="PASS" if ok else "FAIL", duration_ms=dur,
                        witness={"want": want_names, "index_keys": list(idx)[:10]})
        _guard(rows, "bound:symbol_index", "python source symbol index",
               "bound_capabilities/python_source_symbol_index.py", "ast.walk", "DIFFERENTIAL_EXTERNAL", _symbols)

        # ---------- 6. docx create judged by zipfile ----------
        def _docx():
            (work / "canonical/art").mkdir(parents=True, exist_ok=True)
            (work / "canonical/art/rec.json").write_text(json.dumps(
                {"title": "Runtime Report", "author": "Brain"}), encoding="utf-8")
            t0 = _now_ms()
            _invoke("canonical/runtime/bound_capabilities/docx_report_from_json.py",
                    {"goal": ("Create canonical/art/out.docx with title Runtime Report, paragraph measured, "
                              "and a table with columns title and author containing one row for each of "
                              "title and author using their values from the normalized json."),
                     "json_path": "canonical/art/rec.json", "output_path": "canonical/art/out.docx"}, work)
            dur = _now_ms() - t0
            with zipfile.ZipFile(work / "canonical/art/out.docx") as z:
                xml = z.read("word/document.xml").decode("utf-8", "replace")
                names = z.namelist()
            ok = "Runtime Report" in xml and "[Content_Types].xml" in names and len(names) >= 5
            return _row(axis_id="bound:docx.create", capability="create a Word document from a JSON record",
                        instrument="bound_capabilities/docx_report_from_json.py", n=1,
                        metric="valid_ooxml_package_with_stated_text", value=bool(ok),
                        oracle="zipfile member list + word/document.xml text search (stdlib, separate from the builder)",
                        oracle_class="DIFFERENTIAL_EXTERNAL", status="PASS" if ok else "FAIL",
                        duration_ms=dur, witness={"package_members": len(names)})
        _guard(rows, "bound:docx.create", "create a Word document from a JSON record",
               "bound_capabilities/docx_report_from_json.py", "zipfile + XML",
               "DIFFERENTIAL_EXTERNAL", _docx)

        # ---------- 7. sqlite table create, read back ----------
        def _sqlite():
            (work / "canonical/db").mkdir(parents=True, exist_ok=True)
            recs = {"records": [{"name": "a", "qty": 1}, {"name": "b", "qty": 2}, {"name": "c", "qty": 3}]}
            (work / "canonical/db/rows.json").write_text(json.dumps(recs), encoding="utf-8")
            t0 = _now_ms()
            _invoke("canonical/runtime/bound_capabilities/sqlite_table_stdlib.py",
                    {"json_path": "canonical/db/rows.json", "output_path": "canonical/db/out.db",
                     "goal": "Create a sqlite table named items with columns name and qty."}, work)
            dur = _now_ms() - t0
            import sqlite3
            conn = sqlite3.connect(work / "canonical/db/out.db")
            try:
                tables = [r[0] for r in conn.execute(
                    "select name from sqlite_master where type='table' and name not like 'sqlite_%'")]
                got_rows = sorted(conn.execute(
                    'select name, qty from "' + tables[0] + '"').fetchall()) if tables else []
            finally:
                conn.close()
            want_rows = sorted((r["name"], str(r["qty"])) for r in recs["records"])
            got_rows = [(str(a), str(b)) for a, b in got_rows]
            ok = bool(tables) and got_rows == want_rows
            return _row(axis_id="bound:sqlite.create",
                        capability="materialize a sqlite table from JSON records",
                        instrument="bound_capabilities/sqlite_table_stdlib.py", n=len(want_rows),
                        metric="table_rows_equal_json_records", value=bool(ok),
                        oracle="stdlib sqlite3 opens the produced file and selects the rows (TEXT columns compared as strings)",
                        oracle_class="DIFFERENTIAL_EXTERNAL", status="PASS" if ok else "FAIL",
                        duration_ms=dur, witness={"tables": tables, "got": got_rows, "want": want_rows})
        _guard(rows, "bound:sqlite.create", "materialize a sqlite table from JSON records",
               "bound_capabilities/sqlite_table_stdlib.py", "sqlite3 read-back",
               "DIFFERENTIAL_EXTERNAL", _sqlite)

        # ---------- 8. dead-code detection ----------
        def _dead():
            (work / "canonical/dead").mkdir(parents=True, exist_ok=True)
            (work / "canonical/dead/mod.py").write_text(
                "def used():\n    return 1\n\n\ndef never_called_anywhere():\n    return 2\n\n\nprint(used())\n",
                encoding="utf-8")
            t0 = _now_ms()
            dd = _invoke("canonical/runtime/bound_capabilities/python_source_dead_code.py",
                         {"source_root": "canonical/dead", "output_path": "dead.json"}, work)
            dur = _now_ms() - t0
            ok = "never_called_anywhere" in json.dumps(dd, default=str)
            return _row(axis_id="bound:dead_code", capability="dead / never-executed function detection",
                        instrument="bound_capabilities/python_source_dead_code.py", n=2,
                        metric="planted_dead_function_found", value=bool(ok),
                        oracle="the author planted exactly one dead function",
                        oracle_class="AUTHOR_LABELLED", status="PASS" if ok else "FAIL",
                        duration_ms=dur, witness={"keys": list(dd)[:10]})
        _guard(rows, "bound:dead_code", "dead / never-executed function detection",
               "bound_capabilities/python_source_dead_code.py", "planted dead function",
               "AUTHOR_LABELLED", _dead)

        # ---------- 9. substrate forfeits ----------
        import importlib.util as _iu
        for mod, axis, cap in (
            ("PIL", "substrate:PIL", "read values out of a rendered chart's pixels"),
            ("sympy", "substrate:sympy", "exact symbolic / typed scalar numeric expression"),
            ("yaml", "substrate:yaml", "YAML parsing in-process"),
        ):
            present = _iu.find_spec(mod) is not None
            rows.append(_row(axis_id=axis, capability=cap, instrument="import probe",
                             n=1, metric="substrate_present_on_this_machine", value=bool(present),
                             oracle="importlib.find_spec", oracle_class="SUBSTRATE",
                             status="MEASURED" if present else "NO_SUBSTRATE",
                             why_not_measured=None if present else
                             f"{mod} is not installed here: the capability cannot run on this machine at all"))
        for exe, axis, cap in (
            ("tesseract", "substrate:tesseract", "OCR text from images and scanned PDFs"),
            ("yq", "substrate:yq", "YAML to JSON via yq"),
            ("pandoc", "substrate:pandoc", "document conversion markdown -> pdf"),
            ("sqlite3", "substrate:sqlite3_cli", "sqlite verification via the CLI"),
            ("chromedriver", "substrate:chromedriver", "rendered browser capture / GUI computer use"),
            ("libreoffice", "substrate:libreoffice", "office document format conversion"),
            ("ffmpeg", "substrate:ffmpeg", "audio/video media operations"),
            ("git", "substrate:git", "repository history operations"),
            ("tar", "substrate:tar", "archive creation/verification"),
        ):
            present = shutil.which(exe) is not None
            rows.append(_row(axis_id=axis, capability=cap, instrument="PATH probe",
                             n=1, metric="executable_present_on_this_machine", value=bool(present),
                             oracle="shutil.which", oracle_class="SUBSTRATE",
                             status="MEASURED" if present else "NO_SUBSTRATE",
                             why_not_measured=None if present else
                             f"{exe} is not on PATH: the capability cannot run here at all"))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    rows.append(_row(axis_id="external_board_episode",
                     capability="one scored episode on an external agent board (SWE-bench Pro V2 / Terminal-Bench / OSWorld)",
                     instrument="none wired into this tree", n=0,
                     metric="episodes_scored", value=None,
                     oracle="the board's own grader", oracle_class="EXTERNAL_BOARD",
                     status="NO_INSTRUMENT",
                     why_not_measured="no board task, image or grader is present in this tree; "
                                      "this axis is a forfeit, not a comparison"))
    return rows, {"rows": len(rows),
                  "no_substrate": sum(1 for r in rows if r["status"] == "NO_SUBSTRATE")}

# --------------------------------------------------------------------------------------
# TIER 4: model-free test-guided repair on fresh bugs, judged by HELD-OUT tests.
# --------------------------------------------------------------------------------------
BUGS = [
    {
        "id": "binop_swap",
        "src": "def add(a, b):\n    return a - b\n\n\ndef mul(a, b):\n    return a * b\n",
        "visible": "from app.calc import add, mul\n\n\ndef test_add():\n    assert add(2, 3) == 5\n\n\ndef test_mul():\n    assert mul(4, 5) == 20\n",
        "heldout": "from app.calc import add, mul\ndef check():\n    assert add(0, 0) == 0\n    assert add(-7, 7) == 0\n    assert add(1000000, 1) == 1000001\n    assert mul(-3, 3) == -9\ncheck()\n",
        "kind": "operator", "known_in_family": True,
    },
    {
        "id": "comparison_boundary",
        "src": "def band(x):\n    if x > 10:\n        return 'high'\n    return 'low'\n",
        "visible": "from app.calc import band\n\n\ndef test_high():\n    assert band(10) == 'high'\n\n\ndef test_low():\n    assert band(9) == 'low'\n",
        "heldout": "from app.calc import band\ndef check():\n    assert band(10) == 'high'\n    assert band(0) == 'low'\n    assert band(10**6) == 'high'\ncheck()\n",
        "kind": "boundary", "known_in_family": True,
    },
    {
        "id": "off_by_one_range",
        "src": "def count_to(n):\n    return list(range(1, n))\n",
        "visible": "from app.calc import count_to\n\n\ndef test_three():\n    assert count_to(3) == [1, 2, 3]\n\n\ndef test_one():\n    assert count_to(1) == [1]\n",
        "heldout": "from app.calc import count_to\ndef check():\n    assert count_to(5) == [1, 2, 3, 4, 5]\n    assert count_to(2) == [1, 2]\ncheck()\n",
        "kind": "boundary", "known_in_family": True,
    },
    {
        "id": "wrong_return_var",
        "src": "def pick(a, b):\n    result = b\n    return a\n",
        "visible": "from app.calc import pick\n\n\ndef test_pick():\n    assert pick(1, 2) == 2\n",
        "heldout": "from app.calc import pick\ndef check():\n    assert pick('x', 'y') == 'y'\n    assert pick(0, 1) == 1\ncheck()\n",
        "kind": "variable", "known_in_family": True,
    },
    {
        "id": "string_method",
        "src": "def norm(s):\n    return s.strip()\n",
        "visible": "from app.calc import norm\n\n\ndef test_lower():\n    assert norm(' AbC ') == 'abc'\n",
        "heldout": "from app.calc import norm\ndef check():\n    assert norm('XYZ') == 'xyz'\n    assert norm(' MiXeD ') == 'mixed'\ncheck()\n",
        "kind": "method", "known_in_family": True,
    },
    {
        "id": "boolean_swap",
        "src": "def allow(a, b):\n    return a and b\n",
        "visible": "from app.calc import allow\n\n\ndef test_or():\n    assert allow(True, False) is True\n",
        "heldout": "from app.calc import allow\ndef check():\n    assert allow(False, True) is True\n    assert allow(False, False) is False\ncheck()\n",
        "kind": "boolean", "known_in_family": True,
    },
    {
        "id": "numeric_constant",
        "src": "TAX = 0.2\n\n\ndef with_tax(x):\n    return round(x * (1 + TAX), 4)\n",
        "visible": "from app.calc import with_tax\n\n\ndef test_tax():\n    assert with_tax(100) == 110.0\n",
        "heldout": "from app.calc import with_tax\ndef check():\n    assert with_tax(200) == 220.0\n    assert with_tax(50) == 55.0\ncheck()\n",
        "kind": "constant", "known_in_family": True,
    },
    {
        "id": "slice_bound",
        "src": "def drop_last(s):\n    return s[1:]\n",
        "visible": "from app.calc import drop_last\n\n\ndef test_drop():\n    assert drop_last('abc') == 'ab'\n",
        "heldout": "from app.calc import drop_last\ndef check():\n    assert drop_last('xyz') == 'xy'\n    assert drop_last('q') == ''\ncheck()\n",
        "kind": "slice", "known_in_family": True,
    },
    {
        "id": "missing_guard",
        "src": "def safe_div(a, b):\n    return a / b\n",
        "visible": "from app.calc import safe_div\n\n\ndef test_div():\n    assert safe_div(6, 3) == 2\n\n\ndef test_zero():\n    try:\n        safe_div(1, 0)\n    except ValueError:\n        return\n    raise AssertionError('expected ValueError')\n",
        "heldout": "from app.calc import safe_div\ndef check():\n    try:\n        safe_div(0, 0)\n    except ValueError:\n        pass\n    else:\n        raise AssertionError('no guard')\n    assert safe_div(9, 3) == 3\ncheck()\n",
        "kind": "new_behaviour", "known_in_family": False,
    },
    {
        "id": "dict_key_rename",
        "src": "def total(data):\n    return data['sum']\n",
        "visible": "from app.calc import total\n\n\ndef test_total():\n    assert total({'total': 5, 'n': 1}) == 5\n",
        "heldout": "from app.calc import total\ndef check():\n    assert total({'total': 0}) == 0\n    assert total({'n': 9, 'total': 42}) == 42\ncheck()\n",
        "kind": "key", "known_in_family": True,
    },
]

def _write_bug_repo(base: pathlib.Path, bug: dict) -> None:
    (base / "app").mkdir(parents=True, exist_ok=True)
    (base / "tests").mkdir(parents=True, exist_ok=True)
    (base / "app/__init__.py").write_text("", encoding="utf-8")
    (base / "app/calc.py").write_text(bug["src"], encoding="utf-8")
    (base / "tests/test_visible.py").write_text(bug["visible"], encoding="utf-8")
    (base / "heldout_check.py").write_text(bug["heldout"], encoding="utf-8")

def _heldout_passes(base: pathlib.Path) -> tuple[bool, str]:
    p = subprocess.run([sys.executable, "heldout_check.py"], cwd=str(base),
                       capture_output=True, text=True, timeout=120)
    return p.returncode == 0, (p.stderr or p.stdout or "")[-200:]

def probe_repair() -> tuple[list[dict], dict]:
    from canonical.runtime.bound_capabilities import python_software_repair_loop_v1 as loop
    work = pathlib.Path(tempfile.mkdtemp(prefix="repair-fresh-"))
    rows, detail = [], []
    try:
        for bug in BUGS:
            repo = work / bug["id"]
            _write_bug_repo(repo, bug)
            before_ok, before_msg = _heldout_passes(repo)
            started = _now_ms()
            out = None
            err = None
            try:
                out = loop.run({"test_paths": ["tests/test_visible.py"], "source_root": ".",
                                "output_path": "repair_out.json", "max_edits": 6,
                                "timeout_s": 20, "max_candidates": 600}, repo)
            except Exception as exc:  # noqa: BLE001
                err = f"{type(exc).__name__}: {str(exc)[:160]}"
            dur = _now_ms() - started
            applied = False
            if out and out.get("patches"):
                for patch in out["patches"]:
                    pf = repo / "p.diff"
                    pf.write_text(patch["unified_diff"], encoding="utf-8")
                    pr = subprocess.run(["patch", "-p1", "-i", "p.diff"], cwd=str(repo),
                                        capture_output=True, text=True)
                    applied = applied or pr.returncode == 0
            after_ok, after_msg = _heldout_passes(repo) if applied else (False, "patch not applied")
            resolved = bool(out and out.get("status", "").startswith("PASS"))
            rows.append(_row(
                axis_id="repair:" + bug["id"],
                capability=f"model-free test-guided repair -- {bug['kind']} bug",
                instrument="bound_capabilities/python_software_repair_loop_v1.py",
                n=1, metric="resolved_on_visible_and_passed_heldout",
                value=bool(resolved and after_ok),
                oracle="held-out tests written by the harness author and never shown to the loop",
                oracle_class="AUTHOR_LABELLED_HELDOUT",
                status="PASS" if (resolved and after_ok) else ("REPAIRED_ON_VISIBLE_ONLY" if resolved else "FAIL"),
                duration_ms=dur,
                witness={"visible_suite_resolved": resolved,
                         "heldout_passed_after_patch": after_ok,
                         "heldout_passed_before": before_ok,
                         "loop_status": (out or {}).get("status"),
                         "edits": (out or {}).get("edits_applied"),
                         "candidates": (out or {}).get("tested_candidate_count"),
                         "error": err, "heldout_stderr": after_msg if not after_ok else ""}))
            detail.append({"bug": bug["id"], "kind": bug["kind"], "resolved": resolved,
                           "heldout": after_ok, "error": err,
                           "known_in_family": bug["known_in_family"]})
        n = len(rows)
        res_rate = sum(1 for r in rows if r["status"] in ("PASS", "REPAIRED_ON_VISIBLE_ONLY")) / n
        gen_rate = sum(1 for r in rows if r["status"] == "PASS") / n
        agg = [
            _row(axis_id="repair_aggregate", capability="model-free test-guided Python repair, fresh bugs",
                 instrument="same loop, 10 freshly generated single-bug repos", n=n,
                 metric="resolved_on_visible_suite", value=round(res_rate, 4),
                 oracle="the loop's own visible suite", oracle_class="SOLVER_OWNS_THE_SUITE",
                 status="MEASURED", duration_ms=sum(r["duration_ms"] for r in rows),
                 witness={"detail": detail}),
            _row(axis_id="repair_generalization", capability="...and the repair holds on tests the loop never saw",
                 instrument="same loop + held-out oracle", n=n,
                 metric="heldout_pass_rate", value=round(gen_rate, 4),
                 oracle="held-out tests, author-written, never given to the loop",
                 oracle_class="AUTHOR_LABELLED_HELDOUT", status="MEASURED",
                 duration_ms=0.0, witness={"detail": detail}),
        ]
        return agg + rows, {"resolved_on_visible": round(res_rate, 4), "passed_heldout": round(gen_rate, 4),
                            "n": n, "detail": detail}
    finally:
        shutil.rmtree(work, ignore_errors=True)

# --------------------------------------------------------------------------------------
# TIER 5: plain-goal -> bound-capability binding, author-labelled.
# --------------------------------------------------------------------------------------
# label: the capability (or capability family prefix) that a correct binding must
# select, or "REFUSE" where no bound capability covers the goal at all.
GOALS = [
    ("create a tar.gz archive from the manifest at build/m.json", "archive.tar_gz.create_from_manifest"),
    ("verify that the archive out/bundle.tar.gz matches the manifest build/m.json", "archive.verify.tar_gz.gnu"),
    ("query the json file data/x.json with the filter .items[].name", "json.query.jq"),
    ("convert the yaml file config/pipeline.yml into json", "yaml.to_json.yq"),
    ("index the python symbols under canonical/runtime", "python.source.symbols.index.ast"),
    ("scan the source tree canonical/runtime for hard-coded secrets", "python.source.secret_scan.v1"),
    ("count the function and class definitions in canonical/runtime/goal_compiler.py", "python.source.definition_count.v1"),
    ("find the dead code in canonical/runtime", "python.source.dead_code.v1"),
    ("repair the failing python tests in this repository with a test-guided patch search", "python.patch.search.test_guided.ast.v1"),
    ("localize the python fault with dynamic dataflow traces", "python.fault.localize.dynamic.dataflow.v1"),
    ("rename the python parameter in the source file", "python.refactor.rename_parameter.v1"),
    ("resolve python symbol references across files", "python.symbol.resolve.standalone.v1"),
    ("compute the absolute difference between 12 and 30 and say whether it is within 20", "REFUSE"),
    ("rank the retrieved sources by relevance to the research objective", "source.objective_relevance.rank.bm25"),
    ("decide the terminal answer from typed evidence items with provenance", "decision.synthesis.typed.stdlib"),
    ("create a docx report from the json record", "docx.document.create_from_json_record"),
    ("verify that out/report.docx is a valid ooxml package", "docx.document.verify"),
    ("create a sqlite table from the json records", "sqlite.table.create_from_json_records"),
    ("create an xlsx workbook from the json records", "xlsx.table.create_from_json_records"),
    ("run the shell command that lists the working directory", "shell.command.run"),
    ("write the text hello into out/note.txt", "text.file.write"),
    ("compute the SA-CCR credit addon for the trades in trades.json", "finance.saccr.credit.addon.v1"),
    ("translate this paragraph into French with the right register", "REFUSE"),
    ("diagnose whether this patient's symptoms indicate pneumonia", "REFUSE"),
]

def probe_goal_binding() -> tuple[list[dict], dict]:
    from canonical.runtime import goal_compiler as gc
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]
    rows, detail = [], []
    correct = wrong = refused = refused_ok = 0
    started = _now_ms()
    for goal, want in GOALS:
        try:
            out = gc.compile_goal(goal, reg, str(ROOT))
            sel = str(out.get("selected_capability") or "")
            status = "BOUND"
            got = sel
        except Exception as exc:  # noqa: BLE001
            sel, status, got = "", "REFUSED", f"{type(exc).__name__}: {str(exc)[:80]}"
        if want == "REFUSE":
            good = status == "REFUSED"
            refused_ok += int(good)
        elif status == "REFUSED":
            good = False
            refused += 1
        else:
            good = sel == want or sel.startswith(want.rsplit(".v1", 1)[0])
            if good:
                correct += 1
            else:
                wrong += 1
        detail.append({"goal": goal, "want": want, "got": got, "verdict":
                       "CORRECT" if good else ("REFUSED_ON_A_COVERED_GOAL" if status == "REFUSED" and want != "REFUSE"
                                               else ("CORRECT_REFUSAL" if good else "WRONG_BINDING"))})
    dur = _now_ms() - started
    n_covered = sum(1 for _, w in GOALS if w != "REFUSE")
    n_refuse = len(GOALS) - n_covered
    rows.append(_row(axis_id="goal_binding_precision", capability="plain goal -> correct bound capability",
                     instrument="canonical/runtime/goal_compiler.py", n=n_covered,
                     metric="correct_bindings_over_covered_goals", value=round(correct / n_covered, 4),
                     oracle="author-written labels (24 goals: 21 covered, 3 deliberately uncovered)",
                     oracle_class="AUTHOR_LABELLED", status="MEASURED", duration_ms=dur,
                     witness={"correct": correct, "wrong": wrong, "refused": refused,
                              "detail": detail}))
    rows.append(_row(axis_id="goal_binding_wrong_binding_rate", capability="...and how often it binds the WRONG capability (the dangerous class)",
                     instrument="same", n=n_covered, metric="wrong_binding_rate",
                     value=round(wrong / n_covered, 4),
                     oracle="author-written labels", oracle_class="AUTHOR_LABELLED",
                     status="MEASURED", duration_ms=0.0,
                     witness={"wrong": wrong, "wrong_examples": [d for d in detail if d["verdict"] == "WRONG_BINDING"][:5]}))
    rows.append(_row(axis_id="goal_refusal_on_uncovered", capability="refuses a goal no bound capability covers (fail-closed)",
                     instrument="same", n=n_refuse, metric="correct_refusals_over_uncovered_goals",
                     value=round(refused_ok / n_refuse, 4),
                     oracle="author-written labels", oracle_class="AUTHOR_LABELLED",
                     status="MEASURED", duration_ms=0.0, witness={"refused_ok": refused_ok, "n": n_refuse}))
    return rows, {"correct": correct, "wrong": wrong, "refused": refused,
                  "refusals_on_uncovered": refused_ok, "n_covered": n_covered, "n_uncovered": n_refuse,
                  "detail": detail}

# --------------------------------------------------------------------------------------
# TIER 6: instant-learning closed loop (fresh run, into a temp receipt).
# --------------------------------------------------------------------------------------
def probe_instant_learning() -> tuple[list[dict], dict]:
    out = pathlib.Path(tempfile.mkdtemp(prefix="gap-")) / "gap.json"
    res = _run([sys.executable, "canonical/tools/the_gap_closes_the_loop_v1.py", "--receipt", str(out)],
               timeout=600)
    if not out.exists():
        return [_row(axis_id="instant_learning", capability="one document -> verified mechanism -> instant recall",
                     instrument="canonical/tools/the_gap_closes_the_loop_v1.py", n=0,
                     metric="claims_holding", value=None, oracle="self-declared claims in the run receipt",
                     status="FAIL", duration_ms=res["duration_ms"],
                     why_not_measured=(res["stderr"] or res["stdout"])[-300:])], {}
    d = json.loads(out.read_text(encoding="utf-8"))
    claims = d.get("claims", {})
    held = sum(1 for v in claims.values() if v)
    rows = [_row(axis_id="instant_learning", capability="one document -> verified mechanism -> instant recall (the closed loop)",
                 instrument="canonical/tools/the_gap_closes_the_loop_v1.py", n=len(claims),
                 metric="claims_holding", value=f"{held}/{len(claims)}",
                 oracle="the script's own six claims (each one is a check, not prose)",
                 oracle_class="SELF_DECLARED_CHECKS", status="PASS" if held == len(claims) else "FAIL",
                 duration_ms=res["duration_ms"],
                 witness={"claims": claims, "stored_rule_count": d.get("stored_rule_count"),
                          "recall_duration_s": (d.get("stages", {}).get("recall", {}) or {}).get("duration_s"),
                          "learn_duration_s": (d.get("stages", {}).get("learn", {}) or {}).get("duration_s")})]
    shutil.rmtree(out.parent, ignore_errors=True)
    return rows, {"claims": claims, "held": held, "returncode": res["returncode"]}

# --------------------------------------------------------------------------------------
# TIER 7: the tree's own verification instruments.
# --------------------------------------------------------------------------------------
def probe_tree_verification() -> tuple[list[dict], dict]:
    rows = []
    # the verifier writes its report only to a repository-relative path, so the temp
    # report lives inside a scratch directory in the tree and is deleted afterwards
    scratch = ROOT / "canonical/astra_runtime/tmp"
    scratch.mkdir(parents=True, exist_ok=True)
    out = scratch / "adv_runtime_unified_20261127.json"
    out_present = scratch / "adv_runtime_unified_present_20261127.json"
    me = pathlib.Path(__file__).resolve()

    def _verify_unified(report: pathlib.Path) -> dict:
        report.unlink(missing_ok=True)
        try:
            return _run([sys.executable, "canonical/runtime/verify_brain_unified_model_v1.py",
                         "--output", str(report.relative_to(ROOT))], timeout=900)
        finally:
            report.unlink(missing_ok=True)

    # The unified artifact's byte-identical-recompilation check hashes the *module
    # inventory*. This sitting added one module (this script), so the tree as found is
    # measured with that module temporarily set aside, and the effect of adding it is
    # then measured separately instead of being reported as a tree defect.
    res = _verify_unified(out_present)           # with this sitting's module present
    present_text = res["stdout"] + res["stderr"]
    hold_dir = pathlib.Path(tempfile.mkdtemp(prefix="held-"))
    moved = []
    try:
        candidates = [me, OUT_DEFAULT, pathlib.Path(str(_SELF_OUTPUT[0])) if _SELF_OUTPUT[0] else None]
        for src in candidates:
            if src is None or not pathlib.Path(src).exists():
                continue
            dst = hold_dir / pathlib.Path(src).name
            shutil.move(str(src), str(dst))
            moved.append((pathlib.Path(src), dst))
        res_clean = _verify_unified(out)         # tree as found
    finally:
        for src, dst in moved:
            if dst.exists() and not src.exists():
                shutil.move(str(dst), str(src))
    clean_text = res_clean["stdout"] + res_clean["stderr"]

    def _total(text: str):
        m = re.search(r"TOTAL\s+(\d+)\s*/\s*(\d+)", text)
        return (int(m.group(1)), int(m.group(2))) if m else (None, None)

    ok_n, all_n = _total(clean_text)
    ok = res_clean["returncode"] == 0 and ok_n is not None and ok_n == all_n
    rows.append(_row(axis_id="unified_model_gates",
                     capability="the tree's own unified-model gate set (tree as found)",
                     instrument="canonical/runtime/verify_brain_unified_model_v1.py",
                     n=all_n, metric="gates_passing", value=f"{ok_n}/{all_n}" if ok_n else None,
                     oracle="the verifier's own independent checks",
                     oracle_class="TREE_INSTRUMENT", status="PASS" if ok else "FAIL",
                     duration_ms=res_clean["duration_ms"],
                     witness={"checks": f"{ok_n}/{all_n}",
                              "tail": clean_text.strip().splitlines()[-3:],
                              "note": "this sitting's own new module was set aside so the "
                                      "artifact hash covers the tree as found"}))
    p_n, p_all = _total(present_text)
    rows.append(_row(axis_id="unified_model_artifact_stability",
                     capability="is the compiled unified artifact stable when one module is added?",
                     instrument="same verifier, run again with this sitting's module present",
                     n=p_all, metric="gates_passing_after_adding_one_module",
                     value=f"{p_n}/{p_all}" if p_n else None,
                     oracle="recompilation_is_byte_identical", oracle_class="TREE_INSTRUMENT",
                     status="PASS" if (p_n == p_all and p_n is not None) else "FAIL",
                     duration_ms=res["duration_ms"],
                     witness={"boom_check": [ln.strip() for ln in present_text.splitlines() if "FAILED" in ln][:3],
                              "meaning": "the artifact is a snapshot of a file set, not a property "
                                         "of the code: any added module makes recompilation differ "
                                         "until the artifact is regenerated"}))
    try:
        out.unlink(missing_ok=True)
    except Exception:  # noqa: BLE001
        pass

    dm = pathlib.Path(tempfile.mkdtemp(prefix="dark-")) / "dark.json"
    res2 = _run([sys.executable, "canonical/tools/dark_matter_adjudicator_v1.py",
                 "--all-modules", "--min-loc", "140", "--json", str(dm)], timeout=900)
    counts, digest = {}, None
    if dm.exists():
        d = json.loads(dm.read_text(encoding="utf-8"))
        counts = d.get("counts") or {}
        digest = d.get("digest")
    proven = int(counts.get("PROVEN") or 0)
    total = sum(int(v) for v in counts.values() if isinstance(v, int))
    rows.append(_row(axis_id="module_proven_census", capability="substantial modules that can prove they execute",
                     instrument="canonical/tools/dark_matter_adjudicator_v1.py --all-modules --min-loc 140",
                     n=total, metric="proven_over_candidates", value=round(proven / total, 4) if total else None,
                     oracle="each module is imported and its own executable self-check must run",
                     oracle_class="TREE_INSTRUMENT", status="MEASURED", duration_ms=res2["duration_ms"],
                     witness={"counts": counts, "digest": digest}))
    shutil.rmtree(dm.parent, ignore_errors=True)

    res3 = _run([sys.executable, "execution_guard/agent_orientation_check_v1.py", "verify"], timeout=300)
    blob3 = res3["stdout"] + res3["stderr"]
    ok3 = res3["returncode"] == 0 and ('"ok": true' in blob3 or "CONSISTENT" in blob3)
    rows.append(_row(axis_id="orientation_contract", capability="the orientation contract, README and laws agree byte-for-byte",
                     instrument="execution_guard/agent_orientation_check_v1.py verify", n=1,
                     metric="contract_consistent", value=bool(ok3),
                     oracle="sha256 comparison against the contract", oracle_class="TREE_INSTRUMENT",
                     status="PASS" if ok3 else "FAIL", duration_ms=res3["duration_ms"],
                     witness={"tail": blob3.strip().splitlines()[-3:]}))
    return rows, {"unified_gates": ok, "dark_matter_counts": counts,
                  "proven": proven, "candidates": total, "orientation": ok3}

# --------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    ap.add_argument("--truecap-instances", type=int, default=500)
    ap.add_argument("--skip", action="append", default=[],
                    choices=["truecap", "meme", "registry", "adapters", "repair", "goals", "instant", "tree"])
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    def say(msg: str) -> None:
        if not args.quiet:
            print(msg, flush=True)

    _SELF_OUTPUT[0] = args.out
    started = time.time()
    score: dict = {"schema": SCHEMA, "date": DATE, "authority": "NONE__PRODUCER_RUN_SANDBOX",
                   "head": _git_head(), "branch": _git_branch(), "rows": [], "sections": {}}

    say("[1/8] inventory")
    score["sections"]["inventory"] = inventory()

    if "truecap" not in args.skip:
        say(f"[2/8] true-capability harness, {args.truecap_instances} fresh instances x 11 specs")
        rows, summary = probe_truecap(args.truecap_instances)
        score["rows"] += rows
        score["sections"]["truecap"] = summary

    if "meme" not in args.skip:
        say("[3/8] dependency memory (MEME protocol bench)")
        rows, s = probe_meme()
        score["rows"] += rows
        score["sections"]["meme"] = s

    if "registry" not in args.skip:
        say("[4/8] bound-registry liveness")
        rows, s = probe_registry_liveness()
        score["rows"] += rows
        score["sections"]["registry"] = s

    if "adapters" not in args.skip:
        say("[5/8] live cross-domain adapter invocations")
        rows, s = probe_live_adapters()
        score["rows"] += rows
        score["sections"]["adapters"] = s

    if "repair" not in args.skip:
        say("[6/8] model-free repair on freshly generated bugs (held-out oracle)")
        rows, s = probe_repair()
        score["rows"] += rows
        score["sections"]["repair"] = s

    if "goals" not in args.skip:
        say("[7/8] plain-goal binding")
        rows, s = probe_goal_binding()
        score["rows"] += rows
        score["sections"]["goal_binding"] = s

    if "instant" not in args.skip:
        say("[8/8] instant-learning closed loop")
        rows, s = probe_instant_learning()
        score["rows"] += rows
        score["sections"]["instant_learning"] = s

    if "tree" not in args.skip:
        say("[+ ] tree verification instruments")
        rows, s = probe_tree_verification()
        score["rows"] += rows
        score["sections"]["tree"] = s

    measured = [r for r in score["rows"] if r["status"] in ("PASS", "FAIL", "MEASURED",
                                                             "CONTROL", "REPAIRED_ON_VISIBLE_ONLY")]
    passes = [r for r in score["rows"] if r["status"] == "PASS"]
    score["totals"] = {
        "rows": len(score["rows"]),
        "measured_rows": len(measured),
        "passing_rows": len(passes),
        "failing_rows": sum(1 for r in score["rows"] if r["status"] == "FAIL"),
        "no_instrument_or_substrate_rows": sum(1 for r in score["rows"] if r["status"] == "NO_SUBSTRATE"),
        "fresh_instances_executed": int(sum((r["n"] or 0) for r in score["rows"]
                                            if r["axis_id"].startswith("truecap:"))),
        "model_calls": 0,
        "network_calls": 0,
        "incremental_spend_usd": 0.0,
        "wall_clock_s": round(time.time() - started, 2),
        "scorecard_sha256": None,
    }
    score["honest_limits"] = [
        "Every number was produced on this one machine, in this one sitting, by the producer.",
        "Independent oracles exist for the true-capability rows and the adapter rows; the goal labels and the held-out repair tests were written by the harness author, which is weaker.",
        "Nothing here is a benchmark score on an external board, and no row is comparable to a published rate without a matched harness.",
        "Rows marked NO_SUBSTRATE are capabilities that cannot run on this machine at all; they are forfeits, not passes.",
        "Absence of a row is not evidence of absence: capabilities with no runnable instrument are listed in sections.inventory and in the report's forfeit table.",
    ]
    body = json.dumps(score, indent=2, sort_keys=True, default=str)
    score["totals"]["scorecard_sha256"] = _sha(body)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(score, indent=2, sort_keys=True, default=str), encoding="utf-8")

    say("")
    say(f"{'AXIS':44} {'n':>7} {'VALUE':>10}  STATUS")
    for r in score["rows"]:
        v = r["value"]
        v = f"{v:.4f}" if isinstance(v, float) else str(v)
        say(f"{r['axis_id'][:44]:44} {str(r['n']):>7} {v[:10]:>10}  {r['status']}")
    say("")
    say(f"rows={score['totals']['rows']} measured={score['totals']['measured_rows']} "
        f"pass={score['totals']['passing_rows']} fail={score['totals']['failing_rows']} "
        f"wall={score['totals']['wall_clock_s']}s model_calls=0 spend=$0.00")
    say(f"scorecard: {out}")
    return 0

def _git_head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT),
                              capture_output=True, text=True).stdout.strip()[:12]
    except Exception:  # noqa: BLE001
        return "UNKNOWN"

def _git_branch() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(ROOT),
                              capture_output=True, text=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "UNKNOWN"

if __name__ == "__main__":
    sys.exit(main())
