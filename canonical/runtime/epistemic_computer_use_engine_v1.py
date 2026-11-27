"""Goal-Directed Epistemic Computer-Use Engine.

Architecture:
    Start knowing ZERO hardcoded workflows about any tool in an arbitrary
    computer environment. Let the GOAL + SENSED ENVIRONMENT define the exact
    minimal questions the agent must answer:

      1. SENSE: Inspect workspace files, extensions, magic bytes, directories,
         and `$PATH` availability ONLY for goal-relevant tools.
      2. FORMULATE QUESTIONS: Turn the goal + sensed gaps into minimal,
         targeted epistemic questions (NOT "learn everything on the machine").
      3. ACQUIRE INSTANT KNOWLEDGE (Multi-Source, Zero LLM, Zero Weights):
           - Kind 1 (`local_manual`): Live `<tool> --help` / `<tool> <subcmd> --help`
             / `man` from the actual installed binary on THIS machine.
           - Kind 2 (`web_command_guide`): Live HTTPS fetch of structured,
             hole-parameterized command guides (`tldr-pages/tldr` via GitHub API
             with `github.com/blob` fallback + session cache).
           - Kind 3 (`web_documentation`): Live `jit_knowledge_v1.py` multi-source
             corroboration (GitHub / PyPI / npm / README code blocks) plus an
             optional pluggable `open_web_fetcher` for unrestricted environments.
         Every acquired web recipe's flags are cross-checked against the local
         binary's `--help` so stale or OS-incompatible flags are caught before
         execution and corroboration (`kinds_answered >= 2`) is measured.
      4. BIND & TEST IN STATE COPY (`the_branch_is_the_model`):
         Bind recipe holes to sensed workspace objects and goal targets, run in
         an isolated tempdir copy, check postconditions + frame invariants, and
         use `stderr` from any failure to formulate follow-up epistemic questions.
      5. COMMIT & DISTILL PERMANENTLY (`instant_cu_procedure_store_v1`):
         Once verified, apply to the real workspace and store the hole-abstracted
         procedure + observable preconditions in external inspectable/editable/
         deletable JSON (`parameters_stored: 0`, `external_model_calls: 0`).
         Future unseen workspaces with matching goals recall in Tier 0 with zero
         web lookups; counterexamples narrow or quarantine the stored procedure.
"""
from __future__ import annotations

import base64
import dataclasses
import difflib
import hashlib
import html as _html
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
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import instant_cu_procedure_store_v1 as PROC_STORE
from canonical.runtime import jit_knowledge_v1 as JIT

SCHEMA = "BRAIN_EPISTEMIC_COMPUTER_USE_ENGINE_V1"
AUTHORITY = "NONE"

_UA = {
    "User-Agent": "project-brain-epistemic-cu/1",
    "Accept": "application/vnd.github+json",
}

_DISK_CACHE_DIR = pathlib.Path(
    os.environ.get("BRAIN_EPISTEMIC_CACHE_DIR", "/tmp/brain_epistemic_cache")
)

_STOPWORDS = frozenset({
    "the", "and", "for", "with", "from", "into", "that", "this", "file", "files",
    "path", "your", "using", "use", "make", "create", "write", "save", "output",
    "input", "all", "are", "have", "has", "been", "should", "must", "will", "can",
    "to", "in", "of", "on", "at", "by", "as", "an", "a", "be", "is", "or", "it",
    "its", "their", "them", "then", "also", "only", "new", "named", "called",
})

# Standard media-type / keyword -> candidate executable names (checked via shutil.which;
# NO workflow or flags are hardcoded here — ONLY which installed binary to ask `--help` / web about).
_DOMAIN_TOOL_HINTS: dict[str, tuple[str, ...]] = {
    "tar": ("tar",),
    "tgz": ("tar",),
    "tar.gz": ("tar", "gzip"),
    "gzip": ("gzip", "tar"),
    "gz": ("gzip", "tar"),
    "zip": ("zip", "unzip"),
    "unzip": ("unzip",),
    "json": ("jq", "python3"),
    "jq": ("jq",),
    "base64": ("base64",),
    "sha256": ("sha256sum",),
    "sha1": ("sha1sum",),
    "md5": ("md5sum",),
    "checksum": ("sha256sum", "md5sum"),
    "patch": ("patch",),
    "diff": ("diff", "patch"),
    "sed": ("sed",),
    "awk": ("awk",),
    "grep": ("grep",),
    "sort": ("sort",),
    "uniq": ("uniq", "sort"),
    "cut": ("cut", "awk"),
    "tr": ("tr",),
    "wc": ("wc",),
    "find": ("find",),
    "head": ("head",),
    "tail": ("tail",),
    "openssl": ("openssl",),
    "certificate": ("openssl",),
    "x509": ("openssl",),
    "sqlite": ("sqlite3",),
    "sqlite3": ("sqlite3",),
    "git": ("git",),
    "gpg": ("gpg",),
    "xxd": ("xxd",),
    "gcc": ("gcc",),
    "python": ("python3",),
}

_EXT_TOOL_HINTS: dict[str, tuple[str, ...]] = {
    ".tar": ("tar",),
    ".tgz": ("tar",),
    ".gz": ("gzip", "tar"),
    ".zip": ("unzip", "zip"),
    ".json": ("jq", "python3"),
    ".patch": ("patch",),
    ".diff": ("patch", "diff"),
    ".b64": ("base64",),
    ".base64": ("base64",),
    ".pem": ("openssl",),
    ".crt": ("openssl",),
    ".key": ("openssl",),
    ".db": ("sqlite3",),
    ".sqlite": ("sqlite3",),
    ".sqlite3": ("sqlite3",),
    ".csv": ("awk", "cut", "sort", "python3"),
    ".tsv": ("awk", "cut", "sort"),
    ".txt": ("grep", "sed", "sort", "awk", "base64", "sha256sum", "wc"),
    ".log": ("grep", "awk", "sort", "wc"),
    ".c": ("gcc",),
}


@dataclasses.dataclass
class EpistemicQuestion:
    kind: str  # "local_help" | "web_tldr" | "web_jit_docs" | "error_refinement"
    tool: str
    subcommand: str
    query: str
    reason: str


@dataclasses.dataclass
class LocalHelpKnowledge:
    tool: str
    subcommand: str
    available: bool
    raw_excerpt: str
    short_flags: set[str]
    long_flags: set[str]
    flag_descriptions: dict[str, str]
    inline_examples: list[str]


@dataclasses.dataclass
class CommandRecipe:
    tool: str
    subcommand: str
    description: str
    template: str
    source_kind: str  # "web_command_guide" | "local_manual" | "web_documentation"
    source_url: str
    corroborated_flags: list[str] = dataclasses.field(default_factory=list)
    unverified_flags: list[str] = dataclasses.field(default_factory=list)
    corroborated_source_kinds: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class EpistemicSolveResult:
    status: str  # "VERIFIED" | "FAILED"
    tier_used: str  # "TIER0_RECALL" | "TIER1_EPISTEMIC_WEB_AND_HELP" | "TIER1_EPISTEMIC_LOCAL_HELP" | "NONE"
    workspace: str
    tool_used: str
    command_executed: str
    stdout_excerpt: str
    stderr_excerpt: str
    questions_asked: list[dict[str, Any]]
    sources_consulted: list[dict[str, Any]]
    corroborated_kinds: list[str]
    attempts: int
    refinement_rounds: int
    learned_procedure_id: str | None
    recalled_procedure_id: str | None
    verification_details: dict[str, Any]
    model_calls: int = 0
    parameters_stored: int = 0
    elapsed_s: float = 0.0


# ---------------------------------------------------------------------------
# 1. Sense Unknown Environment (Zero Prior Knowledge)
# ---------------------------------------------------------------------------

def _detect_magic(path: pathlib.Path) -> str:
    try:
        head = path.read_bytes()[:64]
    except OSError:
        return "unreadable"
    if not head:
        return "empty"
    if head.startswith(b"SQLite format 3\x00"):
        return "sqlite3_db"
    if head[:1] == b"\x0d" and len(head) >= 8:
        return "sqlite3_leaf_page_0x0d"
    if head.startswith(b"\x1f\x8b"):
        return "gzip"
    if head.startswith(b"PK\x03\x04"):
        return "zip"
    if head.startswith(b"BZh"):
        return "bzip2"
    if head.startswith(b"PAR1"):
        return "parquet"
    if head.startswith(b"-----BEGIN "):
        return "pem"
    if head.startswith(b"\x7fELF"):
        return "elf"
    try:
        full_head = path.read_bytes()[:512]
        if len(full_head) >= 265 and full_head[257:262] == b"ustar":
            return "tar"
    except OSError:
        pass
    try:
        txt = head.decode("utf-8")
        st = txt.lstrip()
        if st.startswith(("{", "[")):
            return "json_like"
        if st.startswith("--- ") or "\n@@ " in txt:
            return "unified_diff"
        return "text"
    except UnicodeDecodeError:
        return "binary"


def _file_digest(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            while True:
                b = f.read(65536)
                if not b:
                    break
                h.update(b)
        return h.hexdigest()[:16]
    except OSError:
        return "ERR"


def sense_unknown_environment(workspace: str | pathlib.Path) -> dict[str, Any]:
    root = pathlib.Path(workspace).resolve()
    files: list[dict[str, Any]] = []
    dirs: list[str] = []
    ext_counts: dict[str, int] = {}
    magic_counts: dict[str, int] = {}
    digests: dict[str, str] = {}

    if root.exists():
        for p in sorted(root.rglob("*")):
            rel = str(p.relative_to(root))
            parts = p.relative_to(root).parts
            if any(part == ".git" for part in parts[:-1]):
                continue
            if p.is_dir():
                if len(dirs) < 100:
                    dirs.append(rel)
                continue
            if not p.is_file():
                continue
            ext = "".join(p.suffixes[-2:]).lower() if len(p.suffixes) >= 2 and p.suffixes[-2].lower() == ".tar" else p.suffix.lower()
            magic = _detect_magic(p)
            ext_counts[ext] = ext_counts.get(ext, 0) + 1
            magic_counts[magic] = magic_counts.get(magic, 0) + 1
            if len(files) < 200:
                files.append({
                    "rel": rel,
                    "abs": str(p),
                    "name": p.name,
                    "ext": ext,
                    "size": p.stat().st_size,
                    "magic": magic,
                })
                digests[rel] = _file_digest(p)

    return {
        "workspace": str(root),
        "files": files,
        "dirs": dirs,
        "ext_counts": ext_counts,
        "magic_counts": magic_counts,
        "has_git": (root / ".git").is_dir() or any(d.endswith(".git") for d in dirs),
        "digests": digests,
    }


# ---------------------------------------------------------------------------
# 2. Goal-Defined Epistemic Question Formulation
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    return [
        t for t in re.findall(r"[a-z0-9_.-]+", text.lower())
        if len(t) >= 2 and t not in _STOPWORDS
    ]


def parse_goal_specification(instruction: str, env: Mapping[str, Any]) -> dict[str, Any]:
    ws = pathlib.Path(env["workspace"])
    tokens = _tokenize(instruction)
    token_set = set(tokens)

    # Extract quoted strings (e.g., jq filters, sed scripts, grep patterns, literal args)
    quoted_literals: list[str] = []
    for m in re.finditer(r"`([^`\n]{1,160})`|'([^'\n]{1,160})'|\"([^\"\n]{1,160})\"", instruction):
        val = m.group(1) or m.group(2) or m.group(3) or ""
        if val and val not in quoted_literals:
            quoted_literals.append(val)

    # Extract path-like tokens mentioned in the instruction
    raw_path_tokens: list[str] = []
    for m in re.finditer(r"(?:^|[\s`'\"(])((?:[/.~]?[\w.-]+/)+[\w.-]*|[\w.-]+\.[A-Za-z0-9]{1,8})(?=$|[\s`'\".,;):])", instruction):
        cand = m.group(1).strip().rstrip(".,;:")
        if cand and cand not in raw_path_tokens:
            raw_path_tokens.append(cand)

    existing_rel_map = {f["rel"]: f for f in env.get("files", [])}
    existing_name_map = {f["name"]: f for f in env.get("files", [])}
    existing_dirs = set(env.get("dirs", []))

    input_paths: list[str] = []
    output_paths: list[str] = []
    input_dirs: list[str] = []
    output_dirs: list[str] = []

    def _resolve_rel(tok: str) -> tuple[str, bool, bool]:
        p = pathlib.Path(tok)
        if p.is_absolute():
            try:
                rel = str(p.resolve().relative_to(ws))
                return rel, p.is_file(), p.is_dir()
            except ValueError:
                return str(p), p.is_file(), p.is_dir()
        cleaned = tok.lstrip("./")
        if cleaned in existing_rel_map:
            return cleaned, True, False
        if cleaned in existing_dirs or (ws / cleaned).is_dir():
            return cleaned, False, True
        if cleaned in existing_name_map:
            return existing_name_map[cleaned]["rel"], True, False
        return cleaned, (ws / cleaned).is_file(), (ws / cleaned).is_dir()

    # Use local context ("into/to/as/write/save/output/create <path>" vs "from/of/extract/read <path>")
    for tok in raw_path_tokens:
        if tok.startswith(("http://", "https://")):
            continue
        rel, is_f, is_d = _resolve_rel(tok)
        pos = instruction.find(tok)
        before = instruction[max(0, pos - 40):pos].lower() if pos >= 0 else ""
        is_output_ctx = bool(re.search(
            r"\b(?:to|into|as|output|save|write|create|produce|generate|archive|compressed|result|destination|target)\b\s*(?:file|directory|dir|folder|archive)?\s*$",
            before,
        ))
        is_dir_ctx = tok.endswith("/") or bool(re.search(r"\b(?:directory|dir|folder)\b\s*$", before))

        if is_f and not is_output_ctx:
            if rel not in input_paths:
                input_paths.append(rel)
        elif is_d and not is_output_ctx:
            if rel not in input_dirs:
                input_dirs.append(rel)
        elif is_output_ctx:
            if is_dir_ctx and "." not in pathlib.Path(rel).name:
                if rel not in output_dirs:
                    output_dirs.append(rel)
            else:
                if rel not in output_paths:
                    output_paths.append(rel)
        else:
            if not is_f and not is_d:
                if is_dir_ctx and "." not in pathlib.Path(rel).name:
                    if rel not in output_dirs:
                        output_dirs.append(rel)
                elif "." in pathlib.Path(rel).name:
                    if rel not in output_paths:
                        output_paths.append(rel)

    # Also detect explicitly named input/output directories like "from directory docs" / "into directory unpacked"
    for m in re.finditer(r"\b(?:from|of|in|on)\s+(?:the\s+)?(?:directory|dir|folder)\s+[`'\"]?([A-Za-z0-9_./-]+)[`'\"]?", instruction, re.I):
        d = m.group(1).strip().strip("/")
        if d and (d in existing_dirs or (ws / d).is_dir()) and d not in input_dirs:
            input_dirs.append(d)
    for m in re.finditer(r"\b(?:into|to)\s+(?:the\s+)?(?:directory|dir|folder)\s+[`'\"]?([A-Za-z0-9_./-]+)[`'\"]?", instruction, re.I):
        d = m.group(1).strip().strip("/")
        if d and d not in output_dirs and d not in input_paths and d not in output_paths:
            output_dirs.append(d)

    # If no explicit input_paths mentioned, fall back to workspace files (excluding output_paths)
    if not input_paths and not input_dirs:
        for f in env.get("files", []):
            if f["rel"] not in output_paths:
                input_paths.append(f["rel"])

    # Candidate tools from: (a) explicit instruction mentions on $PATH, (b) domain keywords, (c) file extensions/magic
    tool_scores: dict[str, float] = {}

    def _bump(tool: str, score: float) -> None:
        if shutil.which(tool):
            tool_scores[tool] = tool_scores.get(tool, 0.0) + score

    for tok in re.findall(r"\b[a-z][a-z0-9_-]{1,20}\b", instruction.lower()):
        if tok in _DOMAIN_TOOL_HINTS:
            for t in _DOMAIN_TOOL_HINTS[tok]:
                _bump(t, 4.0 if tok == t else 2.5)
        elif tok not in _STOPWORDS and len(tok) >= 2 and shutil.which(tok):
            # Avoid accidentally treating common English verbs like "test", "join", "split", "id", "dir"
            # as primary tools unless nothing stronger appears
            if tok in {"tar", "jq", "sed", "awk", "grep", "gzip", "gunzip", "zip", "unzip",
                       "base64", "sha256sum", "md5sum", "patch", "diff", "openssl", "sqlite3",
                       "git", "sort", "uniq", "cut", "tr", "wc", "find", "head", "tail",
                       "xxd", "gpg", "gcc", "python3"}:
                _bump(tok, 4.5)

    for p in input_paths + output_paths:
        low = p.lower()
        if low.endswith(".tar.gz") or low.endswith(".tgz"):
            _bump("tar", 3.5)
            _bump("gzip", 1.5)
        else:
            ext = pathlib.Path(low).suffix
            for t in _EXT_TOOL_HINTS.get(ext, ()):
                _bump(t, 1.5)

    for magic in env.get("magic_counts", {}):
        if magic == "gzip":
            _bump("tar", 2.0)
            _bump("gzip", 2.5)
        elif magic == "tar":
            _bump("tar", 3.5)
        elif magic == "zip":
            _bump("unzip", 3.0)
            _bump("zip", 1.5)
        elif magic == "json_like":
            _bump("jq", 2.0)
        elif magic == "unified_diff":
            _bump("patch", 3.5)
        elif magic == "pem":
            _bump("openssl", 3.0)
        elif magic == "sqlite3_db":
            _bump("sqlite3", 3.0)

    # Extra semantic boosts from instruction action verbs
    low_inst = instruction.lower()
    if any(w in low_inst for w in ("extract", "unpack", "decompress", "untar")):
        if any(p.endswith((".tar.gz", ".tgz", ".tar")) for p in input_paths):
            _bump("tar", 4.0)
        elif any(p.endswith(".zip") for p in input_paths):
            _bump("unzip", 4.0)
        elif any(p.endswith(".gz") for p in input_paths):
            _bump("gzip", 4.0)
    if any(w in low_inst for w in ("archive", "compress", "tarball", "pack")):
        if any(p.endswith((".tar.gz", ".tgz", ".tar")) for p in output_paths):
            _bump("tar", 4.0)
        elif any(p.endswith(".zip") for p in output_paths):
            _bump("zip", 4.0)
    if any(w in low_inst for w in ("decode", "encode")) and "base64" in low_inst:
        _bump("base64", 5.0)
    if any(w in low_inst for w in ("apply patch", "apply the patch", "patch ")):
        _bump("patch", 5.0)
    if any(w in low_inst for w in ("sha256", "sha-256")):
        _bump("sha256sum", 5.0)
    if any(w in low_inst for w in ("query", "filter", "select", "extract field", "keys")) and any(
        p.endswith(".json") for p in input_paths
    ):
        _bump("jq", 3.5)

    candidate_tools = [t for t, _ in sorted(tool_scores.items(), key=lambda kv: (-kv[1], kv[0]))][:4]

    # Detect explicit subcommand for multi-subcommand tools (git, openssl)
    subcommand = ""
    for tool in candidate_tools:
        if tool in ("git", "openssl"):
            m = re.search(rf"\b{re.escape(tool)}\s+([a-z][a-z0-9-]+)\b", low_inst)
            if m:
                subcommand = m.group(1)
                break

    # Identify archive path & non-archive file paths cleanly
    archive_paths = [p for p in input_paths + output_paths if p.lower().endswith((".tar.gz", ".tgz", ".tar", ".zip", ".gz"))]
    non_archive_inputs = [p for p in input_paths if p not in archive_paths]

    return {
        "instruction": instruction,
        "tokens": tokens,
        "token_set": sorted(token_set),
        "candidate_tools": candidate_tools,
        "subcommand": subcommand,
        "input_paths": input_paths,
        "non_archive_inputs": non_archive_inputs,
        "output_paths": output_paths,
        "input_dirs": input_dirs,
        "output_dirs": output_dirs,
        "archive_paths": archive_paths,
        "quoted_literals": quoted_literals,
        "intent_signature": _build_intent_signature(candidate_tools, tokens, output_paths, output_dirs),
    }


def _build_intent_signature(
    tools: Sequence[str],
    tokens: Sequence[str],
    output_paths: Sequence[str],
    output_dirs: Sequence[str],
) -> str:
    action_vocab = {
        "extract", "unpack", "decompress", "compress", "archive", "create",
        "decode", "encode", "filter", "query", "sort", "unique", "deduplicate",
        "count", "replace", "substitute", "patch", "apply", "diff", "hash",
        "checksum", "sha256", "verify", "sign", "convert", "merge", "split",
        "search", "match", "remove", "delete", "list", "format", "pretty",
    }
    acts = sorted(t for t in set(tokens) if t in action_vocab)[:4]
    primary_tool = tools[0] if tools else "unknown"
    out_kind = "dir" if output_dirs and not output_paths else ("file" if output_paths else "inplace")
    return f"epistemic__{primary_tool}__{'_'.join(acts) or 'run'}__{out_kind}"


def formulate_epistemic_questions(
    goal_spec: Mapping[str, Any],
    env: Mapping[str, Any],
) -> list[EpistemicQuestion]:
    """Ask ONLY what the goal + unknown environment demand — never 'everything'."""
    questions: list[EpistemicQuestion] = []
    tools = list(goal_spec.get("candidate_tools") or [])[:3]
    subcmd = str(goal_spec.get("subcommand") or "")
    intent_str = " ".join(goal_spec.get("tokens", [])[:6])

    for idx, tool in enumerate(tools):
        questions.append(EpistemicQuestion(
            kind="local_help",
            tool=tool,
            subcommand=subcmd if idx == 0 else "",
            query=f"{tool} {subcmd} --help".strip(),
            reason=f"Discover exact flags & syntax of installed `{tool}` on this host",
        ))
        questions.append(EpistemicQuestion(
            kind="web_tldr",
            tool=tool,
            subcommand=subcmd if idx == 0 else "",
            query=f"tldr {tool} {subcmd}".strip(),
            reason=f"Fetch live hole-parameterized command recipes for `{tool}` matching goal `{intent_str}`",
        ))

    if tools:
        questions.append(EpistemicQuestion(
            kind="web_jit_docs",
            tool=tools[0],
            subcommand=subcmd,
            query=f"{tools[0]} {subcmd} {intent_str}".strip(),
            reason=f"Corroborate `{tools[0]}` usage across independent web sources via jit_knowledge_v1",
        ))
    return questions


# ---------------------------------------------------------------------------
# 3. Multi-Source Instant Knowledge Acquisition (Local + Live Web)
# ---------------------------------------------------------------------------

def query_local_cli_help(tool: str, subcommand: str = "", timeout_s: float = 5.0) -> LocalHelpKnowledge:
    """Interrogate the actual installed binary on THIS machine (`--help` / `-h`)."""
    if not shutil.which(tool):
        return LocalHelpKnowledge(tool, subcommand, False, "", set(), set(), {}, [])

    cmd_variants: list[list[str]] = []
    if subcommand:
        cmd_variants.append([tool, subcommand, "--help"])
        cmd_variants.append([tool, "help", subcommand])
    cmd_variants.extend([[tool, "--help"], [tool, "-h"]])
    if shutil.which("man"):
        cmd_variants.append(["man", tool])

    combined = ""
    for cmd in cmd_variants:
        try:
            cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
            txt = (cp.stdout or "") + "\n" + (cp.stderr or "")
            if len(txt.strip()) >= 40:
                combined = txt
                break
        except Exception:
            continue

    short_flags: set[str] = set()
    long_flags: set[str] = set()
    flag_descs: dict[str, str] = {}
    inline_examples: list[str] = []

    for ln in combined.splitlines():
        st = ln.strip()
        # Parse flag documentation lines like "-d, --decode   decode data"
        flags_in_ln = re.findall(r"(?<![A-Za-z0-9-])(--[a-zA-Z0-9][a-zA-Z0-9_-]*|-[a-zA-Z0-9])(?![A-Za-z0-9_-])", st)
        if flags_in_ln and (st.startswith("-") or re.match(r"^\s*-", ln)):
            for fl in flags_in_ln:
                if fl.startswith("--"):
                    long_flags.add(fl)
                else:
                    short_flags.add(fl)
                if fl not in flag_descs:
                    flag_descs[fl] = st[:180]
        # Also detect inline command examples starting with the tool name
        if st.startswith(f"{tool} ") and len(st) < 140 and not st.lower().startswith(f"{tool}:"):
            inline_examples.append(st)

    # Also scan short option clusters in Usage lines (e.g. "tar [-cfxzv] ...")
    for m in re.finditer(r"-\[?([a-zA-Z0-9]{2,12})\]?", combined[:1200]):
        for ch in m.group(1):
            short_flags.add(f"-{ch}")

    return LocalHelpKnowledge(
        tool=tool,
        subcommand=subcommand,
        available=bool(combined.strip()),
        raw_excerpt=combined[:3000],
        short_flags=short_flags,
        long_flags=long_flags,
        flag_descriptions=flag_descs,
        inline_examples=inline_examples[:12],
    )


def _http_get_cached(url: str, timeout_s: float = 8.0) -> tuple[bool, str, str]:
    """Fetch HTTPS text with disk cache so repeat epistemic probes are instant & polite."""
    _DISK_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
    cache_file = _DISK_CACHE_DIR / f"{key}.json"
    if cache_file.is_file():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            if time.time() - float(cached.get("ts", 0)) < 3600.0:
                return bool(cached.get("ok")), str(cached.get("body", "")), str(cached.get("err", ""))
        except Exception:
            pass

    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        cache_file.write_text(json.dumps({"ts": time.time(), "ok": True, "body": body, "err": ""}), encoding="utf-8")
        return True, body, ""
    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
        # Cache 404 briefly (10 min), transient errors very briefly (20s)
        ttl_offset = 0.0 if "404" in err else 3580.0
        try:
            cache_file.write_text(json.dumps({"ts": time.time() - ttl_offset, "ok": False, "body": "", "err": err}), encoding="utf-8")
        except OSError:
            pass
        return False, "", err


def _extract_tldr_markdown_from_github_blob(html_text: str) -> str:
    """Fallback parser for `github.com/.../blob/main/...md` HTML payload (no API rate limit)."""
    m = re.search(r'"rawLines"\s*:\s*(\[.*?\])\s*,\s*"stylingDirectives"', html_text)
    if m:
        try:
            lines = json.loads(m.group(1))
            if isinstance(lines, list):
                return "\n".join(str(x) for x in lines)
        except Exception:
            pass
    # Fallback: strip tags around code/list blocks if JSON blob changed
    m2 = re.search(r"<article[^>]*>(.*?)</article>", html_text, re.S)
    if m2:
        cleaned = re.sub(r"<[^>]+>", "\n", m2.group(1))
        return _html.unescape(cleaned)
    return ""


def fetch_web_tldr_recipes(
    tool: str,
    subcommand: str = "",
    timeout_s: float = 8.0,
) -> tuple[list[CommandRecipe], list[dict[str, Any]]]:
    """Fetch live structured command guides from `github.com/tldr-pages/tldr`."""
    page_names = []
    if subcommand:
        page_names.append(f"{tool}-{subcommand}")
    page_names.append(tool)

    recipes: list[CommandRecipe] = []
    provenance: list[dict[str, Any]] = []

    for pname in page_names:
        md_text = ""
        source_url = ""
        for platform_dir in ("common", "linux"):
            api_url = f"https://api.github.com/repos/tldr-pages/tldr/contents/pages/{platform_dir}/{pname}.md"
            ok, body, err = _http_get_cached(api_url, timeout_s=timeout_s)
            if ok and body:
                try:
                    payload = json.loads(body)
                    if payload.get("content"):
                        md_text = base64.b64decode(payload["content"]).decode("utf-8", errors="replace")
                        source_url = str(payload.get("html_url") or api_url)
                        break
                except Exception:
                    pass
            # Rate-limit fallback to github.com blob HTML
            if not ok and ("403" in err or "429" in err):
                blob_url = f"https://github.com/tldr-pages/tldr/blob/main/pages/{platform_dir}/{pname}.md"
                ok2, body2, _ = _http_get_cached(blob_url, timeout_s=timeout_s)
                if ok2 and body2:
                    extracted = _extract_tldr_markdown_from_github_blob(body2)
                    if "`" in extracted:
                        md_text = extracted
                        source_url = blob_url
                        break

        if not md_text:
            continue

        provenance.append({
            "kind": "web_command_guide",
            "provider": "tldr-pages/tldr",
            "url": source_url,
            "bytes": len(md_text),
        })

        # Parse tldr format: `- description:` followed by `` `command template` ``
        cur_desc = ""
        for raw_ln in md_text.splitlines():
            ln = raw_ln.strip()
            if ln.startswith("- ") and ln.endswith(":"):
                cur_desc = ln[2:-1].strip()
                # Strip tldr mnemonic brackets like "[c]reate" -> "create"
                cur_desc = re.sub(r"\[([A-Za-z0-9-]+)\]", r"\1", cur_desc)
            elif ln.startswith("`") and ln.endswith("`") and len(ln) > 2:
                tpl = ln[1:-1].strip()
                if cur_desc and tpl:
                    recipes.append(CommandRecipe(
                        tool=tool,
                        subcommand=subcommand,
                        description=cur_desc,
                        template=tpl,
                        source_kind="web_command_guide",
                        source_url=source_url,
                    ))
                cur_desc = ""

    return recipes, provenance


def _extract_flags_from_command(cmd_template: str) -> list[str]:
    """Extract CLI flags from a command template, skipping `{{...}}` hole internals."""
    stripped = re.sub(r"\{\{.*?\}\}", " ", cmd_template)
    flags: list[str] = []
    for tok in stripped.split()[1:]:
        if tok.startswith("--") and len(tok) > 2:
            flags.append(tok.split("=", 1)[0])
        elif tok.startswith("-") and len(tok) >= 2 and not tok[1:].isdigit():
            for ch in tok[1:]:
                if ch.isalnum():
                    flags.append(f"-{ch}")
    return flags


def corroborate_recipe_with_local_help(
    recipe: CommandRecipe,
    local_help: LocalHelpKnowledge | None,
) -> CommandRecipe:
    """Cross-check every flag in a web recipe against the actual installed binary's `--help`."""
    kinds = {recipe.source_kind}
    if local_help is None or not local_help.available:
        recipe.corroborated_source_kinds = sorted(kinds)
        return recipe

    # Also expand `{{[-x|--long]}}` choices by preferring flags verified in local_help
    def _pick_flag_choice(m: re.Match[str]) -> str:
        inner = m.group(1)
        if "|" in inner and inner.startswith("[") and inner.endswith("]"):
            opts = [o.strip() for o in inner[1:-1].split("|") if o.strip()]
            for opt in opts:
                if opt in local_help.long_flags or opt in local_help.short_flags:
                    return opt
            return opts[0]
        return m.group(0)

    recipe.template = re.sub(r"\{\{(\[-[^}]+\])\}\}", _pick_flag_choice, recipe.template)

    flags = _extract_flags_from_command(recipe.template)
    corrob: list[str] = []
    unver: list[str] = []
    for fl in flags:
        if fl in local_help.short_flags or fl in local_help.long_flags or fl in local_help.raw_excerpt:
            corrob.append(fl)
        else:
            unver.append(fl)

    recipe.corroborated_flags = corrob
    recipe.unverified_flags = unver
    if local_help.available and (corrob or not flags):
        kinds.add("local_manual")
    recipe.corroborated_source_kinds = sorted(kinds)
    return recipe


def fetch_web_jit_corroboration(
    query: str,
    tool: str,
    open_web_fetcher: Callable[[str], Sequence[Mapping[str, Any]]] | None = None,
    timeout_s: int = 8,
) -> tuple[list[CommandRecipe], list[dict[str, Any]]]:
    """Consult `jit_knowledge_v1` (live GitHub/PyPI/npm/docs) + optional open_web_fetcher."""
    recipes: list[CommandRecipe] = []
    provenance: list[dict[str, Any]] = []

    if open_web_fetcher is not None:
        try:
            docs = list(open_web_fetcher(query) or [])
            for d in docs[:4]:
                url = str(d.get("url") or "open_web")
                body = str(d.get("content") or d.get("summary") or "")
                provenance.append({"kind": "open_web", "provider": "open_web_fetcher", "url": url, "bytes": len(body)})
                for m in re.finditer(r"```(?:sh|bash|shell|console)?\n(.*?)```", body, re.S):
                    for ln in m.group(1).splitlines():
                        st = ln.strip().lstrip("$ ").strip()
                        if st.startswith(f"{tool} "):
                            recipes.append(CommandRecipe(
                                tool=tool,
                                subcommand="",
                                description=str(d.get("title") or query)[:140],
                                template=st,
                                source_kind="web_documentation",
                                source_url=url,
                            ))
        except Exception:
            pass

    # Query repo's own multi-source JIT knowledge engine (bounded & cached)
    try:
        res = JIT.resolve(query, only=("github", "pypi"), limit=2, timeout_s=timeout_s)
        for src_name, items in (res.get("by_source") or {}).items():
            if items:
                provenance.append({
                    "kind": "web_documentation",
                    "provider": f"jit_knowledge_v1:{src_name}",
                    "url": str(items[0].get("url") or ""),
                    "count": len(items),
                })
    except Exception:
        pass

    return recipes, provenance


# ---------------------------------------------------------------------------
# 4. Hole Binding & Candidate Synthesis (Zero Hardcoded Workflows)
# ---------------------------------------------------------------------------

def _normalize_tldr_flag_choices(template: str) -> str:
    """Resolve remaining `{{[-x|--long]}}` choices cleanly."""
    def _rep(m: re.Match[str]) -> str:
        opts = [o.strip() for o in m.group(1)[1:-1].split("|") if o.strip()]
        return opts[0] if opts else ""
    return re.sub(r"\{\{(\[-[^}]+\])\}\}", _rep, template)


def _bind_recipe_holes(
    recipe: CommandRecipe,
    goal_spec: Mapping[str, Any],
    env: Mapping[str, Any],
) -> list[tuple[str, dict[str, str], str | None]]:
    """Bind `{{hole}}` placeholders in a command recipe to sensed env & goal targets.

    Returns a list of `(concrete_command, hole_to_concrete_map, redirect_stdout_to)`.
    """
    tpl = _normalize_tldr_flag_choices(recipe.template)
    holes = re.findall(r"\{\{([^}]+)\}\}", tpl)

    inputs = list(goal_spec.get("input_paths") or [])
    non_arch_inputs = list(goal_spec.get("non_archive_inputs") or [])
    outputs = list(goal_spec.get("output_paths") or [])
    in_dirs = list(goal_spec.get("input_dirs") or [])
    out_dirs = list(goal_spec.get("output_dirs") or [])
    archives = list(goal_spec.get("archive_paths") or [])
    literals = list(goal_spec.get("quoted_literals") or [])

    # Filter literals that are not already file paths
    all_known_paths = set(inputs + outputs + in_dirs + out_dirs + archives)
    expr_literals = [lit for lit in literals if lit not in all_known_paths and lit.lstrip("./") not in all_known_paths]

    is_extract = any(w in goal_spec.get("token_set", []) for w in ("extract", "unpack", "decompress", "untar", "unzip"))
    is_create_arch = any(w in goal_spec.get("token_set", []) for w in ("archive", "compress", "create", "pack", "tarball"))

    used_inputs = 0
    bindings: dict[str, str] = {}  # standard store hole -> concrete value
    concrete_parts: list[tuple[str, str]] = []  # (raw {{hole}}, concrete shell arg)
    unresolved = False

    for raw_h in holes:
        hl = raw_h.lower().strip()
        val: str | None = None
        store_hole = "__ARG_1__"

        # Any hole immediately preceded by POSIX stdout redirection `>` is ALWAYS an output path!
        is_posix_redir_target = bool(re.search(r">\s*\{\{" + re.escape(raw_h) + r"\}\}", tpl))
        if is_posix_redir_target:
            store_hole = "__OUTPUT_PATH__"
            if outputs:
                val = outputs[0]
        elif any(k in hl for k in ("archive", ".tar", ".zip", ".gz", "tarball")):
            store_hole = "__ARCHIVE_PATH__"
            if is_create_arch and outputs:
                val = next((p for p in outputs if p in archives), outputs[0])
            elif is_extract and inputs:
                val = next((p for p in inputs if p in archives), inputs[0])
            elif archives:
                val = archives[0]
            elif outputs:
                val = outputs[0]
            elif inputs:
                val = inputs[0]
        elif any(k in hl for k in ("target_dir", "destination", "output_dir", "directory", "folder")):
            if is_extract and out_dirs:
                val = out_dirs[0]
                store_hole = "__OUTPUT_DIR__"
            elif in_dirs:
                val = in_dirs[0]
                store_hole = "__INPUT_DIR__"
            elif out_dirs:
                val = out_dirs[0]
                store_hole = "__OUTPUT_DIR__"
            else:
                val = "."
                store_hole = "__INPUT_DIR__"
        elif any(k in hl for k in ("output", "target", "dest", "decoded", "encoded")) and not hl.startswith("path/to/file1"):
            store_hole = "__OUTPUT_PATH__"
            if outputs:
                val = outputs[0]
        elif any(k in hl for k in ("patch", "diff")):
            store_hole = "__INPUT_PATH__"
            patch_cand = next((p for p in inputs if p.endswith((".patch", ".diff"))), None)
            val = patch_cand or (inputs[0] if inputs else None)
        elif hl.startswith("cat ") and "path/to/" in hl:
            store_hole = "__INPUT_PATH__"
            if inputs:
                concrete_parts.append((raw_h, f"cat {shlex.quote(inputs[0])}"))
                bindings["__INPUT_PATH__"] = inputs[0]
                continue
        elif any(k in hl for k in ("file1", "files", "path/to/file1")):
            if in_dirs:
                val = in_dirs[0]
                store_hole = "__INPUT_DIR__"
            else:
                store_hole = "__INPUT_PATH__"
                cands = non_arch_inputs or inputs
                if cands:
                    val = " ".join(shlex.quote(c) for c in cands)
                    concrete_parts.append((raw_h, val))
                    bindings["__INPUT_PATH__"] = cands[0]
                    continue
        elif any(k in hl for k in ("file", "input", "source", "path/to/")):
            store_hole = "__INPUT_PATH__"
            pool = non_arch_inputs if (recipe.tool == "tar" and is_create_arch and non_arch_inputs) else inputs
            if used_inputs < len(pool):
                val = pool[used_inputs]
                used_inputs += 1
            elif pool:
                val = pool[0]
            elif in_dirs:
                val = in_dirs[0]
                store_hole = "__INPUT_DIR__"
        elif any(k in hl for k in ("filter", "query", "jq", "expression", "script", "pattern", "regex", "search")):
            store_hole = "__QUERY__" if any(k in hl for k in ("filter", "query", "jq")) else "__PATTERN__"
            if expr_literals:
                val = expr_literals[0]
        elif any(k in hl for k in ("delimiter", "separator", "field", "column", "number", "count", "string")):
            store_hole = "__ARG_1__"
            if expr_literals:
                val = expr_literals[0]
        else:
            if expr_literals:
                val = expr_literals[0]
                store_hole = "__ARG_1__"
            elif inputs:
                val = inputs[0]
                store_hole = "__INPUT_PATH__"

        if val is None:
            unresolved = True
            break

        bindings[store_hole] = val
        # Quote safely unless already inside single/double quotes in the template
        concrete_parts.append((raw_h, val))

    if unresolved:
        return []

    cmd = tpl
    for raw_h, val in concrete_parts:
        token = "{{" + raw_h + "}}"
        idx = cmd.find(token)
        if idx < 0:
            continue
        # If template already wraps token in quotes like `'{{filter}}'`, insert raw; else shlex.quote
        quoted_in_tpl = (
            idx > 0 and idx + len(token) < len(cmd)
            and cmd[idx - 1] == cmd[idx + len(token)]
            and cmd[idx - 1] in ("'", '"')
        )
        if quoted_in_tpl:
            rep = val
        elif raw_h.lower().startswith(("path/to/file1", "cat ")):
            rep = val  # already shell-formatted
        else:
            rep = shlex.quote(val)
        cmd = cmd[:idx] + rep + cmd[idx + len(token):]

    out_variants: list[tuple[str, dict[str, str], str | None]] = []

    # Check if target output_path is already referenced in cmd
    primary_out = outputs[0] if outputs else None
    cmd_writes_output = bool(primary_out and primary_out in cmd)

    if primary_out and not cmd_writes_output:
        b_redir = dict(bindings)
        b_redir["__OUTPUT_PATH__"] = primary_out
        out_variants.append((cmd, b_redir, primary_out))
    out_variants.append((cmd, bindings, None))

    # For extraction into an explicit output_dir when recipe doesn't mention it, add `-C <out_dir>` / `-d <out_dir>`
    if is_extract and out_dirs and out_dirs[0] not in cmd:
        od = out_dirs[0]
        b_dir = dict(bindings)
        b_dir["__OUTPUT_DIR__"] = od
        if recipe.tool == "tar":
            out_variants.insert(0, (f"{cmd} -C {shlex.quote(od)}", b_dir, None))
        elif recipe.tool == "unzip":
            out_variants.insert(0, (f"{cmd} -d {shlex.quote(od)}", b_dir, None))

    return out_variants


def _synthesize_help_fallback_recipes(
    local_help: LocalHelpKnowledge,
    goal_spec: Mapping[str, Any],
) -> list[CommandRecipe]:
    """Synthesize minimal candidate recipes strictly from local `--help` flag descriptions!

    ZERO hardcoded workflows — matches goal words against the binary's own `--help`
    option documentation (`flag_descriptions`).
    """
    recipes: list[CommandRecipe] = []
    expr_lits = [
        lit for lit in (goal_spec.get("quoted_literals") or [])
        if lit not in set(list(goal_spec.get("input_paths") or []) + list(goal_spec.get("output_paths") or []))
    ]
    if not local_help.available:
        if expr_lits:
            recipes.append(CommandRecipe(
                tool=local_help.tool,
                subcommand=local_help.subcommand,
                description=f"direct expression invocation of {local_help.tool} {' '.join(goal_spec.get('tokens', [])[:4])}",
                template=f"{local_help.tool} '{{{{query}}}}' {{{{path/to/file}}}}",
                source_kind="local_manual",
                source_url=f"local://{local_help.tool}/invocation",
                corroborated_source_kinds=["local_manual"],
            ))
        return recipes
    # Include all >=2-char alphanumeric tokens from instruction (including "raw", "output", "case", "ignore")
    raw_inst_toks = set(re.findall(r"[a-z0-9]{2,}", str(goal_spec.get("instruction") or "").lower())) - {
        "the", "and", "for", "with", "from", "into", "that", "this", "file", "files", "use", "using", "save", "write",
        local_help.tool.lower(),
    }
    matched_flags: list[tuple[int, int, str]] = []
    for fl, desc in local_help.flag_descriptions.items():
        desc_toks = set(re.findall(r"[a-z0-9]{2,}", f"{fl} {desc}".lower()))
        ov = len(raw_inst_toks & desc_toks)
        if ov > 0:
            # Prefer higher overlap, then lowercase short flag / concise flag
            is_short_lower = 1 if (len(fl) == 2 and fl[1].islower()) else 0
            matched_flags.append((ov, is_short_lower, fl))
    matched_flags.sort(key=lambda x: (-x[0], -x[1], len(x[2]), x[2]))

    expr_lits = [
        lit for lit in (goal_spec.get("quoted_literals") or [])
        if lit not in set(list(goal_spec.get("input_paths") or []) + list(goal_spec.get("output_paths") or []))
    ]

    for _, _, top_fl in matched_flags[:4]:
        if expr_lits:
            recipes.append(CommandRecipe(
                tool=local_help.tool,
                subcommand=local_help.subcommand,
                description=f"local --help match with expression: {local_help.flag_descriptions.get(top_fl, '')}",
                template=f"{local_help.tool} {top_fl} '{{{{query}}}}' {{{{path/to/file}}}}",
                source_kind="local_manual",
                source_url=f"local://{local_help.tool}/--help",
                corroborated_flags=[top_fl],
                corroborated_source_kinds=["local_manual"],
            ))
        recipes.append(CommandRecipe(
            tool=local_help.tool,
            subcommand=local_help.subcommand,
            description=f"local --help match: {local_help.flag_descriptions.get(top_fl, '')}",
            template=f"{local_help.tool} {top_fl} {{{{path/to/file}}}}",
            source_kind="local_manual",
            source_url=f"local://{local_help.tool}/--help",
            corroborated_flags=[top_fl],
            corroborated_source_kinds=["local_manual"],
        ))
    if expr_lits:
        recipes.append(CommandRecipe(
            tool=local_help.tool,
            subcommand=local_help.subcommand,
            description=f"local --help expression invocation of {local_help.tool} {' '.join(goal_spec.get('tokens', [])[:4])}",
            template=f"{local_help.tool} '{{{{query}}}}' {{{{path/to/file}}}}",
            source_kind="local_manual",
            source_url=f"local://{local_help.tool}/--help",
            corroborated_source_kinds=["local_manual"],
        ))
    # Plain invocation with input file (e.g. `sha256sum {{path/to/file}}`, `sort {{path/to/file}}`)
    recipes.append(CommandRecipe(
        tool=local_help.tool,
        subcommand=local_help.subcommand,
        description=f"local --help base invocation of {local_help.tool}",
        template=f"{local_help.tool} {{{{path/to/file}}}}",
        source_kind="local_manual",
        source_url=f"local://{local_help.tool}/--help",
        corroborated_source_kinds=["local_manual"],
    ))
    return recipes


def _score_recipe(recipe: CommandRecipe, goal_spec: Mapping[str, Any]) -> tuple[float, int, int]:
    goal_toks = set(goal_spec.get("tokens") or [])
    desc_toks = set(_tokenize(recipe.description + " " + recipe.template))
    overlap = float(len(goal_toks & desc_toks))

    # Boost exact matches on action verbs & file extensions
    low_desc = recipe.description.lower()
    low_inst = str(goal_spec.get("instruction") or "").lower()
    for key in ("extract", "create", "gzip", "decode", "encode", "raw", "unique", "reverse",
                "numeric", "patch", "apply", "sha256", "sort", "filter", "in-place", "replace",
                "directory", "archive", "compress", "decompress", "recursive"):
        if key in low_inst and key in low_desc:
            overlap += 2.0

    # Boost recipes that actually use the quoted expression when instruction supplied one
    expr_lits = [
        lit for lit in (goal_spec.get("quoted_literals") or [])
        if lit not in set(list(goal_spec.get("input_paths") or []) + list(goal_spec.get("output_paths") or []))
    ]
    if expr_lits and any(k in recipe.template.lower() for k in ("{{query}}", "{{pattern}}", "{{expression}}", "{{filter}}", "{{script}}")):
        overlap += 2.0

    # Penalize recipes needing stdin/interactive or unrelated flags when not asked
    if "stdin" in low_desc and goal_spec.get("input_paths"):
        overlap -= 1.0
    if "list" in low_desc and not any(w in low_inst for w in ("list", "show", "inspect", "view")):
        overlap -= 2.0
    if "verbose" in low_desc and "extract" not in low_desc:
        overlap -= 0.2

    # Corroboration bonus: web recipe whose flags are verified in local `--help`!
    corrob_kinds = len(recipe.corroborated_source_kinds)
    unver_penalty = len(recipe.unverified_flags)
    if corrob_kinds >= 2 and unver_penalty == 0:
        overlap += 2.5
    elif unver_penalty > 0:
        overlap -= 1.5 * unver_penalty

    tool_rank = 0
    cand_tools = list(goal_spec.get("candidate_tools") or [])
    if recipe.tool in cand_tools:
        tool_rank = len(cand_tools) - cand_tools.index(recipe.tool)

    return (overlap + 0.5 * tool_rank, corrob_kinds, -unver_penalty)


# ---------------------------------------------------------------------------
# 5. State-Copy Execution, Postcondition Checking & Error-Driven Refinement
# ---------------------------------------------------------------------------

def _default_postcondition_check(
    state_dir: pathlib.Path,
    before_env: Mapping[str, Any],
    goal_spec: Mapping[str, Any],
    rc: int,
    stdout: str,
) -> tuple[bool, str, dict[str, Any]]:
    """Built-in structural & format postcondition verifier (when no external test fn given)."""
    details: dict[str, Any] = {"rc": rc}
    if rc != 0:
        return False, f"NONZERO_EXIT_{rc}", details

    out_paths = list(goal_spec.get("output_paths") or [])
    out_dirs = list(goal_spec.get("output_dirs") or [])

    for rel in out_paths:
        p = pathlib.Path(rel) if pathlib.Path(rel).is_absolute() else (state_dir / rel)
        if not p.is_file():
            return False, f"MISSING_OUTPUT_FILE:{rel}", details
        if p.stat().st_size == 0:
            return False, f"EMPTY_OUTPUT_FILE:{rel}", details
        low = p.name.lower()
        # Format integrity checks!
        if low.endswith(".json"):
            try:
                json.loads(p.read_text(encoding="utf-8"))
            except Exception as exc:
                return False, f"INVALID_JSON_OUTPUT:{rel}:{exc}", details
        elif low.endswith((".tar.gz", ".tgz", ".tar")):
            try:
                with tarfile.open(p, "r:*") as tf:
                    members = tf.getnames()
                if not members:
                    return False, f"EMPTY_TAR_ARCHIVE:{rel}", details
                details["archive_members"] = len(members)
            except Exception as exc:
                return False, f"INVALID_TAR_ARCHIVE:{rel}:{exc}", details
        elif low.endswith(".zip"):
            try:
                with zipfile.ZipFile(p, "r") as zf:
                    names = zf.namelist()
                if not names:
                    return False, f"EMPTY_ZIP_ARCHIVE:{rel}", details
                details["zip_members"] = len(names)
            except Exception as exc:
                return False, f"INVALID_ZIP_ARCHIVE:{rel}:{exc}", details

    for rel_d in out_dirs:
        d = state_dir / rel_d
        if not d.is_dir():
            return False, f"MISSING_OUTPUT_DIR:{rel_d}", details
        children = [x for x in d.rglob("*") if x.is_file()]
        if not children:
            return False, f"EMPTY_OUTPUT_DIR:{rel_d}", details
        details["extracted_files"] = len(children)

    # Frame invariance: input files must not be silently deleted unless removal was requested
    low_inst = str(goal_spec.get("instruction") or "").lower()
    allows_delete = any(w in low_inst for w in ("delete", "remove", "purge", "clean", "move", "rename"))
    if not allows_delete:
        for rel in goal_spec.get("input_paths") or []:
            if not (state_dir / rel).exists():
                return False, f"FRAME_VIOLATION_INPUT_DELETED:{rel}", details

    # If neither output_paths nor output_dirs specified, verify workspace actually changed or stdout produced
    if not out_paths and not out_dirs:
        after_env = sense_unknown_environment(state_dir)
        changed = after_env["digests"] != before_env.get("digests", {})
        if not changed and not stdout.strip():
            return False, "NO_OBSERVABLE_EFFECT", details
        details["workspace_changed"] = changed

    return True, "OK", details


def _refine_command_from_stderr(
    cmd: str,
    stderr: str,
    tool: str,
    local_help: LocalHelpKnowledge | None,
    goal_spec: Mapping[str, Any],
) -> list[tuple[str, EpistemicQuestion]]:
    """Closed-loop error-driven epistemic refinement from live stderr."""
    refinements: list[tuple[str, EpistemicQuestion]] = []
    err_low = stderr.lower()

    # 1. Invalid/unrecognized flag -> ask local_help for closest valid flag!
    m_opt = re.search(r"(?:unrecognized|invalid|unknown|illegal)\s+option\s+['`\"]?(--?[a-zA-Z0-9_-]+)['`\"]?", stderr, re.I)
    if m_opt and local_help and local_help.available:
        bad_flag = m_opt.group(1)
        all_flags = sorted(local_help.long_flags | local_help.short_flags)
        close = difflib.get_close_matches(bad_flag, all_flags, n=2, cutoff=0.5)
        q = EpistemicQuestion(
            kind="error_refinement",
            tool=tool,
            subcommand=local_help.subcommand,
            query=f"replace invalid flag {bad_flag} using {tool} --help",
            reason=f"stderr reported `{m_opt.group(0)}`; consulting local --help for valid alternative",
        )
        for rep in close:
            refinements.append((cmd.replace(bad_flag, rep, 1), q))
        # Also try removing the unsupported flag
        refinements.append((re.sub(rf"\s+{re.escape(bad_flag)}\b", "", cmd), q))

    # 2. Missing output directory -> prepend mkdir -p
    if "no such file or directory" in err_low:
        dirs_to_make: list[str] = []
        for d in goal_spec.get("output_dirs") or []:
            dirs_to_make.append(d)
        for p in goal_spec.get("output_paths") or []:
            parent = str(pathlib.Path(p).parent)
            if parent and parent != ".":
                dirs_to_make.append(parent)
        if dirs_to_make:
            mk = " ".join(shlex.quote(d) for d in sorted(set(dirs_to_make)))
            q = EpistemicQuestion(
                kind="error_refinement",
                tool=tool,
                subcommand="",
                query=f"create missing target directory {mk}",
                reason="stderr reported missing directory; prepending mkdir -p prerequisite",
            )
            refinements.append((f"mkdir -p {mk} && {cmd}", q))

    # 3. Patch strip-level mismatch (`can't find file to patch` -> try -p0 / -p1)
    if tool == "patch" and ("can't find file to patch" in err_low or "file to patch" in err_low):
        for plevel in ("-p1", "-p0"):
            if plevel not in cmd:
                q = EpistemicQuestion(
                    kind="error_refinement",
                    tool="patch",
                    subcommand="",
                    query=f"patch strip level {plevel}",
                    reason="patch could not locate target path; probing strip-level flag from --help",
                )
                refinements.append((cmd.replace("patch ", f"patch {plevel} ", 1), q))

    # 4. Suffix-sensitive decompressor (`unknown suffix -- ignored`) -> feed input via stdin `<`
    if "unknown suffix" in err_low:
        toks = shlex.split(cmd)
        if len(toks) >= 2:
            # Find last non-flag token (input path) and feed via `<` so tool reads stream without suffix check
            for ti in range(len(toks) - 1, 0, -1):
                if not toks[ti].startswith("-") and not toks[ti].startswith(">"):
                    inp_tok = toks[ti]
                    new_cmd = " ".join(toks[:ti] + ["<", shlex.quote(inp_tok)] + toks[ti + 1:])
                    q = EpistemicQuestion(
                        kind="error_refinement",
                        tool=tool,
                        subcommand="",
                        query=f"{tool} stream via stdin to bypass unknown suffix",
                        reason="stderr reported `unknown suffix`; feeding input stream via stdin `<`",
                    )
                    refinements.append((new_cmd, q))
                    break

    return refinements


def _run_in_state_copy(
    workspace: pathlib.Path,
    cmd: str,
    redirect_stdout_to: str | None,
    before_env: Mapping[str, Any],
    goal_spec: Mapping[str, Any],
    postcondition_fn: Callable[[pathlib.Path], tuple[bool, str]] | None,
    timeout_s: float = 15.0,
) -> tuple[bool, str, dict[str, Any], pathlib.Path | None, str, str]:
    """Execute `cmd` in a fresh copy of `workspace` and verify postconditions.

    Caller owns cleanup of returned `state_dir` when verified=True.
    """
    tmp_root = pathlib.Path(tempfile.mkdtemp(prefix="brain_epistemic_sc_"))
    state_dir = tmp_root / "ws"
    try:
        shutil.copytree(workspace, state_dir, symlinks=True)
        # Ensure explicitly named output_dirs or output parent dirs can be created if needed by redirect
        if redirect_stdout_to:
            out_p = pathlib.Path(redirect_stdout_to)
            target_p = out_p if out_p.is_absolute() else (state_dir / out_p)
            target_p.parent.mkdir(parents=True, exist_ok=True)
        for od in goal_spec.get("output_dirs") or []:
            (state_dir / od).mkdir(parents=True, exist_ok=True)

        cp = subprocess.run(
            ["bash", "-lc", cmd],
            cwd=str(state_dir),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            stdin=subprocess.DEVNULL,
        )
        if redirect_stdout_to and cp.returncode == 0 and cp.stdout:
            out_p = pathlib.Path(redirect_stdout_to)
            target_p = out_p if out_p.is_absolute() else (state_dir / out_p)
            target_p.parent.mkdir(parents=True, exist_ok=True)
            target_p.write_text(cp.stdout, encoding="utf-8")

        ok_def, reason_def, details = _default_postcondition_check(
            state_dir, before_env, goal_spec, cp.returncode, cp.stdout
        )
        if not ok_def:
            shutil.rmtree(tmp_root, ignore_errors=True)
            return False, reason_def, details, None, cp.stdout[:400], cp.stderr[:400]

        if postcondition_fn is not None:
            ok_ext, reason_ext = postcondition_fn(state_dir)
            details["external_postcondition"] = reason_ext
            if not ok_ext:
                shutil.rmtree(tmp_root, ignore_errors=True)
                return False, reason_ext, details, None, cp.stdout[:400], cp.stderr[:400]

        return True, "VERIFIED", details, state_dir, cp.stdout[:400], cp.stderr[:400]
    except subprocess.TimeoutExpired:
        shutil.rmtree(tmp_root, ignore_errors=True)
        return False, "TIMEOUT", {"timeout_s": timeout_s}, None, "", "TIMEOUT"
    except Exception as exc:
        shutil.rmtree(tmp_root, ignore_errors=True)
        return False, f"EXEC_ERROR:{exc}", {}, None, "", str(exc)


def _sync_state_copy_to_workspace(state_dir: pathlib.Path, workspace: pathlib.Path) -> None:
    """Commit verified files from `state_dir` into `workspace` cleanly."""
    for p in sorted(state_dir.rglob("*")):
        rel = p.relative_to(state_dir)
        dst = workspace / rel
        if p.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        elif p.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)


# ---------------------------------------------------------------------------
# 6. Public Entry Point: Tier 0 Recall -> Live Epistemic Loop -> Distill Memory
# ---------------------------------------------------------------------------

def solve_unknown_environment(
    workspace: str | pathlib.Path,
    instruction: str,
    *,
    postcondition_fn: Callable[[pathlib.Path], tuple[bool, str]] | None = None,
    procedure_store: dict[str, Any] | None = None,
    allow_web: bool = True,
    open_web_fetcher: Callable[[str], Sequence[Mapping[str, Any]]] | None = None,
    max_candidates: int = 20,
    timeout_s: float = 15.0,
) -> EpistemicSolveResult:
    """Enter an unknown environment with ZERO hardcoded tool workflows, learn from
    live local docs + live web guides what the goal demands, verify in a state copy,
    commit atomically, and permanently distill the procedure into external JSON.
    """
    t0 = time.monotonic()
    ws = pathlib.Path(workspace).resolve()
    env = sense_unknown_environment(ws)
    goal_spec = parse_goal_specification(instruction, env)
    task_kind = goal_spec["intent_signature"]

    # Build observable environment traits for Tier 0 recall & precondition narrowing
    primary_tool = goal_spec["candidate_tools"][0] if goal_spec["candidate_tools"] else "none"
    env_observables: list[str] = [
        "domain:epistemic_cli",
        f"has_tool:{primary_tool}",
    ]
    if goal_spec["output_paths"]:
        env_observables.append("has_output_file")
    if goal_spec["output_dirs"]:
        env_observables.append("has_output_dir")
    if goal_spec["archive_paths"]:
        env_observables.append("has_archive_path")
    if goal_spec["input_dirs"]:
        env_observables.append("has_input_dir")
    if goal_spec["quoted_literals"]:
        env_observables.append("has_quoted_literal")

    # Build hole bindings available in THIS environment for Tier 0 instantiation
    env_holes: dict[str, str] = {"__WORKSPACE__": str(ws)}
    if goal_spec["input_paths"]:
        env_holes["__INPUT_PATH__"] = goal_spec["input_paths"][0]
    if goal_spec["output_paths"]:
        env_holes["__OUTPUT_PATH__"] = goal_spec["output_paths"][0]
    if goal_spec["archive_paths"]:
        env_holes["__ARCHIVE_PATH__"] = goal_spec["archive_paths"][0]
    if goal_spec["input_dirs"]:
        env_holes["__INPUT_DIR__"] = goal_spec["input_dirs"][0]
    if goal_spec["output_dirs"]:
        env_holes["__OUTPUT_DIR__"] = goal_spec["output_dirs"][0]
    expr_lits = [
        lit for lit in goal_spec["quoted_literals"]
        if lit not in set(goal_spec["input_paths"] + goal_spec["output_paths"])
    ]
    if expr_lits:
        env_holes["__QUERY__"] = expr_lits[0]
        env_holes["__PATTERN__"] = expr_lits[0]
        env_holes["__ARG_1__"] = expr_lits[0]

    attempts = 0

    # --- TIER 0: Instant Recall from External Zero-Weight Procedure Store ---
    if procedure_store is not None:
        recalled = PROC_STORE.recall_procedures(
            procedure_store,
            domain="epistemic_cli",
            goal_kind=task_kind,
            env_observables=env_observables,
            hole_bindings=env_holes,
        )
        for proc in recalled:
            inst_steps = proc.get("steps") or []
            if not inst_steps:
                continue
            step = inst_steps[0]
            if step.get("op") != "epistemic_shell_recipe":
                continue
            cmd = str(step.get("command") or "")
            redir = step.get("redirect_stdout_to")
            if not cmd:
                continue
            attempts += 1
            ok, reason, details, sc_dir, out_ex, err_ex = _run_in_state_copy(
                ws, cmd, redir, env, goal_spec, postcondition_fn, timeout_s=timeout_s
            )
            if ok and sc_dir is not None:
                try:
                    _sync_state_copy_to_workspace(sc_dir, ws)
                finally:
                    shutil.rmtree(sc_dir.parent, ignore_errors=True)
                # Bump support count on verified recall
                stored = (procedure_store.get("procedures") or {}).get(proc["procedure_id"])
                if isinstance(stored, dict):
                    stored["support_count"] = int(stored.get("support_count", 1)) + 1
                return EpistemicSolveResult(
                    status="VERIFIED",
                    tier_used="TIER0_RECALL",
                    workspace=str(ws),
                    tool_used=str(step.get("tool") or primary_tool),
                    command_executed=cmd + (f" > {redir}" if redir else ""),
                    stdout_excerpt=out_ex,
                    stderr_excerpt=err_ex,
                    questions_asked=[],
                    sources_consulted=[{"kind": "external_procedure_store", "procedure_id": proc["procedure_id"]}],
                    corroborated_kinds=["external_procedure_store"],
                    attempts=attempts,
                    refinement_rounds=0,
                    learned_procedure_id=None,
                    recalled_procedure_id=proc["procedure_id"],
                    verification_details=details,
                    elapsed_s=round(time.monotonic() - t0, 3),
                )
            else:
                # Single-counterexample precondition narrowing / quarantine!
                PROC_STORE.refute_procedure(
                    procedure_store,
                    proc["procedure_id"],
                    counterexample_observables=env_observables,
                    reason=f"TIER0_FAILED:{reason}",
                )

    # --- TIER 1: Goal-Directed Instant Epistemic Acquisition ---
    questions = formulate_epistemic_questions(goal_spec, env)
    questions_log = [dataclasses.asdict(q) for q in questions]
    sources_consulted: list[dict[str, Any]] = []
    local_helps: dict[str, LocalHelpKnowledge] = {}
    all_recipes: list[CommandRecipe] = []
    corroborated_kinds_all: set[str] = set()

    for q in questions:
        if q.kind == "local_help":
            lh = query_local_cli_help(q.tool, q.subcommand)
            local_helps[q.tool] = lh
            if lh.available:
                corroborated_kinds_all.add("local_manual")
                sources_consulted.append({
                    "kind": "local_manual",
                    "tool": q.tool,
                    "flags_discovered": len(lh.short_flags) + len(lh.long_flags),
                })
            all_recipes.extend(_synthesize_help_fallback_recipes(lh, goal_spec))
        elif q.kind == "web_tldr" and allow_web:
            recs, prov = fetch_web_tldr_recipes(q.tool, q.subcommand)
            sources_consulted.extend(prov)
            if recs:
                corroborated_kinds_all.add("web_command_guide")
            all_recipes.extend(recs)
        elif q.kind == "web_jit_docs" and allow_web:
            recs, prov = fetch_web_jit_corroboration(q.query, q.tool, open_web_fetcher=open_web_fetcher)
            sources_consulted.extend(prov)
            if prov:
                corroborated_kinds_all.add("web_documentation")
            all_recipes.extend(recs)

    # Corroborate every acquired recipe against the actual binary's local `--help`
    for r in all_recipes:
        corroborate_recipe_with_local_help(r, local_helps.get(r.tool))

    # Rank recipes by goal overlap + multi-source corroboration
    ranked_recipes = sorted(all_recipes, key=lambda r: _score_recipe(r, goal_spec), reverse=True)

    # Bind holes & deduplicate concrete commands
    seen_cmds: set[tuple[str, str | None]] = set()
    candidates: list[tuple[CommandRecipe, str, dict[str, str], str | None]] = []
    for rec in ranked_recipes:
        for cmd, bindings, redir in _bind_recipe_holes(rec, goal_spec, env):
            key = (cmd, redir)
            if key in seen_cmds:
                continue
            seen_cmds.add(key)
            candidates.append((rec, cmd, bindings, redir))
            if len(candidates) >= max_candidates:
                break
        if len(candidates) >= max_candidates:
            break

    refinement_rounds = 0
    last_err = ""
    last_reason = "NO_CANDIDATES"

    for rec, cmd, bindings, redir in candidates:
        attempts += 1
        ok, reason, details, sc_dir, out_ex, err_ex = _run_in_state_copy(
            ws, cmd, redir, env, goal_spec, postcondition_fn, timeout_s=timeout_s
        )
        if not ok and err_ex:
            # Closed-loop error-driven epistemic refinement!
            refs = _refine_command_from_stderr(cmd, err_ex, rec.tool, local_helps.get(rec.tool), goal_spec)
            for ref_cmd, ref_q in refs[:2]:
                refinement_rounds += 1
                questions_log.append(dataclasses.asdict(ref_q))
                attempts += 1
                ok, reason, details, sc_dir, out_ex, err_ex = _run_in_state_copy(
                    ws, ref_cmd, redir, env, goal_spec, postcondition_fn, timeout_s=timeout_s
                )
                if ok:
                    cmd = ref_cmd
                    break

        if ok and sc_dir is not None:
            try:
                _sync_state_copy_to_workspace(sc_dir, ws)
            finally:
                shutil.rmtree(sc_dir.parent, ignore_errors=True)

            # Distill verified procedure into external zero-weight store!
            learned_id: str | None = None
            if procedure_store is not None:
                hole_bindings: dict[str, str] = {"__WORKSPACE__": str(ws)}
                for h, c in bindings.items():
                    if h in PROC_STORE.ALLOWED_HOLES and c:
                        hole_bindings[h] = c
                if redir:
                    hole_bindings["__OUTPUT_PATH__"] = redir

                step_record: dict[str, Any] = {
                    "op": "epistemic_shell_recipe",
                    "tool": rec.tool,
                    "command": cmd,
                    "redirect_stdout_to": redir,
                    "source_url": rec.source_url,
                }
                ind = PROC_STORE.induce_procedure_from_verified_run(
                    procedure_store,
                    domain="epistemic_cli",
                    goal_kind=task_kind,
                    concrete_steps=[step_record],
                    hole_bindings=hole_bindings,
                    env_observables=env_observables,
                    frame_invariants=["inputs_preserved", "output_valid"],
                    provenance={
                        "source_kind": rec.source_kind,
                        "source_url": rec.source_url,
                        "tool": rec.tool,
                        "corroborated_kinds": sorted(corroborated_kinds_all),
                    },
                )
                if ind is not None:
                    learned_id = ind.get("procedure_id")

            tier = (
                "TIER1_EPISTEMIC_WEB_AND_HELP"
                if "web_command_guide" in corroborated_kinds_all or "web_documentation" in corroborated_kinds_all
                else "TIER1_EPISTEMIC_LOCAL_HELP"
            )
            return EpistemicSolveResult(
                status="VERIFIED",
                tier_used=tier,
                workspace=str(ws),
                tool_used=rec.tool,
                command_executed=cmd + (f" > {redir}" if redir else ""),
                stdout_excerpt=out_ex,
                stderr_excerpt=err_ex,
                questions_asked=questions_log,
                sources_consulted=sources_consulted,
                corroborated_kinds=sorted(corroborated_kinds_all),
                attempts=attempts,
                refinement_rounds=refinement_rounds,
                learned_procedure_id=learned_id,
                recalled_procedure_id=None,
                verification_details=details,
                elapsed_s=round(time.monotonic() - t0, 3),
            )
        last_err = err_ex
        last_reason = reason

    return EpistemicSolveResult(
        status="FAILED",
        tier_used="NONE",
        workspace=str(ws),
        tool_used=goal_spec["candidate_tools"][0] if goal_spec["candidate_tools"] else "",
        command_executed="",
        stdout_excerpt="",
        stderr_excerpt=last_err,
        questions_asked=questions_log,
        sources_consulted=sources_consulted,
        corroborated_kinds=sorted(corroborated_kinds_all),
        attempts=attempts,
        refinement_rounds=refinement_rounds,
        learned_procedure_id=None,
        recalled_procedure_id=None,
        verification_details={"last_failure": last_reason},
        elapsed_s=round(time.monotonic() - t0, 3),
    )
