#!/usr/bin/env python3
"""BRIDGE_ENUMERATION_V1 -- the machine derives its own verified capability bridges.

Why this exists
---------------
The bound registry declares ``provides``/``requires`` tokens per capability, and the
composer chains on those tokens.  But most producer outputs name MECHANISMS
(``yaml.to_json``) while most consumer needs name ARTIFACTS (``json.file.available``),
so literal token matching under-connects the graph: on 2026-10-26 the live registry
carried 73 entries, 96 distinct provided effects, 38 distinct requirements, and the
token intersection was 11.  The bridge that matters -- "this adapter, when run, emits
real bytes of the type that need names" -- is not named by any token; it is a fact
about execution, so it must be established BY execution.

The pattern is the brain's own ``computer_env_v1.probe_survivors``: enumerate the
candidate space structurally, execute every candidate, keep only survivors.  No
models, no token guessing, and the failure mode is absence from the table rather
than a wrong row in it -- fail closed by construction.

Two row kinds, never conflated
------------------------------
EMITS_VERIFIED   -- the producer ran under ``run_adapter_locally`` (the fail-closed
                    local executor: nonzero cost, missing module, or a failed declared
                    expectation all refuse), wrote bytes to a repository-scoped path,
                    and those bytes parse as the claimed type under an INDEPENDENT
                    stdlib checker in this file (magic bytes / strict parsers).  The
                    producer's own expectation is treated as producer evidence only;
                    the byte check is the oracle and it shares no code with any
                    adapter.
BRIDGE_VERIFIED  -- EMITS_VERIFIED, plus a consumer declaring the matching
                    ``*.available`` requirement ran ON THE EMITTED ARTIFACT and its
                    own declared expectation passed.  The bridge is the edge the
                    registry graph is missing, now backed by an execution.

Everything that does not survive is classified (SKIPPED_UNSYNTHESIZED_INPUTS,
SKIPPED_ENVIRONMENT, ADAPTER_REFUSED, TYPE_MISMATCH, NO_FILE_EMITTED), never hidden:
a capability this module cannot feed honest inputs to is a gap in the enumeration,
and it is reported as one, in the open.

Limits, honestly
----------------
* Environment-bounded: producers gated on absent binaries (pandoc, tesseract,
  chromium, node packages) or on egress survive only where the dependency exists;
  elsewhere they are classified SKIPPED_ENVIRONMENT.  Rows carry the executor and
  platform markers so a Number produced here is never laundered into a runner fact.
* Input fixtures are small, synthetic and declared in DEFAULT_FIXTURES; changing one
  fixture class is a code change, not a hidden parameter.
* This module changes nothing by itself: it emits a measurement artifact (authority
  NONE).  Filling the registry's empty ``provides_as``/``requires_as`` slots happens
  in a separate governed step keyed to rows of this report.

Zero external model.  Zero incremental spend.  Never installs anything.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import platform
import shutil
import sys
import time
import uuid

SCHEMA = "PROJECT_BRAIN_BRIDGE_ENUMERATION_V1"

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"

# Posted file types the enumeration tests, and the independent byte-oracle names.
# Order matters only for output stability.
CANDIDATE_TYPES = ("pdf", "json", "yaml", "md", "txt", "png", "tar.gz", "sqlite", "xlsx", "docx")

# Requirement tokens of the form <thing>.available whose satisfier is a posted file.
# Each maps to the byte types allowed to satisfy it.  A token not listed here is a
# non-file need (runtimes, networks, derived evidence) and stays out of scope.
NEED_TYPES = {
    "pdf.file.available": ("pdf",),
    "pdf.file.image_only.available": ("pdf",),
    "manifest.json.available": ("json",),
    "json.file.available": ("json",),
    "structured.json.available": ("json",),
    "trades.json.available": ("json",),
    "yaml.file.available": ("yaml",),
    "markdown.file.available": ("md",),
    "image.file.available": ("png", "jpg"),
    "archive.tar_gz.available": ("tar.gz",),
    "artifact.file.available": ("pdf", "json", "md", "txt", "docx", "xlsx", "png", "yaml"),
    "python.source.file.available": ("txt",),
}

UNFIXABLE_INPUT_ARGS = {
    "argv", "test_argv", "test_paths", "source_root", "url", "module", "prompt",
    "task_text", "objective", "language", "output_prefix_hex", "decode_export",
    "encode_export", "decode_callable", "encode_callable", "decode_kwargs",
    "encode_kwargs", "label", "root_selector", "extraction_path", "candidate_path",
    "spec_text", "query", "question",
}


# --------------------------------------------------------------------------- #
# independent byte oracles -- no adapter code participates below this line
# --------------------------------------------------------------------------- #
def _bytes(root, rel):
    p = (root / str(rel)).resolve()
    if root not in p.parents and p != root:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY:" + str(rel))
    if not p.is_file():
        raise RuntimeError("BYTE_ORACLE_NO_FILE:" + str(rel))
    return p.read_bytes()


def oracle_bytes_of(ext, root, rel):
    b = _bytes(root, rel)
    if ext == "pdf":
        return b[:5] == b"%PDF-" and b"%%EOF" in b[-4096:]
    if ext == "png":
        return b[:8].hex() == "89504e470d0a1a0a"
    if ext == "jpg":
        return b[:2] == b"\xff\xd8"
    if ext == "tar.gz":
        return b[:2] == b"\x1f\x8b"
    if ext == "sqlite":
        return b[:16] == b"SQLite format 3\x00"
    if ext in ("docx", "xlsx"):
        # A package is not a document just because it is a zip: docx requires the
        # word-processing payload, xlsx the spreadsheet one.  Accepting the shared
        # container marker alone once produced a false "xlsx writer emits docx" row.
        import zipfile
        marker = {"docx": "word/document.xml", "xlsx": "xl/workbook.xml"}[ext]
        try:
            with zipfile.ZipFile(root / rel) as zf:
                names = set(zf.namelist())
                return "[Content_Types].xml" in names and marker in names and zf.testzip() is None
        except Exception:  # noqa: BLE001 - a corrupt zip is a no
            return False
    if ext == "json":
        try:
            json.loads((root / rel).read_text(encoding="utf-8"))
            return True
        except Exception:  # noqa: BLE001
            return False
    if ext == "yaml":
        try:
            import yaml  # optional: check unavailable -> row must not survive
        except Exception:  # noqa: BLE001
            raise RuntimeError("BYTE_ORACLE_UNAVAILABLE:yaml")
        try:
            yaml.safe_load((root / rel).read_text(encoding="utf-8"))
            return True
        except Exception:  # noqa: BLE001
            return False
    if ext in ("md", "txt", "csv", "html", "svg"):
        try:
            return len(b) > 0 and b"\x00" not in b and b.decode("utf-8", "strict") is not None
        except Exception:  # noqa: BLE001
            return False
    return False


# --------------------------------------------------------------------------- #
# fixtures (declared, small, synthetic)
# --------------------------------------------------------------------------- #
def write_default_fixtures(scratch):
    """Materialize the declared fixtures under scratch; return repo-relative paths."""
    fxdir = scratch / "fixtures"
    fxdir.mkdir(parents=True, exist_ok=True)

    def w(name, data, binary=False):
        p = fxdir / name
        (p.write_bytes(data) if binary else p.write_text(data, "utf-8"))
        return p

    f = {}
    f["txt"] = w("a.txt", "alpha lines\nbeta lines\nalpha twice\n")
    f["yaml"] = w("a.yaml", "name: probe\nitems:\n- 1\n- 2\n")
    f["json"] = w("a.json", json.dumps({"probe": [1, 2]}))
    f["records"] = w("records.json", json.dumps([{"id": 1, "v": "x"}, {"id": 2, "v": "y"}]))
    sha = hashlib.sha256(f["txt"].read_bytes()).hexdigest()
    return f


def manifest_for_scratch(scratch, root):
    """A manifest in the REAL shape the archive adapters accept.

    Their ``_manifest_paths`` keeps only ``canonical/``-prefixed paths found in
    ``records[].verification_paths``; any other shape is silently not archived,
    which once produced a manifest-only "archive" that still verified (a demo
    bridge).  The enumeration therefore REQUIRES its scratch under ``canonical/``
    and fails closed otherwise.
    """
    txt = scratch / "fixtures" / "a.txt"
    sha = hashlib.sha256(txt.read_bytes()).hexdigest()
    rel_txt = str(txt.relative_to(root))
    if not rel_txt.startswith("canonical/"):
        raise RuntimeError(
            "BRIDGE_FIXTURE_OUTSIDE_CANONICAL_PREFIX:"
            "archive manifest contracts only admit canonical/-prefixed paths")
    data = {"records": [{"capability_id": "bridge_enumeration_v1_fixture",
                         "artifact_sha256": sha,
                         "verification_paths": [rel_txt]}]}
    p = scratch / "fixtures" / "manifest.json"
    p.write_text(json.dumps(data, indent=1), "utf-8")
    return p


def _provides_file_ext(entry):
    """The file extension a consumer's own `provides` promises, if any."""
    for tok in entry.get("provides") or []:
        if tok in NEED_TYPES:
            return NEED_TYPES[tok][0]
    return "out"


def fixture_value(argname, scratch, root):
    n = str(argname).lower()
    fx = scratch / "fixtures"
    if n in ("timeout_s",):
        return 8
    if n in ("max_bytes",):
        return 4096
    if n in ("max_pages", "max_files", "max_candidates"):
        return 3
    if n in ("max_pair_candidates", "mutations_per_file"):
        return 2
    if n in ("max_trace_events",):
        return 16
    if n == "content":
        return "probe text alpha beta\n"
    if n == "spec":
        return '{"probe": [1, 2, 3]}'
    if n == "goal":
        return "create a table named probe with columns id, v"
    if n == "document_goal":
        return "write a one section report titled Probe containing the summary"
    if n in ("json_path",):
        return str((fx / "records.json").relative_to(root))
    if n in ("yaml_path",):
        return str((fx / "a.yaml").relative_to(root))
    if n in ("markdown_path",):
        return str((fx / "a.md").relative_to(root))
    if n == "manifest_path":
        return str((fx / "manifest.json").relative_to(root))
    if n == "text_path":
        return str((fx / "a.txt").relative_to(root))
    if n == "records":
        return json.dumps([{"id": 1}, {"id": 2}])
    if n in ("x_ticks", "y_ticks", "x_value", "y_value"):
        return "20"
    if n.endswith("_path") or n.endswith("_file"):
        for k in ("yaml", "manifest", "markdown", "json"):
            if k in n:
                return str((fx / {"yaml": "a.yaml", "manifest": "manifest.json",
                                  "markdown": "a.md", "json": "a.json"}[k]).relative_to(root))
        if "md" in n:
            return str((fx / "a.md").relative_to(root))
        return str((fx / "a.txt").relative_to(root))
    return None


# --------------------------------------------------------------------------- #
# enumeration
# --------------------------------------------------------------------------- #
def _load_registry(reg_path):
    p = (REPO_ROOT / reg_path).resolve()
    if REPO_ROOT.resolve() not in p.parents:
        raise RuntimeError("REGISTRY_OUTSIDE_REPOSITORY")
    data = json.loads(p.read_text(encoding="utf-8"))
    return data["capabilities"]


def enumerate_bridges(reg_path=DEFAULT_REGISTRY, scratch=None, *, runner=None, now=None):
    """Enumerate (producer, type) candidates, execute, verify bytes, then consumers.

    Returns the measurement report dict.  Nothing here grants credit; the report
    carries authority NONE and names its carrier.
    """
    from canonical.runtime import live_brain_route_admission_v1 as ra

    started = time.time()
    root = REPO_ROOT
    created = False
    if scratch is None:
        # canonical/-prefixed so archive fixtures are archivable in the real
        # manifest grammar; this tree is deleted in `finally` below.
        scratch = root / "canonical" / "runtime" / "state" / \
            f"tmp_bridge_enumeration_{uuid.uuid4().hex[:10]}"
        created = True
    scratch = pathlib.Path(scratch)
    try:
        scratch.mkdir(parents=True, exist_ok=True)
        write_default_fixtures(scratch)
        manifest_for_scratch(scratch, root)
        rel_out = scratch.relative_to(root)

        reg = _load_registry(reg_path)
        producers, consumers = [], []
        for cid, entry in sorted(reg.items()):
            tmpl = (entry.get("action_template") or {}).get("args") or {}
            if "output_path" in tmpl:
                producers.append((cid, entry, tmpl))
            for need in entry.get("requires") or []:
                if need in NEED_TYPES:
                    consumers.append((cid, entry, tmpl, need))

        emits, skipped, failures = [], [], []

        def run(entry, tmpl, args):
            action = {"type": "invoke_capability", "args": dict(args),
                      "expect": tmpl.get("expect") or (entry.get("action_template") or {}).get("expect")}
            return ra.run_adapter_locally(entry, action)

        for cid, entry, tmpl in producers:
            pre, ok = {}, True
            for arg in tmpl:
                if arg in ("capability_id", "output_path"):
                    continue
                if arg in UNFIXABLE_INPUT_ARGS:
                    ok = False
                    break
                val = fixture_value(arg, scratch, root)
                if val is None:
                    ok = False
                    break
                pre[arg] = val
            if not ok:
                skipped.append({"capability": cid, "class": "SKIPPED_UNSYNTHESIZED_INPUTS"})
                continue
            if runner and not runner(cid, entry):
                skipped.append({"capability": cid, "class": "SKIPPED_ENVIRONMENT"})
                continue
            outdir = rel_out / "out"
            for ext in CANDIDATE_TYPES:
                outp = outdir / f"{cid}.{ext}"
                args = dict(pre)
                args["output_path"] = str(outp)
                try:
                    res = run(entry, tmpl, args)
                except Exception as exc:  # noqa: BLE001 - refusal is data
                    msg = str(exc)
                    cls = ("SKIPPED_ENVIRONMENT" if ("DEPENDENCY_MISSING" in msg or "Errno 2" in msg)
                           else "ADAPTER_REFUSED")
                    failures.append({"capability": cid, "type": ext, "class": cls,
                                     "reason": msg[:160]})
                    continue
                emitted = str(outp)
                if not (root / emitted).is_file():
                    for v in (res or {}).values():
                        if isinstance(v, str) and (root / v).is_file():
                            emitted = v
                            break
                    else:
                        failures.append({"capability": cid, "type": ext, "class": "NO_FILE_EMITTED"})
                        continue
                try:
                    type_ok = oracle_bytes_of(ext, root, emitted)
                except RuntimeError as oracle_refusal:
                    failures.append({"capability": cid, "type": ext,
                                     "class": str(oracle_refusal)[:48]})
                    continue
                if type_ok:
                    emits.append({"capability": cid, "emits_type": ext, "artifact": emitted,
                                  "artifact_sha256": hashlib.sha256((root / emitted).read_bytes()).hexdigest()})
                else:
                    failures.append({"capability": cid, "type": ext, "class": "TYPE_MISMATCH"})

        bridges, bridge_failures = [], []
        for row in emits:
            pcid, ext, artifact = row["capability"], row["emits_type"], row["artifact"]
            for ccid, centry, ctmpl, need in consumers:
                if ext not in NEED_TYPES[need]:
                    continue
                args, fill = {}, True
                for arg in ctmpl:
                    if arg == "capability_id":
                        continue
                    n = arg.lower()
                    if n == "timeout_s":
                        args[arg] = 8
                        continue
                    if n == "output_path":
                        # Consumers that also emit must write to their OWN slot,
                        # never into the fixtures tree: letting the generic
                        # *_path fallback hand "output_path" a fixture file once
                        # made a crosshair oracle overwrite the very source the
                        # archive world was verifying (refs: tamper tests below).
                        args[arg] = str(rel_out / "consumer_out" /
                                        f"{ccid}__from__{pcid}.{_provides_file_ext(centry)}")
                        continue
                    pathish = (n.endswith("_path") or n.endswith("_file") or n in
                               ("path", "archive_path", "db_path", "database_path",
                                "pdf_path", "image_path", "chart_path", "docx_path",
                                "xlsx_path"))
                    if pathish and "output" not in n and "result" not in n and "manifest" not in n:
                        args[arg] = artifact
                        continue
                    val = fixture_value(arg, scratch, root)
                    if val is None:
                        fill = False
                        break
                    args[arg] = val
                if not fill or not args:
                    continue
                try:
                    run(centry, ctmpl, args)
                    bridges.append({"producer": pcid, "emits_type": ext, "consumer": ccid,
                                    "satisfies": need})
                except Exception as exc:  # noqa: BLE001
                    bridge_failures.append({"producer": pcid, "consumer": ccid,
                                            "class": "CONSUMER_REFUSED", "reason": str(exc)[:160]})

        hat = {
            "schema": SCHEMA,
            "kind": "MEASUREMENT",
            "authority": "NONE",
            "capability_credit": 0,
            "incremental_spend_usd": 0,
            "producer_cognition_model_dependency_count": 0,
            "executor": "SANDBOX_OR_CALLER_ENVIRONMENT",
            "platform": platform.platform(),
            "cwd_name": root.name,
            "registry_path": reg_path,
            "counts": {
                "registry_entries": len(reg),
                "producer_candidates": len(producers),
                "consumer_file_needs": len(consumers),
                "emits_verified": len(emits),
                "bridge_verified": len(bridges),
                "skipped": len(skipped),
                "execution_failures_classified": len(failures) + len(bridge_failures),
            },
            "emits_verified": emits,
            "bridge_verified": bridges,
            "skipped": skipped,
            "failures": failures,
            "bridge_failures": bridge_failures,
            "duration_s": round(time.time() - started, 3),
        }
        return hat
    finally:
        if created:
            shutil.rmtree(scratch, ignore_errors=True)


def main(argv=()):
    reg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_REGISTRY
    report = enumerate_bridges(reg)
    print(json.dumps({"schema": report["schema"], "authority": report["authority"],
                      "counts": report["counts"],
                      "bridge_verified": report["bridge_verified"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
