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
import re
import shutil
import string
import subprocess
import sys
import tarfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Mapping

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


def _kernel_refuses(entry) -> bool:
    from canonical.runtime.live_brain_route_admission_v1 import kernel_refuses
    return kernel_refuses(entry)


def _failure_reason(result) -> str:
    """Why this result failed, read through the runtime's single accessor."""
    from canonical.runtime.live_brain_route_admission_v1 import failure_reason
    return failure_reason(result)


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
            "executor": "FRONT_LAYER_LOCAL_ADAPTER" if _kernel_refuses(entry) else "PINNED_KERNEL",
        })
    return {
        "capabilities_total": len(rows),
        "executor_kernel_refuses_source_type": sorted(r["capability_id"] for r in rows if r["executor"] == "FRONT_LAYER_LOCAL_ADAPTER"),
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


# Requests NO bound capability can serve.  The only correct answer is pass=False with nothing
# written, so every wording here is a fail-closed test: the machine must not stretch a tool
# it does not have into an answer it cannot give.
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
    "Translate '{s}' into {lang} and write the translation to {o}.",
    "Summarize {src} in three sentences and save the summary to {o}.",
    "Write a Python tutorial for beginners about {thing} and save it to {o}.",
    "Sort the lines of {src} and save the sorted result to {o}.",
    "Count the vowels in {src} and save the count to {o}.",
    "Plan a two week trip to {city} and save the itinerary to {o}.",
    "Explain the ownership rules of {country} and save the explanation to {o}.",
    "Recommend a restaurant in {city} and save the recommendation to {o}.",
    "Predict the closing price of a stock and save the forecast to {o}.",
    "Negotiate the lease of an apartment in {city} and save the agreement to {o}.",
    "Compose a limerick about {thing} and save it to {o}.",
    "Translate the file {src} into {lang} and save the translation to {o}.",
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


def all_generators() -> dict[str, Callable[[random.Random, Path, int], Case]]:
    """Wave-1 families plus the per-capability execution families of live_solver_families_v2/v3/v4/v5/v6/v7, plus the wave-6 cluster-1 coupled repair families."""
    from execution_guard.live_solver_families_v2 import GENERATORS_V2
    from execution_guard.live_solver_families_v3 import GENERATORS_V3
    from execution_guard.live_solver_families_v4 import GENERATORS_V4
    from execution_guard.live_solver_families_v5 import GENERATORS_V5
    from execution_guard.live_solver_families_v6 import GENERATORS_V6
    from execution_guard.live_solver_families_v7 import GENERATORS_V7
    # wave 6, cluster 1: the coupled python-repair families. Same wave number,
    # different work, kept under its own module name so neither is lost.
    from execution_guard.live_solver_families_v6_coupled import GENERATORS_V6_COUPLED
    merged = dict(GENERATORS)
    merged.update(GENERATORS_V2)
    merged.update(GENERATORS_V3)
    merged.update(GENERATORS_V4)
    merged.update(GENERATORS_V5)
    merged.update(GENERATORS_V6)
    merged.update(GENERATORS_V7)
    merged.update(GENERATORS_V6_COUPLED)
    return merged

# Families the compiler advertises but that need binaries / packages this machine lacks.
# Listed so the denominator is honest.  Wave 6 removed three entries by measuring them here:
# CHART_RASTER_READERS (PIL + the F21 pair grammar), KNOWLEDGE_FETCH_ASSESS_ASSERT and
# HTTP_JSON_FETCH__PYPI_AUDIT__WEB_RELEASE (allowlisted https egress to pypi.org/github.com).
NOT_MEASURED_HERE = {
    "MARKDOWN_TO_PDF": "pandoc (apt) not installed here",
    "PDF_TEXT_OCR": "tesseract-ocr (apt) not installed here",
    "QR_BARCODE_GENERATE_DECODE": "qrencode / zbar-tools / zint (apt) not installed here",
    "BROWSER_CAPTURE": "chromedriver (apt) not installed here",
}


# ----------------------------------------------------------------------------- reachability

_FIXTURE_SUFFIX = {
    "archive": ".tar.gz", "tar": ".tar.gz", "zip": ".zip", "json": ".json", "records": ".json", "manifest": ".json", "spec": ".json",
    "config": ".json", "pdf": ".pdf", "markdown": ".md", "md": ".md", "docx": ".docx", "xlsx": ".xlsx", "spreadsheet": ".xlsx",
    "sqlite": ".sqlite", "database": ".sqlite", "yaml": ".yaml", "csv": ".csv", "html": ".html", "image": ".png", "png": ".png",
    "screenshot": ".png", "text": ".txt", "source": ".py", "python": ".py", "test": ".py",
}
_TYPED_EXAMPLE = {
    "jq_filter": 'jq filter ".a"', "expression": 'expression "2*x+1"', "variables": "variables x=2, y=3", "x_value": "x value 3.5",
    "y_value": "y value 2", "x_ticks": "x ticks [0, 1, 2]", "y_ticks": "y ticks [0, 5, 10]", "label": 'label "Curve A"',
    "prompt": 'prompt "which phase is stable"', "pattern": 'pattern "test_*.py"', "test_argv": 'test argv "python3 -m unittest"',
    "objective": 'objective "A is greater than B"', "spec": 'spec "{\\"relation\\": \\"gt\\"}"', "product": 'product "python"',
    "major": "major version 3", "version_field": 'version field "version"', "field_name": 'field name "status"',
    "expected_status": 'expected status "SUPPORTED"', "url_key": 'url key "release_url"', "authoritative": "authoritative true",
    "max_age_s": "max age seconds 600", "url": "https://example.org/release.json", "text": 'text "hello world"',
}


def _output_suffix(entry: Mapping[str, Any], key: str) -> str:
    declared = sorted({str(e)[len("structured.binary.encode."):] for e in (entry.get("provides") or [])
                       if str(e).startswith("structured.binary.encode.") and str(e) != "structured.binary.encode"})
    if len(declared) == 1:
        return "." + declared[0].lower().lstrip(".")
    stem = key[:-5].lower().replace("output_", "")
    if stem in ("result", "report"):
        return ".json"
    if stem != "output" and stem in _FIXTURE_SUFFIX and stem not in ("source", "python", "test"):
        return _FIXTURE_SUFFIX[stem]
    blob = " ".join([str(x) for x in entry.get("provides", [])] + [str(x) for x in entry.get("keywords", [])] + [str(entry.get("adapter_module") or "")]).lower()
    for markers, suffix in ((("xlsx", "spreadsheet", "workbook"), ".xlsx"), (("docx", "word"), ".docx"), (("pdf",), ".pdf"),
                            (("sqlite", "database"), ".sqlite"), (("markdown",), ".md"), (("png", "qr", "barcode", "image", "screenshot"), ".png")):
        if any(m in blob for m in markers):
            return suffix
    return ".json"


def signature_goal(cid: str, entry: Mapping[str, Any], work: Path) -> tuple[str, list[Path]]:
    """One sentence built ONLY from the capability's own registry declaration: its distinctive
    words plus one explicitly stated value per declared input (fixture files for input paths)."""
    from canonical.runtime import goal_compiler as gc
    from canonical.runtime import goal_front_compiler_v1 as front
    words = sorted((gc._tokens(entry.get("provides", [])) | gc._tokens(cid) | gc._tokens(entry.get("keywords", []))) - gc.GENERIC_MATCH_TOKENS)
    parts, fixtures = [], []
    for key in front.input_keys(entry):
        if key == "goal":
            continue
        if key in _TYPED_EXAMPLE:
            parts.append(_TYPED_EXAMPLE[key])
        elif key.endswith("_path") and front._is_output_key(key, entry):
            parts.append("and save it to " + _rel(work / ("out_" + key + _output_suffix(entry, key))))
        elif key.endswith("_path") or key in ("path", "source_root") or key.endswith("_paths"):
            stem = key[:-5].lower() if key.endswith("_path") else key
            if key == "source_root":
                d = work / "src"; d.mkdir(exist_ok=True); fixtures.append(d); parts.append(_rel(d)); continue
            name = {"path": "chart.png", "test_paths": "test_mod.py", "source_paths": "mod.py", "evidence_paths": "evidence.json"}.get(key, stem + _FIXTURE_SUFFIX.get(stem, ".json"))
            f = work / name
            f.write_bytes(b"fixture"); fixtures.append(f); parts.append(_rel(f))
        else:
            parts.append(key + ' "value"')
    return "Use " + " ".join(words) + " on " + " ".join(parts), fixtures


def prose_name_goal(cid: str, entry: Mapping[str, Any]) -> str:
    """One sentence that NAMES a capability that takes no input, in a caller's own words.

    Leak-free by construction: the words are the capability's own name, never its repository
    path, never its receipt document and never the lane's own `.py.auto.vN` suffix.  The
    inventory address is where the capability LIVES; it is not what the capability IS, and a
    sentence that carried it would be measuring the address rather than the capability.

    The name's OWN ORDER is kept, and the version is part of the name: the retrieval path
    separates a capability's version siblings only when the request states the version.  The
    construction is measured, not chosen for tidiness - over the 296 capabilities that take
    no input, the name in its own order reaches 296, the same words re-sorted reach fewer
    (the version lands next to another version and the request stops identifying anything),
    and the name plus the declared keywords reaches fewer still.
    """
    stem = str(cid or "").rsplit("/", 1)[-1]
    stem = re.sub(r"\.py\.auto\.v\d+$", "", stem)
    words = [w for w in stem.split("_") if len(w) > 1]
    if not words:
        return "Run the capability."
    return "Run the " + " ".join(words) + "."


def reachability(work: Path) -> dict[str, Any]:
    """Can the one entry reach every bound capability from a sentence? (compile + bind only, no execution)

    THE PROSE QUESTION IS ASKED FIRST, for every capability, and the internal id is only the
    fallback.  Measured: this metric used to answer the easy question for the 296 capabilities
    that take no input - "can the caller spell the internal id?" - and report them as
    REACHED_BY_EXPLICIT_NAME, which made 296 capabilities look unreachable by a sentence when
    the machine in fact reached 296 of them by prose.  The metric was measuring the id, not the
    capability.  Now a capability that takes no input is asked for BY NAME, the way a caller
    would ask, and only a capability that prose genuinely cannot reach falls back to the id.

    A row therefore states what was PROVED, and the two states are kept apart:
      REACHED_AND_BOUND          - a plain sentence reached it and bound every declared input
      REACHED_BY_EXPLICIT_NAME   - prose could not reach it; naming the internal id did
      ROUTED_ELSEWHERE / NOT_REACHABLE - neither reached it
    """
    from canonical.runtime import goal_compiler as gc
    from canonical.runtime import goal_front_compiler_v1 as front
    from canonical.runtime.live_integrated_brain_v1 import load_verified_registry
    reg = gc._platform_admissible_registry(dict(load_verified_registry()))
    work.mkdir(parents=True, exist_ok=True)
    rows = []
    for cid, entry in sorted(reg.items()):
        if not front.is_plain_goal_routable(entry):
            # A capability that takes no input states no value, so the question is: does a plain
            # sentence NAME it?  The name is the capability's own declaration words - never its
            # path, never its document - which is the same leak-free construction the 66
            # input-taking capabilities are asked with below.
            goal = prose_name_goal(cid, entry)
            try:
                compiled = front.compile_goal(goal, reg, ROOT)
                selected = compiled.get("selected_capability")
                if selected == cid:
                    rows.append({"capability_id": cid, "state": "REACHED_AND_BOUND", "goal": goal,
                                 "detail": ["PROSE_NAME_REACHED"]})
                    continue
                prose_detail = str(selected or compiled.get("compiler_mode"))
            except gc.GoalCompilationFailure as exc:
                prose_detail = exc.code + ":" + str(exc.detail)[:120]
            # F15 remains the fallback: a caller who names the internal id reaches it.
            fallback = f"run {cid}"
            try:
                compiled = front.compile_goal(fallback, reg, ROOT)
            except gc.GoalCompilationFailure as exc:
                rows.append({"capability_id": cid, "state": "NOT_REACHABLE", "goal": goal,
                             "detail": "prose:" + prose_detail + " | by_id:" + exc.code + ":" + str(exc.detail)[:120]})
                continue
            selected = compiled.get("selected_capability")
            if selected == cid:
                rows.append({"capability_id": cid, "state": "REACHED_BY_EXPLICIT_NAME", "goal": goal,
                             "detail": ["F15_EXPLICIT_CAPABILITY_ID_NAMED", "prose:" + prose_detail]})
            else:
                rows.append({"capability_id": cid, "state": "ROUTED_ELSEWHERE", "goal": goal,
                             "detail": "prose:" + prose_detail + " | by_id:" + str(selected or compiled.get("compiler_mode"))})
            continue
        goal, _fixtures = signature_goal(cid, entry, work)
        try:
            compiled = front.compile_goal(goal, reg, ROOT)
            selected = compiled.get("selected_capability")
            if selected == cid:
                rows.append({"capability_id": cid, "state": "REACHED_AND_BOUND", "goal": goal, "detail": sorted(compiled.get("inputs") or {})})
            else:
                rows.append({"capability_id": cid, "state": "ROUTED_ELSEWHERE", "goal": goal, "detail": str(selected or compiled.get("compiler_mode"))})
        except gc.GoalCompilationFailure as exc:
            rows.append({"capability_id": cid, "state": "NOT_REACHABLE", "goal": goal, "detail": exc.code + ":" + str(exc.detail)[:120]})
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["state"]] = counts.get(row["state"], 0) + 1
    return {"capabilities_total": len(rows), "counts": counts, "rows": rows}


def _entry(name: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    if name == "old":
        from canonical.runtime.live_integrated_brain_v1 import run_raw_goal
        return run_raw_goal
    from canonical.runtime.live_brain_route_admission_v1 import solve
    return solve


class _RunPlan:
    """What this run promised to measure, so a partial receipt can name the gap."""

    def __init__(self, entries: list[str], families: list[str]) -> None:
        self.entries = list(entries)
        self.families = list(families)

    def pending(self, measured: Mapping[str, Mapping[str, Any]]) -> list[str]:
        done = set()
        for payload in measured.values():
            done |= set((payload.get("families") or {}).keys())
        return [f for f in self.families if f not in done]


def _write_progress(path: str | Path | None, receipt: Mapping[str, Any]) -> None:
    """Persist the receipt after every family, atomically.

    A forty-minute measurement used to be all-or-nothing: the receipt was written
    once, at the end, so a job that hit its timeout produced NOTHING -- no receipt,
    no summary, no per-family numbers, and therefore no basis for making the next
    run cheaper.  Measured 2026-10-27: the heartbeat was cancelled on 17 of 20 runs
    and every one of them lost its observations too, so the cost of the run was
    paid 17 times and bought 17 blanks.

    Writing after each family costs one small JSON file per family and converts any
    timeout into "here is everything that finished, and here is exactly which
    families never ran".  The receipt says ``run_complete: false`` and the verdict
    function refuses to call an incomplete run ALIVE, so this can add information
    but can never manufacture a pass.
    """
    if path is None:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".partial")
    tmp.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(target)


def _family_plan(only_families: set[str] | None) -> list[str]:
    return [f for f in all_generators() if not only_families or f in only_families]


def _measure_family(job: tuple[str, str, str, str, int, Path]) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    """Measure one family, start to finish.  One body for the serial and parallel paths.

    The seed of a family is derived from the run seed and the family's OWN name, so a
    family's fixtures do not depend on which families ran before it or on how the
    workers were scheduled.  Replaying a seed reproduces the corpus exactly, in any
    order, at any concurrency.
    """
    run_tag, run_seed, entry_name, family, n, work = job
    fn = _entry(entry_name)
    gen = all_generators()[family]
    rng = random.Random(f"project-brain-e2e::{run_seed}::{entry_name}::{family}")
    work.mkdir(parents=True, exist_ok=True)
    ok = 0
    env_blocked = 0
    elapsed = 0
    caps: dict[str, int] = {}
    failures: list[dict[str, Any]] = []
    for i in range(n):
        case, gen_blocker = generated_case(gen, rng, work, i)
        if case is None:
            env_blocked += 1
            if len(failures) < 60:
                failures.append({
                    "family": family, "goal": "(fixture could not be generated)",
                    "why": "ENVIRONMENT_BLOCKED_HERE:" + gen_blocker,
                    "status": "GENERATOR_DEPENDENCY_MISSING", "capability": "-",
                    "admission_rule": None})
            continue
        for a in case.artifacts:
            if a.exists():
                a.unlink()
        t0 = time.perf_counter_ns()
        try:
            # task ids must be unique: the live controller checkpoints per task id and
            # refuses to re-run a finished id (MODEL_INDEPENDENT_CONTROLLER_PLAN_WITHOUT_FINISH)
            result = fn({"task_id": f"{run_tag}_{family}_{i}", "goal": case.goal})
        except Exception as exc:  # noqa: BLE001 - an exception leak is itself a finding
            result = {"pass": None, "status": "EXCEPTION_LEAK", "failure_class": type(exc).__name__ + ":" + str(exc)[:200]}
        elapsed += time.perf_counter_ns() - t0
        cap = str(result.get("compiled_capability_id") or result.get("compiler_mode") or "-")
        caps[cap] = caps.get(cap, 0) + 1
        blocker = environment_blocker(result)
        good, why, blocker = oracle_outcome(case, result, blocker)
        if good:
            ok += 1
        elif blocker:
            env_blocked += 1
            if len(failures) < 60:
                failures.append({"family": family, "goal": case.goal[:220], "why": "ENVIRONMENT_BLOCKED_HERE:" + blocker,
                                 "status": str(result.get("status"))[:120], "capability": cap, "admission_rule": None})
        elif len(failures) < 60:
            failures.append({"family": family, "goal": case.goal[:220], "why": (why + " | " + _failure_reason(result))[:400],
                             "status": str(result.get("status"))[:120], "capability": cap,
                             "admission_rule": ((result.get("route_admission") or {}).get("rule") if isinstance(result.get("route_admission"), dict) else None)})
    row = {"instances": n, "oracle_pass": ok, "environment_blocked_here": env_blocked,
           "pass_rate": round(ok / n, 4) if n else None, "mean_ms": round(elapsed / n / 1e6, 2) if n else None,
           "routes_taken": caps,
           "expected": "all PASS with exact artifact" if family != "OUT_OF_SCOPE_MUST_FAIL_CLOSED" else "all FAIL closed, no artifact"}
    return family, row, failures


def run(seed: int | None, per_family: int, oos_count: int, entries: list[str], keep: bool,
        only_families: set[str] | None = None,
        progress_path: str | Path | None = None,
        workers: int = 1) -> dict[str, Any]:
    replay = seed is not None
    if seed is None:
        seed = int.from_bytes(os.urandom(8), "big")
    run_tag = "E2E_" + hashlib.sha256(f"{seed}:{os.urandom(8).hex()}".encode()).hexdigest()[:10]
    # Per-run, because WORK used to be one fixed directory that every run rmtree'd on
    # start.  Measured 2026-10-27 by running three families in three processes: the
    # PDF family dropped from 3/3 to 2/3 and one process ran for over fifteen minutes,
    # because the runs were deleting each other's fixtures mid-measurement.  A shared
    # mutable work root makes ANY concurrency -- a developer's two shells, a retried
    # job, a second runner -- silently corrupt the measurement.
    work = ROOT / WORK / run_tag
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    kstar_artifact = ROOT / "canonical/astra_runtime/artifacts/TERMINAL_KSTAR_RESULT_20261007_V1.json"
    kstar_existed = kstar_artifact.exists()
    results: dict[str, Any] = {}
    all_families = _family_plan(only_families)
    plan = _RunPlan(entries, all_families)
    for entry_name in entries:
        families: dict[str, dict[str, Any]] = {}
        failures: list[dict[str, Any]] = []

        def record(family: str, row: dict[str, Any], fam_failures: list[dict[str, Any]]) -> None:
            families[family] = row
            failures.extend(fam_failures)
            # Sorted, so two runs of the same seed produce the same receipt whatever
            # order the workers happened to finish in.
            failures.sort(key=lambda f: (str(f.get("family")), str(f.get("goal"))))
            del failures[60:]
            results[entry_name] = _entry_payload(entry_name, families, failures)
            _write_progress(progress_path, _receipt(
                results, plan, seed=seed, replay=replay, run_tag=run_tag, removed=0,
                liveness=None, reach=None, complete=False))

        jobs = [(run_tag, seed, entry_name, family,
                 oos_count if family == "OUT_OF_SCOPE_MUST_FAIL_CLOSED" else per_family,
                 work / entry_name / family)
                for family in all_families]
        if workers > 1 and len(jobs) > 1:
            # Families are independent: separate fixtures, separate artifact paths,
            # separate task ids.  Measuring them at the same time is the difference
            # between a suite that is long and a suite that is slow -- measured
            # 2026-10-27, the 37-family suite did not finish inside 40 minutes, and
            # the wall clock is what the schedule, not the verdict, has to pay for.
            with ProcessPoolExecutor(max_workers=min(workers, len(jobs))) as pool:
                futures = {pool.submit(_measure_family, job): job[3] for job in jobs}
                for fut in as_completed(futures):
                    family, row, fam_failures = fut.result()
                    record(family, row, fam_failures)
        else:
            for job in jobs:
                family, row, fam_failures = _measure_family(job)
                record(family, row, fam_failures)
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
    reach_work = work / "reachability"
    reach = reachability(reach_work)
    if reach_work.exists():
        shutil.rmtree(reach_work)
    receipt = _receipt(results, plan, seed=seed, replay=replay, run_tag=run_tag,
                       removed=removed, liveness=liveness, reach=reach, complete=True)
    _write_progress(progress_path, receipt)
    return receipt


def _entry_payload(entry_name: str, families: Mapping[str, Mapping[str, Any]],
                   failures: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """One entry's numbers, derived from the families measured so far."""
    in_scope = [f for f in families if f != "OUT_OF_SCOPE_MUST_FAIL_CLOSED"]
    total = sum(families[f]["instances"] for f in in_scope)
    return {
        "entry": ("canonical.runtime.live_integrated_brain_v1.run_raw_goal" if entry_name == "old"
                  else "canonical.runtime.live_brain_route_admission_v1.solve"),
        "families": dict(families),
        "in_scope_families_measured": len(in_scope),
        "in_scope_families_all_pass": sum(
            1 for f in in_scope if families[f]["oracle_pass"] == families[f]["instances"]),
        "in_scope_instance_pass_rate": round(
            sum(families[f]["oracle_pass"] for f in in_scope) / max(1, total), 4),
        "out_of_scope_fail_closed_rate": (families["OUT_OF_SCOPE_MUST_FAIL_CLOSED"]["pass_rate"]
                                          if "OUT_OF_SCOPE_MUST_FAIL_CLOSED" in families else None),
        "failures_sample": list(failures),
    }


def _receipt(results: Mapping[str, Any], plan: "_RunPlan", *, seed: int, replay: bool,
             run_tag: str, removed: int, liveness: Any, reach: Any,
             complete: bool) -> dict[str, Any]:
    """The receipt, whether or not the run finished.

    `run_complete` is the field the verdict reads: a partial receipt still carries
    every family that finished and names every family that did not, but it can
    never be ALIVE.
    """
    return {
        "schema": SCHEMA,
        "authority": "NONE",
        "credit": 0,
        "incremental_spend_usd": 0,
        "model_dependency_count": 0,
        "run_complete": complete,
        "pending_families": [] if complete else plan.pending(results),
        "replay": replay,
        "seed": seed,
        "run_tag": run_tag,
        "controller_checkpoints_removed": removed,
        "python": sys.version.split()[0],
        "machine": {"platform": sys.platform, "network_egress": "allowlisted hosts only"},
        "tool_liveness": liveness if liveness is not None else {"measured": False},
        "reachability_from_one_entry": reach if reach is not None else {"measured": False},
        "families_not_measured_here": NOT_MEASURED_HERE,
        "measurements": dict(results),
        "how_to_read": [
            "in_scope_instance_pass_rate is over FRESH goals the compiler has never seen, judged on the real artifact by stdlib oracles.",
            "out_of_scope_fail_closed_rate must be 1.0: every goal no tool can serve must come back pass=False with nothing written.",
            "Families in families_not_measured_here are not failures and not passes; they are unmeasured on this machine.",
            "run_complete=false means the run was interrupted (usually a job timeout): the numbers shown are real for the",
            "families listed and pending_families names the ones that never ran.  An incomplete run is never ALIVE.",
            "Nothing here is a capability credit. Authority NONE.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=None, help="replay seed (labels the run as a replay)")
    ap.add_argument("--per-family", type=int, default=50)
    ap.add_argument("--oos", type=int, default=100)
    ap.add_argument("--jobs", type=int, default=1,
                    help="families measured at the same time (default 1 = serial). Each family is independent.")
    ap.add_argument("--entries", default="old,new", help="comma list of entries to measure: old,new")
    ap.add_argument("--out", default=None, help="receipt path (default: print only)")
    ap.add_argument("--keep", action="store_true", help="keep generated workspaces")
    ap.add_argument("--summary-md", default=None, help="write a plain-language markdown summary here (heartbeat job summary)")
    ap.add_argument("--require-all-alive", action="store_true",
                    help="exit 1 unless, through the new entry, every measured in-scope family passes 100%%, every out-of-scope goal fails closed, and every routable capability is reachable")
    ap.add_argument("--environment-blockers-are-failures", action="store_true",
                    help="count instances blocked by missing apt metadata / refused pip installs as failures (the public runner installs everything)")
    ap.add_argument("--families", default="", help="comma-separated family names to measure (default: all); a debugging aid, never used by the heartbeat verdict")
    ap.add_argument("--summarize", metavar="RECEIPT_JSON",
                    help="print the markdown summary for an existing receipt and exit; no measurement is run")
    ap.add_argument("--environment-blockers-are-failures-for-summary", action="store_true",
                    help=argparse.SUPPRESS)
    ap.add_argument("--annotate", metavar="RECEIPT_JSON",
                    help="print GitHub workflow-command annotations (::error / ::warning / ::notice) for an existing receipt and exit; no measurement is run")
    ns = ap.parse_args(argv)
    if ns.summarize:
        # A run that hit its timeout never reached the code that writes SUMMARY.md,
        # so the job summary said only "heartbeat produced no summary" -- the one
        # run that most needed explaining explained nothing.  Rendering the summary
        # FROM THE PARTIAL RECEIPT means an interrupted run still reports every
        # family it finished and every family it never reached.
        existing = json.loads(Path(ns.summarize).read_text(encoding="utf-8"))
        sys.stdout.write(summary_markdown(
            existing, environment_blockers_are_failures=ns.environment_blockers_are_failures))
        return 0
    if ns.annotate:
        receipt = json.loads(Path(ns.annotate).read_text(encoding="utf-8"))
        for line in annotation_lines(receipt, environment_blockers_are_failures=ns.environment_blockers_are_failures):
            print(line)
        return 0
    receipt = run(ns.seed, ns.per_family, ns.oos, [x.strip() for x in ns.entries.split(",") if x.strip()], ns.keep,
                  only_families={x.strip() for x in ns.families.split(",") if x.strip()} or None,
                  progress_path=ns.out, workers=max(1, ns.jobs))
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if ns.out:
        # The receipt is the ONLY record of a ten-minute measurement.  Measured: the run
        # completed and then died on `FileNotFoundError` because the output directory did not
        # exist, so every observation was lost.  The directory is created here.
        Path(ns.out).parent.mkdir(parents=True, exist_ok=True)
        Path(ns.out).write_text(text, encoding="utf-8")
    summary = {k: {"in_scope_instance_pass_rate": v["in_scope_instance_pass_rate"],
                   "in_scope_families_all_pass": f'{v["in_scope_families_all_pass"]}/{v["in_scope_families_measured"]}',
                   "out_of_scope_fail_closed_rate": v["out_of_scope_fail_closed_rate"]} for k, v in receipt["measurements"].items()}
    live = receipt["tool_liveness"]
    if ns.summary_md:
        Path(ns.summary_md).parent.mkdir(parents=True, exist_ok=True)
        Path(ns.summary_md).write_text(summary_markdown(receipt, environment_blockers_are_failures=ns.environment_blockers_are_failures), encoding="utf-8")
    verdict_errors = alive_errors(receipt, environment_blockers_are_failures=ns.environment_blockers_are_failures)
    print(json.dumps({"seed": receipt["seed"], "replay": receipt["replay"], "entries": summary, "alive_errors": verdict_errors,
                      "tools": {"total": live["capabilities_total"], "adapter_missing": len(live["adapter_missing"]),
                                "adapter_import_failed": len(live["adapter_import_failed"]),
                                "external_dependency_missing_here": len(live["external_dependency_missing_here"]),
                                "zero_input_capabilities": live["zero_input_capabilities"]},
                      "reachability_from_one_entry": receipt["reachability_from_one_entry"]["counts"]}, indent=2))
    if ns.require_all_alive and verdict_errors:
        return 1
    return 0


_ENVIRONMENT_BLOCKERS = ("BOUND_APT_METADATA_NOT_FOUND", "BOUND_PYPI_INSTALL_FAILED", "BOUND_NPM_INSTALL_FAILED",
                         "externally-managed-environment", "BOUND_APT_PACKAGE_NOT_INSTALLED")


def environment_blocker(result: Mapping[str, Any]) -> str | None:
    """A failure caused by this machine (no apt metadata, pip refused) rather than by the Brain."""
    # Read through the single accessor, not `reason` alone.  A blocker surfaced by
    # a different layer lands in a different field, and reading one field counted
    # a machine problem as a Brain failure -- which corrupts the pass rate rather
    # than merely understating the diagnosis.
    reason = _failure_reason(result)
    for marker in _ENVIRONMENT_BLOCKERS:
        if marker in reason:
            return marker
    return None


def missing_dependency_blocker(exc: BaseException) -> str:
    """A blocker naming the library this host does not have."""
    return "ORACLE_DEPENDENCY_MISSING:" + str(getattr(exc, "name", "") or exc)


def oracle_outcome(case: Any, result: Mapping[str, Any], blocker: str | None) -> tuple[bool, str, str | None]:
    """Grade one instance, classifying a missing ORACLE dependency instead of raising it.

    The oracle is the measurement's own checker, so when it needs a library this host
    lacks that is the same class of fact as an adapter blocker -- a property of this
    machine, not of the capability.  Before this the ModuleNotFoundError escaped and
    aborted the whole census, so on any host without openpyxl or python-docx not one
    family could be measured.  Only ModuleNotFoundError is caught: any other oracle
    defect still raises loudly, which is what it should do.  On the public runner,
    where every declared dependency is installed, environment_blockers_are_failures=True
    still turns a blocker into a NOT ALIVE verdict, so this classifies failures rather
    than hiding them.
    """
    try:
        good, why = (False, "") if blocker else case.oracle(result)
    except ModuleNotFoundError as exc:
        return False, "", (blocker or missing_dependency_blocker(exc))
    return good, why, blocker


def generated_case(gen: Any, rng: Any, work: Any, i: int) -> tuple[Any, str | None]:
    """Build one fixture, or report the library this host lacks to build it.

    Same reasoning as oracle_outcome one layer earlier: a generator that cannot even
    create the input file must cost its own family, not every family after it.
    """
    try:
        return gen(rng, work, i), None
    except ModuleNotFoundError as exc:
        return None, missing_dependency_blocker(exc)


def alive_errors(receipt: Mapping[str, Any], environment_blockers_are_failures: bool = False) -> list[str]:
    """The heartbeat's definition of alive, through the one entry only.

    On the public runner every declared dependency is installed, so an environment blocker IS
    a failure there (environment_blockers_are_failures=True).  In a sandbox without apt
    metadata it is reported separately and does not make the verdict NOT ALIVE.
    """
    errors = []
    if receipt.get("run_complete") is not True:
        # A run that did not finish measured some things and not others.  Calling it
        # ALIVE would be the one direction a report must never go -- so an
        # interrupted run is named, with the families it never reached.
        pending = list(receipt.get("pending_families") or [])
        errors.append("MEASUREMENT_INCOMPLETE:" + ",".join(pending[:12]) if pending
                      else "MEASUREMENT_INCOMPLETE")
    new = (receipt.get("measurements") or {}).get("new")
    if not isinstance(new, Mapping):
        return errors + ["NEW_ENTRY_NOT_MEASURED"]
    for family, row in sorted((new.get("families") or {}).items()):
        if family == "OUT_OF_SCOPE_MUST_FAIL_CLOSED":
            continue
        excused = 0 if environment_blockers_are_failures else int(row.get("environment_blocked_here") or 0)
        if (row.get("oracle_pass") or 0) + excused != row.get("instances"):
            errors.append(f"FAMILY_NOT_FULLY_PASSING:{family}:{row.get('oracle_pass')}/{row.get('instances')}")
    if new.get("out_of_scope_fail_closed_rate") != 1.0:
        errors.append(f"OUT_OF_SCOPE_NOT_FAIL_CLOSED:{new.get('out_of_scope_fail_closed_rate')}")
    counts = (receipt.get("reachability_from_one_entry") or {}).get("counts") or {}
    for state in ("NOT_REACHABLE", "ROUTED_ELSEWHERE"):
        if counts.get(state):
            errors.append(f"CAPABILITY_{state}:{counts[state]}")
    return errors


def _wc(text: str) -> str:
    """Escape a workflow-command message (GitHub decodes %0A as newline, %0D, %25)."""
    return str(text).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def annotation_lines(receipt: Mapping[str, Any], environment_blockers_are_failures: bool = False) -> list[str]:
    """GitHub check annotations carrying the verdict, every family count, and the first failure reasons.

    Annotations are readable through the checks API, unlike job logs and artifacts, so a NOT ALIVE
    verdict explains itself from outside the runner."""
    errors = alive_errors(receipt, environment_blockers_are_failures=environment_blockers_are_failures)
    m = receipt.get("measurements") or {}
    new = m.get("new") or {}
    rows = []
    for fam, row in sorted((new.get("families") or {}).items()):
        env = row.get("environment_blocked_here") or 0
        rows.append(f"{fam} {row.get('oracle_pass')}/{row.get('instances')}" + (f" (env-blocked {env})" if env else ""))
    lines = []
    verdict = "ALIVE" if not errors else "NOT ALIVE"
    lines.append(f"::notice title=Live Brain heartbeat {verdict}::" + _wc("; ".join(rows) or "no families measured"))
    for err in errors[:8]:
        lines.append("::error title=NOT ALIVE::" + _wc(err))
    seen: set[str] = set()
    for f in new.get("failures_sample") or []:
        fam = str(f.get("family"))
        if fam in seen:
            continue
        seen.add(fam)
        if len(seen) > 8:
            break
        lines.append(f"::warning title=first failure in {fam}::" + _wc(f"{f.get('status')} | {f.get('why')} | goal: {f.get('goal')}")[:1000])
    return lines


def summary_markdown(receipt: Mapping[str, Any], environment_blockers_are_failures: bool = False) -> str:
    m = receipt["measurements"]; live = receipt["tool_liveness"]; reach = receipt["reachability_from_one_entry"]
    errors = alive_errors(receipt, environment_blockers_are_failures=environment_blockers_are_failures)
    complete = receipt.get("run_complete") is True
    lines = ["# Live Brain heartbeat", "",
             f"**Verdict: {'ALIVE' if not errors else 'NOT ALIVE'}** - seed {receipt['seed']}, python {receipt['python']}, platform {receipt['machine']['platform']}", ""]
    if not complete:
        # Say it in the first paragraph, not in a footnote: the numbers below are
        # real but they are not a verdict, and a reader who skims must not mistake
        # them for one.
        pending = [str(f) for f in (receipt.get("pending_families") or [])]
        lines += [f"**This run did NOT finish.** {len(pending)} of the planned families were never "
                  f"measured, so no verdict about the whole creature can be given.", ""]
        if pending:
            lines += ["Families never reached:", ""] + [f"- `{f}`" for f in pending] + [""]
        lines += ["Everything below is what the families that DID run produced. It is a "
                  "measurement of part of the suite, not of Brain.", ""]
    if errors:
        lines += ["Why not alive:", ""] + [f"- `{e}`" for e in errors] + [""]
    lines += ["| Fresh-goal family | " + " | ".join(m.keys()) + " |", "|---|" + "---|" * len(m)]
    families = sorted({f for e in m.values() for f in e["families"]})
    for f in families:
        cells = []
        for e in m:
            row = m[e]["families"].get(f)
            if row is None:
                cells.append("-")
            else:
                env = row.get("environment_blocked_here") or 0
                cells.append(f"{row['oracle_pass']}/{row['instances']}" + (f" ({env} blocked by this machine)" if env else ""))
        lines.append(f"| {f} | " + " | ".join(cells) + " |")
    if live.get("measured") is False:
        lines += ["", "Tool liveness and reachability were not reached in this run (it was "
                  "interrupted before the closing census).", ""]
        return "\n".join(lines) + "\n"
    lines += ["", "Reachability from the one entry: " + ", ".join(f"{k} {v}" for k, v in sorted(reach["counts"].items())) + f" (of {reach['capabilities_total']})", ""]
    not_runnable = sorted(set(live["adapter_import_failed"]) | set(live["external_dependency_missing_here"]) | set(live["adapter_missing"]))
    lines += [f"Tools runnable on this machine: {live['capabilities_total'] - len(not_runnable)} of {live['capabilities_total']}", ""]
    if not_runnable:
        lines += ["Not runnable here:", ""] + [f"- `{cid}`" for cid in not_runnable] + [""]
    rows = [r for r in reach["rows"] if r["state"] != "REACHED_AND_BOUND"]
    if rows:
        lines += ["Capabilities not reached from a sentence (or blocked by design):", ""] + [f"- `{r['capability_id']}`: {r['state']} - {r['detail']}" for r in rows] + [""]
    lines += ["Families not measured here: " + ", ".join(sorted(receipt["families_not_measured_here"])), "", "Authority NONE. Credit 0. Nothing here is a capability claim."]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
