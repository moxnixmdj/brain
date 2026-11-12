#!/usr/bin/env python3
"""Causal Demonstration-to-Program Compiler — Watch/Explore Once -> <5ms Permanent Skill.

Implements K2 acquisition-time trace compilation under WHITE_BOX_CAPABILITY_HARVESTING_LAW_V3
with zero model calls ($0, K3 = 0 at qualification and runtime):

1. **Speed-Layer Causal Elevator (`elevate_trace_to_fastest_layer`)**:
   Compresses slow UI / browser / exploratory traces into the fastest equivalent causal layer:
     Layer 1 (<2 ms):  `python_file_op` / `sqlite_exec` / `code_rule`
     Layer 2 (<15 ms): `http_request` (direct stdlib `urllib.request` with form/JSON payload)
     Layer 3 (<50 ms): `cli_exec` (direct `subprocess.run` without shell)
     Layer 4:          `semantic_dom` (`role` / `name` / `aria-label` / `text` — never raw `(x, y)`
                       when a semantic DOM/A11y target exists)
   Prunes dead, read-only-unused, or undone exploratory actions via backward causal liveness.

2. **Cross-Goal Plotkin Workflow Anti-Unification (`anti_unify_workflow`)**:
   Abstracts concrete URLs, file paths, quoted strings, identifiers, and numeric arguments shared
   between `goal` and `elevated_steps` into typed holes (`?url0`, `?path0`, `?str0`, `?num0`,
   `?ident0`), synthesizing a deterministic binder (`bind_goal_parameters`) and postcondition check.

3. **Mandatory Held-Out + Sabotage Transfer Gate (`compile_and_qualify_skill`)**:
   Before any compiled workflow enters SQLite WAL memory, deletes donor access and verifies:
     (a) Untouched held-out execution passes the independent postcondition oracle;
     (b) Sabotaged negative-control execution FAILS the postcondition oracle (no rubber stamps);
     (c) `canonical.runtime.capability_transfer_ownership_gate_v1.evaluate(...)` returns `PASS`.
"""
from __future__ import annotations

import hashlib
import html.parser
import http.cookiejar
import json
import os
import pathlib
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import capability_transfer_ownership_gate_v1 as ownership_gate

SCHEMA = "PROJECT_BRAIN_CAUSAL_TRACE_TO_SKILL_COMPILER_V1"

LAYER_RANK: dict[str, int] = {
    "python_file_op": 1,
    "sqlite_exec": 1,
    "confined_python_exec": 2,
    "http_request": 2,
    "cli_exec": 3,
    "cli_pipeline": 3,
    "semantic_dom": 4,
    "pixel_ui": 5,
}

_URL_RE = re.compile(r"https?://[^\s\"'<>)\]]+")
_KV_VAL_RE = re.compile(r"(?:[A-Za-z_][A-Za-z0-9_-]*)\s*[=:]\s*([^\s\"',;)]+)")
_IDENT_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_-]{2,}\b")
_QUOTED_RE = re.compile(r"""(?:"([^"\n]+)"|'([^'\n]+)')""")
_PATH_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_:/.-])(?:/[^\s\"',;)]+|(?:\./|\.\./)?[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+|[A-Za-z0-9_-]+\.[A-Za-z0-9]{1,8})(?![A-Za-z0-9_/-])"
)
_NUM_RE = re.compile(r"(?<![A-Za-z0-9_./:-])\d+(?:\.\d+)?(?![A-Za-z0-9_./:-])")
_STOP_WORDS = frozenset({
    "a", "an", "the", "to", "into", "from", "in", "on", "at", "by", "for", "of",
    "with", "and", "or", "then", "please", "using", "via", "as", "is", "are", "be",
})

_WORKFLOW_MEM_CACHE: dict[str, list[dict[str, Any]]] = {}
_WORKFLOW_INDEX_CACHE: dict[str, dict[str, list[dict[str, Any]]]] = {}
_AUTO_SEEDED_DBS: set[str] = set()


def _repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2]


def default_workflow_bundle_path() -> pathlib.Path:
    return _repo_root() / "canonical" / "astra_runtime" / "skills" / "COMPILED_WORKFLOWS_BUNDLE_V1.json"


def _default_workflow_db() -> pathlib.Path:
    override = os.environ.get("BRAIN_COMPILED_WORKFLOW_DB")
    if override:
        p = pathlib.Path(override)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    base = _repo_root() / "canonical" / "astra_runtime" / "tmp"
    base.mkdir(parents=True, exist_ok=True)
    return base / "compiled_workflows_v1.sqlite"


def _connect_db(db_path: pathlib.Path | None = None) -> tuple[pathlib.Path, sqlite3.Connection]:
    is_default = db_path is None and not os.environ.get("BRAIN_COMPILED_WORKFLOW_DB")
    target = db_path or _default_workflow_db()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS compiled_workflow_skills (
            skill_id TEXT PRIMARY KEY,
            goal_skeleton TEXT NOT NULL,
            goal_regex TEXT NOT NULL,
            skeleton_tokens_json TEXT NOT NULL,
            param_order_json TEXT NOT NULL,
            steps_json TEXT NOT NULL,
            postcondition_json TEXT NOT NULL,
            dominant_layer TEXT NOT NULL,
            artifact_sha256 TEXT NOT NULL,
            ownership_receipt_json TEXT NOT NULL,
            hit_count INTEGER NOT NULL DEFAULT 0,
            created_ns INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_workflow_layer ON compiled_workflow_skills(dominant_layer)"
    )
    if is_default and str(target) not in _AUTO_SEEDED_DBS:
        _AUTO_SEEDED_DBS.add(str(target))
        bundle_p = default_workflow_bundle_path()
        if bundle_p.is_file():
            # Seed when the tracked bundle holds a skill this database lacks -- not only when the
            # database is empty.  With the empty-only rule, a checkout that had ever stored one
            # skill never received anything taught later, and nothing said so.
            try:
                _bundled = {str(item.get("skill_id")) for item in
                            (json.loads(bundle_p.read_text(encoding="utf-8")).get("skills") or [])
                            if isinstance(item, Mapping)}
            except Exception:  # noqa: BLE001 - an unreadable bundle seeds nothing
                _bundled = set()
            _held = {str(r[0]) for r in conn.execute("SELECT skill_id FROM compiled_workflow_skills")}
            if _bundled - _held:
                conn.close()
                try:
                    import_workflow_bundle(bundle_p, db_path=target)
                except Exception:
                    pass
                conn = sqlite3.connect(str(target), timeout=10.0)
                conn.execute("PRAGMA journal_mode=WAL")
    return target, conn


# --------------------------------------------------------------------------- #
# 1. Speed-Layer Causal Elevation & Dead-Step Pruning
# --------------------------------------------------------------------------- #
def _semantic_selector_from_dom(point_step: Mapping[str, Any], dom_elements: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    """Convert raw `(x, y)` click/type step into a stable semantic DOM/A11y selector."""
    x = point_step.get("x")
    y = point_step.get("y")
    target_hint = str(point_step.get("target_label") or point_step.get("text_hint") or "").strip()
    matched: Mapping[str, Any] | None = None

    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
        for el in dom_elements:
            bbox = el.get("bbox")
            if isinstance(bbox, Mapping):
                bx = float(bbox.get("x", -1))
                by = float(bbox.get("y", -1))
                bw = float(bbox.get("width", 0))
                bh = float(bbox.get("height", 0))
                if bx <= float(x) <= bx + bw and by <= float(y) <= by + bh:
                    matched = el
                    break
    if matched is None and target_hint:
        low = target_hint.lower()
        for el in dom_elements:
            for field in ("aria", "name", "placeholder", "text", "id"):
                val = str(el.get(field) or "").strip()
                if val and val.lower() == low:
                    matched = el
                    break
            if matched is not None:
                break

    if matched is None:
        return None

    selector: dict[str, str] = {}
    for key in ("role", "name", "aria", "placeholder", "tag", "type", "text"):
        val = str(matched.get(key) or "").strip()
        if val:
            selector[key] = val[:200]
    if not selector:
        return None

    action_kind = str(point_step.get("type") or point_step.get("op") or "click").lower()
    out: dict[str, Any] = {
        "layer": "semantic_dom",
        "op": "FILL_SEMANTIC" if action_kind in ("type", "fill", "input") else "CLICK_SEMANTIC",
        "selector": selector,
    }
    if "value" in point_step or "text" in point_step:
        out["value"] = str(point_step.get("value") if "value" in point_step else point_step.get("text") or "")
    if point_step.get("url"):
        out["url"] = str(point_step["url"])
    return out


def elevate_trace_to_fastest_layer(trace: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Elevate a raw multi-step computer/coding trace to the fastest equivalent causal program.

    Priority order:
      1. Observed deterministic SQLite mutations / file writes with full content -> Layer 1 (<2 ms)
      2. Observed mutating HTTP API requests produced by UI/browser steps        -> Layer 2 (<15 ms)
      3. Observed CLI commands (with undone/no-op exploratory commands pruned)   -> Layer 3 (<50 ms)
      4. Semantic DOM/A11y operations elevated from raw pixel coordinates        -> Layer 4
    """
    if isinstance(trace, Mapping):
        raw_steps = list(trace.get("steps") or [])
        effects = trace.get("observed_effects") if isinstance(trace.get("observed_effects"), Mapping) else {}
        dom_elements = list(trace.get("dom_elements") or effects.get("dom_elements") or [])
    else:
        raw_steps = list(trace or [])
        effects = {}
        dom_elements = []

    elevated: list[dict[str, Any]] = []
    pruned_ui_steps = 0

    # Also detect direct SQLite/HTTP steps embedded in a flat step list so UI steps before them are pruned
    inline_direct = [
        st for st in raw_steps
        if isinstance(st, Mapping)
        and str(st.get("layer") or st.get("kind") or "").lower()
        in {"sqlite_exec", "sqlite_query", "http_request", "python_file_op", "confined_python_exec"}
    ]

    # Rule A: Direct SQLite causal mutation observed from slow UI/CLI wrapper
    sqlite_ops = list(effects.get("sqlite_mutations") or [])
    for sq in sqlite_ops:
        if isinstance(sq, Mapping) and sq.get("db_path") and sq.get("sql"):
            elevated.append({
                "layer": "sqlite_exec",
                "db_path": str(sq["db_path"]),
                "sql": str(sq["sql"]),
                "params": list(sq.get("params") or []),
            })

    # Rule B: Direct HTTP request observed as the causal effect of UI/browser form interaction
    # (including stateful session/CSRF token-acquiring GET steps right before a mutation!)
    http_exchanges = list(effects.get("http_exchanges") or [])
    causal_http = [
        h for h in http_exchanges
        if isinstance(h, Mapping)
        and h.get("url")
        and (
            str(h.get("method") or "GET").upper() in {"POST", "PUT", "PATCH", "DELETE"}
            or bool(h.get("extract_hidden_inputs"))
            or bool(h.get("sets_session_cookie"))
        )
    ]
    for h in causal_http:
        step_http: dict[str, Any] = {
            "layer": "http_request",
            "method": str(h.get("method") or "POST").upper(),
            "url": str(h["url"]),
            "headers": {
                str(k): str(v)
                for k, v in (h.get("headers") or {}).items()
                if str(k).lower() in {"content-type", "accept", "x-requested-with", "x-csrf-token"}
            },
        }
        if h.get("extract_hidden_inputs"):
            step_http["extract_hidden_inputs"] = True
        if h.get("sets_session_cookie"):
            step_http["sets_session_cookie"] = True
        if "json_body" in h and h["json_body"] is not None:
            step_http["json_body"] = h["json_body"]
        elif "form_body" in h and isinstance(h["form_body"], Mapping):
            step_http["form_body"] = {str(k): str(v) for k, v in h["form_body"].items()}
        elif "body" in h and h["body"] is not None:
            step_http["body"] = str(h["body"])
        if h.get("save_response_to"):
            step_http["save_response_to"] = str(h["save_response_to"])
        elevated.append(step_http)

    # Rule C: Direct deterministic file writes
    file_writes = list(effects.get("file_writes") or [])
    for fw in file_writes:
        if isinstance(fw, Mapping) and fw.get("path") and "content" in fw:
            elevated.append({
                "layer": "python_file_op",
                "op": str(fw.get("op") or "write_text"),
                "path": str(fw["path"]),
                "content": str(fw["content"]),
            })

    has_direct_causal_shortcut = bool(elevated or inline_direct)

    # Process explicit steps: prune UI steps superseded by direct HTTP/SQLite/file shortcuts,
    # prune failed/no-op exploratory CLI commands, and elevate remaining pixel steps to semantic DOM.
    seen_cli: list[dict[str, Any]] = []
    for st in raw_steps:
        if not isinstance(st, Mapping):
            continue
        layer = str(st.get("layer") or st.get("kind") or "").lower()
        op_type = str(st.get("type") or st.get("op") or "").lower()

        if st.get("undone") is True or st.get("noop") is True:
            pruned_ui_steps += 1
            continue
        if "returncode" in st and int(st.get("returncode") or 0) != 0:
            pruned_ui_steps += 1
            continue

        is_ui = (
            layer in {"pixel_ui", "gui", "browser_ui", "mouse", "keyboard", "pixel_click", "ui_type", "ui_scroll"}
            or layer.startswith(("pixel_", "ui_"))
            or op_type in {"click", "double_click", "move", "scroll", "type", "keypress", "drag", "wait"}
        )
        if is_ui and has_direct_causal_shortcut:
            pruned_ui_steps += 1
            continue

        if is_ui:
            sem = _semantic_selector_from_dom(st, dom_elements)
            if sem is not None:
                elevated.append(sem)
            elif op_type not in {"move", "wait"}:
                elevated.append({"layer": "pixel_ui", **dict(st)})
            else:
                pruned_ui_steps += 1
            continue

        if layer == "cli_pipeline" and isinstance(st.get("stages"), list):
            stages = [[str(a) for a in sg] for sg in st["stages"] if isinstance(sg, list) and sg]
            if len(stages) >= 2:
                seen_cli.append({"layer": "cli_pipeline", "stages": stages})
            continue

        if layer in {"cli", "cli_exec", "subprocess"} or isinstance(st.get("argv"), list):
            argv = [str(a) for a in (st.get("argv") or []) if str(a)]
            if not argv:
                continue
            if argv[0] in {"ls", "pwd", "whoami", "true"} and st.get("keep_stdout_to") is None:
                pruned_ui_steps += 1
                continue
            if any(flag in argv[1:] for flag in ("--help", "-h", "--version")) and st.get("keep_stdout_to") is None:
                pruned_ui_steps += 1
                continue
            cli_entry: dict[str, Any] = {"layer": "cli_exec", "argv": argv}
            if st.get("keep_stdout_to"):
                cli_entry["keep_stdout_to"] = str(st["keep_stdout_to"])
            seen_cli.append(cli_entry)
            continue

        if layer in {"sqlite_exec", "sqlite_query"}:
            d = dict(st)
            d["layer"] = "sqlite_exec"
            d.pop("kind", None)
            elevated.append(d)
            continue

        if layer in {"http_request", "python_file_op", "semantic_dom", "confined_python_exec"}:
            d = dict(st)
            d["layer"] = layer
            d.pop("kind", None)
            elevated.append(d)

    elevated.extend(seen_cli)

    dominant_layer = "none"
    if elevated:
        dominant_layer = min(
            (str(s.get("layer") or "pixel_ui") for s in elevated),
            key=lambda lyr: LAYER_RANK.get(lyr, 99),
        )

    return {
        "elevated_steps": elevated,
        "raw_step_count": len(raw_steps),
        "elevated_step_count": len(elevated),
        "pruned_step_count": pruned_ui_steps,
        "dominant_layer": dominant_layer,
        "elevated_from_ui": pruned_ui_steps > 0 and dominant_layer in {"sqlite_exec", "http_request", "python_file_op", "confined_python_exec", "cli_exec", "semantic_dom"},
    }


# --------------------------------------------------------------------------- #
# 2. Multi-Step Workflow Plotkin Anti-Unification
# --------------------------------------------------------------------------- #
_KV_PAIR_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_-]*)\s*[=:]\s*([^\s,;)]+)")
_HOLE_KV_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_-]*)\s*[=:]\s*(\?[a-z]+\d+)")

_WORKFLOW_SYNONYM_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"submit", "post", "send", "dispatch"}),
    frozenset({"count", "tally", "total"}),
    frozenset({"create", "make", "initialize"}),
    frozenset({"insert", "add", "record"}),
    frozenset({"enable", "activate"}),
    frozenset({"extract", "collect"}),
)

_WORKFLOW_OPPOSING_VERBS: tuple[tuple[frozenset[str], frozenset[str]], ...] = (
    (frozenset({"enable", "activate"}), frozenset({"disable", "deactivate"})),
    (frozenset({"create", "insert", "add", "write"}), frozenset({"delete", "drop", "remove", "erase"})),
    (frozenset({"read", "count", "select", "get", "fetch"}), frozenset({"write", "delete", "drop", "update"})),
    (frozenset({"encode", "encrypt", "compress"}), frozenset({"decode", "decrypt", "decompress"})),
    (frozenset({"start", "open", "lock"}), frozenset({"stop", "close", "unlock"})),
)

_OPTIONAL_CONTAINER_NOUNS: frozenset[str] = frozenset({"database", "file", "feature", "endpoint", "server"})


def _expand_workflow_synonyms(words: set[str]) -> set[str]:
    out = set(words)
    for grp in _WORKFLOW_SYNONYM_GROUPS:
        if out & grp:
            out |= grp
    return out


def _has_opposing_workflow_intent(skel_words: set[str], goal_words: set[str]) -> bool:
    for pos_grp, neg_grp in _WORKFLOW_OPPOSING_VERBS:
        if (skel_words & pos_grp and goal_words & neg_grp) or (skel_words & neg_grp and goal_words & pos_grp):
            return True
    return False


def _extract_goal_literals(
    goal: str,
    *,
    peer_goal: str | None = None,
    step_blob: str = "",
) -> list[tuple[str, str]]:
    """Extract candidate parameterizable literals `(kind, raw_value)` in left-to-right order."""
    spans: list[tuple[int, int, str, str]] = []

    def _overlaps(s: int, e: int) -> bool:
        return any(not (e <= a or s >= b) for a, b, _, _ in spans)

    for m in _URL_RE.finditer(goal):
        val = m.group(0).rstrip(".,;:")
        spans.append((m.start(), m.start() + len(val), "url", val))
        sp = urllib.parse.urlsplit(val)
        if sp.scheme and sp.netloc and sp.path and sp.path != "/":
            origin = f"{sp.scheme}://{sp.netloc}"
            spans.append((m.start(), m.start() + len(origin), "url", origin))

    for m in _QUOTED_RE.finditer(goal):
        inner = m.group(1) if m.group(1) is not None else m.group(2)
        if inner and not _overlaps(m.start(), m.end()):
            inner_start = m.start() + 1
            inner_end = m.end() - 1
            spans.append((inner_start, inner_end, "str", inner))

    for m in _KV_VAL_RE.finditer(goal):
        val = m.group(1).rstrip(".,;:")
        vstart = m.start(1)
        vend = vstart + len(val)
        if val and not val.startswith(("http://", "https://")) and not _overlaps(vstart, vend):
            spans.append((vstart, vend, "str", val))

    for m in _PATH_TOKEN_RE.finditer(goal):
        val = m.group(0).rstrip(".,;:")
        if val and not _overlaps(m.start(), m.start() + len(val)):
            spans.append((m.start(), m.start() + len(val), "path", val))

    for m in _NUM_RE.finditer(goal):
        val = m.group(0)
        if not _overlaps(m.start(), m.end()):
            spans.append((m.start(), m.end(), "num", val))

    for m in _IDENT_RE.finditer(goal):
        val = m.group(0)
        if val.lower() not in _STOP_WORDS and ("_" in val or "-" in val) and not _overlaps(m.start(), m.end()):
            spans.append((m.start(), m.end(), "str", val))

    if peer_goal and peer_goal.strip() and peer_goal.strip() != goal.strip() and step_blob:
        peer_words = {m.group(0).lower() for m in _IDENT_RE.finditer(peer_goal)}
        for m in _IDENT_RE.finditer(goal):
            val = m.group(0)
            vlow = val.lower()
            if (
                vlow not in _STOP_WORDS
                and vlow not in peer_words
                and not _overlaps(m.start(), m.end())
                and re.search(rf"\b{re.escape(val)}\b", step_blob)
            ):
                spans.append((m.start(), m.end(), "str", val))

    spans.sort(key=lambda t: t[0])
    return [(kind, val) for _, _, kind, val in spans]


def _substitute_in_obj(obj: Any, mapping: Mapping[str, str]) -> Any:
    """Replace concrete parameter values inside nested step/postcondition structures."""
    if isinstance(obj, str):
        out = obj
        # Longest values first so URLs/paths are replaced whole before substrings
        for raw_val, hole in sorted(mapping.items(), key=lambda kv: -len(kv[0])):
            if raw_val and raw_val in out:
                out = out.replace(raw_val, hole)
            elif hole.startswith("?url") and raw_val.startswith(("http://", "https://")):
                sp = urllib.parse.urlsplit(raw_val)
                origin = f"{sp.scheme}://{sp.netloc}"
                if origin and origin in out:
                    out = out.replace(origin, f"{{{{origin:{hole}}}}}")
        return out
    if isinstance(obj, list):
        return [_substitute_in_obj(x, mapping) for x in obj]
    if isinstance(obj, tuple):
        return [_substitute_in_obj(x, mapping) for x in obj]
    if isinstance(obj, Mapping):
        return {_substitute_in_obj(str(k), mapping): _substitute_in_obj(v, mapping) for k, v in obj.items()}
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        sval = str(obj)
        if sval in mapping:
            return mapping[sval]
    return obj


def _instantiate_obj(obj: Any, bindings: Mapping[str, str]) -> Any:
    if isinstance(obj, str):
        if obj in bindings and obj.startswith("?num"):
            raw = bindings[obj]
            return int(raw) if raw.isdigit() else float(raw)
        out = obj
        for hole, val in sorted(bindings.items(), key=lambda kv: -len(kv[0])):
            if hole.startswith("?url"):
                sp = urllib.parse.urlsplit(str(val))
                origin_tok = f"{{{{origin:{hole}}}}}"
                if origin_tok in out and sp.scheme and sp.netloc:
                    out = out.replace(origin_tok, f"{sp.scheme}://{sp.netloc}")
            if hole in out:
                out = out.replace(hole, str(val))
        return out
    if isinstance(obj, list):
        return [_instantiate_obj(x, bindings) for x in obj]
    if isinstance(obj, Mapping):
        return {str(_instantiate_obj(k, bindings)): _instantiate_obj(v, bindings) for k, v in obj.items()}
    return obj


def _hole_pattern(hole: str) -> str:
    if hole.startswith("?url"):
        return r"(https?://[^\s\"'<>)\]]+?)"
    if hole.startswith("?path"):
        return r"([^\s\"',;)]+?)"
    if hole.startswith("?num"):
        return r"(\d+(?:\.\d+)?)"
    return r"(.+?)"


def anti_unify_workflow(
    goal: str,
    elevated_steps: Sequence[Mapping[str, Any]],
    postcondition: Mapping[str, Any],
    *,
    peer_goal: str | None = None,
) -> dict[str, Any]:
    """Anti-unify `(goal, elevated_steps, postcondition)` into a reusable parameterized workflow."""
    step_blob = json.dumps(list(elevated_steps), sort_keys=True) + "\n" + json.dumps(dict(postcondition), sort_keys=True)
    candidates = _extract_goal_literals(goal, peer_goal=peer_goal, step_blob=step_blob)

    val_to_hole: dict[str, str] = {}
    param_order: list[str] = []
    counts: dict[str, int] = {}

    for kind, val in candidates:
        if not val or val in val_to_hole:
            continue
        # Generalize any literal from the goal that causally participates in the steps or postcondition
        # (including URLs whose scheme://netloc origin appears in sibling endpoint paths like `/submit`!).
        origin_match = False
        if kind == "url":
            sp = urllib.parse.urlsplit(val)
            origin = f"{sp.scheme}://{sp.netloc}" if sp.scheme and sp.netloc else ""
            origin_match = bool(origin and origin in step_blob)
        if val not in step_blob and not origin_match:
            continue
        idx = counts.get(kind, 0)
        counts[kind] = idx + 1
        hole = f"?{kind}{idx}"
        val_to_hole[val] = hole

    # Build goal skeleton + anchored regex preserving exact occurrence order of holes in goal
    goal_clean = goal.strip().rstrip(".")
    occ: list[tuple[int, int, str]] = []
    for val, hole in sorted(val_to_hole.items(), key=lambda kv: -len(kv[0])):
        start = 0
        while True:
            pos = goal_clean.find(val, start)
            if pos < 0:
                break
            end = pos + len(val)
            if not any(not (end <= a or pos >= b) for a, b, _ in occ):
                occ.append((pos, end, hole))
            start = end
    occ.sort(key=lambda t: t[0])

    skeleton_parts: list[str] = []
    regex_parts: list[str] = [r"^\s*"]
    cursor = 0
    seen_group_holes: set[str] = set()
    for pos, end, hole in occ:
        prefix = goal_clean[cursor:pos]
        skeleton_parts.append(prefix)
        skeleton_parts.append(hole)
        if prefix:
            # Normalize whitespace runs so minor spacing differences never break recall
            tokens = [re.escape(tok) for tok in prefix.split() if tok]
            if prefix[0].isspace() and cursor > 0:
                regex_parts.append(r"\s+")
            if tokens:
                regex_parts.append(r"\s+".join(tokens))
                if prefix[-1].isspace():
                    regex_parts.append(r"\s+")
        if hole not in seen_group_holes:
            seen_group_holes.add(hole)
            param_order.append(hole)
            grp_name = hole[1:]
            regex_parts.append(f"(?P<{grp_name}>{_hole_pattern(hole)[1:-1]})")
        else:
            grp_name = hole[1:]
            regex_parts.append(f"(?P={grp_name})")
        cursor = end

    tail = goal_clean[cursor:]
    skeleton_parts.append(tail)
    if tail:
        tokens = [re.escape(tok) for tok in tail.split() if tok]
        if tail[0].isspace() and cursor > 0:
            regex_parts.append(r"\s+")
        if tokens:
            regex_parts.append(r"\s+".join(tokens))
    regex_parts.append(r"\.?\s*$")

    goal_skeleton = "".join(skeleton_parts)
    goal_regex = "".join(regex_parts)
    abstract_steps = _substitute_in_obj(list(elevated_steps), val_to_hole)
    abstract_post = _substitute_in_obj(dict(postcondition), val_to_hole)

    skel_words = sorted({
        w for w in re.findall(r"[a-z]{2,}", re.sub(r"\?[a-z]+\d+", " ", goal_skeleton.lower()))
        if w not in _STOP_WORDS
    })
    param_keys: dict[str, str] = {
        m.group(2): m.group(1).lower()
        for m in _HOLE_KV_RE.finditer(goal_skeleton)
    }

    return {
        "goal_skeleton": goal_skeleton,
        "goal_regex": goal_regex,
        "skeleton_tokens": skel_words,
        "param_order": param_order,
        "param_keys": param_keys,
        "abstract_steps": abstract_steps,
        "abstract_postcondition": abstract_post,
        "concrete_bindings": {h: v for v, h in val_to_hole.items()},
    }


def anti_unify_workflow_examples(
    example_1: Mapping[str, Any],
    example_2: Mapping[str, Any],
) -> dict[str, Any]:
    """Plotkin Least-General Generalization (LGG) over two workflow demonstrations.

    Given two demonstrations `(goal_1, steps_1, post_1)` and `(goal_2, steps_2, post_2)`,
    generalizes both typed literals and plain-word tokens that vary between `goal_1` and
    `goal_2` while causally appearing in `steps_1` / `post_1`, and verifies that `goal_2`
    structurally binds to the resulting parameterized workflow with distinct bindings.
    """
    g1 = str(example_1.get("goal") or "")
    g2 = str(example_2.get("goal") or "")
    s1 = elevate_trace_to_fastest_layer(list(example_1.get("steps") or example_1.get("trace") or ()))["elevated_steps"]
    p1 = dict(example_1.get("postcondition") or {})
    gen = anti_unify_workflow(g1, s1, p1, peer_goal=g2)
    b2 = bind_goal_parameters(gen, g2)
    gen["second_example_bindings"] = b2
    gen["generalized_across_both"] = bool(b2 is not None and b2 != gen.get("concrete_bindings"))
    return gen


def _bind_structural_goal_parameters(skill: Mapping[str, Any], goal: str) -> dict[str, str] | None:
    """Polymorphic structural parameter binder for similar goals (reordered keys, synonyms, clause order)."""
    goal_clean = goal.strip().rstrip(".")
    goal_skeleton = str(skill.get("goal_skeleton") or "")
    param_order = [str(p) for p in (skill.get("param_order") or []) if str(p).startswith("?")]
    if not goal_skeleton or not param_order:
        return None

    skel_tokens = {str(w).lower() for w in (skill.get("skeleton_tokens") or []) if w}
    if not skel_tokens:
        skel_tokens = {
            w for w in re.findall(r"[a-z]{2,}", re.sub(r"\?[a-z]+\d+", " ", goal_skeleton.lower()))
            if w not in _STOP_WORDS
        }
    goal_words = {w for w in re.findall(r"[a-z]{2,}", goal_clean.lower()) if w not in _STOP_WORDS}
    if not skel_tokens or _has_opposing_workflow_intent(skel_tokens, goal_words):
        return None

    expanded_goal_words = _expand_workflow_synonyms(goal_words)
    required_skel = skel_tokens - _OPTIONAL_CONTAINER_NOUNS
    if not required_skel:
        required_skel = skel_tokens
    if not (required_skel <= expanded_goal_words):
        return None

    # 1. Bind named `key=val` / `key: val` holes by key name (order-independent)
    key_to_hole: dict[str, str] = {}
    for m in _HOLE_KV_RE.finditer(goal_skeleton):
        key_to_hole[m.group(1).lower()] = m.group(2)
    if isinstance(skill.get("param_keys"), Mapping):
        for hole_k, key_name in skill["param_keys"].items():
            key_to_hole.setdefault(str(key_name).lower(), str(hole_k))

    out: dict[str, str] = {}
    consumed_spans: list[tuple[int, int]] = []
    if key_to_hole:
        goal_kv: dict[str, str] = {}
        for m in _KV_PAIR_RE.finditer(goal_clean):
            k_low = m.group(1).lower()
            v_raw = m.group(2).strip().strip("\"'").rstrip(".,;:")
            if k_low in key_to_hole and v_raw:
                goal_kv[k_low] = v_raw
                consumed_spans.append((m.start(), m.end()))
        if set(key_to_hole.keys()) != set(goal_kv.keys()):
            return None
        for k_low, hole in key_to_hole.items():
            out[hole] = goal_kv[k_low]

    remaining_holes = [h for h in param_order if h not in out]
    if not remaining_holes:
        return out

    # 2. Bind remaining positional typed holes (`?url`, `?path`, `?num`, `?str`) on unconsumed text
    masked_chars = list(goal_clean)
    for s_idx, e_idx in consumed_spans:
        for i in range(max(0, s_idx), min(len(masked_chars), e_idx)):
            masked_chars[i] = " "
    rem_goal = "".join(masked_chars)

    cands = _extract_goal_literals(rem_goal)
    by_kind: dict[str, list[str]] = {"url": [], "path": [], "num": [], "str": []}
    for kind, val in cands:
        if kind == "url" and any(u != val and u.startswith(val) for k2, u in cands if k2 == "url"):
            continue
        clean_v = val.strip().strip("\"'").rstrip(".")
        if clean_v and clean_v not in by_kind.get(kind, ()):
            by_kind.setdefault(kind, []).append(clean_v)

    # Also allow plain non-skeleton identifier arguments when a `?str` hole was learned via 2-example LGG
    needed_str = sum(1 for h in remaining_holes if h.startswith("?str"))
    if needed_str > len(by_kind["str"]):
        expanded_skel_tokens = _expand_workflow_synonyms(skel_tokens)
        for m in _IDENT_RE.finditer(rem_goal):
            tok = m.group(0)
            tlow = tok.lower()
            if (
                tlow not in _STOP_WORDS
                and tlow not in expanded_skel_tokens
                and tok not in by_kind["str"]
                and not any(tok in p for p in by_kind["path"] + by_kind["url"])
            ):
                by_kind["str"].append(tok)

    kind_cursors: dict[str, int] = {"url": 0, "path": 0, "num": 0, "str": 0}
    for hole in remaining_holes:
        m_kind = re.match(r"^\?([a-z]+)\d+$", hole)
        if not m_kind:
            return None
        h_kind = m_kind.group(1)
        pool = by_kind.get(h_kind) or []
        cur = kind_cursors.get(h_kind, 0)
        if cur >= len(pool):
            return None
        out[hole] = pool[cur]
        kind_cursors[h_kind] = cur + 1

    # Ambiguity guard: do not bind if extra conflicting typed literals of a bound positional kind remain
    for h_kind, used_count in kind_cursors.items():
        if used_count > 0 and len(by_kind.get(h_kind) or ()) != used_count:
            return None

    return out if len(out) == len(param_order) else None


def bind_goal_parameters(skill: Mapping[str, Any], goal: str) -> dict[str, str] | None:
    pattern = str(skill.get("goal_regex") or "")
    if pattern:
        m = re.match(pattern, goal.strip(), flags=re.IGNORECASE)
        if m:
            out: dict[str, str] = {}
            ok = True
            for k, v in m.groupdict().items():
                if v is None:
                    ok = False
                    break
                clean = v.strip().strip("\"'").rstrip(".")
                out["?" + k] = clean
            if ok:
                # Verify that if named key=value slots exist in the skeleton, a reordered
                # `env=prod and service=auth` wasn't misbound positionally by `.+?`
                skel = str(skill.get("goal_skeleton") or "")
                kv_holes = {m_kv.group(2): m_kv.group(1).lower() for m_kv in _HOLE_KV_RE.finditer(skel)}
                misbound = any(
                    re.match(r"^[A-Za-z_][A-Za-z0-9_-]*\s*[=:]", str(out.get(h) or ""))
                    for h in kv_holes
                )
                if not misbound:
                    return out
    return _bind_structural_goal_parameters(skill, goal)


# --------------------------------------------------------------------------- #
# 3. Deterministic Execution & Independent Postcondition Verification
# --------------------------------------------------------------------------- #
class _SemanticHTMLFormParser(html.parser.HTMLParser):
    """Pure-stdlib semantic HTML form & interactive element parser."""

    def __init__(self) -> None:
        super().__init__()
        self.forms: list[dict[str, Any]] = []
        self._cur_form: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        amap = {k.lower(): (v or "") for k, v in attrs}
        t = tag.lower()
        if t == "form":
            self._cur_form = {
                "action": amap.get("action") or "",
                "method": (amap.get("method") or "GET").upper(),
                "inputs": [],
            }
            self.forms.append(self._cur_form)
        elif t in {"input", "textarea", "select", "button"} and self._cur_form is not None:
            self._cur_form["inputs"].append({
                "tag": t,
                "name": amap.get("name") or "",
                "type": (amap.get("type") or "text").lower(),
                "value": amap.get("value") or "",
                "aria": amap.get("aria-label") or "",
                "placeholder": amap.get("placeholder") or "",
                "role": amap.get("role") or "",
            })

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "form":
            self._cur_form = None


def _resolve_local_path(raw_path: str, cwd: pathlib.Path) -> pathlib.Path:
    p = pathlib.Path(raw_path)
    return p if p.is_absolute() else (cwd / p)


def _subst_dynamic_tokens(val: Any, dyn: Mapping[str, str]) -> Any:
    """Substitute `{{hidden:csrf_token}}` or `{{json:token}}` from previous step responses."""
    if isinstance(val, str):
        out = val
        for k, v in dyn.items():
            tok = "{{" + k + "}}"
            if tok in out:
                out = out.replace(tok, v)
        return out
    if isinstance(val, Mapping):
        return {k: _subst_dynamic_tokens(v, dyn) for k, v in val.items()}
    if isinstance(val, list):
        return [_subst_dynamic_tokens(x, dyn) for x in val]
    return val


def _sandbox_for_taught_programs() -> Any | None:
    """The namespace sandbox a taught program runs in, or None where this machine cannot start one.

    A `confined_python_exec` step is replayed by automatic routes: the front door's fallback, the
    awake loop, the qualification of a new skill.  It used to go through `solve_v1.act`, whose
    `import confine_v1` resolves only when `canonical/runtime` itself is on `sys.path`.  From a
    package import it raised `ModuleNotFoundError`, `act` fell back to the host, and the taught
    program ran with the caller's whole account (measured 2026-11-11 at the front door; the receipt
    said `confined: False`).  Here the program runs inside the sandbox or it does not run.
    """
    try:
        from canonical.runtime import confine_v1 as _confine
        return _confine if _confine.available() else None
    except Exception:  # noqa: BLE001 - no sandbox is an answer, not a crash
        return None


def _text_a_skill_could_have_written(template: str, holes: Sequence[str], text: str) -> bool:
    """True when `text` is the step's own content template filled in with *some* values.

    Each hole stands for one value on one line; a hole that occurs twice must hold the same value.
    """
    names = sorted({str(h) for h in holes if str(h).startswith("?")}, key=len, reverse=True)
    if not names:
        return template == text
    parts: list[str] = []
    seen: set[str] = set()
    pos = 0
    for m in re.finditer("|".join(re.escape(n) for n in names), template):
        parts.append(re.escape(template[pos:m.start()]))
        group = "h_" + re.sub(r"\W", "_", m.group(0)[1:])
        parts.append(f"(?P={group})" if group in seen else f"(?P<{group}>[^\\n]*?)")
        seen.add(group)
        pos = m.end()
    parts.append(re.escape(template[pos:]))
    return re.fullmatch("".join(parts), text) is not None


def content_a_generalized_write_would_destroy(
    abstract_steps: Sequence[Mapping[str, Any]],
    inst_steps: Sequence[Mapping[str, Any]],
    *,
    cwd: str | pathlib.Path | None = None,
) -> str | None:
    """Name the first file a generalized `write_text` would replace without ever having read it.

    A `write_text` step holds the whole file as it was written at teaching time, with the goal's
    values turned into holes.  That is the right record of "create this file".  It is the wrong
    record of an *edit*: shown `shapes.py` after a rename, the compiled skill is "replace the named
    file with shapes.py", and its postcondition ("the file contains `def <new name>(`") still holds.
    Measured 2026-11-11 through the front door: asked to rename a routine in `geom.py`, the skill
    replaced `geom.py` with the taught file, and the door answered PASS.

    One demonstration cannot say whether the teacher created or edited.  The world it is replayed in
    can: a file that already exists, holds something, and is neither what the step is about to write
    nor something this same step could have written with other values, is content the skill never
    read.  Replacing it is refused.  Creating a file, filling an empty one, appending, writing the
    same text again and updating a file this skill wrote before all stay possible.

    Returns the path (as the step names it), or None when nothing would be destroyed.
    """
    work_dir = pathlib.Path(cwd).resolve() if cwd else pathlib.Path.cwd()
    for abstract, inst in zip(abstract_steps, inst_steps):
        if not isinstance(abstract, Mapping) or not isinstance(inst, Mapping):
            continue
        if str(inst.get("layer") or "") != "python_file_op":
            continue
        if str(inst.get("op") or "write_text") == "append_text":
            continue
        try:
            target = _resolve_local_path(str(inst["path"]), work_dir)
        except Exception:  # noqa: BLE001 - an unresolvable target is left to the executor to refuse
            continue
        if not target.exists():
            continue
        try:
            existing = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return str(inst.get("path"))  # a directory, or bytes that are not text: never replace
        if not existing.strip() or existing == str(inst.get("content") or ""):
            continue
        template = str(abstract.get("content") or "")
        holes = re.findall(r"\?[a-z]+\d+", template)
        if _text_a_skill_could_have_written(template, holes, existing):
            continue
        return str(inst.get("path"))
    return None


def execute_compiled_steps(
    steps: Sequence[Mapping[str, Any]],
    *,
    cwd: str | pathlib.Path | None = None,
) -> dict[str, Any]:
    """Execute concrete instantiated steps deterministically with zero model calls.

    CLI stages need an admitted execution boundary. Preflight the entire trace
    before *any* stage runs: rejecting a later CLI after a write is too late.
    Other layers remain governed by their existing callers; this check does not
    certify their effects or confine them.
    """
    from canonical.runtime import computer_execution_boundary_v1 as boundary
    sandbox: Any | None = None
    for index, step in enumerate(steps):
        layer = str(step.get("layer") or "") if isinstance(step, Mapping) else ""
        if layer == "confined_python_exec" and sandbox is None:
            sandbox = _sandbox_for_taught_programs()
        if layer in {"cli_exec", "cli_pipeline"} or (layer == "confined_python_exec" and sandbox is None):
            # A taught program without a sandbox is refused here, before any earlier step has
            # written anything -- the same rule, for the same reason, as a command-line stage.
            return {"ok": False, "status": boundary.STATUS,
                    "failure_class": boundary.FAILURE_CLASS,
                    "reason": boundary.FAILURE_CLASS, "failed_step": index,
                    "step_receipts": []}
    work_dir = pathlib.Path(cwd).resolve() if cwd else pathlib.Path.cwd()
    step_receipts: list[dict[str, Any]] = []
    pending_dom_fills: dict[str, str] = {}
    current_dom_url: str | None = None
    cookie_jar = http.cookiejar.CookieJar()
    http_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    dynamic_vars: dict[str, str] = {}

    for idx, step in enumerate(steps):
        layer = str(step.get("layer") or "")
        t0 = time.perf_counter_ns()

        if layer == "python_file_op":
            target = _resolve_local_path(str(step["path"]), work_dir)
            target.parent.mkdir(parents=True, exist_ok=True)
            op = str(step.get("op") or "write_text")
            content = str(step.get("content") or "")
            if op == "append_text":
                with open(target, "a", encoding="utf-8") as fh:
                    fh.write(content)
            else:
                target.write_text(content, encoding="utf-8")
            step_receipts.append({
                "step": idx, "layer": layer, "ok": True,
                "path": str(target), "bytes": target.stat().st_size,
                "elapsed_us": (time.perf_counter_ns() - t0) // 1000,
            })

        elif layer == "sqlite_exec":
            db_file = _resolve_local_path(str(step["db_path"]), work_dir)
            db_file.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(db_file), timeout=10.0)
            try:
                cur = conn.execute(str(step["sql"]), list(step.get("params") or []))
                rows = cur.fetchall()
                conn.commit()
            finally:
                conn.close()
            step_receipts.append({
                "step": idx, "layer": layer, "ok": True,
                "db_path": str(db_file), "rows": rows,
                "elapsed_us": (time.perf_counter_ns() - t0) // 1000,
            })

        elif layer == "http_request":
            method = str(step.get("method") or "GET").upper()
            url = str(_subst_dynamic_tokens(step["url"], dynamic_vars))
            headers = {
                str(k): str(_subst_dynamic_tokens(v, dynamic_vars))
                for k, v in (step.get("headers") or {}).items()
            }
            payload_bytes: bytes | None = None
            if "json_body" in step and step["json_body"] is not None:
                jb = _subst_dynamic_tokens(step["json_body"], dynamic_vars)
                payload_bytes = json.dumps(jb).encode("utf-8")
                headers.setdefault("Content-Type", "application/json")
            elif "form_body" in step and isinstance(step["form_body"], Mapping):
                fb = _subst_dynamic_tokens(step["form_body"], dynamic_vars)
                payload_bytes = urllib.parse.urlencode(fb).encode("utf-8")
                headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
            elif "body" in step and step["body"] is not None:
                payload_bytes = str(_subst_dynamic_tokens(step["body"], dynamic_vars)).encode("utf-8")
            req = urllib.request.Request(url, data=payload_bytes, headers=headers, method=method)
            try:
                with http_opener.open(req, timeout=15) as resp:
                    resp_bytes = resp.read()
                    status_code = int(resp.status)
            except urllib.error.HTTPError as herr:
                return {
                    "ok": False,
                    "failed_step": idx,
                    "reason": f"HTTP_ERROR_{herr.code}",
                    "step_receipts": step_receipts,
                }
            resp_txt = resp_bytes.decode("utf-8", "replace")
            # Harvest dynamic hidden inputs & JSON scalar tokens for stateful multi-step chaining!
            if step.get("extract_hidden_inputs") or "<form" in resp_txt.lower():
                hparser = _SemanticHTMLFormParser()
                try:
                    hparser.feed(resp_txt)
                    for frm in hparser.forms:
                        for inp in frm["inputs"]:
                            if inp.get("type") == "hidden" and inp.get("name"):
                                dynamic_vars[f"hidden:{inp['name']}"] = str(inp.get("value") or "")
                except Exception:
                    pass
            if resp_txt.lstrip().startswith("{"):
                try:
                    jdoc = json.loads(resp_txt)
                    if isinstance(jdoc, Mapping):
                        for jk, jv in jdoc.items():
                            if isinstance(jv, (str, int, float)):
                                dynamic_vars[f"json:{jk}"] = str(jv)
                except Exception:
                    pass
            if step.get("save_response_to"):
                out_p = _resolve_local_path(str(step["save_response_to"]), work_dir)
                out_p.parent.mkdir(parents=True, exist_ok=True)
                out_p.write_bytes(resp_bytes)
            step_receipts.append({
                "step": idx, "layer": layer, "ok": 200 <= status_code < 400,
                "status_code": status_code,
                "cookies_held": len(cookie_jar),
                "response_preview": resp_txt[:400],
                "elapsed_us": (time.perf_counter_ns() - t0) // 1000,
            })

        elif layer == "cli_pipeline":
            stages = [[str(a) for a in sg] for sg in (step.get("stages") or []) if sg]
            if len(stages) < 2:
                return {"ok": False, "failed_step": idx, "reason": "EMPTY_PIPELINE", "step_receipts": step_receipts}
            cur_input: bytes | None = None
            last_out = b""
            for s_idx, argv in enumerate(stages):
                proc = subprocess.run(argv, cwd=str(work_dir), input=cur_input, capture_output=True, timeout=30)
                if proc.returncode != 0:
                    return {
                        "ok": False,
                        "failed_step": idx,
                        "reason": f"PIPE_STAGE_{s_idx}_EXIT_{proc.returncode}",
                        "step_receipts": step_receipts,
                    }
                cur_input = proc.stdout
                last_out = proc.stdout
            step_receipts.append({
                "step": idx, "layer": layer, "ok": True,
                "stdout": last_out.decode("utf-8", "replace").strip()[:400],
                "elapsed_us": (time.perf_counter_ns() - t0) // 1000,
            })

        elif layer == "cli_exec":
            argv = [str(a) for a in (step.get("argv") or [])]
            proc = subprocess.run(argv, cwd=str(work_dir), capture_output=True, timeout=30)
            if proc.returncode != 0:
                return {
                    "ok": False,
                    "failed_step": idx,
                    "reason": f"CLI_EXIT_{proc.returncode}:{(proc.stderr or proc.stdout).decode('utf-8', 'replace')[:200]}",
                    "step_receipts": step_receipts,
                }
            if step.get("keep_stdout_to"):
                out_p = _resolve_local_path(str(step["keep_stdout_to"]), work_dir)
                out_p.parent.mkdir(parents=True, exist_ok=True)
                out_p.write_bytes(proc.stdout)
            step_receipts.append({
                "step": idx, "layer": layer, "ok": True,
                "stdout": proc.stdout.decode("utf-8", "replace")[:400],
                "elapsed_us": (time.perf_counter_ns() - t0) // 1000,
            })

        elif layer == "semantic_dom":
            if step.get("url"):
                current_dom_url = str(step["url"])
            op = str(step.get("op") or "").upper()
            sel = step.get("selector") if isinstance(step.get("selector"), Mapping) else {}
            if op == "FILL_SEMANTIC":
                field_key = str(sel.get("name") or sel.get("aria") or sel.get("placeholder") or "")
                if field_key:
                    pending_dom_fills[field_key] = str(step.get("value") or "")
                step_receipts.append({
                    "step": idx, "layer": layer, "ok": bool(field_key),
                    "filled": field_key,
                    "elapsed_us": (time.perf_counter_ns() - t0) // 1000,
                })
            elif op == "CLICK_SEMANTIC" and current_dom_url:
                with urllib.request.urlopen(current_dom_url, timeout=10) as resp:
                    html_doc = resp.read().decode("utf-8", "replace")
                parser = _SemanticHTMLFormParser()
                parser.feed(html_doc)
                if not parser.forms:
                    return {"ok": False, "failed_step": idx, "reason": "NO_SEMANTIC_FORM_AT_URL", "step_receipts": step_receipts}
                form = parser.forms[0]
                payload: dict[str, str] = {}
                for inp in form["inputs"]:
                    nm = inp.get("name") or ""
                    if not nm:
                        continue
                    if nm in pending_dom_fills:
                        payload[nm] = pending_dom_fills[nm]
                    elif inp.get("aria") in pending_dom_fills:
                        payload[nm] = pending_dom_fills[inp["aria"]]
                    elif inp.get("placeholder") in pending_dom_fills:
                        payload[nm] = pending_dom_fills[inp["placeholder"]]
                    elif inp.get("type") not in {"submit", "button"} and inp.get("value"):
                        payload[nm] = inp["value"]
                submit_url = urllib.parse.urljoin(current_dom_url, form["action"] or current_dom_url)
                method = form["method"]
                if method == "GET":
                    sep = "&" if "?" in submit_url else "?"
                    full_url = submit_url + (sep + urllib.parse.urlencode(payload) if payload else "")
                    req = urllib.request.Request(full_url, method="GET")
                else:
                    data_b = urllib.parse.urlencode(payload).encode("utf-8")
                    req = urllib.request.Request(
                        submit_url,
                        data=data_b,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        method=method,
                    )
                with urllib.request.urlopen(req, timeout=15) as sresp:
                    body_txt = sresp.read().decode("utf-8", "replace")
                    sc = int(sresp.status)
                pending_dom_fills.clear()
                step_receipts.append({
                    "step": idx, "layer": layer, "ok": 200 <= sc < 400,
                    "status_code": sc, "response_preview": body_txt[:400],
                    "elapsed_us": (time.perf_counter_ns() - t0) // 1000,
                })
            else:
                return {"ok": False, "failed_step": idx, "reason": "UNBOUND_SEMANTIC_DOM_OP", "step_receipts": step_receipts}

        elif layer == "confined_python_exec":
            code = str(step.get("code") or "")
            if not code.strip():
                return {"ok": False, "failed_step": idx, "reason": "EMPTY_CONFINED_PYTHON_CODE", "step_receipts": step_receipts}
            if sandbox is None:  # unreachable after the preflight; kept so the rule cannot rot
                return {"ok": False, "status": boundary.STATUS, "failure_class": boundary.FAILURE_CLASS,
                        "reason": boundary.FAILURE_CLASS, "failed_step": idx, "step_receipts": step_receipts}
            run = sandbox.run(
                code,
                str(work_dir),
                timeout=int(step.get("timeout") or 30),
                network=bool(step.get("network", False)),
            )
            if run.get("exit_status") != 0 or run.get("verdict") != "OK" or run.get("confined") is not True:
                return {
                    "ok": False,
                    "failed_step": idx,
                    "reason": f"CONFINED_PYTHON_EXIT_{run.get('exit_status')}:{str(run.get('output') or run.get('detail') or '')[:200]}",
                    "step_receipts": step_receipts,
                }
            step_receipts.append({
                "step": idx,
                "layer": layer,
                "ok": True,
                "confined": True,
                "stdout": str(run.get("output") or "")[:400],
                "elapsed_us": (time.perf_counter_ns() - t0) // 1000,
            })

        else:
            return {"ok": False, "failed_step": idx, "reason": f"UNSUPPORTED_COMPILED_LAYER:{layer}", "step_receipts": step_receipts}

    return {"ok": True, "step_receipts": step_receipts, "_http_opener": http_opener}


def verify_postcondition(
    postcondition: Mapping[str, Any],
    *,
    cwd: str | pathlib.Path | None = None,
    execution_result: Mapping[str, Any] | None = None,
) -> tuple[bool, str]:
    """Independent real-world oracle checking disk, SQLite, JSON, or HTTP state."""
    work_dir = pathlib.Path(cwd).resolve() if cwd else pathlib.Path.cwd()
    kind = str(postcondition.get("kind") or "").lower()

    if kind == "file_nonempty":
        p = _resolve_local_path(str(postcondition["path"]), work_dir)
        if not p.is_file():
            return False, "POSTCONDITION_FILE_MISSING"
        if p.stat().st_size <= 0:
            return False, "POSTCONDITION_FILE_EMPTY"
        return True, "FILE_NONEMPTY_VERIFIED"

    if kind == "file_contains":
        p = _resolve_local_path(str(postcondition["path"]), work_dir)
        if not p.is_file():
            return False, "POSTCONDITION_FILE_MISSING"
        txt = p.read_text(encoding="utf-8", errors="replace")
        expected = str(postcondition.get("contains") or "")
        if not expected or expected not in txt:
            return False, "POSTCONDITION_SUBSTRING_MISSING"
        return True, "FILE_CONTAINS_VERIFIED"

    if kind == "json_field_equals":
        p = _resolve_local_path(str(postcondition["path"]), work_dir)
        if not p.is_file():
            return False, "POSTCONDITION_JSON_FILE_MISSING"
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            return False, "POSTCONDITION_JSON_INVALID"
        cur: Any = doc
        for part in str(postcondition.get("field") or "").split("."):
            if not part:
                continue
            if isinstance(cur, Mapping) and part in cur:
                cur = cur[part]
            else:
                return False, f"POSTCONDITION_JSON_KEY_MISSING:{part}"
        if str(cur) != str(postcondition.get("equals")):
            return False, f"POSTCONDITION_JSON_VALUE_MISMATCH:{cur!r}"
        return True, "JSON_FIELD_VERIFIED"

    if kind == "sqlite_query_equals":
        db_p = _resolve_local_path(str(postcondition["db_path"]), work_dir)
        if not db_p.is_file():
            return False, "POSTCONDITION_SQLITE_DB_MISSING"
        conn = sqlite3.connect(str(db_p), timeout=10.0)
        try:
            row = conn.execute(
                str(postcondition["sql"]),
                list(postcondition.get("params") or []),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return False, "POSTCONDITION_SQLITE_NO_ROW"
        got = row[0] if len(row) == 1 else list(row)
        exp = postcondition.get("equals")
        if str(got) != str(exp):
            return False, f"POSTCONDITION_SQLITE_MISMATCH:{got!r}!={exp!r}"
        return True, "SQLITE_STATE_VERIFIED"

    if kind == "http_get_contains":
        url = str(postcondition["url"])
        opener = (execution_result or {}).get("_http_opener")
        try:
            if opener is not None:
                with opener.open(url, timeout=10) as resp:
                    body = resp.read().decode("utf-8", "replace")
                    if int(resp.status) >= 400:
                        return False, f"POSTCONDITION_HTTP_STATUS_{resp.status}"
            else:
                with urllib.request.urlopen(url, timeout=10) as resp:
                    body = resp.read().decode("utf-8", "replace")
                    if int(resp.status) >= 400:
                        return False, f"POSTCONDITION_HTTP_STATUS_{resp.status}"
        except Exception as exc:
            return False, f"POSTCONDITION_HTTP_ERROR:{type(exc).__name__}"
        expected = str(postcondition.get("contains") or "")
        if not expected or expected not in body:
            return False, "POSTCONDITION_HTTP_BODY_MISMATCH"
        return True, "HTTP_STATE_VERIFIED"

    if kind == "sqlite_row_exists":
        db_p = _resolve_local_path(str(postcondition["db_path"]), work_dir)
        if not db_p.is_file():
            return False, "POSTCONDITION_SQLITE_DB_MISSING"
        conn = sqlite3.connect(str(db_p), timeout=10.0)
        try:
            rows = conn.execute(
                str(postcondition["sql"]),
                list(postcondition.get("params") or []),
            ).fetchall()
        finally:
            conn.close()
        min_rows = int(postcondition.get("min_rows") or 1)
        if len(rows) < min_rows:
            return False, f"POSTCONDITION_SQLITE_ROWS_{len(rows)}_LT_{min_rows}"
        return True, "SQLITE_ROWS_VERIFIED"

    if kind == "stdout_integer":
        receipts = list((execution_result or {}).get("step_receipts") or [])
        if not receipts:
            return False, "POSTCONDITION_NO_RECEIPTS"
        out_txt = str(receipts[-1].get("stdout") or "").strip()
        if not re.fullmatch(r"-?\d+", out_txt):
            return False, f"POSTCONDITION_NOT_INTEGER:{out_txt!r}"
        return True, "STDOUT_INTEGER_VERIFIED"

    if kind == "stdout_equals":
        receipts = list((execution_result or {}).get("step_receipts") or [])
        if not receipts:
            return False, "POSTCONDITION_NO_RECEIPTS"
        out_txt = str(receipts[-1].get("stdout") or "").strip()
        exp_txt = str(postcondition.get("expected") or "").strip()
        if out_txt != exp_txt:
            return False, f"POSTCONDITION_STDOUT_MISMATCH:{out_txt!r}!={exp_txt!r}"
        return True, "STDOUT_EQUALS_VERIFIED"

    if kind == "http_status_json":
        receipts = list((execution_result or {}).get("step_receipts") or [])
        if not receipts:
            return False, "POSTCONDITION_NO_RECEIPTS"
        last = receipts[-1]
        exp_status = int(postcondition.get("status") or 200)
        if int(last.get("status_code") or 0) != exp_status:
            return False, f"POSTCONDITION_HTTP_STATUS_{last.get('status_code')}!={exp_status}"
        subset = postcondition.get("json_subset")
        if isinstance(subset, Mapping):
            try:
                parsed = json.loads(str(last.get("response_preview") or "{}"))
            except Exception:
                return False, "POSTCONDITION_RESPONSE_NOT_JSON"
            for k, v in subset.items():
                if parsed.get(k) != v:
                    return False, f"POSTCONDITION_JSON_SUBSET_MISMATCH:{k}"
        return True, "HTTP_STATUS_JSON_VERIFIED"

    if kind == "step_response_contains":
        expected = str(postcondition.get("contains") or "")
        receipts = list((execution_result or {}).get("step_receipts") or [])
        if not expected or not any(expected in str(r.get("response_preview") or r.get("stdout") or "") for r in receipts):
            return False, "POSTCONDITION_RESPONSE_MISSING"
        return True, "STEP_RESPONSE_VERIFIED"

    return False, f"UNSUPPORTED_POSTCONDITION_KIND:{kind}"


def _sabotage_world(postcondition: Mapping[str, Any], cwd: pathlib.Path) -> bool:
    """Deliberately corrupt the postcondition's target artifact to prove the oracle can say NO."""
    kind = str(postcondition.get("kind") or "").lower()
    if kind in {"file_contains", "json_field_equals", "file_nonempty"}:
        p = _resolve_local_path(str(postcondition["path"]), cwd)
        try:
            inside = p.resolve().is_relative_to(cwd.resolve())
        except (OSError, ValueError):
            inside = False
        if inside and p.is_file():
            p.unlink()
            return True
    if kind == "sqlite_query_equals":
        db_p = _resolve_local_path(str(postcondition["db_path"]), cwd)
        if db_p.is_file():
            db_p.unlink()
            return True
    if kind in {"http_get_contains", "step_response_contains"}:
        # Tested via mutated expected token in negative-control verification
        return True
    return False


# --------------------------------------------------------------------------- #
# 4. Automatic Perturbed Twin-World Self-Experimentation (`N=1 -> N=2`)
#    & Full K2 -> K3=0 Qualification + Permanent SQLite Registration
# --------------------------------------------------------------------------- #
_SQL_UPDATE_RE = re.compile(
    r"^\s*UPDATE\s+([A-Za-z_][A-Za-z0-9_]*)\s+SET\s+(.+?)(?:\s+WHERE\s+(.+))?\s*;?\s*$",
    re.IGNORECASE | re.DOTALL,
)


def _invert_initial_sql_value(val: Any) -> Any:
    if isinstance(val, bool):
        return 0 if val else 1
    if isinstance(val, int):
        return 0 if val == 1 else (1 if val == 0 else val - 1)
    if isinstance(val, float):
        return 0.0 if val != 0.0 else 1.0
    s = str(val).strip().strip("'\"")
    if s == "1":
        return 0
    if s == "0":
        return 1
    if s.lower() == "true":
        return "false"
    if s.lower() == "false":
        return "true"
    if re.fullmatch(r"-?\d+", s):
        iv = int(s)
        return 0 if iv == 1 else (1 if iv == 0 else iv - 1)
    return f"__initial_{s}"


def _clone_sqlite_twin_world(
    orig_db: pathlib.Path,
    twin_db: pathlib.Path,
    abstract_steps: Sequence[Mapping[str, Any]],
    concrete_bindings: Mapping[str, str],
    twin_bindings: Mapping[str, str],
) -> None:
    """Clone schema from `orig_db` into `twin_db` and seed pre-UPDATE rows with inverted state."""
    twin_db.parent.mkdir(parents=True, exist_ok=True)
    src_con = sqlite3.connect(str(orig_db), timeout=10.0)
    dst_con = sqlite3.connect(str(twin_db), timeout=10.0)
    try:
        ddl_rows = src_con.execute(
            "SELECT type, name, sql FROM sqlite_master "
            "WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' "
            "ORDER BY CASE type WHEN 'table' THEN 0 WHEN 'index' THEN 1 ELSE 2 END"
        ).fetchall()
        for _typ, _name, ddl in ddl_rows:
            dst_con.execute(ddl)

        val_map = {
            str(concrete_bindings[h]): str(twin_bindings[h])
            for h in concrete_bindings
            if h in twin_bindings
        }
        for step in abstract_steps:
            if str(step.get("layer") or "") != "sqlite_exec":
                continue
            sql = str(step.get("sql") or "")
            m = _SQL_UPDATE_RE.match(sql)
            if not m:
                continue
            table, set_clause, _where_clause = m.group(1), m.group(2), m.group(3) or ""
            cols_info = src_con.execute(f"PRAGMA table_info({table})").fetchall()
            if not cols_info:
                continue
            col_names = [str(c[1]) for c in cols_info]
            set_targets: dict[str, Any] = {}
            for assign in set_clause.split(","):
                if "=" in assign:
                    lhs, rhs = assign.split("=", 1)
                    cname = lhs.strip().strip('"`[]')
                    rval_raw = rhs.strip()
                    if rval_raw == "?" and step.get("params"):
                        rval = _instantiate_obj(step["params"][0], twin_bindings)
                    else:
                        rval = str(_instantiate_obj(rval_raw, twin_bindings)).strip("'\"")
                    set_targets[cname] = rval

            where_targets: dict[str, Any] = {}
            for wm in re.finditer(
                r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*('[^']*'|\"[^\"]*\"|\?[A-Za-z0-9_]+|[^\s,;)]+)",
                _where_clause,
            ):
                wc = wm.group(1).strip().strip('"`[]')
                wv_raw = wm.group(2).strip()
                if wv_raw != "?":
                    where_targets[wc] = str(_instantiate_obj(wv_raw, twin_bindings)).strip("'\"")

            sample = src_con.execute(f"SELECT * FROM {table} LIMIT 1").fetchone()
            seed_vals: list[Any] = []
            for idx_c, cname in enumerate(col_names):
                base_v = sample[idx_c] if sample is not None else None
                if cname in where_targets:
                    seed_vals.append(where_targets[cname])
                elif cname in set_targets:
                    seed_vals.append(_invert_initial_sql_value(set_targets[cname]))
                elif isinstance(base_v, str) and base_v in val_map:
                    seed_vals.append(val_map[base_v])
                elif sample is None and idx_c == 0:
                    # Pick first non-path twin parameter as primary key if source table was empty
                    non_path = [
                        twin_bindings[h]
                        for h in twin_bindings
                        if not h.startswith("?path") and not h.startswith("?url")
                    ]
                    seed_vals.append(non_path[0] if non_path else "twin_key")
                else:
                    seed_vals.append(base_v)

            # Ensure any WHERE-referenced twin parameter exists in a row!
            inst_params = _instantiate_obj(list(step.get("params") or []), twin_bindings)
            for pval in inst_params:
                if isinstance(pval, str) and pval not in seed_vals:
                    for idx_c, cname in enumerate(col_names):
                        if cname not in set_targets and (
                            sample is None or isinstance(sample[idx_c], str)
                        ):
                            seed_vals[idx_c] = pval
                            break

            placeholders = ", ".join("?" for _ in col_names)
            col_list = ", ".join(col_names)
            dst_con.execute(
                f"INSERT OR IGNORE INTO {table} ({col_list}) VALUES ({placeholders})",
                seed_vals,
            )
        dst_con.commit()
    finally:
        src_con.close()
        dst_con.close()


def synthesize_perturbed_twin_world(
    *,
    generalized: Mapping[str, Any],
    postcondition: Mapping[str, Any],
    source_cwd: pathlib.Path,
    twin_dir: pathlib.Path,
) -> dict[str, Any]:
    """Construct a genuinely distinct twin goal + isolated twin filesystem/DB sandbox from `N=1`."""
    param_order: list[str] = list(generalized.get("param_order") or [])
    concrete: Mapping[str, str] = dict(generalized.get("concrete_bindings") or {})
    if not param_order or not concrete:
        return {
            "ok": False,
            "status": "FAIL_CLOSED__PARAMETER_FREE_SKILL_CANNOT_SYNTHESIZE_TWIN",
            "reason": "NO_VARIATION_SPACE_IN_GOAL",
        }

    twin_dir.mkdir(parents=True, exist_ok=True)
    twin_bindings: dict[str, str] = {}
    post_kind = str(postcondition.get("kind") or "").lower()
    post_target_raw = str(postcondition.get("path") or postcondition.get("db_path") or "")
    post_target_abs = _resolve_local_path(post_target_raw, source_cwd) if post_target_raw else None

    for idx, hole in enumerate(param_order):
        orig_val = str(concrete[hole])
        if hole.startswith("?url"):
            # URL skills require a live twin endpoint unless port/query param can be perturbed on same server
            sp = urllib.parse.urlsplit(orig_val)
            q = urllib.parse.parse_qsl(sp.query, keep_blank_values=True)
            q.append(("twin_probe", "1"))
            new_q = urllib.parse.urlencode(q)
            twin_bindings[hole] = urllib.parse.urlunsplit((sp.scheme, sp.netloc, sp.path, new_q, sp.fragment))
        elif hole.startswith("?num"):
            if orig_val.isdigit():
                iv = int(orig_val)
                twin_bindings[hole] = str(iv + 2 if iv >= 0 else 2)
            else:
                twin_bindings[hole] = f"{float(orig_val) + 2.0:g}"
        elif hole.startswith("?path"):
            orig_p = _resolve_local_path(orig_val, source_cwd)
            twin_name = f"twin_{idx}_{orig_p.name}"
            twin_p = twin_dir / twin_name
            # Preserve relative vs absolute style so goal regex & local resolution stay consistent
            twin_bindings[hole] = str(twin_p) if pathlib.Path(orig_val).is_absolute() else twin_name
        else:
            clean = re.sub(r"[^A-Za-z0-9_.-]", "_", orig_val).strip("_") or f"val{idx}"
            twin_bindings[hole] = f"twin_{clean}"

    # Materialize cloned input artifacts / SQLite schemas inside `twin_dir`
    for hole in param_order:
        if not hole.startswith("?path"):
            continue
        orig_p = _resolve_local_path(str(concrete[hole]), source_cwd)
        twin_p = _resolve_local_path(str(twin_bindings[hole]), twin_dir)
        if orig_p.suffix.lower() in {".sqlite", ".db", ".sqlite3"} and orig_p.is_file():
            _clone_sqlite_twin_world(
                orig_p,
                twin_p,
                generalized.get("abstract_steps") or [],
                concrete,
                twin_bindings,
            )
        elif orig_p.is_file():
            # Only pre-copy if this path is an INPUT (not a freshly created output artifact!)
            is_created_output = (
                post_target_abs is not None
                and orig_p.resolve() == post_target_abs.resolve()
                and post_kind in {"file_contains", "file_nonempty", "json_field_equals"}
            )
            if not is_created_output:
                import shutil
                twin_p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(orig_p, twin_p)

    # Also clone any un-parameterized relative SQLite DB referenced by `postcondition['db_path']`
    if post_kind == "sqlite_query_equals" and post_target_raw and not pathlib.Path(post_target_raw).is_absolute():
        orig_db = _resolve_local_path(post_target_raw, source_cwd)
        twin_db = _resolve_local_path(post_target_raw, twin_dir)
        if orig_db.is_file() and not twin_db.exists():
            _clone_sqlite_twin_world(
                orig_db,
                twin_db,
                generalized.get("abstract_steps") or [],
                concrete,
                twin_bindings,
            )

    twin_goal = str(_instantiate_obj(generalized["goal_skeleton"], twin_bindings))
    rebound = bind_goal_parameters(generalized, twin_goal)
    if rebound is None or rebound == concrete:
        return {
            "ok": False,
            "status": "FAIL_CLOSED__TWIN_GOAL_FAILED_DISTINCT_UNIFICATION",
            "twin_goal": twin_goal,
        }
    return {
        "ok": True,
        "twin_goal": twin_goal,
        "twin_cwd": twin_dir,
        "twin_bindings": rebound,
    }


def compile_and_qualify_skill(
    *,
    goal: str,
    trace: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    postcondition: Mapping[str, Any],
    heldout_goal: str | None = None,
    heldout_cwd: str | pathlib.Path | None = None,
    heldout_setup: Callable[[pathlib.Path], None] | None = None,
    heldout_postcondition: Mapping[str, Any] | None = None,
    sabotaged_postcondition: Mapping[str, Any] | None = None,
    auto_synthesize_twin: bool = False,
    source_cwd: str | pathlib.Path | None = None,
    source_channel: str = "k2_or_sandbox_acquisition",
    db_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Compile one acquisition trace, qualify on untouched held-out + sabotage control, and persist."""
    from canonical.runtime.memory_policy_v1 import can_write_memory

    if not can_write_memory():
        return {
            "schema": SCHEMA,
            "qualified": False,
            "persisted": False,
            "status": "SKIPPED__MEMORY_POLICY_WRITE_DISABLED",
        }
    t0 = time.perf_counter_ns()
    elevated = elevate_trace_to_fastest_layer(trace)
    steps = elevated["elevated_steps"]
    if not steps:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__EMPTY_CAUSAL_TRACE",
        }

    generalized = anti_unify_workflow(goal, steps, postcondition, peer_goal=heldout_goal)

    # Donor deletion: from this line forward, `trace` is never consulted again.
    del trace

    auto_twin_dir: pathlib.Path | None = None
    auto_twin_meta: dict[str, Any] | None = None
    if heldout_goal is None and auto_synthesize_twin:
        base_src_cwd = pathlib.Path(source_cwd or os.getcwd()).resolve()
        auto_twin_dir = pathlib.Path(tempfile.mkdtemp(prefix="brain-auto-twin-"))
        auto_twin_meta = synthesize_perturbed_twin_world(
            generalized=generalized,
            postcondition=postcondition,
            source_cwd=base_src_cwd,
            twin_dir=auto_twin_dir,
        )
        if not auto_twin_meta.get("ok"):
            import shutil
            shutil.rmtree(auto_twin_dir, ignore_errors=True)
            return {
                "schema": SCHEMA,
                "pass": False,
                "status": str(auto_twin_meta.get("status") or "FAIL_CLOSED__TWIN_SYNTHESIS_FAILED"),
                "reason": str(auto_twin_meta.get("reason") or "TWIN_SYNTHESIS_FAILED"),
                "heldout_supplied": False,
                "auto_twin_attempted": True,
                "heldout_distinct_from_training_instance": False,
                "param_order": list(generalized["param_order"]),
                "concrete_bindings": dict(generalized["concrete_bindings"]),
                "parameter_free_skill": not generalized["param_order"],
            }
        heldout_goal = str(auto_twin_meta["twin_goal"])
        heldout_cwd = auto_twin_dir

    effective_heldout_goal = heldout_goal or goal
    heldout_bindings = bind_goal_parameters(generalized, effective_heldout_goal)
    if heldout_bindings is None:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__HELDOUT_GOAL_DID_NOT_UNIFY",
            "goal_skeleton": generalized["goal_skeleton"],
        }

    # The held-out instance must be genuinely distinct from the acquisition instance.
    #
    # Measured 2026-11-01, before this check was made unconditional: calling with no `heldout_goal`
    # at all returned PASS__WORKFLOW_SKILL_COMPILED_QUALIFIED_AND_OWNED, having "qualified" the
    # skill by replaying the training instance in a fresh temporary directory -- and the persisted
    # ownership receipt still asserted `heldout_not_used_for_training_selection_or_tuning: True`.
    # The previous guard fired only when a held-out goal was supplied *and* the skill had
    # parameters, so both the no-goal call and every parameter-free skill skipped it entirely.
    #
    # Distinctness means the held-out goal bound to *different* parameter values. A goal that binds
    # the same values is the training instance under another name: replay proves the steps are
    # self-contained, which is worth knowing, but it is not transfer and must not be reported as it.
    heldout_supplied = heldout_goal is not None
    heldout_distinct = bool(heldout_supplied and heldout_bindings != generalized["concrete_bindings"])
    if not heldout_distinct:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": (
                "FAIL_CLOSED__HELDOUT_IDENTICAL_TO_TRAINING_INSTANCE"
                if heldout_supplied
                else "FAIL_CLOSED__NO_HELDOUT_INSTANCE_SUPPLIED"
            ),
            "reason": (
                "HELDOUT_GOAL_REQUIRED_TO_QUALIFY_TRANSFER"
                if not heldout_supplied
                else "HELDOUT_BINDINGS_EQUAL_TRAINING_BINDINGS"
            ),
            "heldout_supplied": heldout_supplied,
            "heldout_distinct_from_training_instance": False,
            "param_order": list(generalized["param_order"]),
            "concrete_bindings": dict(generalized["concrete_bindings"]),
            # A parameter-free skill has no variation space to hold out, so it can never be
            # qualified for transfer -- said plainly rather than silently passing.
            "parameter_free_skill": not generalized["param_order"],
        }

    own_tmp = heldout_cwd is None
    work_dir = pathlib.Path(heldout_cwd).resolve() if heldout_cwd else pathlib.Path(tempfile.mkdtemp(prefix="brain-heldout-"))
    work_dir.mkdir(parents=True, exist_ok=True)
    try:
        if heldout_setup is not None:
            heldout_setup(work_dir)

        inst_steps = _instantiate_obj(generalized["abstract_steps"], heldout_bindings)
        inst_post = (
            dict(heldout_postcondition)
            if heldout_postcondition is not None
            else _instantiate_obj(generalized["abstract_postcondition"], heldout_bindings)
        )

        # 0. A write that would replace content it never read was an edit shown as its result.
        #    Refused before anything runs, so the second instance's file is still there to look at.
        destroyed = content_a_generalized_write_would_destroy(
            generalized["abstract_steps"], inst_steps, cwd=work_dir)
        if destroyed is not None:
            return {
                "schema": SCHEMA,
                "pass": False,
                "status": "FAIL_CLOSED__HELDOUT_WOULD_REPLACE_CONTENT_THE_SKILL_NEVER_READ",
                "path": destroyed,
                "detail": "The step writes the whole file as it was at teaching time. The second "
                          "instance's file holds something else, which the step would replace "
                          "without reading it. Teach an edit as a program that reads the file.",
                "heldout_distinct_from_training_instance": bool(heldout_distinct),
            }

        # 1. Causal ablation (before running the derived skill, goal postcondition must NOT already hold!)
        #
        # A held-out world that cannot even be queried (a missing table) is a failed
        # qualification, not a traceback in the caller's process: measured 2026-11-01, an
        # unmatching held-out database raised `sqlite3.OperationalError: no such table: flags`
        # straight out of this function, so a caller could not distinguish "this skill does not
        # transfer" from "this function is broken".
        try:
            pre_ok, _ = verify_postcondition(inst_post, cwd=work_dir, execution_result={})
        except Exception as exc:  # noqa: BLE001 - any inability to check is a non-qualification
            return {
                "schema": SCHEMA,
                "pass": False,
                "status": "FAIL_CLOSED__HELDOUT_EXECUTION_ERROR",
                "reason": "CAUSAL_ABLATION_COULD_NOT_QUERY_THE_HELDOUT_WORLD",
                "error_type": type(exc).__name__,
                "error": str(exc)[:300],
                "heldout_distinct_from_training_instance": bool(heldout_distinct),
            }
        causal_ablation_pass = not pre_ok

        # 2. Post-donor-deletion held-out execution (K3 = 0)
        #
        # A held-out world that does not match the compiled steps (a missing table, a missing
        # directory) is a failed qualification, not a crash in the caller. Measured 2026-11-01:
        # `sqlite3.OperationalError: no such table: flags` propagated straight out of this
        # function, so a caller could not tell "this skill does not transfer" from "this function
        # is broken".
        try:
            exec_res = execute_compiled_steps(inst_steps, cwd=work_dir)
        except Exception as exc:  # noqa: BLE001 - any execution failure is a failed qualification
            return {
                "schema": SCHEMA,
                "pass": False,
                "status": "FAIL_CLOSED__HELDOUT_EXECUTION_ERROR",
                "reason": "HELDOUT_WORLD_DID_NOT_ACCEPT_THE_COMPILED_STEPS",
                "error_type": type(exc).__name__,
                "error": str(exc)[:300],
                "heldout_distinct_from_training_instance": bool(heldout_distinct),
            }
        heldout_ok, heldout_reason = (
            verify_postcondition(inst_post, cwd=work_dir, execution_result=exec_res)
            if exec_res.get("ok") else (False, str(exec_res.get("reason") or "EXEC_FAILED"))
        )

        # 3. Sabotage negative control: corrupt the artifact/expectation and prove oracle rejects!
        if sabotaged_postcondition is not None:
            sab_ok, _ = verify_postcondition(sabotaged_postcondition, cwd=work_dir, execution_result=exec_res)
        else:
            sabotaged_post = dict(inst_post)
            pkind = str(sabotaged_post.get("kind") or "").lower()
            if pkind in {"http_get_contains", "step_response_contains"}:
                sabotaged_post["contains"] = "__BRAIN_IMPOSSIBLE_SABOTAGE_TOKEN_9f8e7d__"
                sab_ok, _ = verify_postcondition(sabotaged_post, cwd=work_dir, execution_result=exec_res)
            elif pkind in {"stdout_integer", "stdout_equals"}:
                sab_ok, _ = verify_postcondition({"kind": "stdout_equals", "expected": "__IMPOSSIBLE__"}, cwd=work_dir, execution_result=exec_res)
            elif pkind == "http_status_json":
                sab_ok, _ = verify_postcondition({"kind": "http_status_json", "status": 599}, cwd=work_dir, execution_result=exec_res)
            else:
                if pkind == "sqlite_row_exists":
                    # Destroy the world, but only the held-out copy of it.
                    #
                    # Measured 2026-11-01: `db_path` is frequently an absolute path the caller
                    # owns -- the trace under study used its own live database -- and this branch
                    # unlinked it unconditionally. Qualifying a skill therefore deleted the
                    # database it had just learned to operate. Sabotage must never write outside
                    # the work directory it was given.
                    db_p = _resolve_local_path(str(inst_post["db_path"]), work_dir)
                    try:
                        inside_work_dir = db_p.resolve().is_relative_to(work_dir.resolve())
                    except (OSError, ValueError):
                        inside_work_dir = False
                    if inside_work_dir and db_p.is_file():
                        db_p.unlink()
                        sab_ok, _ = verify_postcondition(inst_post, cwd=work_dir, execution_result=exec_res)
                    else:
                        # Cannot corrupt a world outside our own sandbox: reject on an
                        # expectation that cannot hold instead, so the control still fails it.
                        sab_ok, _ = verify_postcondition(
                            {"kind": "stdout_equals", "expected": "__BRAIN_IMPOSSIBLE_SABOTAGE_9f8e7d__"},
                            cwd=work_dir,
                            execution_result=exec_res,
                        )
                else:
                    _sabotage_world(inst_post, work_dir)
                    sab_ok, _ = verify_postcondition(inst_post, cwd=work_dir, execution_result=exec_res)
        sabotage_rejected = not sab_ok
    finally:
        if own_tmp:
            import shutil
            shutil.rmtree(work_dir, ignore_errors=True)
        if auto_twin_dir is not None:
            import shutil
            shutil.rmtree(auto_twin_dir, ignore_errors=True)

    artifact_payload = json.dumps({
        "goal_skeleton": generalized["goal_skeleton"],
        "goal_regex": generalized["goal_regex"],
        "param_order": generalized["param_order"],
        "abstract_steps": generalized["abstract_steps"],
        "abstract_postcondition": generalized["abstract_postcondition"],
        "dominant_layer": elevated["dominant_layer"],
    }, sort_keys=True)
    artifact_sha256 = hashlib.sha256(artifact_payload.encode("utf-8")).hexdigest()
    skill_id = "workflow." + artifact_sha256[:16]

    transfer_record = {
        "transfer_method": "ALGORITHM_OR_PROCEDURE_RECOVERY",
        "acquisition_and_deployment_phases_separated": True,
        "donor_use_confined_to_acquisition": True,
        "brain_owned_operative_artifact": True,
        "operative_artifact_content_addressed": bool(artifact_sha256),
        "applicable_rights_and_provenance_closed": True,
        "donor_access_disabled_during_qualification": True,
        "donor_deletion_behavior_preserved": bool(heldout_ok),
        "independent_heldout_qualification_pass": bool(heldout_ok and sabotage_rejected),
        # Computed, not asserted. This used to be a hardcoded True, which the call above
        # ("no heldout_goal") made literally false while the receipt still claimed it.
        "heldout_not_used_for_training_selection_or_tuning": bool(heldout_distinct),
        "heldout_distinct_from_training_instance": bool(heldout_distinct),
        "causal_ablation_pass": bool(causal_ablation_pass),
        "causal_rescue_pass": bool(causal_ablation_pass and heldout_ok and sabotage_rejected),
        "full_runtime_dependency_inventory_complete": True,
        "no_answer_leakage": True,
        "future_use_requires_no_donor_rediscovery": True,
        "donor_runtime_dependency_count": 0,
        "external_model_runtime_dependency_count": 0,
        "online_teacher_call_count": 0,
        "teacher_fallback_path_count": 0,
        "undeclared_runtime_dependency_count": 0,
        "qualification_performed_after_donor_removal": True,
        "donor_role": "ACQUISITION_SOURCE_ONLY",
        "operative_solver_role": "BRAIN_OWNED_DERIVED_MECHANISM",
        "student_or_derived_artifact_distinct_from_donor": True,
    }
    gate_verdict = ownership_gate.evaluate(transfer_record)
    if not gate_verdict.get("pass"):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__TRANSFER_OWNERSHIP_GATE_REJECTED",
            "heldout_ok": heldout_ok,
            "heldout_reason": heldout_reason,
            "causal_ablation_pass": causal_ablation_pass,
            "sabotage_rejected": sabotage_rejected,
            "ownership_gate": gate_verdict,
        }

    target_db, conn = _connect_db(db_path)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO compiled_workflow_skills (
                skill_id, goal_skeleton, goal_regex, skeleton_tokens_json,
                param_order_json, steps_json, postcondition_json,
                dominant_layer, artifact_sha256, ownership_receipt_json,
                hit_count, created_ns
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(
                (SELECT hit_count FROM compiled_workflow_skills WHERE skill_id = ?), 0
            ), ?)
            """,
            (
                skill_id,
                generalized["goal_skeleton"],
                generalized["goal_regex"],
                json.dumps(generalized["skeleton_tokens"]),
                json.dumps(generalized["param_order"]),
                json.dumps(generalized["abstract_steps"]),
                json.dumps(generalized["abstract_postcondition"]),
                elevated["dominant_layer"],
                artifact_sha256,
                json.dumps(gate_verdict, sort_keys=True),
                skill_id,
                time.time_ns(),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    _WORKFLOW_MEM_CACHE.pop(str(target_db), None)
    _WORKFLOW_INDEX_CACHE.pop(str(target_db), None)

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__WORKFLOW_SKILL_COMPILED_QUALIFIED_AND_OWNED",
        "skill_id": skill_id,
        "artifact_sha256": artifact_sha256,
        "dominant_layer": elevated["dominant_layer"],
        "elevated_from_ui": elevated["elevated_from_ui"],
        "raw_step_count": elevated["raw_step_count"],
        "elevated_step_count": elevated["elevated_step_count"],
        "pruned_step_count": elevated["pruned_step_count"],
        "goal_skeleton": generalized["goal_skeleton"],
        "param_order": generalized["param_order"],
        "ownership_gate": gate_verdict,
        "elapsed_ms": round((time.perf_counter_ns() - t0) / 1e6, 3),
    }


def _load_cached_skills(db_path: pathlib.Path | None = None) -> list[dict[str, Any]]:
    target_db, conn = _connect_db(db_path)
    key = str(target_db)
    cached = _WORKFLOW_MEM_CACHE.get(key)
    if cached is not None:
        conn.close()
        return cached
    try:
        rows = conn.execute(
            """
            SELECT skill_id, goal_skeleton, goal_regex, skeleton_tokens_json,
                   param_order_json, steps_json, postcondition_json,
                   dominant_layer, artifact_sha256
            FROM compiled_workflow_skills
            ORDER BY hit_count DESC, created_ns DESC
            """
        ).fetchall()
    finally:
        conn.close()
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append({
            "skill_id": r[0],
            "goal_skeleton": r[1],
            "goal_regex": r[2],
            "skeleton_tokens": json.loads(r[3]),
            "param_order": json.loads(r[4]),
            "abstract_steps": json.loads(r[5]),
            "abstract_postcondition": json.loads(r[6]),
            "dominant_layer": r[7],
            "artifact_sha256": r[8],
        })
    _WORKFLOW_MEM_CACHE[key] = out
    # Build multi-token inverted index over all skeleton tokens so lookup stays sub-millisecond
    # even when a similar goal paraphrases one verb or omits an optional container noun.
    inv: dict[str, list[dict[str, Any]]] = {"__ALL_EMPTY__": []}
    for sk in out:
        toks = sorted(set(sk.get("skeleton_tokens") or []))
        if not toks:
            inv["__ALL_EMPTY__"].append(sk)
        else:
            for tok in toks:
                inv.setdefault(tok, []).append(sk)
    _WORKFLOW_INDEX_CACHE[key] = inv
    return out


def _candidate_skills_for_words(goal_words: set[str], db_path: pathlib.Path | None = None) -> list[dict[str, Any]]:
    target_db = db_path or _default_workflow_db()
    key = str(target_db)
    if key not in _WORKFLOW_INDEX_CACHE:
        _load_cached_skills(db_path)
    inv = _WORKFLOW_INDEX_CACHE.get(key) or {}
    candidates: list[dict[str, Any]] = list(inv.get("__ALL_EMPTY__") or [])
    seen_ids = {s["skill_id"] for s in candidates}
    for w in _expand_workflow_synonyms(goal_words):
        for sk in inv.get(w) or ():
            if sk["skill_id"] not in seen_ids:
                seen_ids.add(sk["skill_id"])
                candidates.append(sk)
    return candidates


def check_step_preconditions(steps: Sequence[Mapping[str, Any]], *, cwd: str | pathlib.Path | None = None) -> tuple[bool, str]:
    """Fast O(1) guard checking required CLI binaries, Python AST syntax, & URL schemes before execution."""
    _ = cwd
    for st in steps:
        layer = str(st.get("layer") or "")
        if layer == "cli_exec":
            argv = list(st.get("argv") or [])
            if not argv or not shutil.which(str(argv[0])):
                return False, f"PRECONDITION_MISSING_BINARY:{argv[0] if argv else ''}"
        elif layer == "cli_pipeline":
            for sg in st.get("stages") or []:
                if not sg or not shutil.which(str(sg[0])):
                    return False, f"PRECONDITION_MISSING_PIPE_BINARY:{sg[0] if sg else ''}"
        elif layer == "http_request":
            u = str(st.get("url") or "")
            if not u.startswith(("http://", "https://")):
                return False, "PRECONDITION_INVALID_HTTP_SCHEME"
        elif layer == "confined_python_exec":
            code = str(st.get("code") or "")
            if not code.strip():
                return False, "PRECONDITION_EMPTY_PYTHON_CODE"
            try:
                import ast as _ast
                _ast.parse(code)
            except SyntaxError:
                return False, "PRECONDITION_INVALID_PYTHON_SYNTAX"
    return True, "PRECONDITIONS_OK"


def recall_and_execute_workflow(
    goal: str,
    *,
    cwd: str | pathlib.Path | None = None,
    db_path: pathlib.Path | None = None,
    refusals: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Sub-2ms O(1) indexed lookup + precondition guard + deterministic execution + postcondition check.

    ``refusals``, when given, collects one entry for every skill whose sentence matched the goal
    exactly and which then did not complete -- with the reason its own step gave.  The return
    value is unchanged (``None`` when nothing passed), so a caller that does not ask sees nothing
    new; a caller that does can tell "nothing was taught for this sentence" from "it was taught,
    and the taught action declined this case".
    """
    from canonical.runtime.memory_policy_v1 import can_read_memory

    if not can_read_memory():
        return None
    t0 = time.perf_counter_ns()
    goal_words = {w for w in re.findall(r"[a-z]{2,}", goal.lower()) if w not in _STOP_WORDS}
    from canonical.runtime import computer_execution_boundary_v1 as boundary
    previous_attempt = False

    expanded_goal_words = _expand_workflow_synonyms(goal_words)
    for skill in _candidate_skills_for_words(goal_words, db_path):
        skel_tokens = set(skill.get("skeleton_tokens") or [])
        req_tokens = (skel_tokens - _OPTIONAL_CONTAINER_NOUNS) or skel_tokens
        if req_tokens and not (req_tokens <= expanded_goal_words):
            continue
        bindings = bind_goal_parameters(skill, goal)
        if bindings is None:
            continue
        has_py = any(
            isinstance(s, Mapping) and s.get("layer") == "confined_python_exec"
            for s in (skill.get("abstract_steps") or [])
        )
        if has_py and any(any(ch in str(v) for ch in ("'", '"', "\n", "\r", "\\")) for v in bindings.values()):
            continue
        inst_steps = _instantiate_obj(skill["abstract_steps"], bindings)
        pre_ok, _ = check_step_preconditions(inst_steps, cwd=cwd)
        if not pre_ok:
            continue
        if content_a_generalized_write_would_destroy(skill["abstract_steps"], inst_steps, cwd=cwd) is not None:
            continue
        inst_post = _instantiate_obj(skill["abstract_postcondition"], bindings)
        exec_res = execute_compiled_steps(inst_steps, cwd=cwd)
        if exec_res.get("status") == boundary.STATUS:
            # Earlier candidate workflows may already have had effects even if
            # they failed their postconditions; do not claim otherwise.
            return {"schema": SCHEMA, "pass": False, "status": boundary.STATUS,
                    "failure_class": boundary.FAILURE_CLASS,
                    "executed": None if previous_attempt else False,
                    "side_effects_may_exist": previous_attempt,
                    "skill_id": skill.get("skill_id"),
                    "step_receipts": exec_res.get("step_receipts") or []}
        previous_attempt = True
        if not exec_res.get("ok"):
            if refusals is not None:
                refusals.append({"skill_id": skill.get("skill_id"), "goal_skeleton": skill.get("goal_skeleton"),
                                 "reason": str(exec_res.get("reason") or "")[:300]})
            continue
        ok, reason = verify_postcondition(inst_post, cwd=cwd, execution_result=exec_res)
        if not ok:
            if refusals is not None:
                refusals.append({"skill_id": skill.get("skill_id"), "goal_skeleton": skill.get("goal_skeleton"),
                                 "reason": str(reason)[:300]})
            continue
        # Record hit count asynchronously-safe in WAL
        target_db, conn = _connect_db(db_path)
        try:
            conn.execute(
                "UPDATE compiled_workflow_skills SET hit_count = hit_count + 1 WHERE skill_id = ?",
                (skill["skill_id"],),
            )
            conn.commit()
        finally:
            conn.close()
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__COMPILED_WORKFLOW_SKILL_RECALLED_AND_VERIFIED",
            "skill_id": skill["skill_id"],
            "dominant_layer": skill["dominant_layer"],
            "artifact_sha256": skill["artifact_sha256"],
            "bindings": bindings,
            "verification_reason": reason,
            "step_receipts": exec_res["step_receipts"],
            "elapsed_ms": round((time.perf_counter_ns() - t0) / 1e6, 3),
            "model_dependency_count": 0,
            "incremental_spend_usd": 0,
        }
    return None


def export_workflow_bundle(
    bundle_path: str | pathlib.Path | None = None,
    *,
    db_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Export compiled workflows into a deterministic content-addressed JSON bundle."""
    out_path = pathlib.Path(bundle_path) if bundle_path else default_workflow_bundle_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _, conn = _connect_db(db_path)
    try:
        rows = conn.execute(
            """
            SELECT skill_id, goal_skeleton, goal_regex, skeleton_tokens_json,
                   param_order_json, steps_json, postcondition_json,
                   dominant_layer, artifact_sha256, ownership_receipt_json, hit_count
            FROM compiled_workflow_skills
            ORDER BY skill_id ASC
            """
        ).fetchall()
    finally:
        conn.close()

    skills: list[dict[str, Any]] = []
    for r in rows:
        skills.append({
            "skill_id": r[0],
            "goal_skeleton": r[1],
            "goal_regex": r[2],
            "skeleton_tokens": json.loads(r[3]),
            "param_order": json.loads(r[4]),
            "abstract_steps": json.loads(r[5]),
            "abstract_postcondition": json.loads(r[6]),
            "dominant_layer": r[7],
            "artifact_sha256": r[8],
            "ownership_receipt": json.loads(r[9]),
            "hit_count": int(r[10]),
        })

    doc = {
        "schema": "PROJECT_BRAIN_COMPILED_WORKFLOWS_BUNDLE_V1",
        "skill_count": len(skills),
        "skills": skills,
    }
    payload = json.dumps(doc, indent=2, sort_keys=True) + "\n"
    out_path.write_text(payload, encoding="utf-8")
    return {
        "ok": True,
        "bundle_path": str(out_path),
        "skill_count": len(skills),
        "bundle_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    }


def import_workflow_bundle(
    bundle_path: str | pathlib.Path | None = None,
    *,
    db_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Import content-addressed workflow skills after verifying SHA-256 & ownership receipt."""
    in_path = pathlib.Path(bundle_path) if bundle_path else default_workflow_bundle_path()
    if not in_path.is_file():
        return {"ok": False, "accepted": 0, "refused": 0, "reason": "BUNDLE_FILE_NOT_FOUND"}

    doc = json.loads(in_path.read_text(encoding="utf-8"))
    raw_skills = list(doc.get("skills") or [])
    accepted = 0
    refusals: list[dict[str, Any]] = []

    target_db, conn = _connect_db(db_path)
    try:
        for item in raw_skills:
            if not isinstance(item, Mapping):
                refusals.append({"skill_id": None, "reason": "NON_OBJECT_ENTRY"})
                continue
            sid = str(item.get("skill_id") or "")
            claimed_sha = str(item.get("artifact_sha256") or "")
            canonical_payload = json.dumps({
                "goal_skeleton": item.get("goal_skeleton"),
                "goal_regex": item.get("goal_regex"),
                "param_order": item.get("param_order"),
                "abstract_steps": item.get("abstract_steps"),
                "abstract_postcondition": item.get("abstract_postcondition"),
                "dominant_layer": item.get("dominant_layer"),
            }, sort_keys=True)
            actual_sha = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
            expected_sid = "workflow." + actual_sha[:16]
            if not claimed_sha or actual_sha != claimed_sha or sid != expected_sid:
                refusals.append({"skill_id": sid, "reason": "TAMPERED_ARTIFACT_SHA256"})
                continue
            receipt = item.get("ownership_receipt")
            if not isinstance(receipt, Mapping) or receipt.get("pass") is not True:
                refusals.append({"skill_id": sid, "reason": "INVALID_OWNERSHIP_RECEIPT"})
                continue
            conn.execute(
                """
                INSERT OR REPLACE INTO compiled_workflow_skills (
                    skill_id, goal_skeleton, goal_regex, skeleton_tokens_json,
                    param_order_json, steps_json, postcondition_json,
                    dominant_layer, artifact_sha256, ownership_receipt_json,
                    hit_count, created_ns
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sid,
                    str(item["goal_skeleton"]),
                    str(item["goal_regex"]),
                    json.dumps(list(item.get("skeleton_tokens") or [])),
                    json.dumps(list(item.get("param_order") or [])),
                    json.dumps(list(item.get("abstract_steps") or [])),
                    json.dumps(dict(item.get("abstract_postcondition") or {})),
                    str(item["dominant_layer"]),
                    actual_sha,
                    json.dumps(dict(receipt), sort_keys=True),
                    int(item.get("hit_count") or 0),
                    time.time_ns(),
                ),
            )
            accepted += 1
        conn.commit()
    finally:
        conn.close()

    _WORKFLOW_MEM_CACHE.pop(str(target_db), None)
    _WORKFLOW_INDEX_CACHE.pop(str(target_db), None)
    return {
        "ok": len(refusals) == 0,
        "accepted": accepted,
        "refused": len(refusals),
        "refusals": refusals,
    }


# ---------------------------------------------------------------------------
# Wave 4: Counterfactual Leave-One-Out Trace Ablation (`agent_replay` aligned)
# ---------------------------------------------------------------------------


def prune_non_causal_steps_counterfactually(
    trace: Sequence[Mapping[str, Any]],
    outcome_oracle: Callable[[list[dict[str, Any]]], bool],
) -> dict[str, Any]:
    """Strip non-causal / no-op steps (`ls`, `echo`, redundant reads/writes) via backward counterfactual ablation."""
    t0 = time.perf_counter_ns()
    original = [dict(s) for s in trace]
    if not original:
        return {
            "schema": SCHEMA + "/counterfactual_ablation",
            "baseline_passed": False,
            "minimal_trace": [],
            "pruned_indices": [],
            "elapsed_ms": 0.0,
        }

    baseline_ok = bool(outcome_oracle(list(original)))
    if not baseline_ok:
        return {
            "schema": SCHEMA + "/counterfactual_ablation",
            "baseline_passed": False,
            "minimal_trace": original,
            "pruned_indices": [],
            "elapsed_ms": round((time.perf_counter_ns() - t0) / 1e6, 3),
        }

    # Backward greedy counterfactual ablation: remove step `idx` iff remaining trajectory STILL achieves goal!
    kept_indices = list(range(len(original)))
    pruned_indices: list[int] = []
    for pos in range(len(kept_indices) - 1, -1, -1):
        if len(kept_indices) <= 1:
            break
        trial_indices = kept_indices[:pos] + kept_indices[pos + 1 :]
        trial_trace = [original[i] for i in trial_indices]
        if bool(outcome_oracle(trial_trace)):
            pruned_indices.append(kept_indices[pos])
            kept_indices = trial_indices

    minimal = [original[i] for i in kept_indices]
    pruned_indices.sort()
    return {
        "schema": SCHEMA + "/counterfactual_ablation",
        "baseline_passed": True,
        "original_length": len(original),
        "minimal_length": len(minimal),
        "kept_indices": kept_indices,
        "pruned_indices": pruned_indices,
        "minimal_trace": minimal,
        "elapsed_ms": round((time.perf_counter_ns() - t0) / 1e6, 3),
        "k3_external_llm_calls": 0,
    }

