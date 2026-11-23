#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scan an arbitrary environment, retrieve what is known, get the gap filled honestly.

THE IDEA (the owner's, taken literally):

    "All the agent should do is scan everything in the environment, then retrieve
     from his memory what he knows and what he doesn't know. What he doesn't
     know, he should get it instantly -- because everything on the computer has
     a guide."

This module is that flow: one call, honest by construction. It is NOT a new
learner, NOT a new store, NOT a new planner. It is the reconnaissance layer
that sits under all three:

  1. SCAN -- bounded filesystem observation. Never executes anything except
     what the environment's own broker runs for its declared runner.
  2. REMEMBER -- retrieve what the stores already hold (Perfect Algorithm rules
     admitted for this family, observed priors for this kind, the broker's
     evidence-keyed cache). Nothing is re-trusted blindly.
  3. FILL THE GAP -- what remains unknown is asked of the instant-knowledge
     tier: local guides first (offline, completeness-gated), then the web, only
     when the caller opts in. Web knowledge is labeled EXTERNAL and never
     counted as capability.
  4. REPORT -- a checkpoint packet in the shape the frontier (Exploration
     Checkpoint Coverage, arXiv 2606.31422) asks for: goal + environment +
     checkpoint evidence + what remains unknown + a decision. Known items are
     labeled by their source; unknown items are named, never fabricated.

A page environment (page_url=) follows the same contract:
  - SCAN loads the page through the repo's own browser driver and records the
    title, URL, and every interactive affordance with the name a person would
    call it. A page declares no manifest, so the affordances ARE the declared
    surface -- they are reported as such, and nothing else is fabricated.
  - It never persists, never re-plans, never counts the web tier as
    capability. Refusals refuse by name.

What this flow REFUSES to do:
  - It does not plan or pick actions. Planning is the Perfect Algorithm's job;
    this is reconnaissance.
  - It does not persist anything. The stores are written by their owners
    (the Perfect Algorithm's run(), the broker). This flow only READS memory.
  - It does not count the web tier as capability. Every document carries its
    authority; the receipt names which tier actually answered.
  - It does not guess at the contract. If the environment cannot say what
    counts as success, the question is reported UNKNOWN by name.

Model calls: 0. Network: 0 unless allow_web=True. Spend: $0.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import time
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import local_guide_v1 as guide
from canonical.swe_kernel import perfect_algorithm_v1 as pa
from canonical.swe_kernel import the_environment_broker_v1 as broker

SCHEMA = "PROJECT_BRAIN_ENVIRONMENT_SCAN_KNOW_V1"
AUTHORITY = "NONE__OBSERVED_HOST_EVIDENCE_AND_GATES"

KNOWN_SCAN = "KNOWN_SCAN"
KNOWN_MEMORY = "KNOWN_MEMORY"
KNOWN_BROKER = "KNOWN_BROKER"
KNOWN_LOCAL_GUIDE = "KNOWN_LOCAL_GUIDE"
KNOWN_WEB = "KNOWN_WEB"
UNKNOWN = "UNKNOWN"

KNOWN_ALL = "KNOWN__ALL_QUESTIONS_ANSWERED"
OPEN_GAP = "OPEN__GAP_REMAINS"
REFUSE_EMPTY_GOAL = "REFUSE__EMPTY_GOAL"
REFUSE_NOT_A_DIRECTORY = "REFUSE__NOT_A_DIRECTORY"
REFUSE_NO_EVIDENCE = "REFUSE__NO_EVIDENCE"
REFUSE_PAGE_SCHEME = "REFUSE__PAGE_SCHEME_UNSUPPORTED"
REFUSE_PAGE_UNLOADABLE = "REFUSE__PAGE_UNLOADABLE"

_MANIFEST_NAMES = ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
                   "package.json", "cargo.toml", "go.mod", "Makefile")
_DOC_NAMES = ("readme.md", "readme", "readme.txt", "agents.md", "llms.txt")
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv",
              ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build",
              ".next", ".cache", "out", "target"}


def _run_tests_goal_requested(goal: str) -> bool:
    text = str(goal or "").lower()
    return bool(re.search(r"\b(run|pytest|test|check|verify|suite|pass|ci)\b", text))


def _detect_kind(files: Sequence[str]) -> str:
    names = {os.path.basename(f).lower() for f in files}
    if any(n in names for n in ("pyproject.toml", "setup.py", "setup.cfg",
                                "requirements.txt")):
        return "python"
    if "package.json" in names:
        return "node"
    if "cargo.toml" in names:
        return "rust"
    if "go.mod" in names:
        return "go"
    if "makefile" in names:
        return "make"
    return "unknown"


def _walk(root: pathlib.Path, max_files: int, max_depth: int) -> tuple[list[str], bool]:
    """Bounded, filesystem-only. Returns (files, truncated)."""
    files: list[str] = []
    truncated = False
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        depth = len(pathlib.Path(dirpath).relative_to(root).parts)
        if depth >= max_depth:
            dirnames[:] = []
            if dirnames or filenames:
                truncated = True
            continue
        for name in filenames:
            if len(files) >= max_files:
                truncated = True
                return files, truncated
            full = pathlib.Path(dirpath) / name
            try:
                st = full.stat()
                if st.st_size > 0:  # record only real non-empty files
                    files.append(str(full.relative_to(root)))
            except OSError:
                continue
    return files, truncated


def _layout(root: pathlib.Path, files: Sequence[str]) -> str:
    if files and all(f.split("/", 1)[0] == "src" for f in files):
        return "src-layout"
    if "src" in {f.split("/", 1)[0] for f in files}:
        return "src-layout"
    if any("/" in f for f in files):
        return "nested"
    return "flat"


def _read_manifest(root: pathlib.Path, rel: str) -> dict[str, Any]:
    name = os.path.basename(rel).lower()
    try:
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {"present": False}
    out: dict[str, Any] = {"present": True}
    if name.endswith((".toml", ".cfg")):
        m = re.search(r"^\s*requires-python\s*=\s*[\"']([^\"']+)[\"']", text, re.MULTILINE)
        if m:
            out["requires_python"] = m.group(1).strip()
        m = re.search(r"dependencies\s*=\s*\[(.*?)\]", text, re.DOTALL)
        if m:
            out["declared_deps"] = re.findall(r"[\"']([^\"']+)[\"']", m.group(1))[:32]
    elif name == "package.json":
        try:
            data = json.loads(text)
            out["name"] = data.get("name")
            out["version"] = data.get("version")
            out["scripts"] = sorted((data.get("scripts") or {}).keys())[:16]
            engines = data.get("engines")
            if engines:
                out["engines"] = dict(engines)
        except Exception:
            out["parse_error"] = True
    elif name == "requirements.txt":
        deps = [ln.strip() for ln in text.splitlines()
               if ln.strip() and not ln.strip().startswith("#")]
        out["declared_deps"] = deps[:32]
    return out


def _docs_in(files: Sequence[str]) -> list[str]:
    out: list[str] = []
    for f in files:
        name = os.path.basename(f).lower()
        if name in _DOC_NAMES or name.startswith("readme"):
            out.append(f)
    return sorted(out)


def _guide_answer(goal: str, root: pathlib.Path, query: str, *,
                  tools=None, deadline_s: float) -> dict[str, Any] | None:
    try:
        return guide.lookup(query, root=root, tools=tools,
                           timeout_s=5.0, deadline_s=deadline_s)
    except Exception:
        return None


def _scan_page_url(url: str) -> dict[str, Any]:
    """Load a page through the repo's own browser driver. Never fabricates.

    Returns the page's declared surface: title, URL, text sample, and the
    interactive affordances with a label a person would use. Any failure is
    honest and named -- the page is NOT recorded as scanned on refusal.
    """
    try:
        from canonical.runtime import browser_v1 as browser
    except Exception as e:
        return {"ok": False, "reason": f"REFUSE__BROWSER_IMPORT:{e}", "url": url}
    try:
        state = browser.state(url)
    except Exception as e:
        return {"ok": False, "reason": f"REFUSE__PAGE_LOAD_EXCEPTION:{e}", "url": url}
    if not (state or {}).get("ok"):
        return {"ok": False, "reason": (state or {}).get("reason") or "REFUSE__PAGE_LOAD_FAILED",
                "url": url}
    data = state.get("data") or {}
    elements = data.get("elements") or []
    affordances = []
    for e in elements[:80]:
        label = (e.get("text") or e.get("aria") or e.get("name") or e.get("placeholder") or "").strip()
        affordances.append({
            "tag": e.get("tag"),
            "type": e.get("type"),
            "label": label[:200],
            "disabled": bool(e.get("disabled")),
            "href": e.get("href") or "",
        })
    return {
        "ok": True,
        "url": data.get("url") or url,
        "title": data.get("title") or "",
        "text": (data.get("text") or "")[:8000],
        "text_chars": len(data.get("text") or ""),
        "elements": elements,
        "affordances": affordances,
        "element_count": len(elements),
    }


def scan_and_know(
    root: str | pathlib.Path | None,
    goal: str,
    *,
    page_url: str | None = None,
    memory_path_: str | pathlib.Path | None = None,
    broker_memory_path_: str | pathlib.Path | None = None,
    allow_web: bool = False,
    tools: Sequence[str] | None = None,
    max_files: int = 4000,
    max_depth: int = 4,
    local_guide_deadline_s: float = 30.0,
    env_kind: str | None = None,
    goal_family: str | None = None,
) -> dict[str, Any]:
    """One honest reconnaissance flow: scan, retrieve known vs unknown, fill the gap.

    Never persists anything; never claims capability; never fabricates a contract.
    Two distinct stores are consulted, read-only:
      memory_path_        -- the Perfect Algorithm's store (rules + priors)
      broker_memory_path_ -- the broker's evidence-keyed cache (Python run-tests
                             contract only; the broker is allowed to write it,
                             it is its own store, never the Perfect Algorithm's)
    Returns a checkpoint packet.
    """
    started = time.perf_counter()
    page_mode = page_url is not None
    if page_mode:
        root_path: pathlib.Path | None = None
        receipt_root = str(page_url)
    else:
        root_path = pathlib.Path(root).resolve() if root else None
        receipt_root = str(root_path)
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "root": receipt_root,
        "goal": str(goal or ""),
        "verdict": None,
        "scanned": None,
        "questions": [],
        "memory": None,
        "gap_count": 0,
        "known": [],
        "unknown": [],
        "persist": "NONE -- this flow only reads memory and never persists; "
                   "consumers persist through their own stores",
        "seconds": None,
    }

    def _finish() -> dict[str, Any]:
        receipt["seconds"] = round(time.perf_counter() - started, 4)
        gaps = [q for q in receipt["questions"] if q["status"] == UNKNOWN]
        receipt["unknown"] = [q["question"] for q in gaps]
        receipt["known"] = [q["question"] for q in receipt["questions"]
                           if q["status"] != UNKNOWN]
        receipt["gap_count"] = len(gaps)
        if receipt["verdict"] is None:
            receipt["verdict"] = KNOWN_ALL if not gaps else OPEN_GAP
        return receipt

    # ---- validation ------------------------------------------------
    if not str(goal or "").strip():
        receipt["verdict"] = REFUSE_EMPTY_GOAL
        return _finish()
    if page_mode:
        from urllib.parse import urlparse
        scheme = urlparse(str(page_url)).scheme.lower()
        if scheme not in {"http", "https"}:
            receipt["verdict"] = REFUSE_PAGE_SCHEME
            return _finish()
    else:
        if root_path is None or not root_path.is_dir():
            receipt["verdict"] = REFUSE_NOT_A_DIRECTORY
            return _finish()

    # ---- 1. scan ---------------------------------------------------
    page: dict[str, Any] | None = None
    files: list[str] = []
    truncated = False
    kind = "unknown"
    layout = "flat"
    manifests: dict[str, Any] = {}
    docs: list[str] = []
    if page_mode:
        page = _scan_page_url(str(page_url))
        if not page.get("ok"):
            receipt["verdict"] = REFUSE_PAGE_UNLOADABLE
            receipt["scanned"] = {"kind": "browser_page", "layout": "page",
                                 "reason": page.get("reason", "REFUSE__PAGE_UNLOADABLE")}
            return _finish()
        kind = "browser_page"
        layout = "page"
        receipt["scanned"] = {
            "file_count": 0,
            "truncated": False,
            "kind": kind,
            "layout": layout,
            "manifests": [],
            "docs": [],
            "manifest_details": {},
            "page": {
                "title": page["title"],
                "url": page["url"],
                "text_chars": page["text_chars"],
                "element_count": page["element_count"],
                "affordances": page["affordances"],
            },
        }
    else:
        files, truncated = _walk(root_path, max_files, max_depth)
        kind = _detect_kind(files)
        manifest_rels = [f for f in files
                         if os.path.basename(f).lower() in {n.lower() for n in _MANIFEST_NAMES}]
        docs = _docs_in(files)
        for rel in manifest_rels:
            parsed = _read_manifest(root_path, rel)
            if parsed.get("present"):
                manifests[os.path.basename(rel)] = parsed
        layout = _layout(root_path, files)
        receipt["scanned"] = {
            "file_count": len(files),
            "truncated": truncated,
            "kind": kind,
            "layout": layout,
            "manifests": sorted(manifests),
            "docs": docs[:16],
            "manifest_details": manifests,
        }

        if not files:
            receipt["verdict"] = REFUSE_NO_EVIDENCE
            return _finish()

    # ---- 2. memory (read-only) -------------------------------------
    fam = goal_family or pa._default_family(goal)
    kind_key = env_kind or ("plain" if kind == "unknown" else kind)
    memory: dict[str, Any] = {}
    if memory_path_:
        try:
            memory = pa.load_memory(memory_path_)
        except Exception:
            memory = {}
    known_rules = pa.lookup(memory, fam, kind_key) if memory else []
    known_priors = pa.priors_for(memory, kind_key) if memory else {}

    receipt["memory"] = {
        "rules_known": known_rules,
        "prior_keys": sorted(known_priors.get("model", {}).keys()) if known_priors else [],
        "family": fam,
        "env_kind": kind_key,
    }

    # ---- 3. questions -----------------------------------------------
    questions: list[dict[str, Any]] = []

    def _q(question: str, status: str, source: str, detail: Any) -> None:
        questions.append({"question": question, "status": status,
                          "source": source, "detail": detail})

    # Q1: what IS this thing?
    if page_mode:
        _q("what is this thing", KNOWN_SCAN, "scan",
           {"kind": kind, "layout": layout, "title": page["title"],
            "url": page["url"], "text_chars": page["text_chars"],
            "element_count": page["element_count"]})
    else:
        _q("what is this thing", KNOWN_SCAN, "scan",
           {"kind": kind, "layout": layout, "file_count": len(files),
            "truncated": truncated, "manifests": sorted(manifests),
            "docs": docs[:16]})

    # Q2: what is DECLARED to be needed?
    if page_mode:
        # a page declares no manifest; the affordances ARE its declared surface.
        affordances = page["affordances"]
        labels = [a["label"] for a in affordances if a["label"]][:40]
        _q("what are the declared requirements", KNOWN_SCAN, "scan",
           {"title": page["title"], "url": page["url"],
            "affordances": affordances[:40],
            "note": "a page declares no manifest; the affordances are the "
                    "only declared surface"})
    else:
        declared: dict[str, Any] = {}
        for name, parsed in manifests.items():
            for key in ("requires_python", "declared_deps", "engines", "scripts"):
                if parsed.get(key):
                    declared[f"{name}:{key}"] = parsed[key]
        _q("what are the declared requirements",
           KNOWN_SCAN if declared else KNOWN_SCAN,
           "scan",
           declared if declared else {"reason": "no manifest declares requirements"})

    # Q3: what RUNS/CHECKS it?
    runner_verdict: dict[str, Any] | None = None
    if page_mode:
        # a page has no runner contract; the affordances are its only declared
        # execution surface -- report them as what CAN be done here.
        affordances = page["affordances"]
        labels = [a["label"] for a in affordances if a["label"]][:40]
        _q("what runs/checks it", KNOWN_SCAN, "scan",
           {"affordances": labels,
            "note": "a page has no runner contract; affordances are its "
                    "only declared execution surface"})
        # Q4: a page declares no success contract beyond its affordances.
        _q("what counts as success", UNKNOWN, "page",
           {"reason": "a page declares no contract; success is not declared here"})
    elif kind == "python" and _run_tests_goal_requested(goal):
        try:
            # the broker's cache is a DIFFERENT store with a different schema;
            # never let it overwrite the Perfect Algorithm's memory file
            if broker_memory_path_:
                runner_verdict = broker.broker(root_path, "run-tests",
                                               pathlib.Path(broker_memory_path_))
            else:
                runner_verdict = broker.broker(root_path, "run-tests")
        except Exception as e:  # honest refusal-by-name, never a silent PASS
            runner_verdict = {"verdict": f"REFUSE__BROKER_ERROR:{e}"}
        verdict = str((runner_verdict or {}).get("verdict") or "")
        if verdict.startswith("ENVIRONMENT_BROKERED"):
            source = KNOWN_BROKER
            _q("what runs/checks it", source, "broker",
               {"verdict": verdict,
                "from_memory": (runner_verdict or {}).get("from_memory"),
                "runner": (runner_verdict or {}).get("runner", {})})
        else:
            _q("what runs/checks it", UNKNOWN, "broker",
               {"verdict": verdict or "REFUSE__BROKER_NO_ANSWER"})
    else:
        seen = _guide_answer(goal, root_path, "what runs/checks this environment",
                            tools=tools, deadline_s=local_guide_deadline_s)
        if seen and seen.get("status") == "PASS__LOCAL_GUIDE_FOUND":
            _q("what runs/checks it", KNOWN_LOCAL_GUIDE, "local_guide",
               {"documents": seen.get("documents", [])[:3]})
        else:
            _q("what runs/checks it", UNKNOWN, "local_guide",
               {"reason": "no broker in contract and no guide answered"})

    # Q4: what counts as success / the contract?
    # (page mode already answered Q4 in the Q3 branch)
    if not page_mode:
        contract_seen = _guide_answer(goal, root_path, "what counts as success in this environment",
                                      tools=tools, deadline_s=local_guide_deadline_s)
        if contract_seen and contract_seen.get("status") == "PASS__LOCAL_GUIDE_FOUND":
            _q("what counts as success", KNOWN_LOCAL_GUIDE, "local_guide",
               {"documents": contract_seen.get("documents", [])[:3]})
        else:
            _q("what counts as success", UNKNOWN, "local_guide",
               {"reason": "no guide answered the contract question"})

    # ---- 4. gap-fill with web only when the caller opts in ----------
    if allow_web:
        gap_questions = [q["question"] for q in questions if q["status"] == UNKNOWN]
        if gap_questions:
            try:
                from canonical.runtime import jit_knowledge_v1 as jit
                for q_text in gap_questions:
                    try:
                        jit_out = jit.resolve(f"{q_text}: {goal[:160]}",
                                               limit=3, timeout=12)
                    except Exception:
                        continue
                    if jit_out.get("complete"):
                        for row in questions:
                            if row["question"] == q_text and row["status"] == UNKNOWN:
                                row["status"] = KNOWN_WEB
                                row["source"] = "web"
                                row["detail"] = {
                                    "authority": "EXTERNAL_PUBLIC_EVIDENCE_FETCHED",
                                    "document_count": jit_out.get("document_count"),
                                    "sources_answered": jit_out.get("sources_answered"),
                                    "kinds_answered": jit_out.get("kinds_answered"),
                                }
            except Exception:
                pass

    receipt["questions"] = questions

    if isinstance(known_priors, dict) and known_priors.get("model"):
        receipt["memory"]["prior_keys"] = sorted(known_priors["model"].keys())

    return _finish()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=None,
                        help="Environment directory to scan. Ignored when "
                             "--page-url is given.")
    parser.add_argument("--goal", required=True)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    parser.add_argument("--allow-web", action="store_true",
                        help="Allow the web tier to fill the gap (labeled external)")
    parser.add_argument("--memory", type=pathlib.Path, default=None,
                        help="Perfect Algorithm memory store to consult read-only")
    parser.add_argument("--broker-memory", type=pathlib.Path, default=None,
                        help="Broker cache path (Python run-tests contract only)")
    parser.add_argument("--tools", nargs="*", default=None,
                        help="Tools whose --help is read as guide (offline)")
    parser.add_argument("--page-url", default=None,
                        help="URL of a live page to scan instead of a filesystem "
                             "environment (http/https only)")
    args = parser.parse_args(argv)
    out = scan_and_know(args.root, args.goal, page_url=args.page_url,
                        memory_path_=args.memory,
                        broker_memory_path_=args.broker_memory,
                        allow_web=args.allow_web, tools=args.tools)
    text = json.dumps(out, indent=1, sort_keys=True)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if str(out.get("verdict", "")).startswith(("KNOWN__", "OPEN__")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
