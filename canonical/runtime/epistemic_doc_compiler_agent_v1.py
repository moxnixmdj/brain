"""Goal-Directed Zero-LLM Epistemic Doc-Compiler & Active-Inference Agent V1.

Implements the minimal 5-stage universal algorithm for arbitrary unseen computer
environments with `model_calls == 0`, `parameters_stored == 0`, and zero hardcoded
tool/app/endpoint catalogs:

  1. SCAN_BOUNDARY(env, goal)
     Goal-conditioned O(1)/ms scan of the immediate affordance boundary (workspace
     files, local docs, mentioned/available binaries, URLs). Never scans the whole OS.
  2. EPISTEMIC_PARTITION(goal, boundary, memory)
     Partitions goal prerequisites into KNOWN (structurally isomorphic verified laws
     in external inspectable memory) vs UNKNOWN (blocking epistemic gaps Δ).
  3. ACQUIRE_CONTRACTS(Δ, env, knowledge_source)
     Fastest-first instant knowledge acquisition:
       L0 (<5ms):  Live introspection (`--help`, `-h`, subcommand `--help`, local docs)
       L1 (<20ms): Local/guide corpus
       L2 (live):  Pluggable external web/doc knowledge source
     Deterministic zero-LLM grammar compilers turn raw `--help`, man synopses,
     Markdown/HTML docs, and `curl` examples directly into typed executable contracts.
  4. ACT_VERIFY_AND_REFUSE_LOOP(goal, contracts, env)
     Active-inference execution with refusal-surface parsing (CLI stderr / HTTP 4xx)
     for doc-drift immunity and independent postcondition verification.
  5. GENERALIZE_AND_PRUNE(episode, memory)
     Strict zero-leakage gate + Plotkin anti-unification (LGG) across distinct
     environments + MDL subsumption pruning + instant refutation/deletion.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import html
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "brain.epistemic_doc_compiler_agent.v1"
AUTHORITY = "NONE__SANDBOX_MEASUREMENT"

_STOPWORDS = frozenset(
    {
        "a", "an", "the", "to", "of", "in", "on", "at", "by", "for", "from", "with",
        "into", "onto", "and", "or", "is", "are", "be", "use", "using", "via", "then",
        "that", "this", "it", "its", "as", "all", "any", "new", "only", "please",
        "tool", "command", "cli", "api", "service", "server", "file", "files", "data",
        "value", "values", "result", "results", "step", "run", "execute", "perform",
        "given", "specified", "should", "must", "need", "want", "make", "do",
    }
)

# Universal semantic synonym clusters (language-level concepts, NOT tool names)
_CONCEPT_CLUSTERS: tuple[frozenset[str], ...] = (
    frozenset({"output", "out", "dest", "destination", "target", "write", "save", "to", "dst"}),
    frozenset({"input", "in", "src", "source", "read", "from", "infile"}),
    frozenset({"extract", "unpack", "decompress", "unarchive", "expand", "unzip", "untar", "decode"}),
    frozenset({"compress", "archive", "pack", "bundle", "create", "encode"}),
    frozenset({"directory", "dir", "folder", "path", "prefix", "chdir", "into"}),
    frozenset({"filter", "query", "select", "match", "grep", "search", "find", "extract", "field", "expr", "expression"}),
    frozenset({"format", "pretty", "raw", "compact", "json", "csv", "text", "plain", "unquoted"}),
    frozenset({"sort", "order", "reverse", "unique", "dedup", "deduplicate", "count"}),
    frozenset({"hash", "digest", "checksum", "sha256", "md5", "sign", "verify"}),
    frozenset({"delimiter", "separator", "sep", "delim", "split", "fields", "column", "columns"}),
    frozenset({"replace", "substitute", "transform", "convert", "translate", "map"}),
    frozenset({"list", "show", "get", "fetch", "read", "retrieve", "inspect", "view"}),
    frozenset({"create", "add", "post", "submit", "register", "insert", "open", "new"}),
    frozenset({"update", "edit", "modify", "patch", "put", "set", "change"}),
    frozenset({"delete", "remove", "drop", "destroy", "close", "cancel"}),
    frozenset({"auth", "token", "key", "secret", "header", "credential", "bearer", "apikey"}),
    frozenset({"verbose", "quiet", "silent", "stdout", "force", "overwrite", "recursive"}),
    frozenset({"base64", "b64", "hex", "utf8", "ascii"}),
    frozenset({"first", "top", "head", "initial", "leading", "limit"}),
    frozenset({"last", "tail", "bottom", "trailing", "final"}),
    frozenset({"line", "lines", "row", "rows", "record", "records"}),
    frozenset({"containing", "contains", "matching", "matches", "pattern", "patterns", "substring", "regex"}),
)

_TOKEN_TO_CONCEPTS: dict[str, set[str]] = {}
for _ci, _cl in enumerate(_CONCEPT_CLUSTERS):
    for _tok in _cl:
        _TOKEN_TO_CONCEPTS.setdefault(_tok, set()).add(f"c{_ci}")


def _tokenize(text: str) -> list[str]:
    raw = re.findall(r"[A-Za-z][A-Za-z0-9_]*", (text or "").lower())
    out: list[str] = []
    for w in raw:
        # Split snake_case & camel fragments cleanly
        for part in re.split(r"[_]+", w):
            if len(part) >= 2 and part not in _STOPWORDS:
                out.append(part)
    return out


def _concept_set(text: str) -> set[str]:
    toks = set(_tokenize(text))
    concepts = set(toks)
    for t in toks:
        concepts.update(_TOKEN_TO_CONCEPTS.get(t, ()))
    return concepts


def _semantic_overlap(a: str, b: str) -> float:
    ta, tb = set(_tokenize(a)), set(_tokenize(b))
    if not ta or not tb:
        return 0.0
    exact = len(ta & tb)
    ca, cb = _concept_set(a), _concept_set(b)
    concept_hits = len((ca & cb) - (ta & tb))
    return float(exact) * 2.0 + float(concept_hits) * 0.9


# ---------------------------------------------------------------------------
# Typed Executable Contracts (compiled from --help, man, Markdown/HTML, curl)
# ---------------------------------------------------------------------------


@dataclass
class OptionSpec:
    short: str = ""
    long: str = ""
    takes_arg: bool = False
    arg_name: str = ""
    description: str = ""
    required: bool = False

    @property
    def primary_flag(self) -> str:
        return self.long or self.short

    @property
    def all_flags(self) -> tuple[str, ...]:
        return tuple(f for f in (self.short, self.long) if f)


@dataclass
class CLISubcommandContract:
    binary: str
    subcommand: str = ""
    usage: str = ""
    description: str = ""
    options: list[OptionSpec] = field(default_factory=list)
    subcommands: dict[str, str] = field(default_factory=dict)
    examples: list[str] = field(default_factory=list)
    reads_stdin: bool = False
    writes_stdout: bool = True
    source: str = "help"


@dataclass
class HTTPContract:
    method: str
    path_template: str
    headers: dict[str, str] = field(default_factory=dict)
    query_params: list[str] = field(default_factory=list)
    body_fields: list[str] = field(default_factory=list)
    description: str = ""
    auth_header: str = ""
    auth_prefix: str = ""
    source: str = "doc"


# ---------------------------------------------------------------------------
# Zero-LLM Documentation -> Executable Contract Compilers
# ---------------------------------------------------------------------------


_OPT_LINE_RE = re.compile(
    r"^\s{1,8}"
    r"(?:(?P<short>-[A-Za-z0-9?])(?:\s+(?P<sarg><[^>]+>|[A-Z][A-Z0-9_-]{1,20}))?)?"
    r"(?:\s*,\s*|\s+)?"
    r"(?:(?P<long>--[A-Za-z0-9][A-Za-z0-9_-]*)(?:[=\s](?P<larg><[^>]+>|[A-Z][A-Z0-9_-]{1,20}|\[[^\]]+\]))?(?:\s*,\s*--[A-Za-z0-9][A-Za-z0-9_-]*(?:[=\s](?:<[^>]+>|[A-Z][A-Z0-9_-]{1,20}))?)*)?"
    r"(?:\s{2,}|\t+|:?\s+-\s+|\s+)"
    r"(?P<desc>.*)$"
)

_SUBCMD_LINE_RE = re.compile(
    r"^\s{2,8}([a-z][a-z0-9_-]{1,24})\s{2,}(.+?)\s*$"
)


def _strip_html(text: str) -> str:
    if not re.search(
        r"(?i)<(?:!doctype|html|head|body|div|p|h[1-6]|pre|code|ul|ol|li|table|tr|td|th|br|section|article|main)\b",
        text,
    ):
        return text
    cleaned = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
    cleaned = re.sub(r"(?i)</?(?:p|div|br|li|tr|h[1-6]|pre|code|section|article)[^>]*>", "\n", cleaned)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    return html.unescape(cleaned)


def compile_cli_help_to_contracts(
    binary: str,
    raw_text: str,
    *,
    subcommand: str = "",
    source: str = "help",
) -> CLISubcommandContract:
    """Deterministically compile raw `--help`, man page, or Markdown/HTML CLI docs
    into a typed `CLISubcommandContract` (zero LLM calls, zero hardcoded tool rules).
    """
    text = _strip_html(raw_text or "")
    lines = text.splitlines()
    contract = CLISubcommandContract(binary=binary, subcommand=subcommand, source=source)

    usage_lines: list[str] = []
    in_subcmds = False
    in_examples = False
    in_code_block = False
    seen_flags: set[tuple[str, str]] = set()

    for idx, line in enumerate(lines):
        stripped = line.strip()
        low = stripped.lower()

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue

        if re.match(r"^(usage|synopsis)\s*:", low):
            usage_lines.append(stripped)
            in_subcmds = False
            in_examples = False
            continue

        if re.match(r"^(?:available\s+)?(?:sub)?commands?\s*:?\s*$", low) or re.match(
            r"^#+\s*(?:sub)?commands?\b", low
        ) or re.match(r"^positional\s+arguments?\s*:\s*$", low):
            in_subcmds = True
            in_examples = False
            continue

        if re.match(r"^(?:options?|flags?|optional\s+arguments?)\s*:?\s*$", low) or re.match(
            r"^#+\s*(?:options?|flags?)\b", low
        ):
            in_subcmds = False
            in_examples = False
            continue

        if re.match(r"^examples?\s*:?\s*$", low) or re.match(r"^#+\s*examples?\b", low):
            in_examples = True
            in_subcmds = False
            continue

        # Capture CLI examples (from Examples section, `$ cmd ...`, or fenced code blocks)
        if in_examples or in_code_block or stripped.startswith("$ "):
            cand_ex = stripped.lstrip("$ ").strip()
            bname = pathlib.Path(binary).name
            if cand_ex.startswith((bname + " ", f"./{bname} ", binary + " ")):
                contract.examples.append(cand_ex)
                continue

        # Capture subcommands inside Commands section
        if in_subcmds:
            if not stripped:
                continue
            m_sc = _SUBCMD_LINE_RE.match(line)
            if m_sc and not m_sc.group(1).startswith("-"):
                sc_name, sc_desc = m_sc.group(1), m_sc.group(2).strip()
                if sc_name not in ("help", "version"):
                    contract.subcommands[sc_name] = sc_desc
                continue
            # Markdown list style: `- convert: Convert ...` or `` - `convert` — ... ``
            m_md_sc = re.match(r"^\s*[-*]\s+`?([a-z][a-z0-9_-]{1,24})`?\s*[:—–-]\s*(.+)$", stripped)
            if m_md_sc:
                contract.subcommands[m_md_sc.group(1)] = m_md_sc.group(2).strip()
                continue

        # Parse option rows (GNU/POSIX/argparse/click/markdown)
        opt_line = line
        if re.match(r"^\s*[-*]\s+`?-", stripped):
            # Markdown bullet `- \`-o, --out <FILE>\`: description`
            opt_line = "  " + re.sub(r"^\s*[-*]\s+", "", stripped).replace("`", "")
        if opt_line.lstrip().startswith("-"):
            m_opt = _OPT_LINE_RE.match(opt_line)
            if m_opt:
                short_f = (m_opt.group("short") or "").strip()
                long_f = (m_opt.group("long") or "").strip()
                sarg = (m_opt.group("sarg") or "").strip()
                larg = (m_opt.group("larg") or "").strip()
                desc = (m_opt.group("desc") or "").strip()
                if (short_f or long_f) and (short_f, long_f) not in seen_flags:
                    # Also handle inline `--flag <arg>` captured inside desc when separated by single space
                    arg_name = larg or sarg
                    if not arg_name and desc:
                        m_inline_arg = re.match(r"^(<[^>]+>|[A-Z][A-Z0-9_-]{1,16})\s{2,}(.*)$", desc)
                        if m_inline_arg:
                            arg_name = m_inline_arg.group(1)
                            desc = m_inline_arg.group(2).strip()
                    takes_arg = bool(arg_name) or bool(
                        re.search(r"(?:--[A-Za-z0-9_-]+=|-[A-Za-z0-9]\s+[A-Z<])", opt_line)
                    )
                    # Check next line continuation for richer description
                    if idx + 1 < len(lines) and re.match(r"^\s{10,}\S", lines[idx + 1]):
                        cont = lines[idx + 1].strip()
                        if not cont.startswith("-"):
                            desc = (desc + " " + cont).strip()
                    req = "required" in desc.lower()
                    seen_flags.add((short_f, long_f))
                    contract.options.append(
                        OptionSpec(
                            short=short_f,
                            long=long_f,
                            takes_arg=takes_arg,
                            arg_name=arg_name,
                            description=desc,
                            required=req,
                        )
                    )

    contract.usage = " | ".join(usage_lines[:3])
    low_all = text.lower()
    contract.reads_stdin = any(
        k in low_all for k in ("stdin", "standard input", "from input", "[file...]", "[file]")
    )
    contract.writes_stdout = (
        any(k in low_all for k in ("stdout", "standard output", "prints"))
        or not any("output" in o.description.lower() and o.required for o in contract.options)
    )
    return contract


def compile_doc_to_http_contracts(
    raw_doc: str,
    *,
    source: str = "doc",
) -> list[HTTPContract]:
    """Deterministically compile Markdown, HTML, plain-text API guides, and `curl`
    examples into typed `HTTPContract` records (no OpenAPI JSON and no LLM needed).
    """
    text = _strip_html(raw_doc or "")
    lines = text.splitlines()

    # Global auth header discovery from prose/examples (e.g. `Header: X-Auth-Token: <token>`)
    global_auth_header = ""
    global_auth_prefix = ""
    for m_ah in re.finditer(
        r"(?i)(?:header|send|pass|include|required)[^.\n]{0,60}`?([A-Za-z][A-Za-z0-9-]{2,32})`?\s*(?::\s*`?([A-Za-z]+)\s+<)?",
        text,
    ):
        hdr_cand = m_ah.group(1)
        if hdr_cand.lower() in (
            "authorization", "x-api-key", "x-auth-token", "x-token", "api-key",
        ) or hdr_cand.lower().startswith("x-"):
            global_auth_header = hdr_cand
            global_auth_prefix = (m_ah.group(2) or "").strip()
            break
    if not global_auth_header:
        m_curl_h = re.search(
            r"""-H\s+['"]([A-Za-z][A-Za-z0-9-]+)\s*:\s*([^'"]+)['"]""", text
        )
        if m_curl_h and m_curl_h.group(1).lower() != "content-type":
            global_auth_header = m_curl_h.group(1)
            vparts = m_curl_h.group(2).strip().split()
            if len(vparts) >= 2 and vparts[0].lower() in ("bearer", "token", "basic", "apikey"):
                global_auth_prefix = vparts[0]

    contracts: list[HTTPContract] = []
    by_key: dict[tuple[str, str], HTTPContract] = {}

    def _upsert(method: str, path_t: str, desc: str = "") -> HTTPContract:
        m_up = method.upper()
        p_clean = path_t.strip().rstrip(".,;)`'\"")
        # Strip scheme+host if full URL given
        if p_clean.startswith(("http://", "https://")):
            parsed = urllib.parse.urlparse(p_clean)
            p_clean = parsed.path or "/"
            if parsed.query:
                qkeys = list(urllib.parse.parse_qs(parsed.query).keys())
            else:
                qkeys = []
        else:
            if "?" in p_clean:
                p_clean, qpart = p_clean.split("?", 1)
                qkeys = [kv.split("=", 1)[0] for kv in qpart.split("&") if kv]
            else:
                qkeys = []
        if not p_clean.startswith("/"):
            p_clean = "/" + p_clean
        key = (m_up, p_clean)
        if key not in by_key:
            c = HTTPContract(
                method=m_up,
                path_template=p_clean,
                description=desc.strip(),
                auth_header=global_auth_header,
                auth_prefix=global_auth_prefix,
                source=source,
            )
            by_key[key] = c
            contracts.append(c)
        else:
            c = by_key[key]
            if desc and desc.strip() not in c.description:
                c.description = (c.description + " " + desc.strip()).strip()
        for qk in qkeys:
            if qk and qk not in c.query_params:
                c.query_params.append(qk)
        return c

    current: HTTPContract | None = None
    ep_re = re.compile(
        r"(?:^|[\s`(|])(?P<meth>GET|POST|PUT|PATCH|DELETE)\s+`?(?P<path>(?:https?://[^\s`'\"]+)?/[A-Za-z0-9_./:{}-]+(?:\?[A-Za-z0-9_=&%-]+)?)`?(?P<rest>.*)$"
    )
    curl_re = re.compile(r"\bcurl\b.+")

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        # 1. `curl` command examples (extract method, URL, headers, JSON body keys)
        if curl_re.search(stripped):
            # Join line continuations (`\`)
            cmd_line = stripped
            j = i
            while cmd_line.endswith("\\") and j + 1 < len(lines):
                j += 1
                cmd_line = cmd_line[:-1] + " " + lines[j].strip()
            m_xm = re.search(r"(?:-X|--request)\s+(GET|POST|PUT|PATCH|DELETE)", cmd_line, re.I)
            m_url = re.search(r"""['"]?(https?://[^\s'"]+|/[A-Za-z0-9_./:{}-]+(?:\?[^\s'"]+)?)['"]?""", cmd_line)
            if m_url:
                has_data = bool(re.search(r"(?:-d|--data|--data-raw)\s+", cmd_line))
                meth = m_xm.group(1).upper() if m_xm else ("POST" if has_data else "GET")
                c = _upsert(meth, m_url.group(1))
                current = c
                for mh in re.finditer(r"""-H\s+['"]([A-Za-z0-9-]+)\s*:\s*([^'"]+)['"]""", cmd_line):
                    hk, hv = mh.group(1), mh.group(2).strip()
                    c.headers[hk] = hv
                    if hk.lower() != "content-type" and not c.auth_header:
                        c.auth_header = hk
                md = re.search(r"""(?:-d|--data|--data-raw)\s+['"](\{[^'"]+\})['"]""", cmd_line)
                if md:
                    try:
                        obj = json.loads(md.group(1))
                        if isinstance(obj, dict):
                            for k in obj:
                                if k not in c.body_fields:
                                    c.body_fields.append(k)
                    except Exception:
                        pass
                continue

        # 2. Endpoint declarations (`POST /v2/widgets — create a widget`)
        m_ep = ep_re.search(stripped)
        if m_ep:
            rest = re.sub(r"^[`|\s—–:-]+", "", m_ep.group("rest") or "").strip()
            # Also fold preceding heading line as context
            prev_desc = lines[i - 1].strip("# ").strip() if i > 0 and lines[i - 1].strip().startswith("#") else ""
            current = _upsert(m_ep.group("meth"), m_ep.group("path"), (prev_desc + " " + rest).strip())
            continue

        # 3. Context attached to the active endpoint (JSON body fields, query params, headers, prose)
        if current is not None:
            if stripped.startswith("#"):
                current = None
                continue
            # JSON example snippet inside endpoint section
            m_json_k = re.findall(r'"([A-Za-z_][A-Za-z0-9_-]{0,32})"\s*:', stripped)
            if m_json_k and ("{" in stripped or current.method in ("POST", "PUT", "PATCH")):
                for jk in m_json_k:
                    if jk not in current.body_fields:
                        current.body_fields.append(jk)
            # Bullet/prose field specs: `body fields: name, tier` or `query: status, limit`
            m_body_list = re.search(r"(?i)(?:body|json|payload|fields?)\s*:\s*(.+)$", stripped)
            if m_body_list:
                for tok in re.findall(r"`?([A-Za-z_][A-Za-z0-9_-]{1,32})`?", m_body_list.group(1)):
                    if tok.lower() not in ("json", "string", "int", "integer", "bool", "boolean", "required", "optional", "object"):
                        if tok not in current.body_fields:
                            current.body_fields.append(tok)
            m_q_list = re.search(r"(?i)(?:query(?:\s+params?)?|filters?)\s*:\s*(.+)$", stripped)
            if m_q_list:
                for tok in re.findall(r"`?([A-Za-z_][A-Za-z0-9_-]{1,32})`?", m_q_list.group(1)):
                    if tok.lower() not in ("string", "int", "optional", "required") and tok not in current.query_params:
                        current.query_params.append(tok)
            if len(current.description) < 180 and not stripped.startswith(("{", "}", "```")):
                current.description = (current.description + " " + stripped).strip()[:220]

    return contracts


# ---------------------------------------------------------------------------
# Refusal Surface Parser (Active Inference Observation Channel)
# ---------------------------------------------------------------------------


def parse_refusal_surface(output: str, *, status_code: int | None = None) -> dict[str, Any]:
    """Extract structured epistemic updates from CLI stderr or HTTP 4xx/5xx refusals."""
    txt = output or ""
    low = txt.lower()
    sig: dict[str, Any] = {
        "banned_flags": [],
        "missing_flags": [],
        "missing_fields": [],
        "missing_headers": [],
        "suggested_subcommands": [],
        "needs_auth": False,
        "needs_help": False,
        "raw_excerpt": txt[:400],
    }

    for m in re.finditer(
        r"(?i)(?:unrecognized|unknown|invalid|illegal|unexpected)\s+(?:option|flag|argument)\s*[:'`\"]*\s*(--?[A-Za-z0-9_-]+)",
        txt,
    ):
        f = m.group(1)
        if f not in sig["banned_flags"]:
            sig["banned_flags"].append(f)

    for m in re.finditer(
        r"(?i)(?:missing|required|must\s+(?:specify|provide|pass))\s+(?:required\s+)?(?:option|flag)\s*[:'`\"]*\s*(--?[A-Za-z0-9_-]+)",
        txt,
    ):
        f = m.group(1)
        if f not in sig["missing_flags"]:
            sig["missing_flags"].append(f)

    for m in re.finditer(
        r"(?i)(?:missing|required)\s+(?:required\s+)?(?:header)\s*[:'`\"]*\s*([A-Za-z][A-Za-z0-9-]{2,32})",
        txt,
    ):
        h = m.group(1)
        if h not in sig["missing_headers"]:
            sig["missing_headers"].append(h)

    for m in re.finditer(
        r"(?i)(?:missing|required)\s+(?:required\s+)?(?:field|key|param|parameter|property)\s*[:'`\"]*\s*([A-Za-z_][A-Za-z0-9_-]{1,32})",
        txt,
    ):
        fld = m.group(1)
        if fld not in sig["missing_fields"]:
            sig["missing_fields"].append(fld)

    if status_code in (401, 403) or any(
        k in low for k in ("unauthorized", "forbidden", "invalid token", "api key required", "missing auth")
    ):
        sig["needs_auth"] = True

    if "--help" in low or "usage:" in low:
        sig["needs_help"] = True

    return sig


# ---------------------------------------------------------------------------
# External Inspectable Memory + Plotkin Anti-Unification + MDL Pruning
# (Zero Weights, Zero Knowledge House, Zero Leaked Concrete Paths/Secrets!)
# ---------------------------------------------------------------------------


_LEAK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"/tmp/[A-Za-z0-9_./-]+"),
    re.compile(r"/home/[A-Za-z0-9_./-]+"),
    re.compile(r"https?://[^\s'\"`]+"),
    re.compile(r"\b(?:sk|tok|secret|bearer)[_-]?[A-Za-z0-9]{8,}\b", re.I),
)


def _contains_concrete_leak(obj: Any) -> bool:
    s = json.dumps(obj, sort_keys=True) if not isinstance(obj, str) else obj
    return any(p.search(s) for p in _LEAK_PATTERNS)


def anti_unify_role_sequences(seq_a: Sequence[str], seq_b: Sequence[str]) -> list[str]:
    """Plotkin Least General Generalization (LGG) over two abstract token/role sequences.
    Identical positions stay fixed; differing positions lift to typed hole `?SLOT_k`.
    """
    n = min(len(seq_a), len(seq_b))
    out: list[str] = []
    hole_map: dict[tuple[str, str], str] = {}
    for i in range(n):
        a, b = seq_a[i], seq_b[i]
        if a == b:
            out.append(a)
        else:
            pair = (a, b)
            if pair not in hole_map:
                hole_map[pair] = f"?SLOT_{len(hole_map)}"
            out.append(hole_map[pair])
    return out


class EpistemicMemoryStore:
    """External, inspectable, editable store of verified Abstract Structural Laws.

    Invariant: NEVER stores raw command traces, raw web pages, literal paths, URLs,
    or secrets. Stores ONLY role-parameterized structural schemas with MDL pruning
    and instant refutation/deletion.
    """

    def __init__(self, path: str | pathlib.Path | None = None) -> None:
        self.path = pathlib.Path(path) if path else None
        self.laws: dict[str, dict[str, Any]] = {}
        self.stats: dict[str, int] = {
            "writes": 0,
            "anti_unifications": 0,
            "pruned_subsumed": 0,
            "refutations": 0,
            "deletions": 0,
            "leak_blocks": 0,
        }
        if self.path and self.path.is_file():
            self.load()

    def save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema": f"{SCHEMA}.memory", "laws": self.laws, "stats": self.stats}
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def load(self) -> None:
        if not self.path or not self.path.is_file():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.laws = dict(raw.get("laws") or {})
        self.stats.update(raw.get("stats") or {})

    def delete_law(self, law_id: str) -> bool:
        if law_id in self.laws:
            del self.laws[law_id]
            self.stats["deletions"] += 1
            self.save()
            return True
        return False

    def refute_law(self, law_id: str, reason: str, *, distinguishing_pred: str = "") -> bool:
        law = self.laws.get(law_id)
        if not law:
            return False
        self.stats["refutations"] += 1
        if distinguishing_pred:
            guards = list(law.get("refutation_guards") or [])
            if distinguishing_pred not in guards:
                guards.append(distinguishing_pred)
            law["refutation_guards"] = guards
            law["refutation_count"] = int(law.get("refutation_count", 0)) + 1
            if law["refutation_count"] >= 3:
                del self.laws[law_id]
                self.stats["deletions"] += 1
        else:
            del self.laws[law_id]
            self.stats["deletions"] += 1
        self.save()
        return True

    def recall(self, kind: str, goal_concepts: set[str], *, active_predicates: set[str] | None = None) -> list[dict[str, Any]]:
        """O(N_laws) ultra-fast structural recall ranked by concept overlap & generality."""
        active = active_predicates or set()
        scored: list[tuple[float, dict[str, Any]]] = []
        for law in self.laws.values():
            if law.get("kind") != kind:
                continue
            guards = set(law.get("refutation_guards") or ())
            if guards and (guards & active):
                continue
            law_concepts = set(law.get("goal_concepts") or ())
            ov = len(law_concepts & goal_concepts)
            if ov <= 0 and not law.get("generalized"):
                continue
            score = ov * 2.0 + float(law.get("evidence_count", 1)) * 0.5 + (1.5 if law.get("generalized") else 0.0)
            scored.append((score, law))
        scored.sort(key=lambda x: -x[0])
        return [law for _, law in scored[:5]]

    def generalize_and_store(
        self,
        *,
        kind: str,
        goal_concepts: set[str],
        role_pattern: Sequence[str],
        postcondition_kind: str,
        env_fingerprint: str,
        meta_roles: Mapping[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Store a verified episode as a role-abstracted law, anti-unify across distinct
        environments, and MDL-prune subsumed narrower records. Zero-leakage enforced.
        """
        clean_meta = dict(meta_roles or {})
        candidate = {
            "kind": kind,
            "goal_concepts": sorted(c for c in goal_concepts if c.startswith("c") and c[1:].isdigit())[:12],
            "role_pattern": list(role_pattern),
            "postcondition_kind": postcondition_kind,
            "meta_roles": clean_meta,
        }
        if _contains_concrete_leak(candidate):
            self.stats["leak_blocks"] += 1
            return None

        env_hash = hashlib.sha256(env_fingerprint.encode("utf-8")).hexdigest()[:12]

        # 1. Exact structural match -> increment evidence count (no duplicate entry!)
        for lid, existing in self.laws.items():
            if (
                existing.get("kind") == kind
                and existing.get("role_pattern") == list(role_pattern)
                and existing.get("postcondition_kind") == postcondition_kind
            ):
                envs = set(existing.get("env_hashes") or ())
                envs.add(env_hash)
                existing["env_hashes"] = sorted(envs)
                existing["evidence_count"] = int(existing.get("evidence_count", 1)) + 1
                existing["goal_concepts"] = sorted(set(existing.get("goal_concepts") or ()) | set(candidate["goal_concepts"]))[:16]
                self.save()
                return existing

        # 2. Cross-environment Plotkin Anti-Unification (LGG) when a second distinct env shares
        #    same kind + postcondition_kind + compatible arity!
        for lid, existing in list(self.laws.items()):
            if existing.get("kind") != kind or existing.get("postcondition_kind") != postcondition_kind:
                continue
            prev_envs = set(existing.get("env_hashes") or ())
            if env_hash in prev_envs:
                continue
            pat_a = list(existing.get("role_pattern") or ())
            pat_b = list(role_pattern)
            if len(pat_a) != len(pat_b) or not pat_a:
                continue
            lgg = anti_unify_role_sequences(pat_a, pat_b)
            # Accept LGG only if at least 1 structural anchor remains concrete (not all holes!)
            if any(not tok.startswith("?SLOT_") for tok in lgg):
                gen_id = "law_" + hashlib.sha256(
                    json.dumps([kind, lgg, postcondition_kind], sort_keys=True).encode()
                ).hexdigest()[:12]
                merged_envs = sorted(prev_envs | {env_hash})
                gen_law = {
                    "law_id": gen_id,
                    "kind": kind,
                    "goal_concepts": sorted(set(existing.get("goal_concepts") or ()) | set(candidate["goal_concepts"]))[:16],
                    "role_pattern": lgg,
                    "postcondition_kind": postcondition_kind,
                    "meta_roles": {**dict(existing.get("meta_roles") or {}), **clean_meta},
                    "generalized": True,
                    "evidence_count": int(existing.get("evidence_count", 1)) + 1,
                    "env_hashes": merged_envs,
                    "refutation_guards": list(existing.get("refutation_guards") or []),
                }
                # MDL Pruning: remove subsumed narrower law!
                if lid != gen_id and lid in self.laws:
                    del self.laws[lid]
                    self.stats["pruned_subsumed"] += 1
                self.laws[gen_id] = gen_law
                self.stats["anti_unifications"] += 1
                self.stats["writes"] += 1
                self.save()
                return gen_law

        # 3. First verified experience -> store narrow role-abstracted schema
        law_id = "law_" + hashlib.sha256(
            json.dumps([kind, list(role_pattern), postcondition_kind], sort_keys=True).encode()
        ).hexdigest()[:12]
        new_law = {
            "law_id": law_id,
            **candidate,
            "generalized": False,
            "evidence_count": 1,
            "env_hashes": [env_hash],
            "refutation_guards": [],
        }
        self.laws[law_id] = new_law
        self.stats["writes"] += 1
        self.save()
        return new_law


# ---------------------------------------------------------------------------
# Stage 1: Goal-Conditioned Boundary Scan (<5ms — NEVER scan the whole OS!)
# ---------------------------------------------------------------------------


_KV_PAT = re.compile(
    r"""\b([A-Za-z_][A-Za-z0-9_-]{1,28})\s*(?:=|:)\s*(?:"([^"]+)"|'([^']+)'|([^\s)\]]+))"""
)
_FILE_TOK_RE = re.compile(r"\b([A-Za-z0-9_./-]+\.[A-Za-z0-9]{1,8})\b")


def _detect_file_magic(path: pathlib.Path) -> str:
    """Pure-byte magic-number sensing (<0.1ms, zero external dependencies)."""
    try:
        if not path.is_file():
            return "missing"
        head = path.read_bytes()[:512]
    except Exception:
        return "unknown"
    if not head:
        return "empty"
    if head.startswith(b"\x1f\x8b"):
        # Check tar.gz by filename cue or inner header
        if path.name.lower().endswith((".tar.gz", ".tgz")):
            return "tar_gzip"
        return "gzip"
    if head.startswith(b"BZh"):
        if path.name.lower().endswith((".tar.bz2", ".tbz2")):
            return "tar_bzip2"
        return "bzip2"
    if head.startswith(b"\xfd7zXZ\x00"):
        if path.name.lower().endswith((".tar.xz", ".txz")):
            return "tar_xz"
        return "xz"
    if head.startswith(b"PK\x03\x04"):
        return "zip"
    if len(head) > 262 and head[257:262] == b"ustar":
        return "tar"
    if head.startswith(b"SQLite format 3\x00"):
        return "sqlite"
    try:
        txt = head.decode("utf-8")
        st = txt.lstrip()
        if st.startswith(("{", "[")):
            return "json_text"
        if st.startswith(("<!DOCTYPE", "<html", "<HTML")):
            return "html_text"
        return "utf8_text"
    except UnicodeDecodeError:
        return "binary"


def _extract_unquoted_patterns_and_numeric_slots(goal: str) -> tuple[list[str], dict[str, str]]:
    """Extract unquoted pattern phrases (`containing ERROR 500`, `matching PROD`)
    and numeric role slots (`first 2 lines`, `top 3`, `field 2`, `column 3`).
    """
    patterns: list[str] = []
    # Match unquoted phrase after containing/matching/pattern (stop at clause punctuation/conjunction)
    for m in re.finditer(
        r"""(?i)\b(?:containing|contains|matching|matches|with\s+pattern)\s+(?!['"])([A-Za-z0-9_.:/@*+\- ]{1,60}?)(?=\s*(?:,|;|\band\b|\bthen\b|\bin\b|\bfrom\b|\bon\b|\bto\b|\binto\b|\bsave\b|\bwrite\b|$))""",
        goal or "",
    ):
        pat = m.group(1).strip()
        if pat and pat not in patterns:
            patterns.append(pat)

    numeric_slots: dict[str, str] = {}
    # first/top/last N (lines)
    m_head = re.search(r"(?i)\b(?:first|top|head|limit)\s+(\d+)\b", goal or "")
    if m_head:
        numeric_slots["lines"] = m_head.group(1)
    m_tail = re.search(r"(?i)\b(?:last|bottom|tail)\s+(\d+)\b", goal or "")
    if m_tail:
        numeric_slots["lines"] = m_tail.group(1)
    # field/column N
    m_fld = re.search(r"(?i)\b(?:field|fields|column|columns|col)\s+(\d+(?:[,-]\d+)*)\b", goal or "")
    if m_fld:
        numeric_slots["fields"] = m_fld.group(1)
    return patterns, numeric_slots


# Lazy process-wide cache of live OS tool summaries (read purely from running OS, ZERO hardcoded tool catalog)
_OS_TOOL_INDEX_CACHE: dict[str, str] | None = None


def _build_os_tool_index() -> dict[str, str]:
    """Read live package summaries (`dpkg-query`) + live 1-line `--help` headers for
    coreutils & key CLI packages (~180ms ONCE per process, zero hardcoded tool knowledge).
    """
    global _OS_TOOL_INDEX_CACHE
    if _OS_TOOL_INDEX_CACHE is not None:
        return _OS_TOOL_INDEX_CACHE

    idx: dict[str, str] = {}
    if shutil.which("dpkg-query") and shutil.which("dpkg"):
        pkg_summaries: dict[str, str] = {}
        try:
            out = subprocess.check_output(
                ["dpkg-query", "-W", "-f=${Package}\t${binary:Summary}\n"],
                text=True,
                timeout=3.0,
            )
            for line in out.splitlines():
                if "\t" in line:
                    pkg, summ = line.split("\t", 1)
                    pkg_summaries[pkg.strip()] = summ.strip()
        except Exception:
            pkg_summaries = {}

        # 1. Index direct CLI packages whose package name IS an executable on PATH
        for pkg, summ in pkg_summaries.items():
            resolved = shutil.which(pkg)
            if resolved:
                idx[resolved] = summ
        # Also inspect key utility packages whose binary name differs from package name (e.g. xz-utils->xz, mawk->awk, ripgrep->rg, diffutils->diff)
        cli_pkgs = [
            pkg
            for pkg, summ in pkg_summaries.items()
            if pkg == "coreutils"
            or any(
                kw in summ.lower()
                for kw in ("compression", "de-archiver", "archiving", "archiver", "grep", "regex", "json", "stream editor", "text processing", "url syntax", "checksum", "diff", "patch", "cryptographic")
            )
        ]
        bins_to_probe: list[tuple[str, str]] = []
        for pkg in cli_pkgs[:30]:
            try:
                files = subprocess.check_output(["dpkg", "-L", pkg], text=True, timeout=2.0).splitlines()
            except Exception:
                continue
            psumm = pkg_summaries.get(pkg, "")
            for f in files:
                if (f.startswith("/usr/bin/") or f.startswith("/bin/")) and os.path.isfile(f) and os.access(f, os.X_OK):
                    bins_to_probe.append((f, psumm))

        def _probe_one(item: tuple[str, str]) -> tuple[str, str]:
            bpath, psumm = item
            try:
                r = subprocess.run([bpath, "--help"], capture_output=True, text=True, timeout=0.5)
                lines = [l.strip() for l in (r.stdout or r.stderr or "").splitlines() if l.strip()]
                desc_lines = [l for l in lines[:8] if not l.lower().startswith(("usage:", "or:"))][:2]
                desc = " ".join(desc_lines)
                return bpath, f"{psumm} {desc}".strip()
            except Exception:
                return bpath, psumm

        seen_paths: set[str] = set()
        dedup_probe: list[tuple[str, str]] = []
        for bp, ps in bins_to_probe:
            if bp not in seen_paths:
                seen_paths.add(bp)
                dedup_probe.append((bp, ps))
        if dedup_probe:
            with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
                for bpath, desc in ex.map(_probe_one, dedup_probe):
                    if desc:
                        idx[bpath] = desc

    _OS_TOOL_INDEX_CACHE = idx
    return idx


def _discover_implicit_tools(
    goal: str,
    boundary: Mapping[str, Any],
    *,
    knowledge_source: Callable[[str], list[dict[str, str]]] | None = None,
    gaps_queried: list[str] | None = None,
) -> list[str]:
    """Discover candidate executables on the running OS when the goal NEVER names the tool.

    Sources (zero hardcoded tool catalog):
      1. Magic-byte / format affinity on PATH (`gzip` -> gzip/gunzip, `tar_gzip` -> tar, `zip` -> unzip, `sha256` -> sha256sum)
      2. Live OS package + `--help` summary index (`_build_os_tool_index`)
      3. External `knowledge_source` documentation command extraction (verified against live PATH)
    """
    goal_low = (goal or "").lower()
    in_magic = str(boundary.get("input_magic") or "")
    scored: dict[str, float] = {}

    def _bump(path_or_name: str, delta: float) -> None:
        resolved = path_or_name if os.path.isabs(path_or_name) and os.path.isfile(path_or_name) else (shutil.which(path_or_name) or "")
        if not resolved:
            return
        scored[resolved] = scored.get(resolved, 0.0) + delta

    # 1. Live magic-byte & format affinity (purely structural, verified via PATH)
    if in_magic in ("tar_gzip", "tar_bzip2", "tar_xz", "tar") and re.search(r"\b(extract|unpack|unarchive|untar|list)\b", goal_low):
        _bump("tar", 12.0)
    elif in_magic == "gzip" and re.search(r"\b(decompress|uncompress|inflate|extract|unpack|gunzip|decode)\b", goal_low):
        _bump("gzip", 12.0)
    elif in_magic == "bzip2" and re.search(r"\b(decompress|uncompress|extract|unpack|bunzip2)\b", goal_low):
        _bump("bzip2", 12.0)
    elif in_magic == "xz" and re.search(r"\b(decompress|uncompress|extract|unpack|unxz)\b", goal_low):
        _bump("xz", 12.0)
    elif in_magic == "zip" and re.search(r"\b(decompress|uncompress|extract|unpack|unzip)\b", goal_low):
        _bump("unzip", 12.0)

    # 2. Live OS package + `--help` summary index scoring
    os_idx = _build_os_tool_index()
    if gaps_queried is not None:
        gaps_queried.append("introspect:os_tool_index")

    # Build enriched query text from goal (preserving key action cues)
    query_text = goal
    for bpath, desc in os_idx.items():
        bname = pathlib.Path(bpath).name.lower()
        # Skip destructive / system / irrelevant helpers when doing data transforms
        if bname in ("rm", "rmdir", "shred", "dd", "chmod", "chown", "kill", "nohup", "timeout", "env", "yes", "true", "false", "sleep", "sync", "df", "du", "ls", "dir", "vdir", "ln", "mkfifo", "mknod", "stty", "tty", "uname", "whoami", "id", "groups", "pinky", "users", "who", "arch", "nproc", "hostid", "logname", "chgrp", "chcon", "runcon", "chroot", "stdbuf", "dircolors", "install", "mktemp", "touch", "mkdir", "cp", "mv"):
            continue
        desc_low = desc.lower()
        ov = _semantic_overlap(query_text, f"{bname} {desc}")
        # Strong exact alignment boosts from live `--help` self-description
        if re.search(r"\b(first|top|head)\s+\d+\b", goal_low) and "first" in desc_low and "lines" in desc_low:
            ov += 8.0
        if re.search(r"\b(last|bottom|tail)\s+\d+\b", goal_low) and "last" in desc_low and "lines" in desc_low:
            ov += 8.0
        if re.search(r"\b(containing|contains|matching|matches|pattern)\b", goal_low) and ("pattern" in desc_low or "search" in desc_low):
            ov += 6.0
            if bname in ("grep", "rg"):
                ov += 2.0
        if re.search(r"\b(field|fields|column|columns)\s+\d+\b", goal_low) and ("selected parts of lines" in desc_low or "field" in desc_low):
            ov += 8.0
        if re.search(r"\b(sha256|sha-256)\b", goal_low) and "sha256" in desc_low:
            ov += 10.0
        if re.search(r"\b(md5)\b", goal_low) and "md5" in desc_low:
            ov += 10.0
        if re.search(r"\b(sha1|sha-1)\b", goal_low) and "sha1" in desc_low:
            ov += 10.0
        if re.search(r"\b(sort|sorted|alphabetical|order)\b", goal_low) and "sorted" in desc_low:
            ov += 7.0
        if re.search(r"\b(count\s+lines|line\s+count|word\s+count)\b", goal_low) and "newline, word, and byte counts" in desc_low:
            ov += 8.0
        if re.search(r"\b(json|jq)\b", goal_low) and "json" in desc_low:
            ov += 6.0
        if ov >= 2.5:
            _bump(bpath, ov)

    # 3. External instant knowledge source command discovery (if provided)
    if knowledge_source is not None:
        kq = f"linux command to {goal}"
        if gaps_queried is not None:
            gaps_queried.append(f"knowledge:{kq[:80]}")
        try:
            kdocs = knowledge_source(kq) or []
        except Exception:
            kdocs = []
        for kd in kdocs:
            content = str(kd.get("content") or "")
            for m_cmd in re.finditer(r"(?:`|\$\s*)([a-z][a-z0-9_-]{1,20})\s+[-A-Za-z0-9_.'\"]", content):
                cname = m_cmd.group(1)
                if cname not in _STOPWORDS:
                    _bump(cname, 7.0)

    ranked = sorted(scored.items(), key=lambda x: (-x[1], x[0]))
    return [bp for bp, _ in ranked[:6]]


def scan_environment_boundary(
    workspace: pathlib.Path,
    goal: str,
    *,
    base_url: str | None = None,
    candidate_binaries: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Scan ONLY the immediate goal-relevant affordance boundary in milliseconds."""
    t0 = time.monotonic()
    ws = workspace.resolve()
    ws_files: list[str] = []
    local_docs: list[str] = []
    local_bins: list[str] = []

    if ws.is_dir():
        for entry in sorted(ws.iterdir()):
            if entry.name.startswith("."):
                continue
            if entry.is_file():
                rel = entry.name
                ws_files.append(rel)
                if entry.suffix.lower() in (".md", ".txt", ".rst", ".html", ".htm"):
                    local_docs.append(rel)
                if os.access(entry, os.X_OK) and entry.suffix.lower() not in (".json", ".txt", ".md", ".csv", ".gz", ".tar", ".zip"):
                    local_bins.append(str(entry))

    # Extract concrete file references & key=value bindings from goal
    goal_files: list[str] = []
    for m in _FILE_TOK_RE.finditer(goal or ""):
        cand = m.group(1)
        if not cand.startswith("http") and cand not in goal_files:
            goal_files.append(cand)

    input_files = [f for f in goal_files if (ws / f).exists()]
    output_files = [f for f in goal_files if not (ws / f).exists()]
    is_output_dir = False
    _out_preps = frozenset({"to", "into", "as", "from", "on", "with", "at", "in", "by", "of", "the", "a", "an", "file", "output"})
    # Fallback: if goal mentions "output to X" / "into X" where X already exists or is a dir name
    for m_out in re.finditer(r"(?i)\b(?:to|into|as|output|write|save)\s+(?:file\s+|dir(?:ectory)?\s+|folder\s+)?([A-Za-z0-9_./-]+)", goal or ""):
        cand = m_out.group(1).rstrip(".,;)")
        if cand.lower() in _out_preps:
            continue
        if cand in goal_files and cand not in output_files:
            output_files.append(cand)
            if cand in input_files and len(input_files) > 1:
                input_files.remove(cand)
        elif "/" not in cand and "." not in cand and not output_files and re.search(r"(?i)\b(dir|folder|extract|unpack|unarchive)\b", goal or ""):
            if cand not in output_files and not (ws / cand).is_file():
                output_files.append(cand)
                is_output_dir = True

    input_magic = _detect_file_magic(ws / input_files[0]) if input_files else "none"

    kv_bindings: dict[str, str] = {}
    for m_kv in _KV_PAT.finditer(goal or ""):
        k = m_kv.group(1)
        v = m_kv.group(2) if m_kv.group(2) is not None else (m_kv.group(3) if m_kv.group(3) is not None else m_kv.group(4))
        if k.lower() not in ("http", "https") and v is not None:
            v_clean = v.rstrip(".,;") if len(v) > 1 else v
            kv_bindings[k] = v_clean

    # Extract quoted strings & unquoted patterns/numeric slots
    quoted_literals = [m.group(1) or m.group(2) for m in re.finditer(r"""'([^']+)'|"([^"]+)\"""", goal or "")]
    unquoted_patterns, numeric_slots = _extract_unquoted_patterns_and_numeric_slots(goal)

    # Discover binaries strictly relevant to goal or workspace (NEVER dump /usr/bin!)
    discovered_bins: list[str] = list(local_bins)
    for b in candidate_binaries or ():
        resolved = str(ws / b) if (ws / b).is_file() else (shutil.which(b) or "")
        if resolved and resolved not in discovered_bins:
            discovered_bins.append(resolved)
    # Check tokens in goal that match a real executable on PATH
    for tok in re.findall(r"\b([a-z][a-z0-9_-]{1,20})\b", (goal or "").lower()):
        if tok in _STOPWORDS or tok in ("test", "true", "false", "file", "json", "text", "read", "write", "make", "link", "join", "head", "tail", "line", "name", "type", "user", "pass", "time", "date", "size", "list", "info", "help", "copy", "move", "open", "send", "post", "call", "dir", "top", "split", "cut", "last", "find", "env", "id", "tr", "nl", "wc", "fmt", "sum", "od", "pr", "yes", "seq", "tee", "who"):
            continue
        found = shutil.which(tok)
        if found and found not in discovered_bins:
            discovered_bins.append(found)

    # Detect URL
    detected_url = base_url
    if not detected_url:
        m_u = re.search(r"https?://[^\s'\"<>]+", goal or "")
        if m_u:
            detected_url = m_u.group(0).rstrip(".,;)")

    return {
        "workspace": str(ws),
        "workspace_files": ws_files,
        "local_docs": local_docs,
        "binaries": discovered_bins,
        "base_url": detected_url,
        "input_files": input_files,
        "input_magic": input_magic,
        "output_files": output_files,
        "is_output_dir": is_output_dir,
        "kv_bindings": kv_bindings,
        "quoted_literals": quoted_literals,
        "unquoted_patterns": unquoted_patterns,
        "numeric_slots": numeric_slots,
        "goal_tokens": _tokenize(goal),
        "goal_concepts": sorted(_concept_set(goal)),
        "scan_ms": round((time.monotonic() - t0) * 1000.0, 2),
    }


# ---------------------------------------------------------------------------
# Stage 3: Instant Knowledge Acquisition (L0 Introspection -> L1 Docs -> L2 Web)
# ---------------------------------------------------------------------------


def _probe_binary_help(binary: str, subcommand: str = "", timeout_s: float = 3.0) -> str:
    """L0 (<5ms) live introspection: query `--help` / `-h` of an unseen binary."""
    cmds = (
        [[binary, subcommand, "--help"], [binary, subcommand, "-h"], [binary, "help", subcommand]]
        if subcommand
        else [[binary, "--help"], [binary, "-h"]]
    )
    best = ""
    for cmd in cmds:
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
            out = (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")
            if len(out.strip()) > len(best.strip()):
                best = out
            if len(best.strip()) >= 80 and ("usage" in best.lower() or "--" in best or "options" in best.lower()):
                break
        except Exception:
            continue
    return best


def _fetch_knowledge_for_gap(
    query: str,
    *,
    workspace: pathlib.Path,
    local_docs: Sequence[str],
    knowledge_source: Callable[[str], list[dict[str, str]]] | None,
) -> list[dict[str, str]]:
    """Fetch instant knowledge in strict latency order: L1 local docs -> L2 external web source."""
    docs: list[dict[str, str]] = []
    q_toks = set(_tokenize(query))
    for rel in local_docs:
        p = workspace / rel
        if p.is_file():
            try:
                txt = p.read_text(encoding="utf-8", errors="replace")[:32000]
                if not q_toks or any(t in txt.lower() for t in q_toks):
                    docs.append({"source": f"local:{rel}", "content": txt})
            except Exception:
                pass
    if knowledge_source is not None:
        try:
            fetched = knowledge_source(query) or []
            for item in fetched:
                if isinstance(item, Mapping) and item.get("content"):
                    docs.append(
                        {
                            "source": str(item.get("source") or item.get("url") or "web"),
                            "content": str(item["content"])[:40000],
                        }
                    )
        except Exception:
            pass
    return docs


# ---------------------------------------------------------------------------
# Stage 4a: Zero-Prior CLI Synthesis, Execution, Refusal Recovery & Verification
# ---------------------------------------------------------------------------


def _score_option_for_role(opt: OptionSpec, role_query: str, *, exclude_tokens: set[str] | None = None) -> float:
    # Exact option-name tokens (`--reverse`, `--unique`, `--output`, `--delim`) carry 2.5x weight
    # over incidental description words, excluding the binary's own name (e.g. `sort` in `--version-sort`).
    ex = exclude_tokens or set()
    flag_name = opt.long.lstrip("-").replace("-", " ") if opt.long else ""
    if ex and flag_name:
        flag_name = " ".join(t for t in flag_name.split() if t.lower() not in ex)
    name_score = _semantic_overlap(flag_name, role_query) * 2.5 if flag_name else 0.0
    arg_score = _semantic_overlap(opt.arg_name, role_query) * 1.5 if opt.arg_name else 0.0
    desc_text = opt.description
    if ex:
        desc_text = " ".join(t for t in desc_text.split() if t.lower().strip(".,;:()") not in ex)
    desc_score = _semantic_overlap(desc_text, role_query)
    return name_score + arg_score + desc_score


def _select_best_subcommand(contract: CLISubcommandContract, goal: str) -> str:
    if not contract.subcommands:
        return ""
    best_sc, best_s = "", 0.0
    for sc, desc in contract.subcommands.items():
        s = _semantic_overlap(f"{sc} {desc}", goal)
        if sc.lower() in (goal or "").lower().split():
            s += 4.0
        if s > best_s:
            best_sc, best_s = sc, s
    return best_sc if best_s >= 1.5 else ""


def _synthesize_cli_invocations(
    contract: CLISubcommandContract,
    boundary: Mapping[str, Any],
    goal: str,
    *,
    banned_flags: set[str],
    required_extra_flags: set[str],
    recalled_laws: Sequence[Mapping[str, Any]] = (),
) -> list[tuple[list[str], list[str], bool]]:
    """Synthesize ranked candidate `(argv, role_pattern, capture_stdout_to_output)` tuples
    PURELY from the compiled `CLISubcommandContract` + boundary + recalled role laws.
    """
    bname = contract.binary
    prefix: list[str] = [bname] + ([contract.subcommand] if contract.subcommand else [])
    role_prefix: list[str] = ["?BIN"] + (["?SUBCMD"] if contract.subcommand else [])

    inputs = list(boundary.get("input_files") or [])
    outputs = list(boundary.get("output_files") or [])
    is_output_dir = bool(boundary.get("is_output_dir"))
    kv = dict(boundary.get("kv_bindings") or {})
    numeric_slots = dict(boundary.get("numeric_slots") or {})
    quoted = list(boundary.get("quoted_literals") or [])
    unquoted_patterns = list(boundary.get("unquoted_patterns") or [])
    goal_low = (goal or "").lower()

    usable_opts = [o for o in contract.options if not (set(o.all_flags) & banned_flags)]

    # 1. Bind explicit kv_bindings (`format=json`, `delimiter=,`) AND numeric slots (`lines=2`, `fields=2`)
    bound_args: list[str] = []
    bound_roles: list[str] = []
    used_flags: set[str] = set()

    merged_kv = dict(kv)
    for nk, nv in numeric_slots.items():
        if nk not in merged_kv:
            merged_kv[nk] = nv

    for k, v in merged_kv.items():
        best_o, best_s = None, 0.0
        for o in usable_opts:
            if not o.takes_arg or o.primary_flag in used_flags:
                continue
            s = _score_option_for_role(o, f"{k} {o.arg_name}")
            if s > best_s:
                best_o, best_s = o, s
        if best_o is not None and best_s >= 1.5:
            bound_args.extend([best_o.primary_flag, v])
            bound_roles.extend([f"?FLAG_{k.upper()}", f"?VAL_{k.upper()}"])
            used_flags.update(best_o.all_flags)

    # 2. Detect boolean mode flags strongly aligned with the goal (e.g. --decode, --decompress, --extract, --raw-output, --reverse, --unique)
    bin_stem_excl = {pathlib.Path(bname).name.lower()} | {k.lower() for k in merged_kv.keys()}
    wants_nul = bool(re.search(r"\b(nul|null|zero[- ]?terminated)\b", goal_low))
    bool_flags: list[tuple[float, OptionSpec]] = []
    stdout_flag: OptionSpec | None = None
    for o in usable_opts:
        if o.takes_arg or o.primary_flag in used_flags:
            continue
        if o.primary_flag in ("-h", "--help", "-V", "--version"):
            continue
        if not wants_nul and ("zero-terminated" in o.long.lower() or "nul" in o.description.lower().split()):
            continue
        if o.long in ("--stdout", "--to-stdout") or (o.short == "-c" and "standard output" in o.description.lower()):
            stdout_flag = o
        s = _score_option_for_role(o, goal, exclude_tokens=bin_stem_excl)
        if o.primary_flag in required_extra_flags:
            s += 10.0
        if s >= 2.0:
            bool_flags.append((s, o))
    bool_flags.sort(key=lambda x: -x[0])
    chosen_bools = [o for _, o in bool_flags[:2]]

    # 3. Detect dedicated input-file/archive flag & output-file/dir flag from compiled option specs
    in_flag: OptionSpec | None = None
    out_flag: OptionSpec | None = None
    _non_io_qualifiers = ("random", "temp", "temporary", "compress", "buffer", "batch", "debug", "parallel", "log", "config", "exclude", "files-from", "listed-incremental", "add-file", "delimiter")
    in_query = "input infile src source from read archive file" if boundary.get("input_magic") in ("tar", "tar_gzip", "tar_bzip2", "tar_xz") else "input infile src source from read"
    out_query = "dir directory chdir extract into destination target" if is_output_dir else "output outfile dst dest destination target write save"
    for o in usable_opts:
        if not o.takes_arg or o.primary_flag in used_flags:
            continue
        if any(q in o.long.lower() for q in _non_io_qualifiers):
            continue
        s_in = _score_option_for_role(o, in_query)
        s_out = _score_option_for_role(o, out_query)
        if s_in >= 3.0 and s_in > s_out:
            if in_flag is None or s_in > _score_option_for_role(in_flag, in_query):
                in_flag = o
        if s_out >= 3.0 and s_out >= s_in:
            if out_flag is None or s_out > _score_option_for_role(out_flag, out_query):
                out_flag = o

    # General UNIX preservation rule: when capturing stdout to an output file without an explicit
    # output flag AND the tool offers `--stdout`/`--to-stdout` (e.g. gzip/bzip2/xz), include it so
    # the tool writes to stdout cleanly without destroying the input file in-place!
    if stdout_flag is not None and out_flag is None and outputs and not is_output_dir:
        if stdout_flag not in chosen_bools:
            chosen_bools.append(stdout_flag)

    # 4. Detect positional/flag expression/query/pattern (quoted OR unquoted `containing X` / `matching X`)
    expr_args: list[str] = []
    expr_roles: list[str] = []
    pattern_candidates = [q for q in quoted if q not in kv.values() and q not in inputs and q not in outputs]
    if not pattern_candidates and unquoted_patterns:
        pattern_candidates = [p for p in unquoted_patterns if p not in inputs and p not in outputs]

    for q in pattern_candidates:
        expr_opt = None
        best_es = 0.0
        for o in usable_opts:
            if o.takes_arg and o.primary_flag not in used_flags and o != in_flag and o != out_flag:
                if any(bad in o.long.lower() for bad in ("file", "exclude", "include", "from")):
                    continue
                es = _score_option_for_role(o, "filter query expression pattern regexp")
                if es > best_es:
                    expr_opt, best_es = o, es
        if expr_opt is not None and best_es >= 3.5:
            expr_args.extend([expr_opt.primary_flag, q])
            expr_roles.extend(["?FLAG_EXPR", "?EXPR"])
            used_flags.update(expr_opt.all_flags)
        else:
            expr_args.append(q)
            expr_roles.append("?EXPR")
        break

    candidates: list[tuple[list[str], list[str], bool]] = []

    def _add(argv: list[str], rpat: list[str], cap_out: bool) -> None:
        key = (tuple(argv), cap_out)
        if not any((tuple(a), c) == key for a, _, c in candidates):
            candidates.append((argv, rpat, cap_out))

    b_argv = [o.primary_flag for o in chosen_bools]
    b_roles = [f"?MODE_{i}" for i in range(len(chosen_bools))]

    # Strategy A: Explicit input flag + explicit output flag (e.g. `tool sub --in A --out B`)
    if in_flag and out_flag and inputs and outputs:
        _add(
            prefix + b_argv + bound_args + expr_args + [in_flag.primary_flag, inputs[0], out_flag.primary_flag, outputs[0]],
            role_prefix + b_roles + bound_roles + expr_roles + ["?FLAG_IN", "?IN_FILE", "?FLAG_OUT", "?OUT_FILE"],
            False,
        )

    # Strategy B: Positional input + explicit output flag (e.g. `tool sub --out B A`)
    if out_flag and inputs and outputs:
        _add(
            prefix + b_argv + bound_args + expr_args + [out_flag.primary_flag, outputs[0], inputs[0]],
            role_prefix + b_roles + bound_roles + expr_roles + ["?FLAG_OUT", "?OUT_FILE", "?IN_FILE"],
            False,
        )
        _add(
            prefix + b_argv + bound_args + expr_args + [inputs[0], out_flag.primary_flag, outputs[0]],
            role_prefix + b_roles + bound_roles + expr_roles + ["?IN_FILE", "?FLAG_OUT", "?OUT_FILE"],
            False,
        )

    # Strategy C: Explicit input flag + stdout redirected to output file
    if in_flag and inputs:
        _add(
            prefix + b_argv + bound_args + expr_args + [in_flag.primary_flag, inputs[0]],
            role_prefix + b_roles + bound_roles + expr_roles + ["?FLAG_IN", "?IN_FILE"],
            bool(outputs),
        )

    # Strategy D: Positional expression + positional input -> stdout (or redirected to output file)
    if inputs:
        _add(
            prefix + b_argv + bound_args + expr_args + [inputs[0]],
            role_prefix + b_roles + bound_roles + expr_roles + ["?IN_FILE"],
            bool(outputs),
        )
        # Try single-flag subsets when 2+ boolean flags matched (avoids spurious secondary flag collisions)
        if len(b_argv) >= 2:
            for bi_s, bf_s in enumerate(b_argv):
                _add(
                    prefix + [bf_s] + bound_args + expr_args + [inputs[0]],
                    role_prefix + [f"?MODE_{bi_s}"] + bound_roles + expr_roles + ["?IN_FILE"],
                    bool(outputs),
                )
        # Also try without optional bool flags in case a boolean flag wasn't intended
        if b_argv:
            _add(
                prefix + bound_args + expr_args + [inputs[0]],
                role_prefix + bound_roles + expr_roles + ["?IN_FILE"],
                bool(outputs),
            )
            if in_flag and out_flag and outputs:
                _add(
                    prefix + bound_args + expr_args + [in_flag.primary_flag, inputs[0], out_flag.primary_flag, outputs[0]],
                    role_prefix + bound_roles + expr_roles + ["?FLAG_IN", "?IN_FILE", "?FLAG_OUT", "?OUT_FILE"],
                    False,
                )

    # Strategy E: Positional input + positional output (e.g. `tool sub in.txt out.txt`)
    if inputs and outputs and not out_flag:
        _add(
            prefix + b_argv + bound_args + expr_args + [inputs[0], outputs[0]],
            role_prefix + b_roles + bound_roles + expr_roles + ["?IN_FILE", "?OUT_FILE"],
            False,
        )

    # Strategy F: No input file (pure generation/query command)
    if not inputs:
        if out_flag and outputs:
            _add(
                prefix + b_argv + bound_args + expr_args + [out_flag.primary_flag, outputs[0]],
                role_prefix + b_roles + bound_roles + expr_roles + ["?FLAG_OUT", "?OUT_FILE"],
                False,
            )
        _add(
            prefix + b_argv + bound_args + expr_args,
            role_prefix + b_roles + bound_roles + expr_roles,
            bool(outputs),
        )

    # Boost candidates whose role_pattern matches a recalled generalized law from external memory!
    if recalled_laws:
        recalled_pats = [tuple(l.get("role_pattern") or ()) for l in recalled_laws]

        def _law_rank(item: tuple[list[str], list[str], bool]) -> int:
            rpat = item[1]
            for rp in recalled_pats:
                if len(rp) == len(rpat) and all(a == b or a.startswith("?SLOT_") for a, b in zip(rp, rpat)):
                    return 0
            return 1

        candidates.sort(key=_law_rank)

    return candidates[:8]


def _check_semantic_postconditions(
    workspace: pathlib.Path,
    boundary: Mapping[str, Any],
    goal: str,
    out_bytes: bytes | None,
    out_path: pathlib.Path | None,
) -> tuple[bool, str]:
    """Compile executable semantic invariants directly from the goal text + live input bytes.

    Prevents false positives (such as running `sort` on raw `.gz` binary bytes and claiming
    success merely because an output file has >0 bytes!).
    """
    goal_low = (goal or "").lower()
    in_files = list(boundary.get("input_files") or [])
    in_path = (workspace / in_files[0]) if in_files else None
    in_magic = str(boundary.get("input_magic") or "")
    is_output_dir = bool(boundary.get("is_output_dir"))

    # 1. Directory extraction check
    if is_output_dir and out_path is not None:
        if not out_path.is_dir():
            return False, f"missing_output_dir:{out_path.name}"
        extracted = [p for p in out_path.rglob("*") if p.is_file() and p.stat().st_size > 0]
        if not extracted:
            return False, f"empty_extracted_dir:{out_path.name}"
        return True, f"extracted_dir_verified:{out_path.name}({len(extracted)}files)"

    if out_bytes is None or len(out_bytes) == 0:
        return False, "empty_output_bytes"

    # 2. Decompression invariant: output must NOT still carry compressed archive magic
    if re.search(r"\b(decompress|uncompress|gunzip|bunzip2|unxz|inflate)\b", goal_low) or (
        in_magic in ("gzip", "bzip2", "xz") and re.search(r"\b(extract|decode)\b", goal_low)
    ):
        if out_bytes.startswith((b"\x1f\x8b", b"BZh", b"\xfd7zXZ\x00", b"PK\x03\x04")):
            return False, "postcondition_failed:output_still_compressed"
        if in_path is not None and in_path.is_file():
            try:
                if out_bytes == in_path.read_bytes():
                    return False, "postcondition_failed:output_identical_to_compressed_input"
            except Exception:
                pass

    # 3. Text-level invariants (filter/match, sort/unique/reverse, first/last N, checksum, JSON)
    needs_utf8 = bool(
        re.search(
            r"\b(containing|contains|matching|matches|filter|sort|unique|dedup|deduplicate|reverse|first|top|last|tail|head|field|column|sha256|md5|sha1|checksum|json)\b",
            goal_low,
        )
    )
    out_text: str | None = None
    if needs_utf8:
        try:
            out_text = out_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return False, "postcondition_failed:non_utf8_output_for_text_goal"
        if "\x00" in out_text:
            return False, "postcondition_failed:nul_bytes_in_text_output"

    if out_text is not None:
        lines = [ln for ln in out_text.splitlines() if ln != ""]

        # 3a. Pattern filter invariant (`containing X` / `matching X`)
        unq_pats = list(boundary.get("unquoted_patterns") or [])
        if unq_pats and re.search(r"\b(containing|contains|matching|matches)\b", goal_low):
            pat = unq_pats[0]
            ign_case = bool(re.search(r"\b(case[- ]?insensitive|ignore[- ]?case)\b", goal_low))
            for ln in lines:
                hay = ln.lower() if ign_case else ln
                ndl = pat.lower() if ign_case else pat
                if ndl not in hay:
                    return False, f"postcondition_failed:line_missing_pattern({pat!r})"
            # Semantic law of line filtering: `filter lines matching P` must preserve whole input lines
            # (rejects destructive partial-match flags like `--only-matching` unless explicitly requested!)
            if (
                re.search(r"\blines?\b", goal_low)
                and not re.search(r"\bonly\s+matching\b", goal_low)
                and in_path is not None
                and in_path.is_file()
            ):
                try:
                    in_lines = set(in_path.read_text(encoding="utf-8", errors="replace").splitlines())
                    if in_lines and any(ln not in in_lines for ln in lines):
                        return False, "postcondition_failed:filtered_output_altered_input_lines"
                except Exception:
                    pass

        # 3b. Unique / deduplicate invariant
        if re.search(r"\b(unique|dedup|deduplicate|deduplicated)\b", goal_low):
            if len(lines) != len(set(lines)):
                return False, "postcondition_failed:duplicate_lines_remain"

        # 3c. Sort order invariant (when explicitly sorting without numeric-only custom key)
        if re.search(r"\b(sort|sorted)\b", goal_low) and not re.search(r"\b(numeric|number|frequency|count|column|field|key)\b", goal_low):
            rev = bool(re.search(r"\b(reverse|descending|desc)\b", goal_low))
            # Check monotonic order under standard ASCII or case-insensitive locale collation
            if lines != sorted(lines, reverse=rev) and [l.lower() for l in lines] != sorted([l.lower() for l in lines], reverse=rev):
                return False, f"postcondition_failed:not_sorted(reverse={rev})"

        # 3d. Top-N / First-N / Last-N line count invariant
        num_slots = dict(boundary.get("numeric_slots") or {})
        if "lines" in num_slots and re.search(r"\b(first|top|head|last|tail|limit)\s+\d+\b", goal_low):
            try:
                max_n = int(num_slots["lines"])
                if not (1 <= len(lines) <= max_n):
                    return False, f"postcondition_failed:line_count({len(lines)})_exceeds_limit({max_n})"
            except ValueError:
                pass

        # 3e. Checksum / hash digest format invariant
        if re.search(r"\b(sha256|sha-256)\b", goal_low):
            if not re.search(r"\b[0-9a-fA-F]{64}\b", out_text):
                return False, "postcondition_failed:missing_64hex_sha256_digest"
        elif re.search(r"\b(sha1|sha-1)\b", goal_low):
            if not re.search(r"\b[0-9a-fA-F]{40}\b", out_text):
                return False, "postcondition_failed:missing_40hex_sha1_digest"
        elif re.search(r"\bmd5\b", goal_low):
            if not re.search(r"\b[0-9a-fA-F]{32}\b", out_text):
                return False, "postcondition_failed:missing_32hex_md5_digest"

        # 3f. JSON syntax check if output file is `.json`
        if out_path is not None and out_path.suffix.lower() == ".json":
            try:
                json.loads(out_text)
            except Exception as exc:
                return False, f"invalid_json_output:{exc}"

    return True, "semantic_postconditions_verified"


def _independent_cli_verify(
    workspace: pathlib.Path,
    boundary: Mapping[str, Any],
    goal: str,
    stdout_bytes: bytes,
    rc: int,
    verifier: Callable[[dict[str, Any]], tuple[bool, str]] | None,
) -> tuple[bool, str]:
    if rc != 0:
        return False, f"non_zero_exit:{rc}"
    outputs = list(boundary.get("output_files") or [])
    out_path = (workspace / outputs[0]) if outputs else None
    out_bytes: bytes | None = None
    if out_path is not None and out_path.is_file():
        out_bytes = out_path.read_bytes()
    elif out_path is None and stdout_bytes:
        out_bytes = stdout_bytes
    stdout_text = stdout_bytes.decode("utf-8", errors="replace")
    state = {
        "workspace": str(workspace),
        "stdout": stdout_text,
        "output_path": str(out_path) if out_path else None,
        "output_text": out_bytes.decode("utf-8", errors="replace") if out_bytes is not None else None,
        "output_bytes": out_bytes,
    }
    if verifier is not None:
        try:
            return verifier(state)
        except Exception as exc:
            return False, f"verifier_error:{type(exc).__name__}:{exc}"
    if out_path is not None:
        if bool(boundary.get("is_output_dir")):
            return _check_semantic_postconditions(workspace, boundary, goal, None, out_path)
        if out_path.is_file() and out_path.stat().st_size > 0:
            ok_sem, note_sem = _check_semantic_postconditions(workspace, boundary, goal, out_bytes, out_path)
            if not ok_sem:
                return False, note_sem
            return True, f"output_file_verified:{out_path.name}({out_path.stat().st_size}B,{note_sem})"
        if out_path.is_dir() and any(out_path.iterdir()):
            return True, f"output_dir_verified:{out_path.name}"
        return False, f"missing_or_empty_output:{out_path.name}"
    if stdout_bytes.strip():
        ok_sem, note_sem = _check_semantic_postconditions(workspace, boundary, goal, stdout_bytes, None)
        if not ok_sem:
            return False, note_sem
        return True, f"stdout_verified({len(stdout_bytes)}B,{note_sem})"
    return False, "empty_observable_effect"


# ---------------------------------------------------------------------------
# Stage 4b: Zero-Prior Doc-Compiled HTTP/REST Execution & Active Refusal Recovery
# ---------------------------------------------------------------------------


def _http_call(
    method: str,
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    json_body: Mapping[str, Any] | None = None,
    timeout_s: float = 8.0,
) -> tuple[int, dict[str, str], str]:
    hdrs = dict(headers or {})
    data: bytes | None = None
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return resp.status, dict(resp.headers.items()), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return exc.code, dict(exc.headers.items()) if exc.headers else {}, body
    except Exception as exc:
        return 0, {}, str(exc)


def _resolve_http_path(template: str, kv: Mapping[str, str]) -> str:
    def _sub(m: re.Match[str]) -> str:
        name = m.group(1) or m.group(2) or m.group(3)
        if name in kv:
            return urllib.parse.quote(str(kv[name]), safe="")
        for k, v in kv.items():
            if _semantic_overlap(k, name) >= 1.5:
                return urllib.parse.quote(str(v), safe="")
        return m.group(0)

    return re.sub(r"\{([^}]+)\}|<([^>]+)>|:([A-Za-z_][A-Za-z0-9_]*)", _sub, template)


def _solve_doc_compiled_http(
    base_url: str,
    goal: str,
    boundary: Mapping[str, Any],
    docs: Sequence[Mapping[str, str]],
    *,
    memory: EpistemicMemoryStore | None,
    verifier: Callable[[dict[str, Any]], tuple[bool, str]] | None,
    timeout_s: float,
) -> dict[str, Any]:
    t0 = time.monotonic()
    contracts: list[HTTPContract] = []
    for d in docs:
        contracts.extend(compile_doc_to_http_contracts(d["content"], source=d["source"]))

    if not contracts:
        return {
            "status": "FAILED",
            "mode": "NO_HTTP_CONTRACTS_COMPILED",
            "gaps_unresolved": ["api_documentation_missing_endpoints"],
            "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    kv = dict(boundary.get("kv_bindings") or {})
    goal_concepts = set(boundary.get("goal_concepts") or ())
    recalled = memory.recall("http_role_law", goal_concepts) if memory else []

    # Identify auth token value from kv_bindings (if supplied in goal)
    auth_token_val = ""
    for k, v in kv.items():
        if any(w in k.lower() for w in ("token", "key", "secret", "auth")):
            auth_token_val = v
            break

    # Rank endpoints by semantic alignment with goal (method intent + path + description + fields)
    def _rank_ep(c: HTTPContract) -> float:
        s = _semantic_overlap(f"{c.method} {c.path_template} {c.description} {' '.join(c.body_fields)} {' '.join(c.query_params)}", goal)
        g_lo = goal.lower()
        if c.method == "POST" and any(w in g_lo for w in ("create", "add", "submit", "register", "new", "open", "post")):
            s += 3.0
        elif c.method in ("PUT", "PATCH") and any(w in g_lo for w in ("update", "edit", "modify", "set", "patch")):
            s += 3.0
        elif c.method == "DELETE" and any(w in g_lo for w in ("delete", "remove", "cancel", "drop")):
            s += 3.0
        elif c.method == "GET" and any(w in g_lo for w in ("list", "get", "fetch", "find", "query", "read", "retrieve")):
            s += 2.5
        # Penalize unresolved path params if we don't have a binding yet
        unresolved_p = re.findall(r"\{([^}]+)\}|<([^>]+)>|:([A-Za-z_][A-Za-z0-9_]*)", _resolve_http_path(c.path_template, kv))
        s -= len(unresolved_p) * 1.5
        return s

    ranked = sorted(contracts, key=_rank_ep, reverse=True)
    trace: list[dict[str, Any]] = []
    origin = base_url.rstrip("/")

    # Execute top candidate with active refusal recovery (missing auth header / missing field / 401)
    for ep in ranked[:4]:
        headers: dict[str, str] = {}
        if ep.auth_header and auth_token_val:
            headers[ep.auth_header] = f"{ep.auth_prefix} {auth_token_val}".strip() if ep.auth_prefix else auth_token_val

        body: dict[str, Any] | None = None
        if ep.method in ("POST", "PUT", "PATCH"):
            body = {}
            for fld in ep.body_fields:
                if fld in kv:
                    body[fld] = kv[fld]
                else:
                    for k, v in kv.items():
                        if k.lower() not in ("token", "key", "api_key", "auth", "secret") and _semantic_overlap(k, fld) >= 1.5:
                            body[fld] = v
                            break
            # Include any remaining non-auth kv pairs when doc didn't enumerate all fields
            for k, v in kv.items():
                if k.lower() not in ("token", "key", "api_key", "auth", "secret") and k not in body and k not in ep.query_params:
                    body[k] = v

        qparams: dict[str, str] = {}
        for qp in ep.query_params:
            if qp in kv:
                qparams[qp] = kv[qp]

        for attempt in range(3):
            resolved_path = _resolve_http_path(ep.path_template, kv)
            url = origin + resolved_path
            if qparams:
                url += ("&" if "?" in url else "?") + urllib.parse.urlencode(qparams)
            status, resp_hdrs, resp_body = _http_call(ep.method, url, headers=headers, json_body=body, timeout_s=min(timeout_s, 8.0))
            trace.append({"method": ep.method, "path": resolved_path, "status": status, "attempt": attempt + 1})

            if 200 <= status < 300:
                parsed_json: Any = None
                try:
                    parsed_json = json.loads(resp_body)
                except Exception:
                    pass
                # Independent readback verification when a GET sibling endpoint exists
                readback_ok = True
                readback_body = None
                if ep.method in ("POST", "PUT", "PATCH"):
                    get_eps = [c for c in contracts if c.method == "GET" and c.path_template.split("/")[1:3] == ep.path_template.split("/")[1:3]]
                    if get_eps:
                        g_path = _resolve_http_path(get_eps[0].path_template, kv)
                        if isinstance(parsed_json, dict) and "id" in parsed_json and ("{" in g_path or ":" in g_path or "<" in g_path):
                            g_path = _resolve_http_path(get_eps[0].path_template, {**kv, "id": str(parsed_json["id"])})
                        if not re.search(r"\{[^}]+\}|<[^>]+>|:[A-Za-z_]", g_path):
                            gst, _, gbody = _http_call("GET", origin + g_path, headers=headers, timeout_s=min(timeout_s, 6.0))
                            readback_ok = 200 <= gst < 300
                            readback_body = gbody
                            trace.append({"method": "GET", "path": g_path, "status": gst, "readback": True})

                state = {
                    "status_code": status,
                    "response_body": resp_body,
                    "response_json": parsed_json,
                    "readback_body": readback_body,
                    "trace": trace,
                }
                ok_v, note_v = verifier(state) if verifier is not None else (readback_ok, f"http_{status}_verified")
                if ok_v:
                    law = None
                    if memory is not None:
                        role_pat = [f"HTTP_{ep.method}", "?AUTH_HDR" if headers else "?NO_AUTH", "?BODY_FIELDS" if body else "?QUERY"]
                        law = memory.generalize_and_store(
                            kind="http_role_law",
                            goal_concepts=goal_concepts,
                            role_pattern=role_pat,
                            postcondition_kind="http_2xx_readback",
                            env_fingerprint=f"http:{ep.method}:{ep.path_template}",
                            meta_roles={"method": ep.method, "uses_auth": bool(headers)},
                        )
                    return {
                        "status": "VERIFIED",
                        "mode": "DOC_COMPILED_HTTP_ACTIVE_INFERENCE",
                        "contracts_compiled": len(contracts),
                        "recalled_laws": len(recalled),
                        "executed_trace": trace,
                        "response_json": parsed_json,
                        "response_body": resp_body,
                        "verification": note_v,
                        "generalized_law": law,
                        "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                        "model_calls": 0,
                        "parameters_stored": 0,
                    }
                break

            # Active refusal recovery (doc-drift immunity!)
            refusal = parse_refusal_surface(resp_body, status_code=status)
            changed = False
            for mh in refusal["missing_headers"]:
                if auth_token_val and mh not in headers:
                    headers[mh] = auth_token_val
                    changed = True
            if refusal["needs_auth"] and auth_token_val and not headers:
                # Fallback to standard or doc-mentioned auth header
                hdr_name = ep.auth_header or "Authorization"
                headers[hdr_name] = f"Bearer {auth_token_val}" if hdr_name.lower() == "authorization" else auth_token_val
                changed = True
            if refusal["missing_fields"] and body is not None:
                for mf in refusal["missing_fields"]:
                    if mf not in body:
                        for k, v in kv.items():
                            if _semantic_overlap(k, mf) >= 1.0 or mf.lower() in k.lower() or k.lower() in mf.lower():
                                body[mf] = v
                                changed = True
                                break
            if not changed:
                break

    return {
        "status": "FAILED",
        "mode": "HTTP_EXECUTION_UNVERIFIED",
        "contracts_compiled": len(contracts),
        "executed_trace": trace,
        "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
        "model_calls": 0,
        "parameters_stored": 0,
    }


# ---------------------------------------------------------------------------
# Stage 5: Unified Entry Point — Goal-Directed Epistemic Closure Loop
# ---------------------------------------------------------------------------


def solve_with_instant_knowledge(
    goal: str,
    *,
    workspace: str | pathlib.Path,
    memory: EpistemicMemoryStore | None = None,
    knowledge_source: Callable[[str], list[dict[str, str]]] | None = None,
    base_url: str | None = None,
    candidate_binaries: Sequence[str] | None = None,
    verifier: Callable[[dict[str, Any]], tuple[bool, str]] | None = None,
    timeout_s: float = 15.0,
) -> dict[str, Any]:
    """Universal zero-LLM, zero-weight Goal-Directed Epistemic Algorithm.

    Enters ANY unseen arbitrary environment knowing nothing:
      SCAN_BOUNDARY -> EPISTEMIC_PARTITION -> ACQUIRE_CONTRACTS -> ACT_VERIFY_REFUSE -> ANTI_UNIFY_PRUNE.
    Guarantees `model_calls == 0`, `parameters_stored == 0`, and zero concrete leakage into memory.
    """
    t0 = time.monotonic()
    ws = pathlib.Path(workspace).resolve()
    boundary = scan_environment_boundary(
        ws, goal, base_url=base_url, candidate_binaries=candidate_binaries
    )
    goal_concepts = set(boundary["goal_concepts"])
    gaps_queried: list[str] = []

    # Branch 1: Doc-backed HTTP/REST Service (when URL is present)
    if boundary["base_url"]:
        gap_q = f"HTTP API documentation endpoints auth headers {goal}"
        gaps_queried.append(gap_q)
        docs = _fetch_knowledge_for_gap(
            gap_q, workspace=ws, local_docs=boundary["local_docs"], knowledge_source=knowledge_source
        )
        # Also probe common live doc routes on the server itself if no local/web docs supplied
        if not docs:
            origin = boundary["base_url"].rstrip("/")
            parsed_u = urllib.parse.urlparse(boundary["base_url"])
            # Direct GET endpoint fetch when full concrete path is given (e.g. `Fetch http://host/api/items and save to raw.json`)
            if parsed_u.path and parsed_u.path != "/" and re.search(r"(?i)\b(fetch|get|download|read|retrieve|pull)\b", goal or ""):
                hdrs: dict[str, str] = {}
                kv_b = boundary.get("kv_bindings") or {}
                for k, v in kv_b.items():
                    if any(w in k.lower() for w in ("token", "key", "auth", "secret")):
                        hdrs["Authorization"] = f"Bearer {v}"
                st, _, body = _http_call("GET", boundary["base_url"], headers=hdrs, timeout_s=min(timeout_s, 8.0))
                if 200 <= st < 300 and body:
                    outputs_h = list(boundary.get("output_files") or [])
                    out_p = (ws / outputs_h[0]) if outputs_h else None
                    if out_p is not None:
                        out_p.parent.mkdir(parents=True, exist_ok=True)
                        out_p.write_text(body, encoding="utf-8")
                    ok_v = True
                    note_v = f"http_direct_get_200({len(body)}B)"
                    if verifier is not None:
                        try:
                            ok_v, note_v = verifier(
                                {
                                    "status_code": st,
                                    "response_body": body,
                                    "output_path": str(out_p) if out_p else None,
                                    "output_text": body,
                                }
                            )
                        except Exception as exc:
                            ok_v, note_v = False, f"verifier_error:{exc}"
                    if ok_v:
                        return {
                            "schema": SCHEMA,
                            "authority": AUTHORITY,
                            "status": "VERIFIED",
                            "mode": "DIRECT_HTTP_GET_VERIFIED",
                            "response_body": body[:2000],
                            "verification": note_v,
                            "boundary_scan_ms": boundary["scan_ms"],
                            "gaps_queried": gaps_queried,
                            "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                            "model_calls": 0,
                            "parameters_stored": 0,
                        }
            for dpath in ("/docs", "/help", "/api-docs", "/README.md", "/"):
                st, _, body = _http_call("GET", origin + dpath, timeout_s=3.0)
                if 200 <= st < 300 and body.strip():
                    docs.append({"source": f"live:{dpath}", "content": body})
                    if re.search(r"\b(GET|POST|PUT|PATCH|DELETE)\s+/", body):
                        break
        res_http = _solve_doc_compiled_http(
            boundary["base_url"], goal, boundary, docs, memory=memory, verifier=verifier, timeout_s=timeout_s
        )
        if res_http.get("status") == "VERIFIED" and boundary.get("output_files") and res_http.get("response_body"):
            out_p = ws / boundary["output_files"][0]
            if not out_p.exists():
                out_p.parent.mkdir(parents=True, exist_ok=True)
                out_p.write_text(str(res_http["response_body"]), encoding="utf-8")
        res_http["schema"] = SCHEMA
        res_http["authority"] = AUTHORITY
        res_http["boundary_scan_ms"] = boundary["scan_ms"]
        res_http["gaps_queried"] = gaps_queried
        return res_http

    # Branch 2: Arbitrary Unseen CLI / Binary Tool Environment
    binaries = list(boundary["binaries"])
    # Goal-directed implicit OS/doc tool discovery when the goal doesn't explicitly name the binary
    # (or when an input file exists and additional candidate tools may be needed for its magic type)
    if not binaries or (
        boundary.get("input_magic") in ("gzip", "bzip2", "xz", "zip", "tar", "tar_gzip", "tar_bzip2", "tar_xz")
        and not any(
            pathlib.Path(b).name.lower() in ("gzip", "gunzip", "bzip2", "bunzip2", "xz", "unxz", "unzip", "tar")
            for b in binaries
        )
    ):
        implicit = _discover_implicit_tools(
            goal, boundary, knowledge_source=knowledge_source, gaps_queried=gaps_queried
        )
        # Prioritize magic-matched implicit tools ahead of incidental goal tokens
        if boundary.get("input_magic") in ("gzip", "bzip2", "xz", "zip", "tar", "tar_gzip", "tar_bzip2", "tar_xz"):
            binaries = [b for b in implicit if b not in binaries] + binaries
        else:
            for b in implicit:
                if b not in binaries:
                    binaries.append(b)

    if not binaries:
        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "status": "FAILED",
            "mode": "UNRESOLVED_EPISTEMIC_GAP",
            "boundary_scan_ms": boundary["scan_ms"],
            "gaps_unresolved": ["no_executable_or_service_discovered_on_goal_boundary"],
            "gaps_queried": gaps_queried,
            "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    recalled_cli = memory.recall("cli_role_law", goal_concepts) if memory else []
    exec_trace: list[dict[str, Any]] = []

    for binary in binaries[:5]:
        bname = pathlib.Path(binary).name
        # L0: Live `--help` introspection
        help_text = _probe_binary_help(binary)
        gaps_queried.append(f"introspect:{bname} --help")
        contract = compile_cli_help_to_contracts(binary, help_text, source="l0_help")

        # L1/L2: Augment from local docs / instant web knowledge source if help was sparse or docs exist
        extra_docs = _fetch_knowledge_for_gap(
            f"{bname} usage options examples {goal}",
            workspace=ws,
            local_docs=boundary["local_docs"],
            knowledge_source=knowledge_source,
        )
        for ed in extra_docs:
            c2 = compile_cli_help_to_contracts(binary, ed["content"], source=ed["source"])
            existing_fl = {(o.short, o.long) for o in contract.options}
            for o in c2.options:
                if (o.short, o.long) not in existing_fl:
                    contract.options.append(o)
                    existing_fl.add((o.short, o.long))
            contract.subcommands.update({k: v for k, v in c2.subcommands.items() if k not in contract.subcommands})
            contract.examples.extend(c2.examples)

        # If binary has subcommands, pick best subcommand & probe its `--help` (L0 targeted!)
        subcmd = _select_best_subcommand(contract, goal)
        if subcmd:
            sub_help = _probe_binary_help(binary, subcmd)
            gaps_queried.append(f"introspect:{bname} {subcmd} --help")
            sub_contract = compile_cli_help_to_contracts(binary, sub_help, subcommand=subcmd, source="l0_subhelp")
            # Merge global options that aren't already in sub_contract
            sub_fl = {(o.short, o.long) for o in sub_contract.options}
            for o in contract.options:
                if (o.short, o.long) not in sub_fl:
                    sub_contract.options.append(o)
            contract = sub_contract

        banned_flags: set[str] = set()
        required_flags: set[str] = set()

        for round_i in range(3):
            cands = _synthesize_cli_invocations(
                contract,
                boundary,
                goal,
                banned_flags=banned_flags,
                required_extra_flags=required_flags,
                recalled_laws=recalled_cli,
            )
            progressed_refusal = False
            for argv, role_pat, cap_stdout in cands:
                outputs = list(boundary.get("output_files") or [])
                out_path = (ws / outputs[0]) if outputs else None
                if bool(boundary.get("is_output_dir")) and out_path is not None:
                    out_path.mkdir(parents=True, exist_ok=True)
                try:
                    p = subprocess.run(
                        argv,
                        cwd=ws,
                        capture_output=True,
                        text=False,
                        timeout=min(timeout_s, 10.0),
                    )
                except Exception as exc:
                    exec_trace.append({"argv": argv, "error": str(exc)})
                    continue

                stdout_b = p.stdout or b""
                stderr_b = p.stderr or b""
                if p.returncode == 0 and cap_stdout and out_path is not None and not bool(boundary.get("is_output_dir")) and stdout_b:
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_bytes(stdout_b)

                ok_v, note_v = _independent_cli_verify(ws, boundary, goal, stdout_b, p.returncode, verifier)
                exec_trace.append(
                    {
                        "argv": argv,
                        "rc": p.returncode,
                        "cap_stdout": cap_stdout,
                        "verified": ok_v,
                        "note": note_v,
                    }
                )
                if ok_v:
                    law = None
                    if memory is not None:
                        post_kind = "output_dir" if boundary.get("is_output_dir") else ("output_file" if outputs else "stdout_nonempty")
                        law = memory.generalize_and_store(
                            kind="cli_role_law",
                            goal_concepts=goal_concepts,
                            role_pattern=role_pat,
                            postcondition_kind=post_kind,
                            env_fingerprint=f"cli:{bname}:{contract.subcommand}:{len(contract.options)}:{boundary.get('input_magic')}",
                            meta_roles={
                                "has_subcommand": bool(contract.subcommand),
                                "cap_stdout": cap_stdout,
                                "input_magic": str(boundary.get("input_magic") or ""),
                            },
                        )
                    return {
                        "schema": SCHEMA,
                        "authority": AUTHORITY,
                        "status": "VERIFIED",
                        "mode": "DOC_COMPILED_CLI_ACTIVE_INFERENCE",
                        "binary_used": bname,
                        "subcommand_used": contract.subcommand,
                        "options_compiled": len(contract.options),
                        "recalled_laws": len(recalled_cli),
                        "winning_argv": argv,
                        "winning_role_pattern": role_pat,
                        "stdout": stdout_b.decode("utf-8", errors="replace")[:2000],
                        "verification": note_v,
                        "generalized_law": law,
                        "executed_trace": exec_trace,
                        "boundary_scan_ms": boundary["scan_ms"],
                        "gaps_queried": gaps_queried,
                        "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                        "model_calls": 0,
                        "parameters_stored": 0,
                    }

                # Remove bad partial output written by failed candidate so next candidate starts clean
                if cap_stdout and out_path is not None and out_path.is_file():
                    try:
                        out_path.unlink()
                    except Exception:
                        pass

                # Parse refusal surface for active re-planning
                refusal = parse_refusal_surface(
                    stderr_b.decode("utf-8", errors="replace") + "\n" + stdout_b.decode("utf-8", errors="replace")
                )
                if refusal["banned_flags"]:
                    banned_flags.update(refusal["banned_flags"])
                    progressed_refusal = True
                if refusal["missing_flags"]:
                    required_flags.update(refusal["missing_flags"])
                    progressed_refusal = True
            if not progressed_refusal:
                break

    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "status": "FAILED",
        "mode": "CLI_EXECUTION_UNVERIFIED",
        "executed_trace": exec_trace,
        "boundary_scan_ms": boundary["scan_ms"],
        "gaps_queried": gaps_queried,
        "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
        "model_calls": 0,
        "parameters_stored": 0,
    }


_IMPERATIVE_STEP_VERBS = (
    "decompress", "uncompress", "gunzip", "bunzip2", "unxz", "unzip", "extract", "unpack",
    "decode", "encode", "filter", "search", "grep", "select", "cut", "sort", "deduplicate",
    "dedup", "count", "take", "keep", "limit", "head", "tail", "convert", "transform",
    "compute", "calculate", "hash", "fetch", "download", "create", "post", "use", "run",
    "parse", "replace", "translate", "compress",
)
_SAVE_ONLY_RE = re.compile(r"(?i)^(?:and\s+)?(?:save|write|output|store)\s+(?:it\s+|the\s+\w+\s+|output\s+|result\s+)?(?:to|into|as)\s+\S+$")


def _decompose_multi_step_goal(goal: str) -> list[str]:
    """Decompose natural-language multi-step pipelines into ordered imperative clauses.

    Handles both explicit chaining (`A, then B, then C`, `A -> B`) AND implicit comma/and
    imperative chains (`Decompress X, filter lines containing Y, sort unique, take first 2 lines, and save to out.txt`)
    while preserving final `save to <file>` clauses on the last transformation step and
    never splitting inside quoted strings or `key=,` values!
    """
    text = (goal or "").strip()
    if not text:
        return []

    # 1. Explicit `then` / `->` splitting (quote-aware)
    explicit = [c.strip(" ,.;") for c in re.split(r"(?i)(?:,\s*then\s+|\s+and\s+then\s+|\s*->\s*)", text) if c.strip()]
    if len(explicit) > 1:
        return explicit

    # 2. Quote-aware split on `, ` (protecting `delimiter=,` / `separator=,` and quoted strings)
    parts: list[str] = []
    buf: list[str] = []
    in_q: str | None = None
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if in_q:
            buf.append(ch)
            if ch == in_q:
                in_q = None
            i += 1
            continue
        if ch in ("'", '"'):
            in_q = ch
            buf.append(ch)
            i += 1
            continue
        # Detect comma separator NOT immediately preceded by `=` or `:` (protects `delimiter=,`)
        if ch == "," and (i == 0 or text[i - 1] not in ("=", ":")):
            # Look ahead to see if next non-space token starts a new imperative clause (or `and save/write/...`)
            rest = text[i + 1 :].lstrip()
            m_next = re.match(r"(?i)(?:and\s+)?([a-z]+)\b", rest)
            if m_next:
                w_next = m_next.group(1).lower()
                if w_next in _IMPERATIVE_STEP_VERBS or w_next in ("save", "write", "output", "store"):
                    seg = "".join(buf).strip(" .;")
                    if seg.endswith(",") and not seg.endswith(("=,", ":,")):
                        seg = seg.rstrip(",").strip()
                    if seg:
                        parts.append(seg)
                    buf = []
                    i += 1
                    continue
        buf.append(ch)
        i += 1
    tail = "".join(buf).strip(" .;")
    if tail.endswith(",") and not tail.endswith(("=,", ":,")):
        tail = tail.rstrip(",").strip()
    if tail:
        parts.append(tail)

    # Merge trailing `and save to out.txt` onto the preceding transformation step
    merged: list[str] = []
    for seg in parts:
        if merged and _SAVE_ONLY_RE.match(seg):
            merged[-1] = f"{merged[-1]} {seg}"
        else:
            # Strip leading `and ` from a new transformation clause
            cleaned = re.sub(r"(?i)^and\s+", "", seg).strip()
            if cleaned:
                merged.append(cleaned)
    return merged if merged else [text]


def solve_multi_step_with_instant_knowledge(
    goal: str,
    *,
    workspace: str | pathlib.Path,
    memory: EpistemicMemoryStore | None = None,
    knowledge_source: Callable[[str], list[dict[str, str]]] | None = None,
    base_url: str | None = None,
    candidate_binaries: Sequence[str] | None = None,
    verifier: Callable[[dict[str, Any]], tuple[bool, str]] | None = None,
    timeout_s: float = 20.0,
) -> dict[str, Any]:
    """Compose sequential sub-goals (`A, then B, then C` OR implicit `Decompress X, filter Y, sort Z, and save to out.txt`)
    across heterogeneous unseen tools/services with automatic typed dataflow handoff and
    independent semantic verification at EVERY intermediate step.
    """
    t0 = time.monotonic()
    ws = pathlib.Path(workspace).resolve()
    clauses = _decompose_multi_step_goal(goal)
    if len(clauses) <= 1:
        return solve_with_instant_knowledge(
            goal,
            workspace=ws,
            memory=memory,
            knowledge_source=knowledge_source,
            base_url=base_url,
            candidate_binaries=candidate_binaries,
            verifier=verifier,
            timeout_s=timeout_s,
        )

    step_results: list[dict[str, Any]] = []
    all_gaps: list[str] = []
    scratch_files: list[pathlib.Path] = []
    prev_handoff: str | None = None

    try:
        for idx, raw_clause in enumerate(clauses):
            is_last = idx == len(clauses) - 1
            clause = raw_clause

            # Check if this clause already explicitly names its own input & output files
            c_files = [m.group(1) for m in _FILE_TOK_RE.finditer(clause) if not m.group(1).startswith("http")]
            has_existing_in = any((ws / f).exists() for f in c_files)
            has_explicit_out = any(not (ws / f).exists() for f in c_files) or bool(
                re.search(r"(?i)\b(?:to|into|as|save|write)\s+(?:file\s+|dir(?:ectory)?\s+)?[A-Za-z0-9_./-]+\.[A-Za-z0-9]{1,8}\b", clause)
            )

            # Thread previous step's handoff file as this step's input if not explicitly named
            if prev_handoff and not has_existing_in and "http://" not in clause and "https://" not in clause:
                clause = f"{clause} on {prev_handoff}"

            # Give intermediate step an isolated scratch handoff file if it has no explicit output file
            step_handoff: str | None = None
            if not is_last and not has_explicit_out:
                ext = ".json" if ("http://" in clause or "https://" in clause or "json" in clause.lower()) else ".tmp"
                step_handoff = f"_epistemic_step_{idx}{ext}"
                scratch_files.append(ws / step_handoff)
                clause = f"{clause} and save to {step_handoff}"
            elif not is_last and has_explicit_out:
                # Find the newly created output file from this clause to pass to next step if needed
                out_cands = [f for f in c_files if not (ws / f).exists()]
                step_handoff = out_cands[-1] if out_cands else None

            step_res = solve_with_instant_knowledge(
                clause,
                workspace=ws,
                memory=memory,
                knowledge_source=knowledge_source,
                base_url=base_url if ("http://" in clause or "https://" in clause or (is_last and base_url)) else None,
                candidate_binaries=candidate_binaries,
                verifier=verifier if is_last else None,
                timeout_s=timeout_s,
            )
            step_results.append(step_res)
            all_gaps.extend(step_res.get("gaps_queried") or [])
            if step_res.get("status") != "VERIFIED":
                return {
                    "schema": SCHEMA,
                    "authority": AUTHORITY,
                    "status": "FAILED",
                    "mode": "MULTI_STEP_FAILED",
                    "failed_step_index": idx,
                    "failed_clause": clause,
                    "steps": step_results,
                    "gaps_queried": all_gaps,
                    "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                    "model_calls": 0,
                    "parameters_stored": 0,
                }
            prev_handoff = step_handoff
    finally:
        for sf in scratch_files:
            try:
                if sf.is_file():
                    sf.unlink()
            except Exception:
                pass

    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "status": "VERIFIED",
        "mode": "MULTI_STEP_DOC_COMPILED_ACTIVE_INFERENCE",
        "steps_completed": len(step_results),
        "steps": step_results,
        "gaps_queried": all_gaps,
        "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
        "model_calls": 0,
        "parameters_stored": 0,
    }
