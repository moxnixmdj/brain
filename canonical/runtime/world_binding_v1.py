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


def _ext_for(name, cid):
    key = (str(name) + " " + str(cid)).lower()
    for hints, ext in _EXT_HINTS:
        if any(h in key for h in hints):
            return ext
    return ".json"


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


def _kind_key_for(token):
    """Map a token ('manifest', 'archive', 'pdf') onto a probe kind key."""
    from canonical.runtime import world_probe_v1 as WP
    if token in WP._FILE_KINDS:
        return token
    for key in WP._FILE_KINDS:
        if key == token or key.startswith(token + ".") or key.endswith("." + token):
            return key
    return None


def _world_path_for(name, cid, root):
    """Find the file the world already has, when the goal never named it.

    Perception already located this kind of file to establish the
    precondition; binding must use the same evidence rather than asking the
    user to repeat themselves. Deterministic: sorted, so the same world
    always yields the same path.
    """
    from canonical.runtime import world_probe_v1 as WP
    # The placeholder's own name is the stronger signal: `manifest_path`
    # must never be satisfied by the .tar.gz the capability also mentions.
    for keys in (WP.kind_keys_for(str(name)), WP.kind_keys_for(str(cid))):
        for key in sorted(keys):
            suffixes, substrings = WP._FILE_KINDS[key]
            for rel in sorted(WP._index(root)):
                if WP._matches_kind(rel, suffixes, substrings):
                    return rel
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
        return _promote(paths[0], True, root)

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
    return paths[0]


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
    for key in keys:
        if key in bound and str(bound[key]).strip():
            continue
        low = key.lower()
        value = None
        if "output" in low:
            value = synthesize_output_path(cid, key, root)
        elif low in ("goal", "task", "objective", "query", "question", "text"):
            value = _quoted(goal)
            if value is None:
                value = str(goal or "").strip()
        elif ("path" in low) or ("file" in low) or ("root" in low) \
                or ("dir" in low) or ("corpus" in low) or low.endswith("_dir"):
            value = _pick_path(key, cid, goal_paths, root)
            if value is None:
                # The goal never named it. The world may already have exactly
                # one thing of this kind -- use that, and record the evidence.
                found = _world_path_for(key, cid, root)
                if found:
                    value = found
                    from_world[key] = found
        elif low in ("pattern", "glob"):
            value = None
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
    }
