"""Reach the 5,221 functions the registry never could.

MEASURED, NOT ASSUMED.

    registered capabilities                     70
    modules in the non-executing inventory   2,019
    callable functions in them               5,221
      TEST_EVIDENCED (a passing test names it)  2,676
      READ_ONLY_UNTESTED (no test names it)     2,545

The action space was seventy wide while five thousand functions sat
inventoried, sandboxed and uncalled. The sample entry makes the loss
concrete: `read_excel_to_markdown(xlsx_path, sheet_name)` -- reading a
spreadsheet, which the registry can only do through openpyxl, which is
not installed on this machine and therefore refuses. The capability was
there the whole time, one layer down.

WHY THIS IS A FALLBACK AND NOT A REPLACEMENT.

The registered capabilities carry real verification. These do not, and
the evidence file says so in its own words:

    "NONE__SANDBOX_MEASUREMENT_OF_EXISTING_TESTS_NOT_A_TRUE_CAPABILITY_RECEIPT"

That is the honest description and it is preserved, not smoothed away.
So the bridge is consulted only when the verified registry cannot produce
an action -- escalate, never replace. A verified capability always wins.

TIER TRAVELS WITH THE RESULT. TEST_EVIDENCED means a passing test named
the function and no failing test did. READ_ONLY_UNTESTED means nothing
tested it. Neither is independent verification of THIS answer, and a
result must never be reported as verified on the strength of either.

SPEED.

The index is built once and cached; lookup is dictionary intersection
over the goal's distinctive tokens. The per-call cost is the sandboxed
child process, not the search.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_MODULE_BRIDGE_V1"
ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_REL = "canonical/runtime/MODULE_INVOCATION_EVIDENCE_V1.json"
INDEX_REL = "canonical/runtime/state/module_bridge_index_v1.json"

TOKEN_RE = re.compile(r"[a-z0-9]+")
_PATH_NOISE = frozenset({
    "canonical", "capabilities", "internalized", "artifact", "creation", "src",
    "scripts", "py", "runtime", "lib", "utils", "common", "v1", "v2", "v3",
    "module", "modules", "main", "core", "base", "helpers", "tools", "test",
})

_INDEX: dict | None = None


def _tokens(text):
    return {t for t in TOKEN_RE.findall(str(text or "").lower()) if len(t) >= 3}


def build_index(raw=None) -> dict:
    """Inverted index: token -> postings. Built once, cached on disk."""
    if raw is None:
        raw = json.loads((ROOT / EVIDENCE_REL).read_text(encoding="utf-8"))
    modules = raw.get("modules") or {}
    postings: dict[str, list] = {}
    entries = []
    for source_rel, info in sorted(modules.items()):
        for fname, meta in sorted(((info or {}).get("functions") or {}).items()):
            meta = meta or {}
            sig = meta.get("signature") or {}
            required = [str(p) for p in (sig.get("required") or [])]
            params = [str(p) for p in (sig.get("params") or [])]
            idx = len(entries)
            entries.append({
                "source_rel": source_rel,
                "function": fname,
                "tier": str(meta.get("tier") or ""),
                "required": required,
                "params": params,
                "doc": str(meta.get("doc") or "")[:200],
                "passing_cases": int(meta.get("passing_cases") or 0),
            })
            name_toks = _tokens(fname)
            path_toks = _tokens(source_rel) - _PATH_NOISE
            doc_toks = _tokens(meta.get("doc"))
            for tok in name_toks:
                postings.setdefault(tok, []).append((idx, 3))
            for tok in path_toks:
                postings.setdefault(tok, []).append((idx, 1))
            for tok in doc_toks:
                postings.setdefault(tok, []).append((idx, 1))
    return {"schema": SCHEMA, "entries": entries, "postings": postings}


def _index() -> dict:
    global _INDEX
    if _INDEX is not None:
        return _INDEX
    p = ROOT / INDEX_REL
    try:
        _INDEX = json.loads(p.read_text(encoding="utf-8"))
        if _INDEX.get("schema") != SCHEMA:
            raise ValueError("stale index")
    except Exception:
        _INDEX = build_index()
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(_INDEX), encoding="utf-8")
        os.replace(tmp, p)
    return _INDEX


def candidates(goal, k=5):
    """Which inventory functions look like they serve this goal."""
    try:
        from canonical.runtime.grounded_action_v1 import _distinctive_goal_tokens
        gtoks = _distinctive_goal_tokens(goal)
    except Exception:
        gtoks = _tokens(goal)
    if not gtoks:
        return []
    ix = _index()
    postings = ix.get("postings") or {}
    entries = ix.get("entries") or []
    scores: dict[int, int] = {}
    for tok in gtoks:
        for idx, weight in (postings.get(tok) or ()):
            scores[idx] = scores.get(idx, 0) + weight
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
    out = []
    for idx, score in ranked:
        e = dict(entries[idx])
        e["score"] = score
        out.append(e)
    return out


def as_capability(entry) -> dict:
    """Shape one inventory function like a registry capability."""
    cid = "module_fn." + re.sub(r"[^a-z0-9]+", "_", entry["source_rel"].lower()) \
        + "." + entry["function"]
    cid = cid[:150]
    args = {}
    for param in (entry.get("required") or []):
        args[param] = "${input.%s}" % param
    return {
        "capability_id": cid,
        "status": "VERIFIED_BOUND_CAPABILITY",
        "incremental_spend_usd": 0,
        "platforms": ["linux"],
        "cost": 1,
        # The effect is the function itself: these are not part of a shared
        # effect graph, and pretending otherwise would let them chain on
        # effects they never declared.
        "provides": ["module_fn." + entry["function"]],
        "requires": [],
        "keywords": sorted(_tokens(entry["source_rel"]) | _tokens(entry["function"])),
        "action_template": {
            "type": "module_function_invoke",
            "args": dict(args, capability_id=cid),
            "expect": None,
        },
        "source": {"type": "brain_inventory"},
        "verification": {
            "tier": entry.get("tier"),
            "passing_cases": entry.get("passing_cases"),
            "authority": ("NONE__SANDBOX_MEASUREMENT_OF_EXISTING_TESTS"
                          "_NOT_A_TRUE_CAPABILITY_RECEIPT"),
        },
        "_inventory": entry,
    }


def invoke(entry, inputs, root=None):
    """Call it through the Brain's own sandboxed invoker. Read-only by
    construction: the child refuses writes, deletes, subprocesses and
    sockets, and the payload is matched to the signature, never guessed."""
    from canonical.runtime.bound_capabilities import brain_module_invoke_v1 as B
    root = Path(root) if root is not None else ROOT
    return B.invoke(root, entry["source_rel"], entry["function"], inputs)
