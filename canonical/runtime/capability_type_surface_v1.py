"""The typed capability surface: what every bound capability actually takes and returns.

Why this exists
---------------
The type knowledge for the registry's input keys used to live inside the plain-goal compiler
(`goal_front_compiler_v1`), tangled together with English parsing.  That made "can the Brain use
capability X?" a question about sentence grammars, and the answer was one bespoke grammar per
capability.

Capabilities are typed functions, not prose problems.  This module is the single authority for
their signatures.  The plain sentence is demoted to one best-effort front end over the typed
interface: where it cannot fill a slot it fails closed and *names the slot*, which is honest,
instead of routing to a capability that will then fail to execute.

Everything here is DERIVED from `BOUND_CAPABILITY_REGISTRY_V1.json`, never hand-maintained per
capability.  A slot whose type cannot be derived is typed `UNKNOWN` and reported -- never
silently guessed as STRING.

Law: TRUE_CAPABILITY_TEST_LAW_V1 section 1 defines a capability over "unseen instances of a
declared input class".  It never mentions a sentence.  This module is what makes the input class
machine-readable.
"""
from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from typing import Any, Callable, Mapping

SCHEMA = "PROJECT_BRAIN_CAPABILITY_TYPE_SURFACE_V1"
REGISTRY = Path(__file__).resolve().parents[0] / "BOUND_CAPABILITY_REGISTRY_V1.json"

# --------------------------------------------------------------------------------- type universe

PATH_FILE = "PATH_FILE"
PATH_OUTPUT = "PATH_OUTPUT"
PATH_DIR = "PATH_DIR"
PATH_LIST = "PATH_LIST"
NUMBER = "NUMBER"
NUMBER_LIST = "NUMBER_LIST"
PAIR_LIST = "PAIR_LIST"
BOOL = "BOOL"
ARGV = "ARGV"
JSON_TEXT = "JSON_TEXT"
KV = "KV"
STRING = "STRING"
UNKNOWN = "UNKNOWN"

_NUM = r"-?\d+(?:\.\d+)?"
_QUOTE_OPEN = "\"'“‘`"
_QUOTE_CLOSE = "\"'”’`"


def _quoted(text: str) -> str | None:
    text = str(text or "").strip()
    if not text:
        return None
    if text[0] in _QUOTE_OPEN:
        close = _QUOTE_CLOSE[_QUOTE_OPEN.index(text[0])]
        end = text.find(close, 1)
        if end != -1:
            return text[1:end]
    return None


def _number(text: str) -> float | None:
    m = re.match(rf"\s*({_NUM})", str(text or ""))
    if not m:
        return None
    raw = m.group(1)
    return float(raw) if "." in raw else int(raw)


def _number_list(text: str) -> list[float] | None:
    inner = re.search(r"\[([^\]]*)\]", str(text or ""))
    if not inner:
        return None
    found = re.findall(_NUM, inner.group(1))
    if not found:
        return None
    return [float(x) if "." in x else int(x) for x in found]


def _pair_list(text: str) -> list[list[float]] | None:
    """`[[100, 0.0], [300, 2.0], [500, 4.0]]` -- pixel/value anchors.

    The chart scene graph calibrates an axis from (pixel, value) PAIRS
    (`chart_raster_scene_graph_v1.calibrate_axis` unpacks two elements per point).  The old
    compiler typed these keys NUMBER_LIST, which is a type error and is why
    `chart.raster.scene_graph.v1` is selected by the router and then fails to execute.
    """
    raw = str(text or "")
    pairs = re.findall(r"\[\s*(%s)\s*,\s*(%s)\s*\]" % (_NUM, _NUM), raw)
    if not pairs:
        # a bare "[0, 1, 2]" is a number list, not anchors: fail closed rather than guess
        return None
    out = []
    for a, b in pairs:
        out.append([float(a) if "." in a else int(a), float(b) if "." in b else int(b)])
    return out


def _bool(text: str) -> bool | None:
    m = re.match(r"\s*(true|false|yes|no)\b", str(text or ""), re.I)
    return (m.group(1).lower() in ("true", "yes")) if m else None


def _kv(text: str) -> dict[str, Any] | None:
    found = re.findall(r"([A-Za-z_]\w*)\s*=\s*(-?\d+(?:\.\d+)?)", str(text or ""))
    if not found:
        return None
    out: dict[str, Any] = {}
    for k, v in found:
        out[k] = float(v) if "." in v else int(v)
    return out


def _argv(text: str) -> list[str] | None:
    q = _quoted(text)
    return shlex.split(q) if q else None


def _json_text(text: str) -> Any | None:
    q = _quoted(text)
    if q is None:
        return None
    try:
        return json.loads(q)
    except ValueError:
        return q


def _string(text: str) -> str | None:
    q = _quoted(text)
    if q is not None:
        return q
    m = re.match(r"\s*([A-Za-z0-9_.:/-]+)", str(text or ""))
    return m.group(1) if m else None


def _path_file(text: str) -> str | None:
    m = re.match(r"\s*([A-Za-z0-9_./-]+\.[A-Za-z0-9_]+)", str(text or ""))
    return m.group(1) if m else None


PARSERS: dict[str, Callable[[str], Any]] = {
    NUMBER: _number,
    NUMBER_LIST: _number_list,
    PAIR_LIST: _pair_list,
    BOOL: _bool,
    KV: _kv,
    ARGV: _argv,
    JSON_TEXT: _json_text,
    STRING: _string,
    PATH_FILE: _path_file,
    PATH_OUTPUT: _path_file,
    PATH_DIR: _string,
    PATH_LIST: _path_file,
}

# --------------------------------------------------------------------------- derivation of types

# Explicit, previously verified knowledge (lifted from goal_front_compiler_v1 verbatim).
_EXPLICIT: dict[str, str] = {
    "x_ticks": PAIR_LIST, "y_ticks": PAIR_LIST,          # was NUMBER_LIST -- a real type error
    "x_value": NUMBER, "y_value": NUMBER, "major": NUMBER, "max_age_s": NUMBER,
    # a repair-loop budget is a bounded attempt count -- a NUMBER; left UNKNOWN
    # it made software.repair.loop.cegis_hypothesis unsampleable
    "budget": NUMBER,
    "authoritative": BOOL, "test_argv": ARGV, "spec": JSON_TEXT, "objective": JSON_TEXT,
    # a slot the router cannot type is a slot the router cannot fill, and an
    # unfilled slot is a chain that never runs
    "content": STRING,
    "module_name": STRING,
    "max_mutants": NUMBER,
    "wall_budget_s": NUMBER,   # relative duration; an absolute timestamp arg
    "provenance": BOOL,        # opt-in interprocedural phase switch
    "argv": ARGV,                  # general command vector -- the universal
                                   # action primitive in any environment
    "actions": JSON_TEXT,          # browser action script, consumed by
                                   # browser_chromedriver_interact
    "variables": KV, "test_paths": PATH_LIST, "source_paths": PATH_LIST,
    "evidence_paths": PATH_LIST, "source_root": PATH_DIR,
    # declared by the registry, consumed by no adapter -- see unconsumed_slots()
    "expected_structure": JSON_TEXT,
    "candidate_response": STRING, "raw_task_text": STRING,
}

# Keys the plain-goal front end can still fill from an unquoted phrase.
_STRING_KEYS = {
    "label", "text", "prompt", "goal", "product", "version_field", "field_name",
    "expected_status", "url_key", "pattern", "jq_filter", "expression", "language",
    "url", "objective", "spec", "path", "argv",
}

# Natural-language aliases for a key (key -> phrases that may name it in a sentence).
KEY_ALIASES: dict[str, tuple[str, ...]] = {
    "jq_filter": ("jq filter", "jq_filter", "jq expression", "filter"),
    "expression": ("expression", "formula"),
    "variables": ("variables", "with variables", "where"),
    "x_value": ("x value", "x_value", "x =", "x=", "at x"),
    "y_value": ("y value", "y_value", "y =", "y=", "at y"),
    "x_ticks": ("x ticks", "x_ticks", "x axis ticks"),
    "y_ticks": ("y ticks", "y_ticks", "y axis ticks"),
    "label": ("label", "curve", "series", "legend entry"),
    "prompt": ("prompt", "question"),
    "pattern": ("pattern", "test pattern", "file pattern"),
    "test_argv": ("test argv", "test_argv", "test command", "command"),
    "objective": ("objective", "claim"),
    "spec": ("spec", "specification", "relation spec"),
    "product": ("product",),
    "major": ("major version", "major"),
    "version_field": ("version field", "version_field"),
    "field_name": ("field name", "field_name", "field"),
    "expected_status": ("expected status", "expected_status", "status"),
    "url_key": ("url key", "url_key", "state key"),
    "authoritative": ("authoritative",),
    "max_age_s": ("max age seconds", "max age", "max_age_s", "maximum age"),
}

_OUTPUT_STEMS = {"output", "result", "report", "screenshot", "image", "artifact", "destination", "dest"}

_STEM_SUFFIXES: dict[str, set[str]] = {
    "archive": {".gz", ".tgz", ".tar", ".zip"}, "tar": {".gz", ".tgz", ".tar"}, "zip": {".zip"},
    "json": {".json"}, "records": {".json"}, "manifest": {".json"}, "spec": {".json"},
    "config": {".json", ".yaml", ".yml", ".toml"}, "pdf": {".pdf"},
    "markdown": {".md", ".markdown"}, "md": {".md"}, "docx": {".docx"}, "xlsx": {".xlsx"},
    "spreadsheet": {".xlsx"}, "sqlite": {".sqlite", ".db", ".sqlite3"},
    "database": {".sqlite", ".db", ".sqlite3"}, "yaml": {".yaml", ".yml"}, "csv": {".csv"},
    "html": {".html", ".htm"}, "image": {".png", ".jpg", ".jpeg", ".webp"}, "png": {".png"},
    "screenshot": {".png", ".jpg", ".jpeg"}, "text": {".txt", ".md"},
    "source": {".py"}, "python": {".py"}, "test": {".py"},
}


def type_of(key: str) -> str:
    """Derive a slot's type from its name. `UNKNOWN` when it cannot be derived -- never a guess."""
    key = str(key or "")
    if not key:
        return UNKNOWN
    if key in _EXPLICIT:
        return _EXPLICIT[key]
    if key.endswith("_paths"):
        return PATH_LIST
    if key.endswith("_path"):
        if key.startswith("output_") or key.split("_")[0] in _OUTPUT_STEMS:
            return PATH_OUTPUT
        return PATH_FILE
    if key == "path":
        return PATH_FILE
    if key.endswith("_root"):
        return PATH_DIR
    if key.endswith("_ticks"):
        return PAIR_LIST
    if key.endswith("_value") or key.endswith("_s") or key in {"dpi", "major"}:
        return NUMBER
    if key.endswith("_list") or key.endswith("_values"):
        return NUMBER_LIST
    if key.startswith("is_") or key.startswith("has_"):
        return BOOL
    if key in _STRING_KEYS:
        return STRING
    # Suffixes observed on arguments the registry never declares but adapters read anyway.
    # Each is a real derivation from the name, not a guess: a thing called *_text_utf8 holds
    # text, a thing called *_sha256 holds a digest, a thing called *_key holds a name.
    if any(key.endswith(sfx) for sfx in ("_text", "_utf8", "_key", "_id", "_sha256",
                                         "_hash", "_hex", "_mode", "_label")):
        return STRING
    if key in {"timeout", "limit", "count", "offset", "width", "height", "dpi"}:
        return NUMBER
    if key in {"mode", "kind"}:
        return STRING
    if key == "evidence":
        return PATH_LIST
    if key == "actions":
        return JSON_TEXT
    return UNKNOWN


# ------------------------------------------------------------------------------------ signatures

_PLACEHOLDER = re.compile(r"\$\{input\.([A-Za-z_][A-Za-z0-9_]*)\}")


def _placeholders_in(value: Any) -> list[str]:
    """Every `${input.X}` mentioned anywhere inside `value`, including nested containers.

    Only looking at top-level strings loses real slots: `auto.apt.zint` passes
    `argv: ["zint", "-o", "${input.output_path}", "-d", "${input.text}"]`, which is a list,
    so the whole argument was skipped and BOTH argv and the ${input.text} inside it became
    invisible to the surface. Measured consequence: 22 of 45 capabilities that fail every
    instance do so because the adapter demands an argument the signature never carried --
    CLI_ARGV_REQUIRED, PYTHON_CODEC_CONTRACT_INCOMPLETE, NODE_CODEC_PACKAGE_ROOT_REQUIRED.
    The name of the argument key and the placeholders inside it are different things, so
    both are collected.
    """
    found: list[str] = []
    if isinstance(value, str):
        for m in _PLACEHOLDER.finditer(value):
            found.append(m.group(1))
    elif isinstance(value, Mapping):
        for item in value.values():
            found.extend(_placeholders_in(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            found.extend(_placeholders_in(item))
    return found


def slots_of(entry: Mapping[str, Any]) -> list[str]:
    """The typed input slots a capability declares, in registry order."""
    args = ((entry.get("action_template") or {}).get("args")) or {}
    found: list[str] = []
    for key, value in args.items():
        if isinstance(value, str) and value.startswith("${input."):
            m = _PLACEHOLDER.fullmatch(value.strip())
            if m:
                found.append(m.group(1))
        # a container may carry placeholders even when the argument itself is not one
        found.extend(_placeholders_in(value))
    return sorted(set(found))


def signature(entry: Mapping[str, Any]) -> dict[str, str]:
    return {slot: type_of(slot) for slot in slots_of(entry)}


def load_registry(path: str | Path | None = None) -> dict[str, Any]:
    return json.loads(Path(path or REGISTRY).read_text(encoding="utf-8"))["capabilities"]


def signatures(registry: Mapping[str, Any] | None = None) -> dict[str, dict[str, str]]:
    registry = registry if registry is not None else load_registry()
    return {cid: signature(entry) for cid, entry in registry.items()}


def unknowns(registry: Mapping[str, Any] | None = None) -> dict[str, list[str]]:
    """Slots whose type could not be derived. Empty means the surface is total."""
    out = {}
    for cid, sig in signatures(registry).items():
        bad = sorted(s for s, t in sig.items() if t == UNKNOWN)
        if bad:
            out[cid] = bad
    return out


# ----------------------------------------------------------------------------------- type checking

def check(cid_signature: Mapping[str, str], args: Mapping[str, Any]) -> list[str]:
    """Type errors in a proposed typed invocation. Empty list means the call is well-typed.

    This is the gate the plain-goal front end must pass through too: a capability is never
    invoked with a slot its type cannot accept.
    """
    errors: list[str] = []
    for slot, want in cid_signature.items():
        if slot not in args:
            errors.append(f"MISSING_SLOT:{slot}:{want}")
            continue
        value = args[slot]
        if not _accepts(want, value):
            errors.append(f"TYPE_MISMATCH:{slot}:want={want}:got={type(value).__name__}")
    for slot in args:
        if slot not in cid_signature:
            errors.append(f"UNDECLARED_SLOT:{slot}")
    return errors


def _accepts(want: str, value: Any) -> bool:
    if want in (NUMBER,):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if want in (NUMBER_LIST,):
        return isinstance(value, (list, tuple)) and all(
            isinstance(v, (int, float)) and not isinstance(v, bool) for v in value)
    if want == PAIR_LIST:
        return (isinstance(value, (list, tuple)) and len(value) >= 3 and all(
            isinstance(p, (list, tuple)) and len(p) == 2
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in p)
            for p in value))
    if want == BOOL:
        return isinstance(value, bool)
    if want == ARGV:
        return isinstance(value, (list, tuple)) and all(isinstance(v, str) for v in value)
    if want == KV:
        return isinstance(value, dict)
    if want == JSON_TEXT:
        return isinstance(value, (dict, list, str, int, float, bool)) or value is None
    if want == STRING:
        return isinstance(value, str)
    if want == PATH_LIST:
        return isinstance(value, (list, tuple)) and all(isinstance(v, str) for v in value)
    if want in (PATH_FILE, PATH_OUTPUT, PATH_DIR):
        return isinstance(value, str) and bool(value.strip())
    return False  # UNKNOWN accepts nothing: fail closed


# --------------------------------------------------------------------------------- type-directed composition

def composable(producer: Mapping[str, Any], consumer_signature: Mapping[str, str], slot: str) -> bool:
    """Can `producer`'s declared `provides` satisfy `slot` of a consumer?

    Composition is decided over TYPES, not over prose: this is what lets N typed capabilities
    cover far more than N tasks without N bespoke sentence grammars.
    """
    want = consumer_signature.get(slot)
    if want is None:
        return False
    provides = {str(p) for p in (producer.get("provides") or [])}
    produces_paths = any(p.endswith(".path") or p.endswith(".artifact") or "_path" in p for p in provides)
    if want in (PATH_FILE, PATH_OUTPUT, PATH_DIR, PATH_LIST):
        return produces_paths
    if want in (NUMBER, NUMBER_LIST, PAIR_LIST, BOOL, KV):
        return any(("value" in p or "rank" in p or "query" in p or "binding" in p or "answer" in p) for p in provides)
    if want == JSON_TEXT:
        return any(("spec" in p or "json" in p or "synthesis" in p) for p in provides)
    if want == STRING:
        return bool(provides)
    return False


# ----------------------------------------------------------------------------- surface integrity

def arg_key_map(entry: Mapping[str, Any]) -> dict[str, str]:
    """placeholder name -> the argument key the adapter actually receives.

    The registry writes `{"path": "${input.pdf_path}"}`: `pdf_path` is the name the goal must
    supply, `path` is the key the adapter reads.  Conflating them produces false defects.
    """
    args = ((entry.get("action_template") or {}).get("args")) or {}
    out: dict[str, str] = {}
    for key, value in args.items():
        if isinstance(value, str):
            m = _PLACEHOLDER.fullmatch(value.strip())
            if m:
                out[m.group(1)] = key
    return out


def unconsumed_slots(registry: Mapping[str, Any] | None = None,
                     adapters_dir: str | Path | None = None) -> dict[str, list[str]]:
    """Declared input slots whose *argument key* no adapter source mentions.

    A slot the adapter never reads is a declaration that cannot be true: the capability advertises
    an input it does not take, so binding it "succeeds" and changes nothing.  These are invisible
    to liveness (the adapter imports fine) and to reachability (the placeholder is real), so
    nothing else in the repository can see them.
    """
    import pathlib
    registry = registry if registry is not None else load_registry()
    base = pathlib.Path(adapters_dir or (Path(__file__).resolve().parents[0] / "bound_capabilities"))
    out: dict[str, list[str]] = {}
    for cid, entry in registry.items():
        mapping = arg_key_map(entry)
        if not mapping:
            continue
        adapter = str(entry.get("adapter_module") or "")
        path = base / (adapter + ".py")
        if not path.is_file():
            continue
        source = "\n".join(_closure_source(path))
        dead = sorted(slot for slot, key in mapping.items() if key not in source)
        if dead:
            out[cid] = dead
    return out


# `args.get("x")` with no second argument is a required read: the caller must supply it or the
# adapter sees None. `args.get("x", default)` is optional. `args["x"]` is required and stricter.
_RE_READ_REQUIRED = re.compile(r"""\bargs\.get\(\s*["']([A-Za-z_]\w*)["']\s*\)""")
_RE_READ_OPTIONAL = re.compile(r"""\bargs\.get\(\s*["']([A-Za-z_]\w*)["']\s*,""")
_RE_READ_SUBSCRIPT = re.compile(r"""\bargs\[\s*["']([A-Za-z_]\w*)["']\s*\]""")


def adapter_arg_reads(entry: Mapping[str, Any],
                      adapters_dir: str | None = None) -> dict[str, list[str]]:
    """Argument keys the adapter reads that the action_template never declares.

    This is the exact complement of `dead_slots`. That function proves every DECLARED slot is
    read; this one finds what is read but never DECLARED. Shipping only the first half is how
    15 capabilities came to fail every single instance with CLI_ARGV_REQUIRED,
    PYTHON_CODEC_CONTRACT_INCOMPLETE and NODE_CODEC_PACKAGE_ROOT_REQUIRED while the surface
    reported "dead slots: 0" and all its tests passed.

    `required` means the adapter reads it with no default, so a call that omits it is
    incomplete. `optional` means a default exists and omitting it is legitimate.
    """
    import pathlib
    base = pathlib.Path(adapters_dir or (Path(__file__).resolve().parents[0] / "bound_capabilities"))
    adapter = str(entry.get("adapter_module") or "")
    path = base / (adapter + ".py")
    if not path.is_file():
        return {"required": [], "optional": []}
    source = "\n".join(_closure_source(path))

    req = set(_RE_READ_REQUIRED.findall(source)) | set(_RE_READ_SUBSCRIPT.findall(source))
    opt = set(_RE_READ_OPTIONAL.findall(source))
    req -= opt  # a default anywhere makes it optional

    declared = set(((entry.get("action_template") or {}).get("args")) or {})
    return {
        "required": sorted(req - declared),
        "optional": sorted(opt - declared),
    }


def undeclared_required(registry: Mapping[str, Any] | None = None,
                        adapters_dir: str | None = None) -> dict[str, list[str]]:
    """Per capability: argument keys the adapter requires but the registry never declares."""
    registry = registry if registry is not None else load_registry()
    out: dict[str, list[str]] = {}
    for cid, entry in registry.items():
        reads = adapter_arg_reads(entry, adapters_dir)
        if reads["required"]:
            out[cid] = reads["required"]
    return out


_CLOSURE_CACHE: dict[str, tuple[str, ...]] = {}


def _closure_source(path: Path) -> tuple[str, ...]:
    """Source of `path` plus every repo-local module it transitively imports.

    Single-file inspection is wrong three times over: an adapter may delegate to a solver, import
    a helper, or reach a binary through a module it never names.  The closure cannot drift from
    the code the way a hand-written declaration does, so it is the only safe witness.
    """
    key = str(path)
    if key in _CLOSURE_CACHE:
        return _CLOSURE_CACHE[key]
    root = Path(__file__).resolve().parents[2]
    seen: list[Path] = []

    def walk(p: Path) -> None:
        p = p.resolve()
        if p in seen or not p.is_file():
            return
        seen.append(p)
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        for module, names in re.findall(
            r"^from\s+(canonical[\w.]*)\s+import\s+(\([^)]*\)|[^\n(]+)", text, re.S | re.M
        ):
            base = root / module.replace(".", "/")
            for part in names.replace("(", " ").replace(")", " ").split(","):
                part = part.split(" as ")[0].strip()
                if part:
                    walk((base / part).with_suffix(".py") if base.is_dir() else base.with_suffix(".py"))
        for module in re.findall(r"^import\s+(canonical[\w.]*)", text, re.M):
            walk((root / module.replace(".", "/")).with_suffix(".py"))

    walk(path)
    out = tuple(p.read_text(encoding="utf-8", errors="replace") for p in seen)
    _CLOSURE_CACHE[key] = out
    return out


def resolve_adapter(entry: Mapping[str, Any], root: Path | None = None) -> Path | None:
    """The adapter file a capability would actually execute, or None.

    A capability can name its implementation two ways, and they live at different
    levels of the record, which is easy to get wrong and silently under-report:
      - source.adapter_path                (a path inside the repository)
      - adapter_module  (TOP LEVEL)        (a module in bound_capabilities/)
    The second is top-level, not under source. Reading it as source.adapter_module
    reports 31 of 70 as having no implementation when the true number is 2.
    """
    root = Path(root or Path(__file__).resolve().parents[2])
    src = entry.get("source") or {}
    p = src.get("adapter_path")
    if p and (root / p).exists():
        return root / p
    m = entry.get("adapter_module") or src.get("adapter_module")
    if m:
        cand = Path(__file__).resolve().parents[0] / "bound_capabilities" / f"{m}.py"
        if cand.exists():
            return cand
    return None


def unresolvable_adapters(registry: Mapping[str, Any] | None = None,
                          root: Path | None = None) -> dict[str, str]:
    """Declared capabilities whose implementation does not exist on disk.

    These are the ones no amount of environment, typing, or domain generator can
    ever make run: they are counted in the registry and have nothing behind them.
    Empty is the only acceptable steady state.
    """
    reg = registry or load_registry()
    out: dict[str, str] = {}
    for cid, entry in reg.items():
        if resolve_adapter(entry, root) is None:
            src = entry.get("source") or {}
            out[cid] = (src.get("adapter_path")
                        or entry.get("adapter_module")
                        or src.get("adapter_module")
                        or "(none declared)")
    return out


# How an adapter CONSUMES a slot determines what a valid file for it contains.
# Guessing from the slot's name is what produced six capabilities failing
# JSONDecodeError at char 0: input_path and discovery_path contain no "json",
# so the sampler wrote prose into a file the adapter parses with json.loads.
_PARSE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("json", re.compile(r"json\.loads|json\.load\b")),
    ("yaml", re.compile(r"yaml\.safe_load|yaml\.load")),
    ("csv", re.compile(r"csv\.DictReader|csv\.reader")),
    ("toml", re.compile(r"toml\.load|tomllib\.load")),
)


def parsed_formats(entry: Mapping[str, Any],
                   registry: Mapping[str, Any] | None = None) -> dict[str, str]:
    """For each declared slot, the file format the adapter actually parses it as.

    This is a small dataflow, not a guess: bind the variable the adapter reads
    the slot into, then find how that variable is parsed. A slot the adapter
    never parses gets no format, and the sampler keeps its name-based default --
    which is right, because unparsed content is genuinely unconstrained.
    """
    path = resolve_adapter(entry)
    if path is None:
        return {}
    text = "\n".join(_closure_source(path))
    slots = set(signature(entry))
    out: dict[str, str] = {}
    for slot in slots:
        # the variable the adapter reads this slot into
        bound = re.findall(
            r"(\w+)\s*=\s*[^=\n]*?args(?:\.get)?\s*[\[(]\s*[\"']" + re.escape(slot) + r"[\"']",
            text)
        for var in bound:
            # how that variable is subsequently parsed
            for fmt, pat in _PARSE_PATTERNS:
                for m in pat.finditer(text):
                    tail = text[m.end():m.end() + 120]
                    head = text[max(0, m.start() - 120):m.start()]
                    if re.search(r"\b" + re.escape(var) + r"\b", tail + head):
                        out.setdefault(slot, fmt)
                        break
                if slot in out:
                    break
            if slot in out:
                break
    return out


def parsed_schema(entry: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """The keys an adapter reads out of a parsed document, and what it demands of them.

    Well-formed JSON is not valid JSON. Three capabilities parse and then reject:
    DECISION_SCHEMA_INVALID, EXTRACTION_SCHEMA_INVALID. The adapter states what it
    wants twice over -- in the keys it reads, and in the comparisons it makes on
    them -- so the schema is mined rather than guessed:

      var["k"]              required key
      var.get("k")          optional key
      var.get("k") != "x"   rejected unless equal to x  -> the accepted value
      var.get("k") == ""    rejected if empty           -> must be non-empty

    This is the same trick as adapter_arg_reads, one level deeper: the consumer
    of a value is the authority on what that value must be.
    """
    path = resolve_adapter(entry)
    if path is None:
        return {}
    text = "\n".join(_closure_source(path))
    formats = parsed_formats(entry)
    slots = [s for s, f in formats.items() if f == "json"]
    out: dict[str, dict[str, Any]] = {}
    for slot in slots:
        bound = re.findall(
            r"(\w+)\s*=\s*[^=\n]*?args(?:\.get)?\s*[\[(]\s*[\"']" + re.escape(slot) + r"[\"']", text)
        keys: dict[str, Any] = {}
        for var in bound:
            # the variable the parsed document lands in
            m = re.search(r"(\w+)\s*=\s*json\.loads\([^)]*" + re.escape(var), text)
            doc = m.group(1) if m else var
            for k in set(re.findall(r"\b" + re.escape(doc) + r"\s*\[\s*[\"']([\w.]+)[\"']", text)):
                keys.setdefault(k, {"required": True})
            for k in set(re.findall(r"\b" + re.escape(doc) + r"\.get\(\s*[\"']([\w.]+)[\"']", text)):
                keys.setdefault(k, {"required": False})
            # A key fed to dict() must be a mapping. Handing it a string is
            # what regressed two capabilities that had been clean:
            # "dictionary update sequence element #0 has length 1".
            for k in list(keys):
                if re.search(r"dict\(\s*" + re.escape(k) + r"\b", text) or \
                   re.search(r"\b" + re.escape(k) + r"\s*\.items\(\)", text) or \
                   re.search(r"\b" + re.escape(k) + r"\s*\.get\(\s*[\"']", text):
                    keys[k]["type"] = "dict"
            # constraints the validator states about those keys
            for k in list(keys):
                pat = (r"\b" + re.escape(doc) + r"\.get\(\s*[\"']" + re.escape(k)
                       + r"[\"']\s*(?:\)|\s*,\s*[^)]*\))\s*(==|!=)\s*[\"']([^\"']*)[\"']")
                for op, val in re.findall(pat, text):
                    keys[k]["equals" if op == "!=" else "rejects"] = val
        if keys:
            out[slot] = keys
    return out
