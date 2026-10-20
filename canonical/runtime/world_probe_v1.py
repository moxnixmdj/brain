"""Perception: turn the machine's actual state into established facts.

THE DEFECT THIS CLOSES, MEASURED NOT GUESSED.

The registry is a graph: a capability PROVIDES effects and REQUIRES effects.
Planning chains provides -> requires. But 44 of the 70 registered
capabilities require at least one effect that NO registered capability
provides -- things like `pdf.file.available`, `python.source.file.available`,
`node.runtime.available`. Those are not planning steps. They are statements
about the world, and the world is the only thing that can answer them.

Nothing in the Brain answered them. `availability_v1.py` names the problem
exactly and then declines it:

    `requires` was already in the registry with a DIFFERENT meaning --
    abstract conditions like "node.runtime.available", not executables.
    Checking those against PATH would report things blocked that are not.

So it evaluates `requires_binaries` (executables on PATH) and leaves `requires`
alone. That is correct for what it does, and it leaves the senses missing.
A capability behind an unanswered precondition is dead code: never proposed,
never executed, and indistinguishable from one that does not exist.

This module is the missing half, composed alongside availability_v1 rather
than folded into it. It answers exactly one question -- "is this precondition
true of THIS machine RIGHT NOW?" -- by LOOKING.

DESIGN RULES, FROM FIRST PRINCIPLES.

1. PROBE ON DEMAND, NEVER SPECULATIVELY. Only the few effects a given goal's
   candidate capabilities actually need are decided. That is what keeps this
   in microseconds instead of walking the tree for every goal.

2. THE GOAL IS A SENSOR TOO. If the goal names a path, that path is the first
   place to look. "extract text from <pdf>" already contains the evidence.

3. FAIL CLOSED ON ANYTHING THE WORLD CANNOT DECIDEDLY ANSWER. An unrecognised
   effect is reported as NOT established, never as established. Inventing a
   fact is worse than lacking one: planning on a false fact produces work
   that no verifier objected to.

4. ZERO LEARNED BYTES, ZERO EXTERNAL CALLS. Looking at a filesystem is not
   inference. Every answer here is decidable without a model.

5. ABSENCE IS INFORMATION, the rule availability_v1 already states:
   "There is no browser on this box" is a true and useful thing for the
   machine to know about where it is. A false effect is not.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_WORLD_PROBE_V1"
ROOT = Path(__file__).resolve().parents[2]

# Trees that are never evidence of anything a user asked for.
_SKIP_DIRS = frozenset({
    ".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "dist", "build", ".next", ".cache",
    ".arena", ".tox", ".nox", ".turbo", "target", "out",
})
_MAX_INDEX = 400_000

# subject -> (suffixes, substrings_any_in_name). Empty means "any file".
_FILE_KINDS = {
    "pdf":                    ((".pdf",), ()),
    "pdf.file.image_only":    ((".pdf",), ()),
    "image":                  ((".png", ".jpg", ".jpeg", ".gif", ".bmp",
                                ".webp", ".tif", ".tiff"), ()),
    "json":                   ((".json",), ()),
    "structured.json":        ((".json",), ()),
    "trades.json":            ((".json",), ("trade",)),
    "manifest.json":          ((".json",), ("manifest",)),
    "yaml":                   ((".yaml", ".yml"), ()),
    "markdown":               ((".md", ".markdown"), ()),
    "python.source":          ((".py",), ()),
    "python.test.corpus":     ((".py",), ("test",)),
    "archive.tar_gz":         ((".tar.gz", ".tgz"), ()),
    "artifact.file":          ((), ()),
    "candidate.response_or_fields": ((".json",), ()),
}

# subject -> executable that must exist on PATH
_RUNTIME_KINDS = {
    "node": "node",
    "npm": "npm",
    "tesseract": "tesseract",
    "gnu_tar": "tar",
    "pandoc": "pandoc",
    "zbarimg": "zbarimg",
    "qrencode": "qrencode",
    "yq": "yq",
    "jq": "jq",
    "sqlite3": "sqlite3",
}

# Facts so basic they are easy to overlook and fatal to miss. The
# computer-use capabilities require `project_present` and `files_known`,
# and nothing in the registry PROVIDES either -- so without deciding them
# here, the machine could see that a file-write capability existed and
# still conclude it was not allowed to use it.
_BOOTSTRAP = {
    "project_present": lambda root, paths: bool(root) and Path(root).is_dir(),
    "files_known":     lambda root, paths: bool(paths) or any(Path(root).iterdir()),
}


def _decide_bootstrap(effect, root, goal_paths):
    rule = _BOOTSTRAP.get(str(effect or "").strip().lower())
    if rule is None:
        return None
    try:
        ok = bool(rule(root, goal_paths))
    except Exception:
        return {"true": False, "how": "bootstrap_probe_failed", "evidence": None}
    return {"true": ok, "how": "bootstrap_observed", "evidence": None}


_INDEX_CACHE: dict[str, list[str]] = {}


def _index(root: Path) -> list[str]:
    """Cached, bounded, relative-path listing of the repository tree."""
    key = str(root)
    cached = _INDEX_CACHE.get(key)
    if cached is not None:
        return cached
    found: list[str] = []
    stack = [str(root)]
    while stack:
        if len(found) >= _MAX_INDEX:
            break
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for entry in it:
                    if entry.name in _SKIP_DIRS:
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(entry.path)
                        continue
                    if entry.is_file(follow_symlinks=False):
                        found.append(os.path.relpath(entry.path, str(root)))
        except OSError:
            continue
    _INDEX_CACHE[key] = found
    return found


def _subjects(effect: str) -> list[str]:
    """Candidate subject keys for an abstract effect name."""
    e = str(effect or "").strip().lower()
    if not e.endswith(".available"):
        return []
    base = e[: -len(".available")]
    out = [base]
    for suffix in (".file", ".corpus", ".runtime", ".text"):
        if base.endswith(suffix):
            out.append(base[: -len(suffix)])
    return out


def _matches_kind(rel: str, suffixes, substrings) -> bool:
    low = rel.lower()
    name = low.rsplit("/", 1)[-1]
    if suffixes and not any(name.endswith(s) for s in suffixes):
        return False
    if substrings and not any(s in low for s in substrings):
        return False
    return True


def _decide_file(subject, goal_paths, root):
    spec = _FILE_KINDS.get(subject)
    if spec is None:
        return None
    suffixes, substrings = spec
    for rel in goal_paths:
        if _matches_kind(rel, suffixes, substrings):
            return {"true": True, "how": "goal_path", "evidence": rel}
    for rel in _index(root):
        if _matches_kind(rel, suffixes, substrings):
            return {"true": True, "how": "tree_scan", "evidence": rel}
    return {"true": False, "how": "no_matching_file", "evidence": None}


def _decide_runtime(subject, _goal_paths, _root):
    exe = _RUNTIME_KINDS.get(subject)
    if exe is None:
        return None
    hit = shutil.which(exe)
    if hit:
        return {"true": True, "how": "path_executable", "evidence": hit}
    return {"true": False, "how": "executable_absent", "evidence": exe}


def _decide_task_scalar(effect, goal, _goal_paths, _root):
    """Effects the task text itself settles, with no filesystem involved."""
    e = effect.lower()
    text = str(goal or "")
    if e.startswith("raw_task.text"):
        ok = bool(text.strip())
        return {"true": ok, "how": "goal_text_present" if ok else "goal_empty",
                "evidence": None}
    if e.startswith("typed.scalar.inputs"):
        import re as _re
        ok = bool(_re.search(r"\d", text))
        return {"true": ok, "how": "goal_has_numeric" if ok else "goal_no_numeric",
                "evidence": None}
    return None


def probe_effect(effect, goal="", goal_paths=(), root=None):
    """Decide ONE abstract precondition against the world.

    Returns a dict with 'true' (bool), 'how' (which sensor decided), and
    'evidence'. `true` is False for anything this module cannot decide -- it
    never guesses, and it never reports an undecidable effect as established.
    """
    root = Path(root) if root is not None else ROOT
    e = str(effect or "").strip()
    if not e:
        return {"true": False, "how": "empty_effect", "evidence": None}

    decided = _decide_task_scalar(e, goal, goal_paths, root)
    if decided is not None:
        return decided
    decided = _decide_bootstrap(e, root, goal_paths)
    if decided is not None:
        return decided

    for subject in _subjects(e):
        decided = _decide_file(subject, goal_paths, root)
        if decided is not None:
            return decided
        decided = _decide_runtime(subject, goal_paths, root)
        if decided is not None:
            return decided

    return {"true": False, "how": "UNDECIDABLE__NOT_ESTABLISHED", "evidence": None}


def established_facts(effects, goal="", goal_paths=(), root=None):
    """The subset of `effects` the world actually confirms right now."""
    root = Path(root) if root is not None else ROOT
    out = []
    for eff in sorted({str(x) for x in effects or ()}):
        if probe_effect(eff, goal=goal, goal_paths=goal_paths, root=root)["true"]:
            out.append(eff)
    return out


def orphan_preconditions(registry):
    """Preconditions no registered capability can produce.

    These are exactly the ones only the world can answer. Everything else is
    a planning problem; these are a perception problem.
    """
    provided = set()
    for entry in (registry or {}).values():
        provided |= {str(x) for x in (entry.get("provides") or [])}
    orphans = {}
    for cid, entry in (registry or {}).items():
        missing = sorted({str(x) for x in (entry.get("requires") or [])} - provided)
        if missing:
            orphans[str(cid)] = missing
    return orphans


# A capability announces the kind of thing it consumes, in its own name and
# in its placeholder names. If the goal names a file of a DIFFERENT known
# kind, the capability cannot run on it. That is a fact about the world, not
# a preference about ranking, so it belongs here and not in a scorer.
_KIND_TOKENS = {
    "pdf":       (".pdf",),
    "image":     (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff"),
    "png":       (".png",),
    "yaml":      (".yaml", ".yml"),
    "json":      (".json",),
    "xlsx":      (".xlsx",),
    "docx":      (".docx",),
    "sqlite":    (".sqlite", ".db"),
    "tar":       (".tar.gz", ".tgz"),
    "markdown":  (".md", ".markdown"),
    "python":    (".py",),
    "source":    (".py",),
    "ast":       (".py",),
}


def _kinds_of(text):
    """Which file kinds a string announces."""
    low = str(text or "").lower()
    return {k for k in _KIND_TOKENS if k in low}


def kind_keys_for(text):
    """Which _FILE_KINDS entries a string announces, via any dotted segment.

    Separate from _kinds_of on purpose: that one feeds CONTRADICTION, where a
    loose match would wrongly eliminate a capability. This one feeds BINDING,
    where a loose match only proposes a file that still has to fit.
    """
    import re as _re
    toks = set(_re.findall(r"[a-z0-9]+", str(text or "").lower()))
    out = set()
    for key in _FILE_KINDS:
        if any(seg in toks for seg in key.split(".")):
            out.add(key)
    return out


def _ext_kinds(rel):
    """Which file kinds a path's extension belongs to."""
    low = str(rel or "").lower()
    return {k for k, exts in _KIND_TOKENS.items() if low.endswith(tuple(exts))}


def _goal_asserted_exts(goal, paths=()):
    """The file kinds the goal's OWN words demand, by extension.

    The named paths are cut out first. `BOUND_PDF_TEXT_TEST.pdf` contains
    the word "pdf", so leaving it in made "verify the xlsx <that.pdf>"
    assert BOTH xlsx and pdf, agree with itself, and verify. A path is
    evidence about the file; only what is left is evidence about intent.
    """
    try:
        from canonical.runtime.world_binding_v1 import _EXT_BY_TOKEN
    except Exception:
        return set()
    import re as _re
    text = str(goal or "")
    for rel in paths or ():
        text = text.replace(str(rel), " ")
    tokens = set(_re.findall(r"[a-z]+", text.lower()))
    return {_EXT_BY_TOKEN[t] for t in tokens if t in _EXT_BY_TOKEN}


_INPUT_PREPOSITIONS = ("from", "using", "against", "with", "out", "off")


def _is_input_position(goal, rel):
    """A path introduced by "from" names what goes IN, not what comes out.

    "create an xlsx table from <a.json>" names two kinds and contradicts
    nothing -- one is the source and one is the product. Checking the
    assert output kind against the source path refused a perfectly good
    goal. The token that introduces a path says which one it is.
    """
    import re as _re
    text = str(goal or "")
    i = text.find(str(rel))
    if i < 0:
        return False
    words = _re.findall(r"[A-Za-z]+", text[:i])
    return bool(words) and words[-1].lower() in _INPUT_PREPOSITIONS


def goal_kind_contradiction(goal, goal_paths=()):
    """The goal names a kind, and the file it names is a different kind.

    `kind_contradiction` compares a CAPABILITY's declared kind against the
    goal's file. What it cannot see is the gap this closes: the goal says
    "verify the xlsx" and names a .pdf. No capability is contradicted --
    `pdf.extract.text.pypdf` matches that file perfectly -- so the machine
    extracted the text of a PDF and reported it as a verified xlsx. The
    two claims disagree with each other, and neither was checked against
    the other.

    When the goal's words and the goal's file disagree, that is a question
    for the user, not a choice for the machine.
    """
    asserted = _goal_asserted_exts(goal, goal_paths)
    if not asserted:
        return None
    for rel in goal_paths or ():
        if _is_input_position(goal, rel):
            continue
        low = str(rel).lower()
        if not any(low.endswith(ext) for ext in asserted):
            return {"asserted": sorted(asserted), "path": str(rel)}
    return None


def kind_contradiction(capability_id, placeholder_names=(), goal_paths=()):
    """True when the capability's declared kind cannot accept the goal's file.

    Only fires when BOTH sides are known kinds and they are disjoint. An
    unrecognised extension never causes a rejection: not knowing is not
    contradicting.
    """
    declared = _kinds_of(capability_id) | _kinds_of(" ".join(placeholder_names or ()))
    if not declared:
        return False
    for rel in goal_paths or ():
        actual = _ext_kinds(rel)
        if actual and not (declared & actual):
            return True
    return False


def needed_effects(registry, capability_ids):
    """Union of orphan preconditions for a set of candidate capabilities."""
    orphans = orphan_preconditions(registry)
    need = set()
    for cid in capability_ids or ():
        need |= set(orphans.get(str(cid)) or ())
    return need
