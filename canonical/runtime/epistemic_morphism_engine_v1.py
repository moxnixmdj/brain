"""Goal-Directed Epistemic Morphism Compiler & Compositional Planner.

Answers the core architectural question cleanly under Elon's Law ("the best part
is no part" + insanely fast):

  1. GOAL-DEFINED EPISTEMIC DIFF (not "learn everything on the OS"):
     - Scan ONLY the workspace (~2ms, zero network) into typed objects via magic
       bytes + extensions.
     - Decompose the goal into a typed transition chain:
         `[(in_type_1, verb_1) -> out_type_1, (in_type_2, verb_2) -> out_type_2, ...]`
     - Compute `Gaps = Required_Transitions \\ Known_Morphisms_In_Memory` (<1ms).
     - Query local `--help` + live web (`tldr-pages` + `jit_knowledge_v1`) IN
       PARALLEL ONLY for the missing `Gaps`. Discard raw prose immediately.

  2. GENERALIZED MEMORY — ATOMIC COMPOSABLE MORPHISMS (never dumb concrete actions):
     - NEVER store concrete filenames, workspace paths, secrets, raw web HTML,
       or monolithic task-specific scripts.
     - Store ONLY atomic typed transition laws (`BRAIN_EPISTEMIC_MORPHISM_STORE_V1`,
       `parameters_stored: 0`, `external_model_dependency: False`):
           `(in_type, verb) --[hole_template + preconditions]--> out_type`
     - Unseen multi-step pipelines recombine previously learned atomic morphisms
       OFFLINE in milliseconds with zero web lookups; hybrid pipelines fetch ONLY
       the missing bridge step(s).
     - Single counterexample narrows or quarantines a morphism fail-closed;
       deleting a JSON entry immediately removes recall.

  3. STATE-COPY EXECUTION & FRAME INVARIANCE:
     - Composed pipelines run step-by-step in an isolated tempdir copy, re-sensing
       intermediate types between steps and refining failed steps from `stderr`.
     - Only verified final outputs are committed to the real workspace (temporary
       intermediate stage files are never leaked).
"""
from __future__ import annotations

import base64
import collections
import concurrent.futures
import dataclasses
import gzip
import hashlib
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import time
import zipfile
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import epistemic_computer_use_engine_v1 as EPI

SCHEMA = "BRAIN_EPISTEMIC_MORPHISM_ENGINE_V1"
STORE_SCHEMA = "BRAIN_EPISTEMIC_MORPHISM_STORE_V1"
AUTHORITY = "NONE"

STATUS_PROVISIONAL = "PROVISIONAL__VERIFIED_MORPHISM"
STATUS_NARROWED = "NARROWED__COUNTEREXAMPLE_REFINED"
STATUS_QUARANTINED = "QUARANTINED__NO_OBSERVABLE_SEPARATION"

MORPHISM_HOLES = frozenset({"__IN__", "__OUT__", "__IN_DIR__", "__OUT_DIR__", "__EXPR__"})

# Ordered canonical action verbs -> (default_in_type, default_out_type, candidate_tools)
# NOTE: Zero flags or command templates are stored here! Tools are ONLY hints for
# which installed binary to interrogate via `--help` + live web when memory misses.
_VERB_SPECS: list[tuple[str, tuple[str, ...], str, str, tuple[str, ...]]] = [
    ("decode_base64", ("decode base64", "base64 decode", "base64-decode", "decode the base64", "from base64"), "file:base64", "file:any", ("base64",)),
    ("encode_base64", ("encode base64", "base64 encode", "to base64"), "file:any", "file:base64", ("base64",)),
    ("decompress_gzip", ("gunzip", "decompress gzip", "decompress the gzip", "decompress .gz"), "file:gzip", "file:any", ("gzip",)),
    ("extract_archive", ("extract", "untar", "unpack", "unzip"), "file:archive", "dir", ("tar", "unzip")),
    ("create_archive", ("tarball", "create a gzipped tar", "create tar", "compress directory", "archive into"), "dir", "file:archive", ("tar", "zip")),
    ("filter_json", ("jq", "filter json", "filter the json", "query json", "extract json"), "file:json", "file:text", ("jq",)),
    ("apply_patch", ("apply patch", "apply the patch", "patch "), "file:patch", "file:any", ("patch",)),
    ("replace_text", ("sed", "replace", "substitute"), "file:text", "file:text", ("sed",)),
    ("search_text", ("grep", "search", "matching lines", "filter lines"), "file:text", "file:text", ("grep",)),
    ("extract_column", ("awk", "column", "field"), "file:text", "file:text", ("awk", "cut")),
    ("sort_unique", ("sort unique", "sort and deduplicate", "unique sort", "removing duplicates", "deduplicate", "sort lines"), "file:text", "file:text", ("sort",)),
    ("hash_sha256", ("sha256", "sha-256", "checksum"), "file:any", "file:text", ("sha256sum",)),
]


# ---------------------------------------------------------------------------
# 1. External Inspectable / Editable / Deletable Atomic Morphism Store
# ---------------------------------------------------------------------------

def new_morphism_store() -> dict[str, Any]:
    return {
        "schema": STORE_SCHEMA,
        "authority": AUTHORITY,
        "external_model_dependency": False,
        "parameters_stored": 0,
        "morphisms": {},
        "negative_host_facts": {"no_help_flag": []},
    }


def load_morphism_store(path: str | pathlib.Path) -> dict[str, Any]:
    p = pathlib.Path(path)
    if not p.is_file():
        return new_morphism_store()
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != STORE_SCHEMA:
        raise ValueError(f"UNEXPECTED_MORPHISM_STORE_SCHEMA: {data.get('schema')!r}")
    data.setdefault("morphisms", {})
    data.setdefault("negative_host_facts", {"no_help_flag": []})
    return data


def save_morphism_store(store: Mapping[str, Any], path: str | pathlib.Path) -> pathlib.Path:
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(store, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p


def delete_morphism(store: dict[str, Any], morphism_id: str) -> bool:
    ms = store.get("morphisms")
    if isinstance(ms, dict) and morphism_id in ms:
        del ms[morphism_id]
        return True
    return False


def _has_leaked_literal_path(template: str) -> bool:
    for bad in ("/tmp/", "/home/", "/var/", "/app/"):
        if bad in template:
            return True
    return False


def induce_morphism(
    store: dict[str, Any],
    *,
    in_type: str,
    verb: str,
    out_type: str,
    tool: str,
    concrete_command: str,
    redirect_stdout: bool,
    hole_bindings: Mapping[str, str],
    observables: Sequence[str],
    corroborated_kinds: Sequence[str],
    source_url: str,
) -> dict[str, Any] | None:
    """Distill ONE verified execution into a pure, generalized atomic morphism.

    Admission gates:
      1. Every concrete workspace value must abstract cleanly to typed holes.
      2. Zero host paths (/tmp, /home, /var, /app) may remain in `command_template`.
      3. Exact round-trip instantiation must reconstruct `concrete_command`.
    """
    valid_bindings = {h: str(v) for h, v in hole_bindings.items() if h in MORPHISM_HOLES and str(v)}
    if not valid_bindings:
        return None

    tpl = concrete_command
    # Abstract longest concrete values first so sub-strings don't clobber parent paths
    for hole, concrete in sorted(valid_bindings.items(), key=lambda kv: -len(kv[1])):
        quoted = shlex.quote(concrete)
        if quoted in tpl:
            tpl = tpl.replace(quoted, hole)
        elif concrete in tpl:
            tpl = tpl.replace(concrete, hole)

    if _has_leaked_literal_path(tpl):
        return None

    # Must actually contain at least one generalized hole (no concrete one-off macros!)
    used_holes = sorted(h for h in MORPHISM_HOLES if h in tpl)
    if not used_holes:
        return None

    # Exact round-trip check
    rebuilt = instantiate_morphism_command(tpl, valid_bindings)
    # Normalize benign single-quote vs unquoted identifier differences in shlex
    try:
        if shlex.split(rebuilt) != shlex.split(concrete_command):
            return None
    except ValueError:
        if rebuilt != concrete_command:
            return None

    sig = json.dumps({
        "in_type": in_type,
        "verb": verb,
        "out_type": out_type,
        "tool": tool,
        "template": tpl,
        "redirect_stdout": redirect_stdout,
    }, sort_keys=True)
    mid = "morph_" + hashlib.sha256(sig.encode("utf-8")).hexdigest()[:12]

    obs_sorted = sorted(set(str(o) for o in observables))
    ms = store.setdefault("morphisms", {})
    existing = ms.get(mid)
    if existing is not None:
        existing["support_count"] = int(existing.get("support_count", 1)) + 1
        prev_sup = set(existing.get("support_observables") or ())
        existing["support_observables"] = sorted(prev_sup & set(obs_sorted)) if prev_sup else obs_sorted
        return existing

    core_req = [o for o in obs_sorted if o.startswith(("tool:", "in_type:", "has_expr:"))]
    rec = {
        "morphism_id": mid,
        "status": STATUS_PROVISIONAL,
        "in_type": in_type,
        "verb": verb,
        "out_type": out_type,
        "tool": tool,
        "command_template": tpl,
        "redirect_stdout": bool(redirect_stdout),
        "required_holes": used_holes,
        "required_observables": sorted(core_req),
        "support_observables": obs_sorted,
        "corroborated_kinds": sorted(set(corroborated_kinds)),
        "source_url": source_url,
        "support_count": 1,
        "refutations": [],
        "external_model_dependency": False,
        "parameters_stored": 0,
    }
    ms[mid] = rec
    return rec


def instantiate_morphism_command(template: str, bindings: Mapping[str, str]) -> str:
    cmd = template
    for hole in sorted(MORPHISM_HOLES, key=len, reverse=True):
        if hole not in cmd:
            continue
        val = str(bindings.get(hole, ""))
        if not val:
            continue
        idx = cmd.find(hole)
        while idx >= 0:
            quoted_around = (
                idx > 0
                and idx + len(hole) < len(cmd)
                and cmd[idx - 1] == cmd[idx + len(hole)]
                and cmd[idx - 1] in ("'", '"')
            )
            rep = val if quoted_around else shlex.quote(val)
            cmd = cmd[:idx] + rep + cmd[idx + len(hole):]
            idx = cmd.find(hole, idx + len(rep))
    return cmd


def _type_compatible(stored_type: str, actual_type: str) -> bool:
    if stored_type == actual_type or stored_type == "file:any" or actual_type == "file:any":
        return True
    if stored_type == "file:archive" and actual_type in ("file:tar.gz", "file:tar", "file:zip", "file:gzip"):
        return True
    if actual_type == "file:archive" and stored_type in ("file:tar.gz", "file:tar", "file:zip", "file:gzip"):
        return True
    return False


def recall_morphisms(
    store: Mapping[str, Any],
    *,
    verb: str,
    in_type: str,
    observables: Sequence[str],
    available_holes: Mapping[str, str],
) -> list[dict[str, Any]]:
    obs_set = set(str(o) for o in observables)
    ms = store.get("morphisms") or {}
    out: list[dict[str, Any]] = []
    for mid, m in sorted(ms.items(), key=lambda kv: (-int(kv[1].get("support_count", 1)), kv[0])):
        if m.get("status") == STATUS_QUARANTINED:
            continue
        if m.get("verb") != verb:
            continue
        if not _type_compatible(str(m.get("in_type") or "file:any"), in_type):
            continue
        req_obs = set(m.get("required_observables") or ())
        if not req_obs.issubset(obs_set):
            continue
        req_holes = m.get("required_holes") or []
        if any(h not in available_holes or not str(available_holes[h]) for h in req_holes):
            continue
        out.append(dict(m))
    return out


def refute_morphism(
    store: dict[str, Any],
    morphism_id: str,
    *,
    counterexample_observables: Sequence[str],
    reason: str = "EXECUTION_FAILED",
) -> dict[str, Any]:
    ms = store.get("morphisms") or {}
    m = ms.get(morphism_id)
    if m is None:
        return {"morphism_id": morphism_id, "status": "NOT_FOUND"}
    ce_set = set(str(o) for o in counterexample_observables)
    sup_set = set(m.get("support_observables") or ())
    req_set = set(m.get("required_observables") or ())
    seps = sorted((sup_set - ce_set) - req_set)
    if seps:
        added = seps[0]
        req_set.add(added)
        m["required_observables"] = sorted(req_set)
        m["status"] = STATUS_NARROWED
        m.setdefault("refutations", []).append({"reason": reason, "added_observable": added})
        return {"morphism_id": morphism_id, "status": "NARROWED", "added_observable": added}
    m["status"] = STATUS_QUARANTINED
    m.setdefault("refutations", []).append({"reason": reason, "resolution": "QUARANTINED"})
    return {"morphism_id": morphism_id, "status": "QUARANTINED"}


# ---------------------------------------------------------------------------
# 2. Fast Media-Type Sensing & Multi-Step Goal Decomposition
# ---------------------------------------------------------------------------

def infer_file_media_type(path: pathlib.Path) -> str:
    if path.is_dir():
        return "dir"
    low = path.name.lower()
    if low.endswith((".tar.gz", ".tgz")):
        return "file:tar.gz"
    if low.endswith(".tar"):
        return "file:tar"
    if low.endswith(".zip"):
        return "file:zip"
    if low.endswith((".b64", ".base64")):
        return "file:base64"
    if low.endswith(".json"):
        return "file:json"
    if low.endswith((".patch", ".diff")):
        return "file:patch"
    if low.endswith(".gz"):
        return "file:gzip"

    # Fall back to magic bytes (works even for extensionless intermediate artifacts!)
    magic = EPI._detect_magic(path)
    if magic == "gzip":
        # Check whether gzip wraps a tar archive!
        try:
            with tarfile.open(path, "r:gz") as tf:
                if tf.getmembers():
                    return "file:tar.gz"
        except Exception:
            pass
        return "file:gzip"
    if magic == "tar":
        return "file:tar"
    if magic == "zip":
        return "file:zip"
    if magic == "json_like":
        return "file:json"
    if magic == "unified_diff":
        return "file:patch"
    if magic == "text":
        # Detect opaque extensionless Base64-encoded binary/text payloads cleanly
        try:
            raw_txt = path.read_text(encoding="ascii").strip()
            compact = re.sub(r"\s+", "", raw_txt)
            if (
                len(compact) >= 24
                and len(compact) % 4 == 0
                and re.fullmatch(r"[A-Za-z0-9+/]+=*", compact)
                and ("+" in compact or "/" in compact or compact.endswith("=") or len(raw_txt.split()) == 1)
            ):
                decoded = base64.b64decode(compact, validate=True)
                # Confirm decoded payload has structured/binary signature (gzip, zip, tar, json, or high-entropy)
                if (
                    decoded.startswith((b"\x1f\x8b", b"PK\x03\x04", b"SQLite format 3", b"{", b"["))
                    or (len(decoded) >= 265 and decoded[257:262] == b"ustar")
                    or any(b < 9 or (13 < b < 32) for b in decoded[:64])
                ):
                    return "file:base64"
        except Exception:
            pass
        return "file:text"
    return "file:any"


def plan_morphism_path(
    store: Mapping[str, Any],
    start_type: str,
    target_type: str,
    *,
    max_depth: int = 5,
) -> list[dict[str, Any]]:
    """Shortest-path BFS over generalized atomic morphisms in `store` (<0.1ms).

    Finds a typed morphism chain `start_type -> ... -> target_type` without any
    intermediate verbs named by the caller.
    """
    if _type_compatible(target_type, start_type):
        return []
    ms = [
        m for m in (store.get("morphisms") or {}).values()
        if m.get("status") != STATUS_QUARANTINED
    ]
    queue: collections.deque[tuple[str, list[dict[str, Any]]]] = collections.deque([(start_type, [])])
    visited: set[str] = {start_type}
    while queue:
        cur_t, path = queue.popleft()
        if len(path) >= max_depth:
            continue
        for m in ms:
            if not _type_compatible(str(m.get("in_type") or "file:any"), cur_t):
                continue
            nxt_t = str(m.get("out_type") or "file:any")
            nxt_path = path + [m]
            if _type_compatible(target_type, nxt_t) and nxt_t != "file:any":
                return nxt_path
            if nxt_t not in visited:
                visited.add(nxt_t)
                queue.append((nxt_t, nxt_path))
    return []


_CONTAINER_TYPES = frozenset({"file:base64", "file:gzip", "file:tar.gz", "file:tar", "file:zip"})


def _infer_unwrap_subgoal(media_type: str, step_idx: int) -> TransitionSubgoal | None:
    """Given an opaque container media type, return the minimal unwrap transition."""
    if media_type == "file:base64":
        return TransitionSubgoal(
            index=step_idx,
            clause="decode base64 file",
            verb="decode_base64",
            in_type="file:base64",
            out_type="file:any",
            candidate_tools=["base64"] if shutil.which("base64") else [],
            explicit_in_path=None,
            explicit_in_dir=None,
            explicit_out_path=None,
            explicit_out_dir=None,
            quoted_expr=None,
            raw_output_requested=False,
            ignore_case_requested=False,
        )
    if media_type == "file:gzip":
        return TransitionSubgoal(
            index=step_idx,
            clause="decompress gzip file to stdout",
            verb="decompress_gzip",
            in_type="file:gzip",
            out_type="file:any",
            candidate_tools=["gzip"] if shutil.which("gzip") else [],
            explicit_in_path=None,
            explicit_in_dir=None,
            explicit_out_path=None,
            explicit_out_dir=None,
            quoted_expr=None,
            raw_output_requested=False,
            ignore_case_requested=False,
        )
    if media_type in ("file:tar.gz", "file:tar"):
        return TransitionSubgoal(
            index=step_idx,
            clause="extract tar archive into directory",
            verb="extract_archive",
            in_type=media_type,
            out_type="dir",
            candidate_tools=["tar"] if shutil.which("tar") else [],
            explicit_in_path=None,
            explicit_in_dir=None,
            explicit_out_path=None,
            explicit_out_dir=None,
            quoted_expr=None,
            raw_output_requested=False,
            ignore_case_requested=False,
        )
    if media_type == "file:zip":
        return TransitionSubgoal(
            index=step_idx,
            clause="extract zip archive into directory",
            verb="extract_archive",
            in_type="file:zip",
            out_type="dir",
            candidate_tools=["unzip"] if shutil.which("unzip") else [],
            explicit_in_path=None,
            explicit_in_dir=None,
            explicit_out_path=None,
            explicit_out_dir=None,
            quoted_expr=None,
            raw_output_requested=False,
            ignore_case_requested=False,
        )
    return None


@dataclasses.dataclass
class TransitionSubgoal:
    index: int
    clause: str
    verb: str
    in_type: str
    out_type: str
    candidate_tools: list[str]
    explicit_in_path: str | None
    explicit_in_dir: str | None
    explicit_out_path: str | None
    explicit_out_dir: str | None
    quoted_expr: str | None
    raw_output_requested: bool
    ignore_case_requested: bool


_OPEN_VOCAB_ENGLISH_STOPWORDS = frozenset({
    "a", "an", "and", "as", "at", "by", "cat", "check", "clear", "column", "command",
    "copy", "count", "create", "data", "date", "dir", "do", "echo", "env", "exit",
    "false", "file", "files", "find", "folder", "for", "free", "from", "get", "group",
    "groups", "host", "id", "if", "in", "info", "input", "install", "into", "is",
    "join", "kill", "last", "less", "line", "lines", "link", "list", "log", "make",
    "man", "more", "move", "name", "new", "nice", "no", "not", "of", "on", "only",
    "open", "or", "out", "output", "path", "print", "raw", "read", "remove", "result",
    "return", "run", "save", "script", "see", "set", "show", "size", "sleep", "split",
    "stat", "sum", "sync", "test", "text", "that", "the", "then", "this", "time", "to",
    "top", "touch", "true", "type", "unique", "use", "user", "users", "using", "value",
    "values", "wait", "watch", "where", "which", "who", "with", "word", "words", "write",
    "yes",
})


def _detect_open_vocab_tool_verb(clause: str) -> tuple[str, str, str, tuple[str, ...]] | None:
    """Elon's Law Open-Vocabulary Morphism Detector:
    Recognizes ANY installed executable on PATH without hardcoding it in _VERB_SPECS!
    """
    low = clause.lower()
    tool: str | None = None
    # 1. Explicit tool invocation cue: `use <tool>`, `using <tool>`, `run <tool>`, `with <tool>`
    for m in re.finditer(r"\b(?:use|using|run|with)\s+([a-z][a-z0-9_.\-]{1,24})\b", low):
        cand = m.group(1)
        if cand not in _OPEN_VOCAB_ENGLISH_STOPWORDS and shutil.which(cand):
            tool = cand
            break
    # 2. Any unambiguous installed binary name in the clause
    if tool is None:
        # Strip filenames with extensions so `data.txt` doesn't confuse tokens
        no_paths = re.sub(r"[A-Za-z0-9_.\-/]+\.[A-Za-z0-9_.\-]+", " ", low)
        for tok in re.findall(r"\b[a-z][a-z0-9_\-]{1,20}\b", no_paths):
            if tok in _OPEN_VOCAB_ENGLISH_STOPWORDS:
                continue
            if shutil.which(tok):
                tool = tok
                break
    if tool is None:
        return None
    # Compute compact intent signature from 1-2 semantic qualifier words (excluding tool & paths)
    no_paths = re.sub(r"[A-Za-z0-9_.\-/]+\.[A-Za-z0-9_.\-]+", " ", low)
    quals = [
        w for w in re.findall(r"\b[a-z]{3,16}\b", no_paths)
        if w != tool and w not in _OPEN_VOCAB_ENGLISH_STOPWORDS
        and w not in ("save", "output", "into", "from", "then", "file", "folder", "result")
    ]
    # Keep deterministic compact intent key (e.g., `lines`, `count`, `reverse`, `default`)
    intent = "_".join(sorted(set(quals))[:2]) if quals else "default"
    verb = f"tool:{tool}:{intent}"
    return verb, "file:any", "file:text", (tool,)


_ENV_TOOL_INDEX_MEM: dict[str, dict[str, str]] | None = None
_SAFE_INDEXABLE_DIRS = ("/usr/bin", "/bin", "/usr/local/bin")
_PROBE_CANDIDATE_TOOLS = (
    "wc", "tac", "rev", "md5sum", "sha1sum", "sha256sum", "sha512sum",
    "head", "tail", "cut", "tr", "uniq", "nl", "fold", "paste", "comm",
    "diff", "cmp", "strings", "od", "hexdump", "xxd", "bzip2", "xz",
    "gzip", "unzip", "zip", "tar", "jq", "awk", "sed", "grep", "sort",
    "base64", "patch", "find", "stat", "file", "fmt", "expand", "unexpand",
    "shuf", "tsort", "join", "split", "csplit", "cksum", "b2sum", "iconv",
)


def index_local_environment_tools(force_refresh: bool = False) -> dict[str, str]:
    """Scan installed CLI binaries on THIS machine into a compact 1-line `--help` summary index.

    Cached in memory and on disk (`/tmp/brain_epistemic_cache/env_tool_index.json`) so
    repeat lookups take <0.2ms. Never crawls user data or arbitrary directories.
    """
    global _ENV_TOOL_INDEX_MEM
    path_key = hashlib.sha256(os.environ.get("PATH", "").encode("utf-8")).hexdigest()[:12]
    if not force_refresh and _ENV_TOOL_INDEX_MEM is not None and path_key in _ENV_TOOL_INDEX_MEM:
        return _ENV_TOOL_INDEX_MEM[path_key]

    cache_file = pathlib.Path("/tmp/brain_epistemic_cache/env_tool_index.json")
    if not force_refresh and cache_file.is_file():
        try:
            loaded = json.loads(cache_file.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and isinstance(loaded.get(path_key), dict):
                _ENV_TOOL_INDEX_MEM = {path_key: dict(loaded[path_key])}
                return _ENV_TOOL_INDEX_MEM[path_key]
        except Exception:
            pass

    present = [t for t in _PROBE_CANDIDATE_TOOLS if shutil.which(t)]

    def _probe_one(tool: str) -> tuple[str, str]:
        try:
            cp = subprocess.run(
                [tool, "--help"],
                capture_output=True, text=True, timeout=1.5,
            )
            txt = (cp.stdout or "") + "\n" + (cp.stderr or "")
            summary_lines: list[str] = []
            for ln in txt.splitlines()[:12]:
                s = ln.strip()
                if not s or s.lower().startswith(("usage:", "try ", "mandatory ", "with no file")):
                    continue
                summary_lines.append(s)
                if len(summary_lines) >= 2:
                    break
            return tool, " ".join(summary_lines)[:220]
        except Exception:
            return tool, ""

    index: dict[str, str] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(12, max(1, len(present)))) as pool:
        for t, desc in pool.map(_probe_one, present):
            if desc:
                index[t] = desc

    _ENV_TOOL_INDEX_MEM = {path_key: index}
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps({path_key: index}, indent=2, sort_keys=True), encoding="utf-8")
    except Exception:
        pass
    return index


def discover_tool_for_unseen_intent(clause: str) -> tuple[str, str, str, tuple[str, ...]] | None:
    """Zero-tool-name Environment Capability Discovery:
    Matches a natural-language goal clause against the live 1-line `--help` summaries
    of binaries installed on THIS machine (without the user naming the binary!).
    """
    low = re.sub(r"[A-Za-z0-9_.\-/]+\.[A-Za-z0-9_.\-]+", " ", clause.lower())
    goal_toks = set(re.findall(r"\b[a-z0-9]{2,18}\b", low)) - {
        "the", "and", "for", "with", "from", "into", "that", "this", "file", "files",
        "use", "using", "save", "write", "output", "result", "then", "number", "compute",
        "calculate", "get", "make", "create", "find", "show", "print", "standard", "each",
    }
    if not goal_toks:
        return None
    # Expand common morphological stems (`lines` -> `line`, `words` -> `word`, `characters` -> `character`)
    expanded = set(goal_toks)
    for t in list(goal_toks):
        if t.endswith("s") and len(t) >= 4:
            expanded.add(t[:-1])
        if t.endswith("ing") and len(t) >= 6:
            expanded.add(t[:-3])

    idx = index_local_environment_tools()
    best_tool: str | None = None
    best_score = 0.0
    for tool, desc in idx.items():
        d_low = f"{tool} {desc}".lower()
        d_toks = set(re.findall(r"\b[a-z0-9]{2,18}\b", d_low))
        d_exp = set(d_toks)
        for dt in list(d_toks):
            if dt.endswith("s") and len(dt) >= 4:
                d_exp.add(dt[:-1])
        ov = expanded & d_exp
        if not ov:
            continue
        # Weight rare/specific tokens higher (e.g., `md5`, `checksum`, `reverse`, `count`, `newline`, `byte`, `characterwise`)
        score = sum(2.5 if len(tok) >= 5 or any(ch.isdigit() for ch in tok) else 1.0 for tok in ov)
        # Bonus if tool name itself overlaps an intent token (e.g. `md5` in `md5sum`)
        if any(tok in tool for tok in expanded if len(tok) >= 3):
            score += 3.0
        if score > best_score:
            best_score = score
            best_tool = tool

    if best_tool is None or best_score < 2.5:
        return None
    quals = sorted(t for t in goal_toks if t != best_tool)[:2]
    intent = "_".join(quals) if quals else "default"
    return f"tool:{best_tool}:{intent}", "file:any", "file:text", (best_tool,)


def _detect_verb_in_clause(clause: str) -> tuple[str, str, str, tuple[str, ...]] | None:
    low = clause.lower()
    low_no_paths = re.sub(r"[A-Za-z0-9_.\-/]+\.[A-Za-z0-9_.\-]+", " ", low)
    # If clause explicitly includes a jq-style dotted selector like `'.records[].tag'`,
    # recognize `filter_json` even when the caller didn't spell out the word "jq"!
    if re.search(r"['\"`]\.[A-Za-z_][A-Za-z0-9_.\[\]]*['\"`]", clause):
        return "filter_json", "file:json", "file:text", ("jq",)
    # Check most specific verbs first using word-boundary matching (never match `sed` inside `reversed.txt`!)
    has_other_hash = bool(re.search(r"\b(?:md5|md5sum|sha1|sha1sum|sha512|sha512sum|b2sum|cksum)\b", low_no_paths))
    for verb, cues, in_t, out_t, tools in _VERB_SPECS:
        if verb == "hash_sha256" and has_other_hash:
            continue
        if any(re.search(rf"\b{re.escape(cue)}\b", low_no_paths) for cue in cues):
            return verb, in_t, out_t, tools
    # Extra single-word matches when unambiguous
    if "base64" in low_no_paths and ("decode" in low_no_paths or ".b64" in low):
        return "decode_base64", "file:base64", "file:any", ("base64",)
    if "sort" in low_no_paths and ("unique" in low_no_paths or "dedup" in low_no_paths or "duplicate" in low_no_paths):
        return "sort_unique", "file:text", "file:text", ("sort",)
    if re.search(r"\bsort\b", low_no_paths):
        return "sort_unique", "file:text", "file:text", ("sort",)
    # Open-vocabulary fallback: ANY installed CLI binary on PATH becomes a composable morphism!
    ov = _detect_open_vocab_tool_verb(clause)
    if ov is not None:
        return ov
    # Zero-tool-name fallback: scan local environment's installed tool index against goal intent!
    return discover_tool_for_unseen_intent(clause)


def _split_pipeline_clauses(instruction: str) -> list[str]:
    """Split a multi-step instruction into ordered causal clauses."""
    # Protect quoted expressions from splitting on `,` or `;`
    placeholders: dict[str, str] = {}
    def _mask(m: re.Match[str]) -> str:
        key = f"__Q{len(placeholders)}__"
        placeholders[key] = m.group(0)
        return key
    masked = re.sub(r"`[^`\n]+`|'[^'\n]+'|\"[^\"\n]+\"", _mask, instruction)

    # Split on explicit sequential connectors: "; ", " -> ", ", then ", " and then ", ", and ", "\n"
    raw_parts = re.split(
        r"\s*(?:;\s*|->\s*|\n+|\b(?:and\s+then|then)\b|,\s+(?:and\s+)?(?=(?:use\s+[a-z0-9_\-]+|run\s+[a-z0-9_\-]+|decode|encode|extract|untar|unpack|unzip|create|archive|compress|decompress|filter|query|sort|deduplicate|apply|patch|replace|substitute|search|compute|hash|sha256)))",
        masked,
        flags=re.I,
    )
    clauses: list[str] = []
    for p in raw_parts:
        st = re.sub(r"^\s*(?:\d+[.)]\s+|[-*]\s+)", "", p).strip(" ,.;:-")
        if not st:
            continue
        for k, v in placeholders.items():
            st = st.replace(k, v)
        clauses.append(st)
    return clauses or [instruction]


def decompose_goal_to_transitions(
    instruction: str,
    env: Mapping[str, Any],
) -> tuple[list[TransitionSubgoal], list[str], list[str]]:
    """Decompose a single-step OR multi-step instruction into ordered typed transitions."""
    global_gs = EPI.parse_goal_specification(instruction, env)
    clauses = _split_pipeline_clauses(instruction)

    subgoals: list[TransitionSubgoal] = []
    for raw_c in clauses:
        vinfo = _detect_verb_in_clause(raw_c)
        if vinfo is None:
            # Merge trailing output specification like "save output to final.txt" onto previous step
            if subgoals:
                prev = subgoals[-1]
                c_gs = EPI.parse_goal_specification(raw_c, env)
                if c_gs["output_paths"] and not prev.explicit_out_path:
                    prev.explicit_out_path = c_gs["output_paths"][0]
                if c_gs["output_dirs"] and not prev.explicit_out_dir:
                    prev.explicit_out_dir = c_gs["output_dirs"][0]
                if "raw" in raw_c.lower():
                    prev.raw_output_requested = True
                prev.clause = prev.clause + " " + raw_c
            continue

        verb, in_t, out_t, hint_tools = vinfo
        c_gs = EPI.parse_goal_specification(raw_c, env)
        avail_tools = [t for t in hint_tools if shutil.which(t)]
        if not avail_tools:
            avail_tools = list(c_gs.get("candidate_tools") or [])

        # Extract non-path quoted expression in this clause
        known_paths = set(c_gs["input_paths"] + c_gs["output_paths"] + global_gs["input_paths"] + global_gs["output_paths"])
        exprs = [q for q in c_gs["quoted_literals"] if q not in known_paths and q.lstrip("./") not in known_paths]

        # Only bind explicit_in_path if the clause itself literally mentions that filename
        existing_rels = {f["rel"] for f in env.get("files", [])}
        exp_in = next((p for p in c_gs["input_paths"] if pathlib.Path(p).name in raw_c or p in raw_c), None)
        exp_in_dir = next((d for d in c_gs["input_dirs"] if d in raw_c), None)
        exp_out = next((p for p in c_gs["output_paths"] if p != exp_in and p not in existing_rels), None)
        if exp_in is None:
            exp_in = next((p for p in c_gs["output_paths"] if p in existing_rels), None)
        exp_out_dir = c_gs["output_dirs"][0] if c_gs["output_dirs"] else None

        subgoals.append(TransitionSubgoal(
            index=len(subgoals),
            clause=raw_c,
            verb=verb,
            in_type=in_t,
            out_type=out_t,
            candidate_tools=avail_tools,
            explicit_in_path=exp_in,
            explicit_in_dir=exp_in_dir,
            explicit_out_path=exp_out,
            explicit_out_dir=exp_out_dir,
            quoted_expr=exprs[0] if exprs else None,
            raw_output_requested="raw" in raw_c.lower(),
            ignore_case_requested=("ignore-case" in raw_c.lower() or "case-insensitive" in raw_c.lower()),
        ))

    # Attach global input to step 0 and global output to last step if not explicitly stated in clause
    if subgoals:
        if not subgoals[0].explicit_in_path and not subgoals[0].explicit_in_dir:
            if global_gs["input_dirs"] and subgoals[0].verb == "create_archive":
                subgoals[0].explicit_in_dir = global_gs["input_dirs"][0]
            elif global_gs["input_paths"]:
                subgoals[0].explicit_in_path = global_gs["input_paths"][0]
        existing_all = {f["rel"] for f in env.get("files", [])}
        if not subgoals[-1].explicit_out_path and not subgoals[-1].explicit_out_dir:
            non_existing_outs = [p for p in global_gs["output_paths"] if p not in existing_all]
            if non_existing_outs:
                subgoals[-1].explicit_out_path = non_existing_outs[-1]
            elif global_gs["output_dirs"]:
                subgoals[-1].explicit_out_dir = global_gs["output_dirs"][-1]

    return subgoals, list(global_gs["output_paths"]), list(global_gs["output_dirs"])


# ---------------------------------------------------------------------------
# 3. Parallel Epistemic Gap Acquisition (Only Missing Transitions!)
# ---------------------------------------------------------------------------

def _acquire_tool_knowledge(
    tool: str,
    allow_web: bool,
    skip_help_tools: set[str],
    open_web_fetcher: Callable[[str], Sequence[Mapping[str, Any]]] | None = None,
) -> tuple[str, EPI.LocalHelpKnowledge, list[EPI.CommandRecipe], list[dict[str, Any]]]:
    lh = (
        EPI.LocalHelpKnowledge(tool, "", False, "", set(), set(), {}, [])
        if tool in skip_help_tools
        else EPI.query_local_cli_help(tool)
    )
    recipes: list[EPI.CommandRecipe] = []
    prov: list[dict[str, Any]] = []
    if lh.available:
        prov.append({"kind": "local_manual", "tool": tool, "flags": len(lh.short_flags) + len(lh.long_flags)})
    if allow_web:
        w_recs, w_prov = EPI.fetch_web_tldr_recipes(tool)
        recipes.extend(w_recs)
        prov.extend(w_prov)
        if open_web_fetcher is not None:
            j_recs, j_prov = EPI.fetch_web_jit_corroboration(tool, tool, open_web_fetcher=open_web_fetcher)
            recipes.extend(j_recs)
            prov.extend(j_prov)
    for r in recipes:
        EPI.corroborate_recipe_with_local_help(r, lh)
    return tool, lh, recipes, prov


def acquire_gaps_parallel(
    gap_tools: Sequence[str],
    *,
    allow_web: bool,
    store: dict[str, Any] | None = None,
    open_web_fetcher: Callable[[str], Sequence[Mapping[str, Any]]] | None = None,
) -> tuple[dict[str, EPI.LocalHelpKnowledge], dict[str, list[EPI.CommandRecipe]], list[dict[str, Any]]]:
    """Fetch local `--help` + live web guides IN PARALLEL ONLY for missing gap tools."""
    unique_tools = list(dict.fromkeys(t for t in gap_tools if t and shutil.which(t)))
    if not unique_tools:
        return {}, {}, []

    skip_help = set((store or {}).get("negative_host_facts", {}).get("no_help_flag") or ())
    helps: dict[str, EPI.LocalHelpKnowledge] = {}
    recipes_by_tool: dict[str, list[EPI.CommandRecipe]] = {}
    prov_all: list[dict[str, Any]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(unique_tools))) as ex:
        futs = [
            ex.submit(_acquire_tool_knowledge, t, allow_web, skip_help, open_web_fetcher)
            for t in unique_tools
        ]
        for f in concurrent.futures.as_completed(futs):
            tool, lh, recs, prov = f.result()
            helps[tool] = lh
            recipes_by_tool[tool] = recs
            prov_all.extend(prov)
            if not lh.available and store is not None:
                neg = store.setdefault("negative_host_facts", {}).setdefault("no_help_flag", [])
                if tool not in neg:
                    neg.append(tool)

    return helps, recipes_by_tool, prov_all


# ---------------------------------------------------------------------------
# 4. Step Execution, Compositional Pipeline Chaining & Morphism Distillation
# ---------------------------------------------------------------------------

def _pick_intermediate_file_for_type(directory: pathlib.Path, want_type: str, explicit_name: str | None) -> str | None:
    """When a previous step extracted a directory, locate the file matching the next step's type."""
    files = sorted(p for p in directory.rglob("*") if p.is_file())
    if not files:
        return None
    if explicit_name:
        for f in files:
            if f.name == pathlib.Path(explicit_name).name or str(f).endswith(explicit_name):
                return str(f)
    for f in files:
        if _type_compatible(want_type, infer_file_media_type(f)):
            return str(f)
    return str(files[0])


def _run_shell_step(
    stage_ws: pathlib.Path,
    cmd: str,
    redirect_out: str | None,
    timeout_s: float = 15.0,
) -> tuple[int, str, str]:
    cp = subprocess.run(
        ["bash", "-lc", cmd],
        cwd=str(stage_ws),
        capture_output=True,
        timeout=timeout_s,
        stdin=subprocess.DEVNULL,
    )
    if redirect_out and cp.returncode == 0 and cp.stdout:
        rel_out = str(redirect_out)
        for _pref in ("/app/", "/workspace/"):
            if rel_out.startswith(_pref):
                rel_out = rel_out[len(_pref):]
                break
        p = pathlib.Path(rel_out) if pathlib.Path(rel_out).is_absolute() else (stage_ws / rel_out)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(cp.stdout)
        except OSError:
            pass
    out_txt = cp.stdout.decode("utf-8", errors="replace") if cp.stdout else ""
    err_txt = cp.stderr.decode("utf-8", errors="replace") if cp.stderr else ""
    return cp.returncode, out_txt, err_txt


def _verify_step_output(
    stage_ws: pathlib.Path,
    sub: TransitionSubgoal,
    out_path: str | None,
    out_dir: str | None,
    in_path: str | None = None,
) -> tuple[bool, str]:
    if out_dir:
        d = stage_ws / out_dir
        if not d.is_dir() or not any(x.is_file() for x in d.rglob("*")):
            return False, f"EMPTY_OUT_DIR:{out_dir}"
        return True, "OK_DIR"
    if out_path:
        p = stage_ws / out_path
        if not p.is_file() or p.stat().st_size == 0:
            return False, f"MISSING_OR_EMPTY_OUT:{out_path}"
        # Mathematical direction-progress invariant for inverse/unwrap verbs:
        # Reject commands that ran the forward encoding/compression instead of unwrapping!
        if in_path and (stage_ws / in_path).is_file():
            try:
                in_b = (stage_ws / in_path).read_bytes()
                out_b = p.read_bytes()
                if sub.verb == "decompress_gzip" and out_b[:2] == b"\x1f\x8b":
                    try:
                        if gzip.decompress(out_b) == in_b:
                            return False, "COMPRESSED_INSTEAD_OF_DECOMPRESSED"
                    except Exception:
                        pass
                elif sub.verb == "decode_base64":
                    try:
                        if base64.b64decode(out_b, validate=True) == in_b:
                            return False, "ENCODED_INSTEAD_OF_DECODED"
                    except Exception:
                        pass
            except Exception:
                pass
        low = p.name.lower()
        if low.endswith((".tar.gz", ".tgz", ".tar")):
            try:
                with tarfile.open(p, "r:*") as tf:
                    if not tf.getnames():
                        return False, "EMPTY_TAR"
            except Exception as exc:
                return False, f"INVALID_TAR:{exc}"
        elif low.endswith(".zip"):
            try:
                with zipfile.ZipFile(p, "r") as zf:
                    if not zf.namelist():
                        return False, "EMPTY_ZIP"
            except Exception as exc:
                return False, f"INVALID_ZIP:{exc}"
        elif low.endswith(".json"):
            try:
                json.loads(p.read_text(encoding="utf-8"))
            except Exception as exc:
                return False, f"INVALID_JSON:{exc}"
        return True, "OK_FILE"
    return True, "OK_INPLACE"


@dataclasses.dataclass
class MorphismPipelineResult:
    status: str  # "VERIFIED" | "FAILED"
    mode: str  # "ALL_TIER0_COMPOSED" | "HYBRID_TIER0_AND_EPISTEMIC" | "ALL_TIER1_EPISTEMIC" | "FAILED"
    steps_trace: list[dict[str, Any]]
    gaps_queried: list[str]
    web_queries_made: int
    morphisms_recalled: list[str]
    morphisms_learned: list[str]
    morphisms_refuted: list[dict[str, Any]]
    elapsed_ms: float
    model_calls: int = 0
    parameters_stored: int = 0


def solve_with_epistemic_morphisms(
    workspace: str | pathlib.Path,
    instruction: str,
    *,
    morphism_store: dict[str, Any] | None = None,
    postcondition_fn: Callable[[pathlib.Path], tuple[bool, str]] | None = None,
    allow_web: bool = True,
    open_web_fetcher: Callable[[str], Sequence[Mapping[str, Any]]] | None = None,
    timeout_s: float = 15.0,
) -> MorphismPipelineResult:
    """Solve ANY single-step or multi-step computer task via Goal-Directed Epistemic Diff
    over generalized atomic morphisms (zero LLM, zero weights, insanely fast).
    """
    t0 = time.monotonic()
    ws = pathlib.Path(workspace).resolve()
    env = EPI.sense_unknown_environment(ws)
    subgoals, global_outs, global_out_dirs = decompose_goal_to_transitions(instruction, env)

    if not subgoals:
        # Delegate straight to single-step epistemic engine if no structured verb matched
        r = EPI.solve_unknown_environment(
            ws, instruction, postcondition_fn=postcondition_fn, allow_web=allow_web, open_web_fetcher=open_web_fetcher
        )
        return MorphismPipelineResult(
            status=r.status,
            mode="ALL_TIER1_EPISTEMIC" if r.status == "VERIFIED" else "FAILED",
            steps_trace=[{"tool": r.tool_used, "command": r.command_executed, "tier": r.tier_used}],
            gaps_queried=[r.tool_used] if r.tool_used else [],
            web_queries_made=1 if r.questions_asked else 0,
            morphisms_recalled=[],
            morphisms_learned=[],
            morphisms_refuted=[],
            elapsed_ms=round((time.monotonic() - t0) * 1000.0, 2),
        )

    # --- STEP 1: Fast Epistemic Diff against Morphism Store (<1ms!) ---
    gap_tools: list[str] = []
    for idx, sub in enumerate(subgoals):
        tool0 = sub.candidate_tools[0] if sub.candidate_tools else "unknown"
        has_hit = False
        if morphism_store is not None:
            for m in (morphism_store.get("morphisms") or {}).values():
                if m.get("status") != STATUS_QUARANTINED and m.get("verb") == sub.verb:
                    if m.get("tool") in sub.candidate_tools or not sub.candidate_tools:
                        has_hit = True
                        break
        if not has_hit:
            gap_tools.extend(sub.candidate_tools[:2])

    # --- STEP 2: Parallel Acquisition ONLY for Missing Gaps ---
    helps, recipes_by_tool, prov_all = acquire_gaps_parallel(
        gap_tools,
        allow_web=allow_web,
        store=morphism_store,
        open_web_fetcher=open_web_fetcher,
    )
    web_queries_made = sum(1 for p in prov_all if p.get("kind") in ("web_command_guide", "web_documentation", "open_web"))

    # --- STEP 3: Execute Composed Pipeline in ONE Isolated State Copy ---
    tmp_root = pathlib.Path(tempfile.mkdtemp(prefix="brain_morph_sc_"))
    stage_ws = tmp_root / "ws"
    shutil.copytree(ws, stage_ws, symlinks=True)

    stage_artifacts_to_clean: list[pathlib.Path] = []
    steps_trace: list[dict[str, Any]] = []
    recalled_ids: list[str] = []
    learned_candidates: list[dict[str, Any]] = []
    refuted_log: list[dict[str, Any]] = []

    prev_out_path: str | None = None
    prev_out_dir: str | None = None
    pipeline_ok = True
    auto_unwrap_counter = 0

    def _execute_one_subgoal(
        sub: TransitionSubgoal,
        cur_in_path: str | None,
        cur_in_dir: str | None,
        cur_out_path: str | None,
        cur_out_dir: str | None,
        actual_in_type: str,
        *,
        is_last: bool,
        auto_unwrapped: bool = False,
    ) -> bool:
        nonlocal web_queries_made
        if cur_out_dir:
            _safe_rel_dir = cur_out_dir.lstrip("/")
            if _safe_rel_dir.startswith("app/"):
                _safe_rel_dir = _safe_rel_dir[4:]
            cur_out_dir = _safe_rel_dir or "."
            (stage_ws / cur_out_dir).mkdir(parents=True, exist_ok=True)

        step_holes: dict[str, str] = {}
        if cur_in_path:
            step_holes["__IN__"] = cur_in_path
        if cur_in_dir:
            step_holes["__IN_DIR__"] = cur_in_dir
        if cur_out_path:
            step_holes["__OUT__"] = cur_out_path
        if cur_out_dir:
            step_holes["__OUT_DIR__"] = cur_out_dir
        if sub.quoted_expr:
            step_holes["__EXPR__"] = sub.quoted_expr

        primary_tool = sub.candidate_tools[0] if sub.candidate_tools else "unknown"
        step_obs = [
            f"tool:{primary_tool}",
            f"in_type:{actual_in_type}",
            f"has_expr:{bool(sub.quoted_expr)}",
            f"raw_out:{sub.raw_output_requested}",
            f"ignore_case:{sub.ignore_case_requested}",
            f"has_out_dir:{bool(cur_out_dir)}",
        ]

        # --- TIER 0: Instant Morphism Recall ---
        if morphism_store is not None:
            cands_m = recall_morphisms(
                morphism_store,
                verb=sub.verb,
                in_type=actual_in_type,
                observables=step_obs,
                available_holes=step_holes,
            )
            for m in cands_m:
                cmd = instantiate_morphism_command(m["command_template"], step_holes)
                redir = cur_out_path if m.get("redirect_stdout") else None
                rc, out_s, err_s = _run_shell_step(stage_ws, cmd, redir, timeout_s=timeout_s)
                ok_v, reason_v = (rc == 0, "RC0") if rc == 0 else (False, f"RC_{rc}")
                if ok_v:
                    ok_v, reason_v = _verify_step_output(stage_ws, sub, cur_out_path, cur_out_dir, cur_in_path)
                if ok_v and is_last and postcondition_fn is not None:
                    try:
                        ok_v, reason_v = postcondition_fn(stage_ws)
                    except Exception as exc:
                        ok_v, reason_v = False, f"POSTCOND_EXC:{exc}"
                if ok_v:
                    recalled_ids.append(m["morphism_id"])
                    stored = (morphism_store.get("morphisms") or {}).get(m["morphism_id"])
                    if isinstance(stored, dict):
                        stored["support_count"] = int(stored.get("support_count", 1)) + 1
                    steps_trace.append({
                        "step": len(steps_trace),
                        "verb": sub.verb,
                        "tier": "TIER0_MORPHISM_RECALL",
                        "auto_unwrapped": auto_unwrapped,
                        "morphism_id": m["morphism_id"],
                        "tool": m["tool"],
                        "command": cmd + (f" > {redir}" if redir else ""),
                    })
                    return True
                else:
                    ref = refute_morphism(
                        morphism_store,
                        m["morphism_id"],
                        counterexample_observables=step_obs,
                        reason=f"STEP_FAILED:{reason_v}",
                    )
                    refuted_log.append(ref)

        # --- TIER 1: Epistemic Live Acquisition (ONLY when Tier 0 missed or refuted!) ---
        missing_now = [t for t in sub.candidate_tools[:2] if t not in helps]
        if missing_now:
            gap_tools.extend(missing_now)
            h2, r2, p2 = acquire_gaps_parallel(
                missing_now, allow_web=allow_web, store=morphism_store, open_web_fetcher=open_web_fetcher
            )
            helps.update(h2)
            recipes_by_tool.update(r2)
            prov_all.extend(p2)
            web_queries_made += sum(1 for p in p2 if p.get("kind") in ("web_command_guide", "web_documentation", "open_web"))

        step_env = EPI.sense_unknown_environment(stage_ws)
        step_gs = {
            "instruction": sub.clause,
            "tokens": EPI._tokenize(sub.clause),
            "token_set": sorted(set(EPI._tokenize(sub.clause))),
            "candidate_tools": sub.candidate_tools,
            "subcommand": "",
            "input_paths": [cur_in_path] if cur_in_path else [],
            "non_archive_inputs": [cur_in_path] if cur_in_path and actual_in_type not in ("file:tar.gz", "file:tar", "file:zip") else [],
            "output_paths": [cur_out_path] if cur_out_path else [],
            "input_dirs": [cur_in_dir] if cur_in_dir else [],
            "output_dirs": [cur_out_dir] if cur_out_dir else [],
            "archive_paths": [p for p in (cur_in_path, cur_out_path) if p and (p.endswith((".tar.gz", ".tgz", ".tar", ".zip", ".gz")) or actual_in_type in ("file:tar.gz", "file:tar", "file:zip", "file:gzip"))],
            "quoted_literals": [sub.quoted_expr] if sub.quoted_expr else [],
        }
        step_recipes: list[EPI.CommandRecipe] = []
        for t in sub.candidate_tools[:2]:
            lh = helps.get(t)
            if lh is not None:
                step_recipes.extend(EPI._synthesize_help_fallback_recipes(lh, step_gs))
            step_recipes.extend(recipes_by_tool.get(t, []))

        ranked = sorted(step_recipes, key=lambda r: EPI._score_recipe(r, step_gs), reverse=True)
        seen_cmds: set[tuple[str, str | None]] = set()
        tried = 0
        for rec in ranked:
            for cmd, _, redir in EPI._bind_recipe_holes(rec, step_gs, step_env):
                key = (cmd, redir)
                if key in seen_cmds:
                    continue
                seen_cmds.add(key)
                tried += 1
                if tried > 20:
                    break
                rc, out_s, err_s = _run_shell_step(stage_ws, cmd, redir, timeout_s=timeout_s)
                if rc != 0 and err_s:
                    for ref_cmd, _ in EPI._refine_command_from_stderr(cmd, err_s, rec.tool, helps.get(rec.tool), step_gs)[:2]:
                        rc2, out_s2, err_s2 = _run_shell_step(stage_ws, ref_cmd, redir, timeout_s=timeout_s)
                        if rc2 == 0:
                            cmd, rc, out_s, err_s = ref_cmd, rc2, out_s2, err_s2
                            break
                ok_v, reason_v = (rc == 0, "RC0") if rc == 0 else (False, f"RC_{rc}")
                if ok_v:
                    ok_v, reason_v = _verify_step_output(stage_ws, sub, cur_out_path, cur_out_dir, cur_in_path)
                if ok_v and is_last and postcondition_fn is not None:
                    try:
                        ok_v, reason_v = postcondition_fn(stage_ws)
                    except Exception as exc:
                        ok_v, reason_v = False, f"POSTCOND_EXC:{exc}"
                if ok_v:
                    steps_trace.append({
                        "step": len(steps_trace),
                        "verb": sub.verb,
                        "tier": "TIER1_EPISTEMIC",
                        "auto_unwrapped": auto_unwrapped,
                        "tool": rec.tool,
                        "command": cmd + (f" > {redir}" if redir else ""),
                        "corroborated_kinds": rec.corroborated_source_kinds,
                    })
                    learned_candidates.append({
                        "in_type": actual_in_type,
                        "verb": sub.verb,
                        "out_type": sub.out_type,
                        "tool": rec.tool,
                        "concrete_command": cmd,
                        "redirect_stdout": bool(redir),
                        "hole_bindings": dict(step_holes),
                        "observables": list(step_obs),
                        "corroborated_kinds": list(rec.corroborated_source_kinds),
                        "source_url": rec.source_url,
                    })
                    return True
                else:
                    if cur_out_path and (stage_ws / cur_out_path).is_file():
                        (stage_ws / cur_out_path).unlink(missing_ok=True)
            if tried > 20:
                break
        return False

    try:
        for idx, sub in enumerate(subgoals):
            is_last = idx == len(subgoals) - 1

            # Determine this step's concrete input (from explicit path OR chained from previous step!)
            cur_in_path = sub.explicit_in_path
            cur_in_dir = sub.explicit_in_dir
            if cur_in_path is None and cur_in_dir is None:
                if prev_out_path:
                    cur_in_path = prev_out_path
                elif prev_out_dir:
                    picked = _pick_intermediate_file_for_type(stage_ws / prev_out_dir, sub.in_type, sub.explicit_in_path)
                    if picked:
                        cur_in_path = str(pathlib.Path(picked).relative_to(stage_ws))
            elif cur_in_path and not (stage_ws / cur_in_path).is_file() and prev_out_dir:
                picked = _pick_intermediate_file_for_type(stage_ws / prev_out_dir, sub.in_type, cur_in_path)
                if picked:
                    cur_in_path = str(pathlib.Path(picked).relative_to(stage_ws))

            # Sense actual runtime media type of this step's input!
            actual_in_type = sub.in_type
            if cur_in_dir and (stage_ws / cur_in_dir).is_dir():
                actual_in_type = "dir"
            elif cur_in_path and (stage_ws / cur_in_path).is_file():
                actual_in_type = infer_file_media_type(stage_ws / cur_in_path)

            # --- AUTOMATIC IMPLICIT TYPE-UNWRAPPING BRIDGE LOOP ---
            # If the user did NOT name intermediate unwrap verbs (e.g., passed `payload.b64`
            # or `data.json.gz.b64` straight to `jq`), automatically unwrap container layers
            # using learned morphisms (or live Epistemic Diff) until `sub.in_type` is reached!
            unwrap_depth = 0
            while (
                cur_in_path
                and not _type_compatible(sub.in_type, actual_in_type)
                and actual_in_type in _CONTAINER_TYPES
                and unwrap_depth < 5
            ):
                unwrap_sub = _infer_unwrap_subgoal(actual_in_type, auto_unwrap_counter)
                if unwrap_sub is None or not unwrap_sub.candidate_tools:
                    break
                auto_unwrap_counter += 1
                unwrap_depth += 1
                if unwrap_sub.out_type == "dir":
                    u_out_dir = f"__brain_unwrap_{auto_unwrap_counter}_dir"
                    u_out_path = None
                    stage_artifacts_to_clean.append(stage_ws / u_out_dir)
                else:
                    u_out_dir = None
                    u_out_path = f"__brain_unwrap_{auto_unwrap_counter}.out"
                    stage_artifacts_to_clean.append(stage_ws / u_out_path)

                ok_u = _execute_one_subgoal(
                    unwrap_sub,
                    cur_in_path,
                    None,
                    u_out_path,
                    u_out_dir,
                    actual_in_type,
                    is_last=False,
                    auto_unwrapped=True,
                )
                if not ok_u:
                    pipeline_ok = False
                    break

                if u_out_dir:
                    picked = _pick_intermediate_file_for_type(stage_ws / u_out_dir, sub.in_type, sub.explicit_in_path)
                    if not picked:
                        pipeline_ok = False
                        break
                    cur_in_path = str(pathlib.Path(picked).relative_to(stage_ws))
                    actual_in_type = infer_file_media_type(stage_ws / cur_in_path)
                elif u_out_path:
                    cur_in_path = u_out_path
                    actual_in_type = infer_file_media_type(stage_ws / cur_in_path)

            if not pipeline_ok:
                break

            # Determine this step's concrete output (final explicit target OR clean internal stage artifact)
            cur_out_path = sub.explicit_out_path
            cur_out_dir = sub.explicit_out_dir
            if not cur_out_path and not cur_out_dir:
                if sub.out_type == "dir":
                    cur_out_dir = f"__brain_stage_{idx}_dir"
                    stage_artifacts_to_clean.append(stage_ws / cur_out_dir)
                elif sub.verb != "apply_patch":
                    ext = ".tar.gz" if sub.out_type == "file:archive" else ".out"
                    cur_out_path = f"__brain_stage_{idx}{ext}"
                    stage_artifacts_to_clean.append(stage_ws / cur_out_path)

            step_solved = _execute_one_subgoal(
                sub,
                cur_in_path,
                cur_in_dir,
                cur_out_path,
                cur_out_dir,
                actual_in_type,
                is_last=is_last,
                auto_unwrapped=False,
            )

            if not step_solved:
                pipeline_ok = False
                break

            prev_out_path = cur_out_path
            prev_out_dir = cur_out_dir

        # Final postcondition check (if not already checked on last step)
        if pipeline_ok and postcondition_fn is not None:
            ok_final, _ = postcondition_fn(stage_ws)
            if not ok_final:
                pipeline_ok = False

        if not pipeline_ok:
            return MorphismPipelineResult(
                status="FAILED",
                mode="FAILED",
                steps_trace=steps_trace,
                gaps_queried=sorted(set(gap_tools)),
                web_queries_made=web_queries_made,
                morphisms_recalled=recalled_ids,
                morphisms_learned=[],
                morphisms_refuted=refuted_log,
                elapsed_ms=round((time.monotonic() - t0) * 1000.0, 2),
            )

        # Clean up internal temporary stage artifacts BEFORE committing to real workspace!
        for art in stage_artifacts_to_clean:
            if art.is_dir():
                shutil.rmtree(art, ignore_errors=True)
            elif art.is_file():
                art.unlink(missing_ok=True)

        # Atomic commit of verified outputs to real workspace
        EPI._sync_state_copy_to_workspace(stage_ws, ws)

        # Distill ONLY the newly verified atomic composable morphisms!
        learned_ids: list[str] = []
        if morphism_store is not None:
            for lc in learned_candidates:
                mrec = induce_morphism(morphism_store, **lc)
                if mrec is not None:
                    learned_ids.append(mrec["morphism_id"])

        if recalled_ids and not learned_candidates:
            mode = "ALL_TIER0_COMPOSED"
        elif recalled_ids and learned_candidates:
            mode = "HYBRID_TIER0_AND_EPISTEMIC"
        else:
            mode = "ALL_TIER1_EPISTEMIC"

        return MorphismPipelineResult(
            status="VERIFIED",
            mode=mode,
            steps_trace=steps_trace,
            gaps_queried=sorted(set(gap_tools)),
            web_queries_made=web_queries_made,
            morphisms_recalled=recalled_ids,
            morphisms_learned=learned_ids,
            morphisms_refuted=refuted_log,
            elapsed_ms=round((time.monotonic() - t0) * 1000.0, 2),
        )
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
