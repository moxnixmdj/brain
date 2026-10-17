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
    "authoritative": BOOL, "test_argv": ARGV, "spec": JSON_TEXT, "objective": JSON_TEXT,
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
    return UNKNOWN


# ------------------------------------------------------------------------------------ signatures

_PLACEHOLDER = re.compile(r"\$\{input\.([A-Za-z_][A-Za-z0-9_]*)\}")


def slots_of(entry: Mapping[str, Any]) -> list[str]:
    """The typed input slots a capability declares, in registry order."""
    args = ((entry.get("action_template") or {}).get("args")) or {}
    found: list[str] = []
    for key, value in args.items():
        if isinstance(value, str) and value.startswith("${input."):
            m = _PLACEHOLDER.fullmatch(value.strip())
            if m:
                found.append(m.group(1))
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
