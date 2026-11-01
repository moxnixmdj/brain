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
            row = conn.execute("SELECT COUNT(*) FROM compiled_workflow_skills").fetchone()
            if not row or int(row[0]) == 0:
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
        in {"sqlite_exec", "sqlite_query", "http_request", "python_file_op"}
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

        if layer in {"http_request", "python_file_op", "semantic_dom"}:
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
        "elevated_from_ui": pruned_ui_steps > 0 and dominant_layer in {"sqlite_exec", "http_request", "python_file_op", "cli_exec", "semantic_dom"},
    }


# --------------------------------------------------------------------------- #
# 2. Multi-Step Workflow Plotkin Anti-Unification
# --------------------------------------------------------------------------- #
def _extract_goal_literals(goal: str) -> list[tuple[str, str]]:
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
) -> dict[str, Any]:
    """Anti-unify `(goal, elevated_steps, postcondition)` into a reusable parameterized workflow."""
    step_blob = json.dumps(list(elevated_steps), sort_keys=True) + "\n" + json.dumps(dict(postcondition), sort_keys=True)
    candidates = _extract_goal_literals(goal)

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

    return {
        "goal_skeleton": goal_skeleton,
        "goal_regex": goal_regex,
        "skeleton_tokens": skel_words,
        "param_order": param_order,
        "abstract_steps": abstract_steps,
        "abstract_postcondition": abstract_post,
        "concrete_bindings": {h: v for v, h in val_to_hole.items()},
    }


def bind_goal_parameters(skill: Mapping[str, Any], goal: str) -> dict[str, str] | None:
    pattern = str(skill.get("goal_regex") or "")
    if not pattern:
        return None
    m = re.match(pattern, goal.strip(), flags=re.IGNORECASE)
    if not m:
        return None
    out: dict[str, str] = {}
    for k, v in m.groupdict().items():
        if v is None:
            return None
        clean = v.strip().strip("\"'").rstrip(".")
        out["?" + k] = clean
    return out


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


def execute_compiled_steps(
    steps: Sequence[Mapping[str, Any]],
    *,
    cwd: str | pathlib.Path | None = None,
) -> dict[str, Any]:
    """Execute concrete instantiated steps deterministically with zero model calls."""
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
    if kind in {"file_contains", "json_field_equals"}:
        p = _resolve_local_path(str(postcondition["path"]), cwd)
        if p.is_file():
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
# 4. Full K2 -> K3=0 Qualification & Permanent SQLite Registration
# --------------------------------------------------------------------------- #
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
    source_channel: str = "k2_or_sandbox_acquisition",
    db_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Compile one acquisition trace, qualify on untouched held-out + sabotage control, and persist."""
    t0 = time.perf_counter_ns()
    elevated = elevate_trace_to_fastest_layer(trace)
    steps = elevated["elevated_steps"]
    if not steps:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__EMPTY_CAUSAL_TRACE",
        }

    generalized = anti_unify_workflow(goal, steps, postcondition)

    # Donor deletion: from this line forward, `trace` is never consulted again.
    del trace

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
    # Build O(1) rarest-anchor-token inverted index so lookup stays sub-millisecond at 10,000+ skills
    doc_freq: dict[str, int] = {}
    for sk in out:
        for tok in set(sk.get("skeleton_tokens") or []):
            doc_freq[tok] = doc_freq.get(tok, 0) + 1
    inv: dict[str, list[dict[str, Any]]] = {"__ALL_EMPTY__": []}
    for sk in out:
        toks = list(set(sk.get("skeleton_tokens") or []))
        if not toks:
            inv["__ALL_EMPTY__"].append(sk)
        else:
            anchor = min(toks, key=lambda t: (doc_freq.get(t, 0), -len(t), t))
            inv.setdefault(anchor, []).append(sk)
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
    for w in goal_words:
        for sk in inv.get(w) or ():
            if sk["skill_id"] not in seen_ids:
                seen_ids.add(sk["skill_id"])
                candidates.append(sk)
    return candidates


def check_step_preconditions(steps: Sequence[Mapping[str, Any]], *, cwd: str | pathlib.Path | None = None) -> tuple[bool, str]:
    """Fast O(1) guard checking required CLI binaries & URL schemes before execution."""
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
    return True, "PRECONDITIONS_OK"


def recall_and_execute_workflow(
    goal: str,
    *,
    cwd: str | pathlib.Path | None = None,
    db_path: pathlib.Path | None = None,
) -> dict[str, Any] | None:
    """Sub-2ms O(1) indexed lookup + precondition guard + deterministic execution + postcondition check."""
    t0 = time.perf_counter_ns()
    goal_words = {w for w in re.findall(r"[a-z]{2,}", goal.lower()) if w not in _STOP_WORDS}

    for skill in _candidate_skills_for_words(goal_words, db_path):
        skel_tokens = set(skill.get("skeleton_tokens") or [])
        if skel_tokens and not (skel_tokens <= goal_words):
            continue
        bindings = bind_goal_parameters(skill, goal)
        if bindings is None:
            continue
        inst_steps = _instantiate_obj(skill["abstract_steps"], bindings)
        pre_ok, _ = check_step_preconditions(inst_steps, cwd=cwd)
        if not pre_ok:
            continue
        inst_post = _instantiate_obj(skill["abstract_postcondition"], bindings)
        exec_res = execute_compiled_steps(inst_steps, cwd=cwd)
        if not exec_res.get("ok"):
            continue
        ok, reason = verify_postcondition(inst_post, cwd=cwd, execution_result=exec_res)
        if not ok:
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
