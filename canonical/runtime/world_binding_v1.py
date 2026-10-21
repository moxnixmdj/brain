"""Complete a capability's inputs when the goal does not state all of them.

THE DEFECT THIS CLOSES, MEASURED NOT GUESSED.

`goal_compiler._bind_inputs` binds what the goal SAYS. Real capabilities also
ask for what the goal IMPLIES, and for that it fails closed:

    "audit the python source canonical/runtime/goal_compiler.py"
      python.source.audit.ast  -> GOAL_INPUT_BINDING_REQUIRED:source_root
      python.tests.audit.unittest -> GOAL_INPUT_BINDING_REQUIRED:pattern

Two distinct gaps, both structural:

1. KIND MISMATCH. The goal names a FILE; the placeholder wants a ROOT or a
   DIRECTORY. The value is one step away and nothing takes that step.

2. UNSTATED OUTPUT. `output_path` is a DESTINATION -- it does not exist in
   the world yet, so no amount of searching will find it. It has to be
   invented, deterministically, from the capability being called.

Failing closed is right for a value that is genuinely missing. It is wrong
for a value that is merely implied: it silently disables a capability that
was correctly chosen. And it corrupts disambiguation, because candidates are
usually ranked BEFORE binding, so several look equally good until you try to
actually call them.

THE ORDERING INSIGHT: BIND FIRST, THEN RANK.

Ambiguity is frequently an artefact of ranking unbound candidates. In the
audit example above, three capabilities match the words; only one can
actually be CALLED with what the goal provides. Bindability is the cheapest
disambiguator there is, because it costs nothing and it is decided by the
world rather than by judgement. Capabilities that cannot be invoked are not
candidates.

COMPOSITION, NOT MODIFICATION. `_bind_inputs` is verified code and is left
exactly as it is. This module consults it first and only fills what it could
not -- the same way V2 composes the cubic patch onto V1.

RULES.
  * Consult `_bind_inputs` first; its answer always wins when complete.
  * Fill only placeholders it left empty.
  * Directories come from the goal's path by promotion, never from guessing.
  * Output paths are synthesised deterministically from the capability id.
  * Anything this module cannot justify is left missing and reported, never
    invented. An invented input is an unverifiable act.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_WORLD_BINDING_V1"
ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = "canonical/astra_runtime/tmp"

# Extensions a placeholder name implies. Order matters: first match wins.
_EXT_HINTS = (
    (("pdf",), ".pdf"),
    (("docx", "word"), ".docx"),
    (("xlsx", "sheet", "workbook"), ".xlsx"),
    (("yaml", "yml"), ".yaml"),
    (("json",), ".json"),
    (("sqlite", "db", "database"), ".sqlite"),
    (("png",), ".png"),
    (("html",), ".html"),
    (("markdown", "md"), ".md"),
    (("csv",), ".csv"),
    (("tar", "archive"), ".tar.gz"),
)
_IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff")

_PLACEHOLDER_RE = re.compile(r"\$\{input\.([A-Za-z0-9_]+)\}")


def _flatten(value, out=None):
    out = [] if out is None else out
    if isinstance(value, dict):
        for v in value.values():
            _flatten(v, out)
    elif isinstance(value, (list, tuple)):
        for v in value:
            _flatten(v, out)
    elif isinstance(value, str):
        out.append(value)
    return out


def placeholders(entry):
    """The ${input.X} names an entry's action template actually needs."""
    text = " ".join(_flatten((entry or {}).get("action_template") or {}))
    return sorted(set(_PLACEHOLDER_RE.findall(text)))


_EXT_BY_TOKEN = {}
for _hints, _ext in _EXT_HINTS:
    for _h in _hints:
        _EXT_BY_TOKEN.setdefault(_h, _ext)


def _ext_for(name, cid):
    """The extension a capability's OUTPUT should carry.

    Two traps, both hit in practice:

    1. AN INPUT NAMING THE OUTPUT. `sqlite.table.create_from_json_records`
       reads json and writes sqlite, but scanning the name naively finds
       "json" first and emits a `.json` file from a sqlite writer. Tokens
       introduced by `from_` name what goes IN, and are stripped.

    2. AN EXPLICIT DESTINATION IGNORED. `yaml.to_json.yq` says where it is
       going in its own name, and that beats any positional guess.
    """
    key = str(cid or "").lower()
    explicit = re.search(r"\.to_([a-z0-9]+)", key)
    if explicit:
        mapped = _EXT_BY_TOKEN.get(explicit.group(1))
        if mapped:
            return mapped
    stripped = re.sub(r"from_[a-z0-9_]+", " ", key)
    best = None
    for hints, ext in _EXT_HINTS:
        for h in hints:
            idx = stripped.find(h)
            if idx >= 0 and (best is None or idx < best[0]):
                best = (idx, ext)
    return best[1] if best else ".json"


_DESTINATION_RE = re.compile(
    r"\b(?:to|into|onto|as)\s+([A-Za-z0-9_./-]*/[A-Za-z0-9_./-]+)", re.I)


def named_destination(goal):
    """The destination the user actually said, if they said one.

    "write X to canonical/tmp/hello.txt" names where it should go.
    Synthesising a path anyway sent the output somewhere else entirely and
    the file never appeared -- the machine looked like it had worked.
    A destination the user names always wins over one we invent; we only
    invent when they did not say.
    """
    matches = _DESTINATION_RE.findall(str(goal or ""))
    return matches[-1].strip("./") if matches else None


def synthesize_output_path(cid, name="output_path", root=None):
    """A deterministic destination for work that does not exist yet.

    Same capability, same inputs -> same path, always. Nothing here is a
    choice, so nothing here has to be defended.
    """
    root = Path(root) if root is not None else ROOT
    digest = hashlib.sha256((str(cid) + "|" + str(name)).encode("utf-8")).hexdigest()
    slug = re.sub(r"[^a-z0-9]+", "_", str(cid).lower()).strip("_")[:48]
    return str(Path(OUTPUT_DIR) / ("brain_out__" + slug + "__" + digest[:10]
                                   + _ext_for(name, cid)))


def _promote(rel, want_dir, root):
    """Take the one step the goal did not: file -> directory, or '.'."""
    if not rel:
        return "."
    p = root / rel
    if want_dir:
        if p.is_dir():
            return rel
        return str(Path(rel).parent) or "."
    return rel


def _ext_for_placeholder(name):
    """The file kind a placeholder's OWN name demands, if it names one.

    `json_path` and `xlsx_path` are different slots of the same capability.
    Binding used to look only at the capability id, and `xlsx.table.verify_
    against_json_records` mentions xlsx before json -- so the workbook was
    also handed to the JSON slot, both slots received one file, and the
    capability tried to json.loads() a binary spreadsheet:

        UnicodeDecodeError: 'utf-8' codec can't decode byte 0x8f

    A slot that names its own kind may only be filled by a file of that
    kind. Returns None when the name names no kind at all, which leaves
    every previously working binding exactly as it was.
    """
    tokens = set(re.sub(r"[^a-z0-9]+", " ", str(name or "").lower()).split())
    for hints, ext in _EXT_HINTS:
        for h in hints:
            if h in tokens:
                return ext
    return None


def _role_token(name):
    """The role a placeholder's name names. `manifest_path` wants a manifest.

    File extensions are not the only signal. `manifest_path` names no
    extension at all, and the world search duly handed it the first JSON
    manifest in the repository -- `canonical/action_intents/ACTION_INTENT_
    ...json`, unrelated to the bundle being verified -- while the manifest
    that actually described that bundle sat beside it the whole time.
    """
    low = re.sub(r"[^a-z0-9]+", "_", str(name or "").lower()).strip("_")
    for suffix in ("_path", "_file", "_root", "_dir", "_corpus", "_records"):
        if low.endswith(suffix):
            low = low[: -len(suffix)]
            break
    low = low.strip("_")
    if not low or low in {"input", "output", "source", "target", "goal", "task"}:
        return None
    return low.split("_")[0] or None


def _stem(filename):
    stem = str(filename or "")
    for sfx in (".tar.gz", ".sqlite", ".xlsx", ".docx", ".json", ".pdf"):
        if stem.lower().endswith(sfx):
            return stem[: -len(sfx)]
    return Path(stem).stem


def _stem_prefixes(filename):
    """Shared prefixes of a filename, longest first.

    `ARCHIVE_VERIFY_BUNDLE` and `ARCHIVE_VERIFY_MANIFEST` share no stem and
    no extension -- they share a project prefix. Two-token prefixes are the
    shortest admitted; a single token matches too much of a working
    directory to be evidence of anything.
    """
    stem = _stem(filename)
    parts = [x for x in re.split(r"[_\-\s]+", stem) if x]
    out = ["_".join(parts[:n]) for n in range(len(parts), 1, -1)]
    return out or [stem]


def _companion_paths(name, cid, paths, root):
    """Siblings sharing the named artifact's stem, in deterministic order.

    Artifacts travel with their source data: `FANOUT_JOIN.xlsx` sits in the
    same directory as `FANOUT_JOIN_MANIFEST.json`, and `ARCHIVE_VERIFY_
    BUNDLE.tar.gz` beside `ARCHIVE_VERIFY_MANIFEST.json`. Any JSON in the
    repository would be a guess; a sibling carrying the artifact's own stem
    is evidence. It still fails closed -- if the records do not contain the
    workbook's columns, or the members do not match, the verifier refuses --
    so a wrong companion cannot manufacture a false pass.
    """
    ext = _ext_for_placeholder(name)
    tok = _role_token(name)
    if not ext and not tok:
        return []
    out = []
    for rel in paths:
        p = root / str(rel)
        if not p.is_file():
            continue
        # Longest shared prefix first. `ARCHIVE_VERIFY_BUNDLE.tar.gz` and
        # `ARCHIVE_VERIFY_MANIFEST.json` do not share a stem -- they share a
        # project prefix, and that is the real signal that they belong to
        # the same job.
        candidates = []
        for prefix in _stem_prefixes(p.name):
            for cand in sorted(p.parent.glob(prefix + "*")):
                if cand not in candidates:
                    candidates.append(cand)
        for cand in candidates:
            if not cand.is_file():
                continue
            low = cand.name.lower()
            if not (bool(ext and low.endswith(ext)) or bool(tok and tok in low)):
                continue
            rel_cand = str(cand.relative_to(root))
            if rel_cand != str(rel) and rel_cand not in out:
                out.append(rel_cand)
    return out


def _kind_key_for(token):
    """Map a token ('manifest', 'archive', 'pdf') onto a probe kind key."""
    from canonical.runtime import world_probe_v1 as WP
    if token in WP._FILE_KINDS:
        return token
    for key in WP._FILE_KINDS:
        if key == token or key.startswith(token + ".") or key.endswith("." + token):
            return key
    return None


# Structural preference is bounded. Measured: the first file holding a record
# collection sits at sorted index 1525 of 9130 and costs 0.08s to reach, but a
# kind with no suitable file at all would otherwise parse the whole matching
# set on every bind.
_STRUCTURAL_SCAN_LIMIT = 4000
_STRUCTURAL_SCAN_MAX_BYTES = 2_000_000

# Kinds whose contents are structured data rather than an opaque blob.
_STRUCTURED_KINDS = frozenset({"json", "manifest.json", "structured.json", "trades.json"})


def _is_record_collection(data):
    """True when a JSON value holds a table of records.

    Same shape the adapters already require -- ``xlsx_table_xlsxwriter
    ._record_items`` and ``sqlite_table_stdlib._find_collection`` both accept a
    mapping whose every value is a mapping, or a list of mappings -- extended
    one level so a nested collection also counts. Nothing here is tool
    specific: this is the shape "records" means.
    """
    if isinstance(data, dict):
        if data and all(isinstance(v, dict) for v in data.values()):
            return True
        return any(_is_record_collection(v) for v in data.values())
    if isinstance(data, list):
        if data and all(isinstance(x, dict) for x in data):
            return True
        return any(_is_record_collection(v) for v in data)
    return False


def _first_with_records(rel_paths, root):
    """The first candidate that actually holds records, within a bounded scan.

    Returns None when nothing in the scanned prefix qualifies; the caller then
    falls back to the plain first match rather than refusing.
    """
    import json as _json
    scanned = 0
    for rel in rel_paths:
        if scanned >= _STRUCTURAL_SCAN_LIMIT:
            return None
        path = root / str(rel)
        try:
            if path.stat().st_size > _STRUCTURAL_SCAN_MAX_BYTES:
                continue
            data = _json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError):
            continue
        scanned += 1
        if _is_record_collection(data):
            return rel
    return None


def _world_path_for(name, cid, root):
    """Find the file the world already has, when the goal never named it.

    Perception already located this kind of file to establish the
    precondition; binding must use the same evidence rather than asking the
    user to repeat themselves. Deterministic: sorted, so the same world
    always yields the same path.

    Suffix alone is not enough for a structured kind. Measured: binding
    ``json_path`` returned ``MIGRATION_STATUS_2026-09-10.json`` purely because
    uppercase sorts first, and that file is a flat status document holding no
    records -- so a consumer that needs a table of records could never use it,
    whatever else was fixed. 3835 of the 9130 matching JSON files here do hold
    records, so preferring one is a general rule rather than a patch for one
    goal. The plain first match stays the fallback, so this can only improve
    the pick.
    """
    from canonical.runtime import world_probe_v1 as WP
    # The placeholder's own name is the stronger signal: `manifest_path`
    # must never be satisfied by the .tar.gz the capability also mentions.
    for keys in (WP.kind_keys_for(str(name)), WP.kind_keys_for(str(cid))):
        for key in sorted(keys):
            suffixes, substrings = WP._FILE_KINDS[key]
            ordered = [rel for rel in sorted(WP._index(root))
                       if WP._matches_kind(rel, suffixes, substrings)]
            if not ordered:
                continue
            if key in _STRUCTURED_KINDS:
                with_records = _first_with_records(ordered, root)
                if with_records is not None:
                    return with_records
            return ordered[0]
    return None


def _pick_path(name, cid, paths, root):
    """Choose the goal path that fits what this placeholder is for."""
    lowered = str(name).lower()
    want_dir = ("root" in lowered) or ("dir" in lowered) or ("corpus" in lowered)
    if not paths:
        return "." if want_dir else None
    if want_dir:
        for rel in paths:
            if (root / rel).is_dir():
                return rel
        # A PATH THE GOAL NAMES THAT IS NOT THERE IS A FACT, NOT A GAP.
        #
        # `audit the python source canonical/runtime/NO_SUCH_DIRECTORY_HERE`
        # was promoted to its parent and audited 2078 files the user never
        # asked about, then reported VERIFIED. The work was real and it was
        # about the wrong thing, which is worse than refusing: a refusal is
        # visible, a substitution is not.
        for rel in paths:
            if not (root / str(rel)).exists():
                return None
        return _promote(paths[0], True, root)

    # THE SLOT'S OWN NAME OUTRANKS THE CAPABILITY'S.
    #
    # `_world_path_for` already states the rule -- "the placeholder's own
    # name is the stronger signal" -- but it was only applied when the goal
    # named no path at all. When the goal named one, the capability id
    # decided, and an id mentioning xlsx before json fills both slots with
    # the same workbook. Two differently-typed slots holding one file is
    # not binding; it is duplication with the type check removed.
    wanted = _ext_for_placeholder(name)
    if wanted:
        for rel in paths:
            if str(rel).lower().endswith(wanted):
                return rel
        companion = _companion_paths(name, cid, paths, root)
        if companion:
            return companion[0]
        return None

    lowered_all = (lowered + " " + str(cid).lower())
    ext = _ext_for(name, cid)
    for rel in paths:
        low = rel.lower()
        if ext != ".json" and low.endswith(ext):
            return rel
        if "image" in lowered_all and low.endswith(_IMAGE_EXT):
            return rel
        if "source" in lowered_all and low.endswith(".py"):
            return rel
        if "test" in lowered_all and "test" in low:
            return rel
    # Same rule for a file: naming one that does not exist is not a reason
    # to hand back a different one that does.
    for rel in paths:
        if not (root / str(rel)).exists():
            return None
    return paths[0]


_TEXT_PARAM_WORDS = ("source", "code", "text", "sample", "query",
                     "expression", "program", "data", "input_text")


def _quoted_all(goal):
    """Every quoted string in the goal, in the order it was said."""
    out = []
    for pat in (r'"([^"]*)"', r"'([^']*)'"):
        out.extend(re.findall(pat, str(goal or "")))
    return out


def _quoted(goal):
    m = re.search(r'"([^"]*)"', str(goal or ""))
    if m:
        return m.group(1)
    m = re.search(r"'([^']*)'", str(goal or ""))
    if m:
        return m.group(1)
    return None


def render_args(entry, bound):
    """Substitute bound values into the template, by ARGUMENT KEY.

    The placeholder name and the argument name are NOT the same thing, and
    conflating them silently disabled most of the registry:

        {"args": {"path": "${input.docx_path}"}}

    Here the adapter reads `path`, while the placeholder is `docx_path`.
    Handing the adapter a dict keyed by placeholder name gave it `path=None`,
    and every such capability died on a path check that looked like an
    environment problem and was actually this. `python.source.audit.ast` was
    the one thing that worked, purely because its names happened to match.

    Raises on anything unbound rather than passing a None through: a missing
    argument is a fact to report, not a default to invent.
    """
    template = (entry or {}).get("action_template") or {}
    args = template.get("args")
    if not isinstance(args, dict) or not args:
        return dict(bound or {})

    def repl(match):
        key = match.group(1)
        if key not in (bound or {}):
            raise KeyError("UNBOUND_TEMPLATE_ARGUMENT:" + key)
        return str(bound[key])

    out = {}
    for key, value in args.items():
        if isinstance(value, str):
            out[key] = _PLACEHOLDER_RE.sub(repl, value)
        elif isinstance(value, (list, tuple)):
            out[key] = [_PLACEHOLDER_RE.sub(repl, v) if isinstance(v, str) else v
                        for v in value]
        else:
            out[key] = value
    return out


def complete_inputs(goal, root, entry, compiler=None, goal_paths=None):
    """Return a full input mapping for `entry`, or report exactly what is missing.

    Never returns a partially justified mapping: `missing` names every
    placeholder that could not be grounded, and the caller decides.
    """
    root = Path(root) if root is not None else ROOT
    keys = placeholders(entry)
    if not keys:
        return {"inputs": {}, "missing": [], "source": "NO_PLACEHOLDERS"}

    bound = {}
    used_compiler = False
    if compiler is not None:
        try:
            bound = dict(compiler._bind_inputs(goal, root, entry) or {})
            used_compiler = True
        except Exception:
            bound = {}

    if goal_paths is None:
        try:
            from canonical.runtime import goal_compiler as _gc
            goal_paths = [str(p[0]) for p in _gc._repo_paths(goal, root)]
        except Exception:
            goal_paths = []

    cid = str((entry or {}).get("capability_id") or "")
    filled = {}
    missing = []
    from_world = {}
    from_companion = {}
    from_demonstrated = {}
    for key in keys:
        low = key.lower()
        # A DESTINATION IS DETERMINED, NOT DISCOVERED.
        #
        # goal_compiler synthesises its own output_path first, and it has no
        # way to know what the artifact should be -- it emitted
        # `brain_out____329bc7434f.json` for a tar.gz writer, and because it
        # succeeded this module never got to correct the extension. The
        # capability determines its own artifact type; the goal cannot.
        roles = (entry or {}).get("_param_roles") or {}
        # A DESTINATION IS DETERMINED BY WHAT THE MODULE DOES, NOT BY WHAT
        # THE PARAMETER IS CALLED. `target_path` holds no "output" and so
        # was searched for in a world where it did not exist yet, leaving
        # the capability unbindable. The forge watched the module run and
        # recorded which parameters create files.
        if "output" in low or roles.get(key) == "output":
            value = named_destination(goal) or synthesize_output_path(cid, key, root)
            filled[key] = value
            continue
        if key in bound and str(bound[key]).strip():
            continue
        value = None
        if low in ("goal", "task", "objective", "query", "question", "text"):
            value = _quoted(goal)
            if value is None:
                value = str(goal or "").strip()
        elif ("path" in low) or ("file" in low) or ("root" in low) \
                or ("dir" in low) or ("corpus" in low) or low.endswith("_dir"):
            value = _pick_path(key, cid, goal_paths, root)
            # SLOTS OF ONE CAPABILITY DESCRIBE ONE JOB AND ARE BOUND JOINTLY.
            #
            # Binding each slot independently handed `archive_path` the
            # bundle and `manifest_path` a manifest from an unrelated
            # directory, then honestly reported a mismatch -- the verifier
            # was right and the binding was wrong. A slot's companion is
            # therefore sought next to what the other slots already found.
            if value is None:
                already = dict(bound)
                already.update(filled)
                pool = list(goal_paths) + [
                    str(v) for v in already.values()
                    if isinstance(v, str) and "/" in v and v not in goal_paths]
                near = _companion_paths(key, cid, pool, root)
                if near:
                    value = near[0]
                    from_companion[key] = value
            # An inference, however well founded, is shown rather than buried.
            if value is not None and value not in goal_paths \
                    and _ext_for_placeholder(key) \
                    and value in _companion_paths(key, cid, goal_paths, root):
                from_companion[key] = value
            if value is None:
                # The goal never named it. The world may already have exactly
                # one thing of this kind -- use that, and record the evidence.
                found = _world_path_for(key, cid, root)
                if found:
                    value = found
                    from_world[key] = found
        elif low in _TEXT_PARAM_WORDS:
            # A CAPABILITY WHOSE INPUT IS CODE, NOT A FILE.
            #
            # Binding only ever filled paths, so the first capability the
            # machine forged for itself -- concrete_execution_oracle, whose
            # inputs are a function and a sample -- was registered and then
            # unreachable: correct, admitted, and unusable. Quoted strings
            # are bound in the order they were said; unquoted, the slot is
            # left missing rather than guessed.
            quoted = _quoted_all(goal)
            if quoted:
                nth = sum(1 for k in filled
                          if str(k).lower() in _TEXT_PARAM_WORDS)
                value = quoted[nth] if nth < len(quoted) else None
            else:
                value = None
        elif low in ("pattern", "glob"):
            value = None
        if value is None:
            # A CAPABILITY ADMITTED BY EVIDENCE CARRIES ITS EVIDENCE.
            #
            # The binder looks for a value in the goal, then in the world.
            # A forged capability was admitted only because concrete values
            # made it run, and those values are recorded with it. When
            # neither the goal nor the world offers anything, the
            # demonstrated case is the only honest witness to what this slot
            # accepts -- better than refusing a capability that has already
            # proven it can be called. The value is reported as
            # demonstrated, never as grounded.
            demo = (entry or {}).get("_forged_defaults") or {}
            if isinstance(demo, dict) and demo.get(key) is not None:
                value = demo[key]
                from_demonstrated[key] = value
        if value:
            filled[key] = value
        else:
            missing.append(key)

    merged = dict(bound)
    merged.update(filled)
    return {
        "inputs": merged,
        "missing": missing,
        "source": "goal_compiler+world_binding" if used_compiler else "world_binding",
        "filled_by_world_binding": sorted(filled),
        "filled_from_world_not_goal": from_world,
        "filled_from_companion_not_goal": from_companion,
        "filled_from_demonstrated_case": from_demonstrated,
    }
