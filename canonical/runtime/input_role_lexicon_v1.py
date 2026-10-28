"""What a person calls a capability input, and what the registry calls that slot.

The compiler binds a slot only when the sentence contains the slot's own noun.
That is why, measured on 2754cf0, eighteen of the sixty-four verified
software-engineering capabilities could not be reached by any sentence:

    python.repo.diff_apply_full_testgate.v1   anchor_path   "the repository"
    python.review.diff_security_gate.v1       worktree_path "the worktree"
    python.contract.check.crosshair.v1        target_path   "the python module"
    python.source.symbols.resolve.v1          queries       "the symbol"
    python.source.change_impact.testselect.v1 changed_paths "the change to"
    python.refactor.extract_function.v1       end_line      "lines 5 to 9"
    python.tests.audit.unittest               pattern       "test_*.py files"

None of those is a missing ability. Each is a missing WORD: the machine knows
what an anchor is and refuses to hear "repository" for it.

This module is that word table, and only that. It is deliberately declarative:
a slot name, the phrases a sentence may introduce it with, and the KIND of
value the slot takes (a directory, an existing file, a list of files, an
identifier, a number the adapter would otherwise default). Nothing here
decides anything; the binders consult it and still fail closed when the
sentence is ambiguous.

Two laws keep it honest:

* an alias only ever ADDS a way to state a role that the sentence already
  states in another way -- a slot whose phrase is absent from the sentence is
  absent from the binding, so nothing is invented;
* the kind is a constraint, not a hint.  A directory role never binds a file,
  and an identifier role never binds a path.
"""
from __future__ import annotations

import re

SCHEMA = "PROJECT_BRAIN_INPUT_ROLE_LEXICON_V1"

# Value kinds.  These are the only four shapes the binder can act on; anything
# else is left to a specialist binder (or refused), never guessed.
KIND_DIR = "dir"
KIND_FILE = "file"
KIND_FILES = "files"
KIND_IDENT = "ident"
KIND_IDENTS = "idents"
KIND_NUMBER = "number"
KIND_TEXT = "text"
KIND_TUNING = "tuning"
# A line coordinate.  One phrase ("lines 4 to 7") states two slots, so the kind
# is about how the span is written, not about a single value.
KIND_LINE = "line"

# slot -> kind.  A slot absent from this map keeps whatever the binder already
# knew how to do with its name.
SLOT_KIND: dict[str, str] = {
    # --- coordinates a sentence states as a span ("lines 4 to 7") -----------
    "start_line": KIND_LINE,
    "end_line": KIND_LINE,
    # --- trees the machine works inside -------------------------------------
    "anchor_path": KIND_DIR,
    "worktree_path": KIND_DIR,
    "apply_directory": KIND_DIR,
    "repo_path": KIND_DIR,
    "source_root": KIND_DIR,
    "source_dir": KIND_DIR,
    "target_root": KIND_DIR,
    "scratch_root": KIND_DIR,
    "test_cwd": KIND_DIR,
    # --- one existing file the machine reads --------------------------------
    "target_path": KIND_FILE,
    "module": KIND_FILE,
    "diff_path": KIND_FILE,
    "index_path": KIND_FILE,
    "manifest": KIND_FILE,
    "task_path": KIND_FILE,
    "pr_intent_path": KIND_FILE,
    "bench_path": KIND_FILE,
    "edits_path": KIND_FILE,
    "measurement_receipt_path": KIND_FILE,
    "result_path": KIND_FILE,
    # --- lists of existing files --------------------------------------------
    "changed_paths": KIND_FILES,
    "test_paths": KIND_FILES,
    "source_paths": KIND_FILES,
    "run_tests": KIND_FILES,
    "evidence_paths": KIND_FILES,
    # --- identifiers the sentence spells ------------------------------------
    "queries": KIND_IDENTS,
    "qualname": KIND_IDENT,
    "old_symbol": KIND_IDENT,
    "new_symbol": KIND_IDENT,
    "old_param": KIND_IDENT,
    "new_param": KIND_IDENT,
    "new_name": KIND_IDENT,
    "pattern": KIND_TEXT,
    # --- execution knobs the adapter already defaults -----------------------
    # Every adapter below writes `args.get("<knob>") or <default>`, so these are
    # the adapter's business, not the caller's.  The binder used to raise on
    # them; measured, that made the type gate unreachable over one string.
    "python_executable": KIND_TUNING,
    "timeout_s": KIND_TUNING,
    "min_coverage_ratio": KIND_TUNING,
    "max_mutants": KIND_TUNING,
    "min_kill_ratio": KIND_TUNING,
    "tolerance": KIND_TUNING,
    # `ref` is a knob the ADAPTER defaults, and each verb decides what "unstated" means:
    # diff -> the unstaged changes, revert -> HEAD, checkout -> a refusal (REF_NOT_STATED).
    # Declared tuning rather than required because "Revert the last commit in <R>" is how an
    # engineer states it, and with `ref` required that sentence could not bind this
    # capability at all -- measured: it fell through to vcs.git.log.v1, a different act.
    "ref": KIND_TUNING,
    "repeats": KIND_TUNING,
    "budget": KIND_TUNING,
}

# slot -> the phrases a sentence may introduce it with.  The slot's own name is
# always also accepted (the binders add it), so these are only the words a
# person uses instead of the registry's noun.
ROLE_ALIASES: dict[str, tuple[str, ...]] = {
    # --- the git surface -------------------------------------------------------
    # "against HEAD", "at commit abc123", "the revision main": a revision is named the way
    # an engineer names it.  These four aliases exist because the capabilities that were
    # just added (vcs.git.diff/checkout/revert) need one, and a slot with no alias could only
    # be bound by its own registry spelling -- measured: the exclusion fallback assigned the
    # OUTPUT path to the slot and the request died as output_path_equals_an_input_path.
    # A BRANCH is a revision: `git checkout <branch>` and `git checkout <sha>` are one act
    # with one slot.  Declared here because a checkout sentence that names a branch and a
    # checkout sentence that names a commit are the same sentence with a different value, and
    # the earlier split (branch_name for the branch, ref for the commit) made the second one
    # unbindable, so "Check out the previous commit ..." was answered by a `git log` listing.
    "ref": ("ref", "revision", "against", "at commit", "at revision", "commit",
            "branch", "branch called", "branch named"),
    "message": ("message", "commit message", "with the message", "saying"),
    "branch_name": ("branch", "branch called", "branch named", "new branch"),
    # "the repository", "the repo", "the checkout", "the tree it was cut from"
    "anchor_path": ("repository", "repo", "git repository", "checkout", "anchor",
                    "tree", "source tree", "project"),
    "worktree_path": ("worktree", "working tree", "checkout", "repository",
                      "repo", "clone", "project"),
    "apply_directory": ("directory", "folder", "tree", "repository", "project"),
    "repo_path": ("repository", "repo", "project", "checkout"),
    "source_root": ("source tree", "sources", "source directory", "tree",
                    "directory", "folder", "project", "package", "under"),
    "test_cwd": ("working directory", "directory", "folder", "cwd"),
    # "the python module X", "the source file X", "the target X"
    "target_path": ("python module", "module", "source file", "source", "file",
                    "target", "script", "program"),
    "module": ("python module", "module", "source file", "module file", "file"),
    "diff_path": ("diff", "diff file", "patch", "patch file", "unified diff",
                  "changes", "change set", "the changes in"),
    "index_path": ("index", "symbol index", "index file"),
    "manifest": ("manifest", "case file", "case", "spec", "specification"),
    "task_path": ("task", "task file", "issue", "issue description"),
    "pr_intent_path": ("pr intent", "pull request intent", "intent", "intent file"),
    "bench_path": ("benchmark", "benchmark file", "bench", "timing script"),
    "edits_path": ("edits", "edit list", "edits file"),
    # lists
    "changed_paths": ("changed files", "changed paths", "changes to",
                      "modified files", "edited files", "the change to",
                      "touched files"),
    "run_tests": ("tests", "test suite", "test file", "test files", "suite",
                  "unit tests", "tests in", "test at"),
    "test_paths": ("tests", "test files", "test suite", "suites", "unit tests"),
    "source_paths": ("sources", "source files", "source", "the sources"),
    "evidence_paths": ("evidence", "evidence files", "evidence documents"),
    # identifiers
    "queries": ("symbol", "symbols", "name", "names", "identifier", "identifiers",
                "the symbol", "the names"),
    "qualname": ("function", "the function", "symbol", "the symbol", "method"),
    "new_symbol": ("to", "rename to", "call it", "new name"),
    "new_param": ("to", "rename to", "new name"),
    "new_name": ("named", "new name", "call it", "into a function named"),
    "pattern": ("pattern", "test pattern", "file pattern", "matching"),
    # branches
    "base_branch": ("base branch", "from branch", "off branch", "against branch"),
    "branch_name": ("branch", "branch called", "branch named", "new branch"),
    # tuning
    "timeout_s": ("timeout", "timeout seconds", "within seconds", "time limit"),
    "python_executable": ("python", "interpreter", "python binary"),
    "min_coverage_ratio": ("minimum coverage", "coverage ratio", "min coverage"),
    "max_mutants": ("max mutants", "mutant budget", "mutants"),
    "min_kill_ratio": ("kill ratio", "mutation score", "minimum kill ratio"),
    "tolerance": ("tolerance", "allowed slowdown", "within"),
    "repeats": ("repeats", "runs", "iterations"),
}

# Words that may sit between a role phrase and the path it introduces.
_CONNECTORS = (
    "the", "a", "an", "at", "in", "into", "of", "under", "within", "inside",
    "from", "to", "for", "with", "is", "named", "called", "located", "found",
    "sitting", "that", "which", "this", "its", "and", "on", "as", "file",
    "files", "directory", "folder", "tree", "path", "=", ":", ",",
)
_CONNECTOR_RE = "|".join(re.escape(w) for w in sorted(_CONNECTORS, key=len, reverse=True))

# How far back a role phrase may sit from the path it governs, in words.
_GAP_WORDS = 6


# The slots the rescue binder may fill.  An explicit allowlist, because the
# generic binder already has careful rules for `*_paths`, `*_root`, `*_dir` and
# `*_path`, and a second, looser rule beside them weakened fail-closed semantics
# that the front compiler's ambiguity tests exist to protect.  Rescue is for the
# slots measured to be unreachable, and nothing else.
RESCUE_SLOTS = frozenset({
    "anchor_path", "worktree_path", "apply_directory", "repo_path",
    "target_path", "source_root", "module", "diff_path", "index_path", "manifest",
    "queries", "pattern", "run_tests", "changed_paths", "start_line",
    "end_line", "new_name", "qualname",
})


_DISABLE = __import__("os").environ.get("BRAIN_ROLE_RESCUE_OFF") == "1"


def is_rescuable(key) -> bool:
    return (not _DISABLE) and str(key or "") in RESCUE_SLOTS


def kind_of(key) -> str | None:
    """The value kind this slot takes, or None when the binder already knows."""
    return SLOT_KIND.get(str(key or ""))


# A tuning slot that is DEFAULTED by its adapter but is still something a sentence states in
# words rather than as a number.  `ref` is the whole case: "Revert the commit 49b9ce0" states a
# revision, the adapter defaults `ref` to HEAD when it is absent, and the tuning rule (which
# binds only a stated NUMBER) therefore threw the stated commit away and reverted HEAD -- a
# different commit, silently.  Listed explicitly, because a name pattern would sweep in knobs
# whose unstated value means something.
TEXTUAL_TUNING = frozenset({"ref"})


# The revisions an engineer names without typing a sha.  Each maps to the revision the phrase
# means, so the adapter receives a revision rather than a word.  Measured: "Check out the
# previous commit in the repository R" was SKIPPED (F24) because `ref` could not be bound,
# and the sentence was then answered by `vcs.git.log.v1` -- a listing -- with a PASS, for a
# request to move HEAD.
_REVISION_PHRASES: tuple[tuple[str, str], ...] = (
    (r"\bthe previous commit\b|\bthe prior commit\b|\bthe commit before\b", "HEAD~1"),
    (r"\bthe last commit\b|\bthe latest commit\b|\bthe most recent commit\b"
     r"|\bthe head commit\b|\bhead of the branch\b", "HEAD"),
)


def revision_from_phrase(goal) -> str:
    """The revision a sentence names in words, or '' when it names none."""
    import re as _re
    text = str(goal or "")
    for pattern, revision in _REVISION_PHRASES:
        if _re.search(pattern, text, _re.I):
            return revision
    return ""


def is_textual_tuning(key) -> bool:
    """A tuning slot whose stated value is text: bound when the sentence states it."""
    return str(key or "") in TEXTUAL_TUNING


def is_tuning(key) -> bool:
    """A slot the ADAPTER itself defaults, so the sentence need not state it.

    This is an explicit list, not a name pattern.  Measured: a pattern heuristic
    ("a name starting with max_ is a knob") swallowed `max_age_s`, which is not a
    knob but the freshness window the knowledge-consistency capability is graded
    on -- the sentence states it and the binding dropped it.
    """
    return kind_of(key) == KIND_TUNING


def phrases_for(key) -> list[str]:
    """Every phrase that may introduce this slot, longest first.

    The slot's own name and its words-with-spaces form are always included, so
    a sentence that uses the registry's vocabulary keeps working unchanged.
    """
    text = str(key or "").lower().strip()
    out: list[str] = []
    for phrase in ROLE_ALIASES.get(text, ()):
        phrase = str(phrase).strip().lower()
        if phrase and phrase not in out:
            out.append(phrase)
    for phrase in (text, text.replace("_", " ")):
        if phrase and phrase not in out:
            out.append(phrase)
    out.sort(key=len, reverse=True)
    return out


def introduced_before(text: str, value: str, phrases, at: int | None = None) -> bool:
    """Does one of ``phrases`` introduce ``value`` at (or before) this mention?

    A connector run of at most ``_GAP_WORDS`` words may sit between the phrase
    and the value ("the repository **with worktree** <path>"), because that is
    how people write.  Anything longer is not this phrase governing this path.
    """
    text = str(text or "")
    if at is None:
        at = text.find(str(value))
    if at < 0:
        return False
    before = text[:at]
    gap = r"(?:\s+(?:" + _CONNECTOR_RE + r")\b){0,%d}" % _GAP_WORDS
    for phrase in phrases or ():
        words = [w for w in re.split(r"[^a-z0-9]+", str(phrase).lower()) if w]
        if not words:
            continue
        pattern = (r"(?<![a-z0-9])"
                   + r"[^a-z0-9]+".join(re.escape(w) for w in words)
                   + r"(?![a-z0-9])" + gap + r"[\s]*$")
        if re.search(pattern, before, flags=re.IGNORECASE):
            return True
    return False
