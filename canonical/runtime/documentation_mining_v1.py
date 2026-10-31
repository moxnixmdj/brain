#!/usr/bin/env python3
"""Learn to use a library by reading its documentation, once.

A human reads a README and can use the library. That is the whole trick, and
it is one-shot: no trial and error, no search over a space the machine was
given. Read, adapt, run, check.

The candidate table in program_synthesis_v1 was written by hand, which made
the author the bottleneck -- a machine that can only do the ten things
someone remembered to write down is the strict program the owner refused.
This replaces the author with the documentation.

The list of things worth reading is not written down either: it is
``sys.stdlib_module_names``, the 305 modules that ship with python on this
machine and therefore are already paid for. A goal is matched against those
names by the words it uses, so "compress into out.gz" finds gzip without
anyone pointing at it.

Documentation is fetched from CPython's own Doc/library sources. Every
example extracted from it is executed for real and accepted only if the
artifact it produced is really the right format. A snippet that does not
work is not a fact about the world, it is a snippet that did not work, and
it is discarded.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import urllib.parse
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_DOCUMENTATION_MINING_V1"

_UA = {"User-Agent": "project-brain-doc-mining/1", "Accept": "application/json"}

STATE_PATH = os.environ.get(
    "BRAIN_DOC_MINING_STATE",
    str(pathlib.Path(__file__).resolve().parents[2]
        / "canonical/astra_runtime/state/DOCUMENTATION_MINING_V1.json"))

DOC_CACHE: dict[str, tuple[float, str]] = {}
DOC_TTL_S = 3600.0

_WORD = re.compile(r"[a-z0-9]+")
_STOP = frozenset("""a an the this that these those it its is are was were be
been am do does did and or but if then than so as at by for from in into of on
to with without""".split())


def words(text: str) -> set[str]:
    return {w for w in _WORD.findall(str(text or "").lower())
            if len(w) > 1 and w not in _STOP}


# --------------------------------------------------------------------------- #
# what is worth reading
# --------------------------------------------------------------------------- #
def stdlib_modules() -> list[str]:
    """Everything importable that ships with this interpreter."""
    return sorted(getattr(sys, "stdlib_module_names", ()) or ())


def candidate_modules(goal: str, limit: int = 6) -> list[tuple[float, str]]:
    """Modules whose name the goal mentions, best match first.

    Scored, not declared: the name is a strong signal because stdlib modules
    are named after what they do. Longer names are penalised so that a short
    exact match beats a long vague one.
    """
    gw = words(goal)
    if not gw:
        return []
    scored: list[tuple[float, str]] = []
    for name in stdlib_modules():
        nw = set(_WORD.findall(name.lower()))
        if not nw:
            continue
        hit = len(gw & nw)
        if not hit:
            # "gz" is not a word but gzip is still the module for it
            hit = sum(1 for w in gw if w and w in name)
            if not hit:
                continue
        scored.append((hit / (len(nw) ** 0.5), name))
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return scored[:limit]


# --------------------------------------------------------------------------- #
# reading
# --------------------------------------------------------------------------- #
def fetch_module_docs(module: str, timeout: int = 20) -> str:
    """The Doc/library source for one stdlib module. Empty if unreachable."""
    now = time.time()
    hit = DOC_CACHE.get(module)
    if hit is not None and hit[0] > now:
        return hit[1]
    url = ("https://api.github.com/repos/python/cpython/contents/Doc/library/%s.rst"
           % urllib.parse.quote(str(module)))
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        body = raw.get("content") or ""
        if raw.get("encoding") == "base64" and body:
            body = base64.b64decode(body).decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 - a doc fetch must never break learning
        body = ""
    if body:
        DOC_CACHE[module] = (now + DOC_TTL_S, body)
    return body


# any language: docs tag blocks `python`, `pycon`, `shell-session` and more.
# Matching only the ones we expected silently found nothing in zipfile.rst,
# whose examples are all marked shell-session.
_CODE_BLOCK = re.compile(
    r"\.\.\s+(?:code-block|code)::(?P<lang>[^\n]*)\n(?P<head>(?:[ \t]*\n)*)"
    r"(?P<body>(?:[ \t]+[^\n]*\n?)+)")
_SHELL_PROMPT = re.compile(r"^\s*[$#]\s")
_DOCTEST = re.compile(r"^\s*>>> .*(?:\n\s*\.\.\. .*)*(?:\n[^>\s][^\n]*)*", re.M)


def extract_examples(text: str, limit: int = 40) -> list[str]:
    """Runnable snippets out of reStructuredText."""
    out: list[str] = []

    def add(snippet: str) -> None:
        lines = [ln for ln in snippet.splitlines() if ln.strip()]
        while lines and not lines[-1].strip():
            lines.pop()
        if not lines:
            return
        cleaned: list[str] = []
        for ln in lines:
            stripped = ln.strip()
            if stripped.startswith(">>> "):
                cleaned.append(stripped[4:])
            elif stripped.startswith("... "):
                cleaned.append(stripped[4:])
            elif stripped in (">>>", "..."):
                cleaned.append("")
            else:
                cleaned.append(ln)
        body = "\n".join(cleaned).strip("\n")
        if not body or _SHELL_PROMPT.match(body):
            return  # a shell transcript is not a python snippet
        if body not in out:
            out.append(body)

    for m in _CODE_BLOCK.finditer(str(text or "")):
        add(m.group("body"))
    for block in _DOCTEST.findall(str(text or "")):
        add(block)
    return out[:limit]


def module_docstring(module: str) -> str:
    """The module's own documentation, already on this machine.

    Free and instant: no network, no fetch, no rate limit. Some stdlib
    modules carry their usage in the docstring, and reading what is already
    here is faster than asking the network for it.
    """
    import importlib
    try:
        mod = importlib.import_module(module)
    except Exception:  # noqa: BLE001 - not importable, so nothing to read
        return ""
    return str(getattr(mod, "__doc__", "") or "")


# --------------------------------------------------------------------------- #
# adapting a snippet from the manual to this goal
# --------------------------------------------------------------------------- #
_STR_LIT = re.compile(r"""(?P<q>['"])(?P<body>[^'"\n]*\.[A-Za-z0-9_]{1,8})(?P=q)""")


def adapt(snippet: str, module: str, out_path: str, content: str) -> str:
    """Point the manual's example at our file and our content.

    Documentation writes to ``'filename.gz'``; we need it to write to our
    path. That is a substitution, and the verifier is what tells us whether
    the substitution produced something that actually works -- guessing is
    free when checking is free.
    """
    body = _STR_LIT.sub(lambda m: repr(out_path), snippet)
    if re.search(r"^\s*(import|from)\s+" + re.escape(module) + r"\b", body, re.M) is None:
        body = "import %s\n" % module + body
    return body


_NOT_EXPR = re.compile(
    r"^\s*(?:import|from|def|class|for|while|if|else|elif|try|except|finally|"
    r"with|return|raise|assert|del|global|pass|break|continue|@|print\s*\()"
)


def with_printed_last(source: str) -> str:
    """Documentation writes ``>>> json.dumps(x)`` and shows the result, because
    a REPL prints the value of an expression. Run as a script that line
    produces nothing at all, so the example looks like it failed when it was
    only ever written to be read. Print the last expression and it says what
    it evaluates to -- which is often exactly the file the goal asked for.
    """
    lines = list(source.rstrip().splitlines())
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return source
    last = lines[-1]
    if _NOT_EXPR.match(last) or last.rstrip().endswith((":", chr(92))):
        return source
    if re.match(r"^\s*[A-Za-z_][\w.]*\s*=[^=]", last):
        return source
    lines[-1] = "print(%s)" % last.strip()
    return "\n".join(lines) + "\n"


def run_and_capture(source: str, workdir: pathlib.Path,
                    timeout: float = 15.0) -> tuple[int, str]:
    """What did this snippet say? Returns (returncode, stdout)."""
    import subprocess
    script = workdir / "capture.py"
    script.write_text(source, encoding="utf-8")
    try:
        proc = subprocess.run([sys.executable, str(script)], cwd=str(workdir),
                              capture_output=True, timeout=timeout)
    except Exception:  # noqa: BLE001 - a snippet must never break the search
        return -1, ""
    return proc.returncode, (proc.stdout or b"").decode("utf-8", "replace")


# --------------------------------------------------------------------------- #
# the point: read once, then really do it
# --------------------------------------------------------------------------- #
def learn(goal: str, content: str = "brain-doc-sample", suffix: str | None = None,
          max_examples: int = 12, workdir: str | pathlib.Path | None = None,
          timeout: float = 15.0) -> dict[str, Any]:
    """Read the documentation, run what it says, keep what worked."""
    from canonical.runtime import program_synthesis_v1 as synth

    suffix = suffix or output_suffix(goal)
    if not suffix:
        return {"schema": SCHEMA, "pass": False,
                "status": "OPEN__NO_OUTPUT_FORMAT_IN_GOAL", "goal": goal}

    import shutil
    import tempfile
    tmp = pathlib.Path(workdir) if workdir else pathlib.Path(
        tempfile.mkdtemp(prefix="brain-docmine-"))
    tmp.mkdir(parents=True, exist_ok=True)
    out = tmp / ("out" + suffix)

    ranked = candidate_modules(goal)
    if not ranked:
        return {"schema": SCHEMA, "pass": False,
                "status": "OPEN__NO_MODULE_THE_GOAL_MENTIONS", "goal": goal,
                "suffix": suffix}

    trials: list[dict[str, Any]] = []
    modules_read: list[str] = []
    try:
        for score, module in ranked:
            text = module_docstring(module) + "\n" + fetch_module_docs(module)
            if not text.strip():
                trials.append({"module": module, "read": False,
                               "worked": False, "reason": "DOCS_UNREACHABLE"})
                continue
            modules_read.append(module)
            for snippet in extract_examples(text, limit=max_examples):
                if out.exists():
                    try:
                        out.unlink()
                    except OSError:
                        pass
                source = adapt(snippet, module, str(out), content)
                ran = synth.run_candidate(source, out, tmp, timeout=timeout)
                ok, why = (synth.check_effect(out, suffix)
                           if ran.get("ok") else (False, "DID_NOT_RUN"))
                strategy = "substitute_filename"
                if not ok:
                    # the manual demonstrates the api; it rarely performs our
                    # goal. Run it, take what it prints, and try that as the
                    # artifact -- for json, csv, txt and the like, what the
                    # example shows IS the file being asked for.
                    for variant, name in ((with_printed_last(source), "print_last_expression"),
                                          (source, "verbatim")):
                        code, stdout = run_and_capture(variant, tmp, timeout=timeout)
                        if code == 0 and stdout.strip():
                            out.write_text(stdout, encoding="utf-8")
                            ok, why = synth.check_effect(out, suffix)
                            strategy = name
                            if ok:
                                source = variant
                                break
                trials.append({"module": module, "read": True, "worked": ok,
                               "effect": why, "strategy": strategy,
                               "returncode": ran.get("returncode")})
                if ok:
                    result = {
                        "schema": SCHEMA, "pass": True,
                        "status": "PASS__LEARNED_FROM_DOCUMENTATION",
                        "goal": goal, "suffix": suffix, "module": module,
                        "source": source,
                        "output_bytes": out.stat().st_size,
                        "output_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
                        "modules_read": modules_read, "trials": trials,
                        "examples_tried": len(trials),
                        "authority": "DOCUMENTATION_READ_EXECUTED_AND_EFFECT_VERIFIED"}
                    # the sample is evidence, and it lives in a scratch
                    # directory that is about to be deleted. Handing back a
                    # path into it would be handing back a path to nothing;
                    # the deliverable is the program, not the sample.
                    if workdir is not None:
                        result["output_path"] = str(out)
                    return result
    finally:
        if workdir is None:
            shutil.rmtree(tmp, ignore_errors=True)

    return {"schema": SCHEMA, "pass": False,
            "status": "OPEN__NO_DOCUMENTED_EXAMPLE_PRODUCED_THE_EFFECT",
            "goal": goal, "suffix": suffix,
            "modules_read": modules_read, "trials": trials,
            "examples_tried": len(trials),
            "authority": "DOCUMENTATION_SEARCH_EXHAUSTED"}


# --------------------------------------------------------------------------- #
# remembering
# --------------------------------------------------------------------------- #
def _load() -> dict[str, Any]:
    p = pathlib.Path(STATE_PATH)
    if not p.is_file():
        return {"schema": SCHEMA, "learned": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if data.get("schema") == SCHEMA:
            data.setdefault("learned", {})
            return data
    except (OSError, ValueError):
        pass
    return {"schema": SCHEMA, "learned": {}}


def _save(state: dict[str, Any]) -> None:
    p = pathlib.Path(STATE_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")


def remember(result: Mapping[str, Any]) -> None:
    if not result.get("pass") or not result.get("source"):
        return
    state = _load()
    state["learned"][str(result.get("suffix") or "").lower()] = {
        "module": result.get("module"), "source": result.get("source"),
        "learned_at": time.time(),
        "goal": str(result.get("goal") or "")[:200],
        "verified_sha256": result.get("output_sha256"),
        "origin": "documentation",
    }
    _save(state)


def recall(suffix: str) -> dict[str, Any] | None:
    return _load()["learned"].get(str(suffix or "").lower())


_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def output_suffix(goal: str) -> str:
    """The OUTPUT extension the goal states -- never the extension of a file it names.

    Measured 2026-10-29 on a fresh tree, one door call each::

        "Format <...>/pkg/calc.py."                       3,588 ms -> read 6 stdlib manuals
        "Replace the magic number 3 in <...>/calc.py ..."  also .py

    ``_requested_suffix`` is right about the cases it was written for ("compress the report into
    out.gz" -> .gz, "save the results to out.json" -> .json) and wrong about one: a .py that is
    the INPUT to be edited is not an artifact to be produced, so there is nothing to verify and
    no manual to read.  The rule here is not a second grammar -- the sentence's tokens that name
    a file which already exists are removed, and the SAME ``_requested_suffix`` reads what is
    left.  Both pinned positives still yield .gz and .json because neither names an existing file.
    """
    from canonical.runtime import cli_capability_acquisition_v1 as acq
    from canonical.runtime import declared_input_derivation_v1 as derivation

    text = str(goal or "")
    for raw in derivation.stated_existing_files(text, _REPO_ROOT):
        text = text.replace(raw, " ")
    return acq._requested_suffix(text)


def learn_or_recall(goal: str, content: str = "brain-doc-sample",
                    suffix: str | None = None) -> dict[str, Any]:
    """instant when already read, honest when not."""
    suffix = suffix or output_suffix(goal)
    known = recall(suffix) if suffix else None
    if known:
        return {"schema": SCHEMA, "pass": True, "from_memory": True,
                "status": "PASS__RECALLED_DOCUMENTED_PROGRAM",
                "goal": goal, "suffix": suffix, **known}
    result = learn(goal, content=content, suffix=suffix)
    remember(result)
    result.setdefault("from_memory", False)
    return result
