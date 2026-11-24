"""Plain goal in, verified work out -- over the whole registry, with no model.

This module adds no intelligence. It is the missing JOIN between four things
the Brain already had, none of which were connected to each other:

  plain_goal_bound_grounding   ranks which capabilities a goal's words match
  world_probe_v1               decides preconditions by LOOKING at the machine
  world_binding_v1             fills in arguments the goal only implies
  astra_runtime                invokes the adapter and refuses unknown routes

Before this, all four existed and the loop still could not close, because
each one alone is unusable:

  * grounding ranks capabilities it can never CALL -- 44 of 70 sit behind
    preconditions nothing provides, so they are scored and then discarded;
  * binding fails closed on destinations and directory roots, which the goal
    states only implicitly, so correctly-chosen capabilities are dropped;
  * invocation refuses anything not fully bound, correctly.

THE SELECTION RULE, AND WHY IT IS NOT A JUDGEMENT.

Candidates are eliminated by FACTS, never ranked by preference:

  1. PERCEPTION -- a candidate whose preconditions the world contradicts is
     not a candidate. "No node on this box" is not a low score, it is an
     absence.
  2. BINDABILITY -- a candidate that cannot be CALLED with what the goal and
     the world together provide is not a candidate. This is the ordering
     insight from world_binding_v1: bind first, then rank. Ambiguity is very
     often an artefact of ranking unbound candidates.
  3. EQUIVALENCE -- survivors that provide exactly the same effect are
     interchangeable, so the cheapest is chosen and that is not a guess.
  4. SPECIFICITY -- if one survivor's effects contain another's, the more
     specific one is chosen; it was ruled out for nobody's benefit otherwise.
  5. Otherwise the goal is genuinely ambiguous and this FAILS CLOSED, naming
     the survivors and the effects that differ. Choosing between two things
     that do different work, without evidence, is guessing with extra steps.

Step 5 is not a defect to be smoothed away. A system that says "two of these
fit and here is exactly how they differ" is more useful than one that picks
and is quietly wrong.

VERIFICATION IS NOT OPTIONAL AND IS NOT SEPARATE. `expect` lives inside the
action template, so the action and its proof are one unit. A capability that
runs and does not meet its own `expect` is a FAILURE, not a success with a
warning. Unknown `expect` types fail closed -- an unrecognised check is not a
passed check.

ZERO LEARNED BYTES, ZERO EXTERNAL LEARNED CALLS, NO MODEL, NO HAND-WRITTEN
TASK CODE. Every decision above is decidable by looking.
"""
from __future__ import annotations

import importlib.util
import pathlib
import re as _re
import re
import json
import sys
import time
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_GROUNDED_ACTION_V1"
ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "canonical" / "runtime"
REGISTRY_PATH = "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"

# How much better the best candidate must be before the system acts on it.
#
# This threshold is owned by CODE, not by a model and not by a prompt, and it
# is recorded in every receipt so the decision can be audited later. It is a
# single general confidence gate, not a per-task special case: it says only
# "when two things both fit, how much better must the better one be before we
# commit?" -- the same shape as the three confidence bands the JEV literature
# prescribes (high -> act, medium -> flag, low -> do not act and escalate).
#
# Below this margin the system does not guess. It reports the survivors and
# the effects that differ, which is a usable answer rather than a wrong one.
DECISIVE_MARGIN_RATIO = 1.25


def _load(name, filename):
    path = RUNTIME / filename
    if not path.is_file():
        raise RuntimeError("MISSING:" + filename)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _compiler():
    from canonical.runtime import goal_compiler
    return goal_compiler


def _binder():
    from canonical.runtime import capability_proposal_generators
    return capability_proposal_generators


def load_registry():
    reg_file = ROOT / REGISTRY_PATH
    snap = reg_file.with_name("BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json")
    txt = reg_file.read_text(encoding="utf-8") if reg_file.is_file() else ""
    if not txt.lstrip().startswith("{") and snap.is_file():
        txt = snap.read_text(encoding="utf-8")
    doc = json.loads(txt)
    caps = doc.get("capabilities")
    if not isinstance(caps, dict) or not caps:
        raise RuntimeError("REGISTRY_INVALID")
    caps = dict(caps)
    if snap.is_file():
        caps.update(json.loads(snap.read_text(encoding="utf-8")).get("capabilities") or {})
    # CAPABILITIES THE MACHINE ADMITTED ITSELF.
    #
    # Union, not modification: a forged capability stands or falls on the
    # same checks as the rest, and its own authority tier says plainly
    # what it does not prove. A forged capability the planner cannot reach
    # would be decoration, so it is loaded into the same registry.
    try:
        from canonical.runtime import capability_forge_v1 as FG
        forged = FG.registered()
        for cid, entry in (forged or {}).items():
            if cid in caps:
                continue
            # A MEMORY OF A TOOL THAT IS GONE IS NOT A CAPABILITY.
            #
            # The forge persists what it admits across runs. That is the point -- the machine keeps
            # what it learned. But the FILE can change underneath it: measured 2026-11-23, a room was
            # rewritten with a new function and `act` still selected the previous run's row, which
            # pointed at a function no longer in the file, and reported
            # RESEARCH_TOOL_SYMBOL_MISSING instead of doing the work.
            #
            # The premise of this whole system is that environments change. A capability survives
            # only while the world still matches it, so a forged row is offered only while the
            # function it names is still there. No content hash is consulted: an edited BODY may
            # still be the same capability, and re-admitting on every edit would forget everything
            # for no reason. The claim being checked is only the one the row actually makes -- that
            # this function, in this file, exists.
            if not _still_real(entry):
                continue
            caps[cid] = entry
    except Exception:
        pass
    return caps


def _still_real(entry) -> bool:
    """Is the function this forged row names still where the row says it is?

    Any doubt answers True: an unreadable file, an odd shape, a path outside the repository -- none
    of them are evidence that the capability is gone, and this check only exists to drop rows the
    world has clearly contradicted.
    """
    try:
        # THE ROW KEEPS THE PATH IN `provides`, AS `forged.<path>::<function>`.
        # `source` is inventory provenance (`{"origin": ...}`), not a location, so reading it here
        # silently answered "no evidence" for every row and the check never fired. Read the fields
        # the row genuinely carries.
        entry = entry or {}
        provided = (entry.get("provides") or [""])[0]
        cid = entry.get("capability_id") or ""
        if "::" not in provided:
            return True
        src, fn = provided.split("::", 1)
        src = src[len("forged."):] if src.startswith("forged.") else src
        fn = fn or cid.rsplit(".", 1)[-1]
        # A PATH THIS CANNOT READ IS NOT A PATH THAT IS GONE.
        # Only a real python tool file can be checked against its own contents; anything else (a
        # bare identifier, a non-source path, a row from another shape) is uninterpretable here,
        # and uninterpretable answers KEEP. Dropping on doubt would forget working capabilities.
        if not src.endswith(".py"):
            return True
        path = ROOT / src
        if not path.is_file():
            return False
        text = path.read_text(encoding="utf-8", errors="replace")
        import ast as _ast
        names = set()
        for node in _ast.walk(_ast.parse(text)):
            if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                names.add(node.name)
        return fn in names
    except Exception:
        return True


# A capability that reports its own outcome as unresolved or failed cannot
# be verified by any field it also carries. terminal.kstar.root.assess
# declared `output_verified == true` while returning status UNRESOLVED, and
# the machine reported VERIFIED_ACTION. Checking a declared field while
# ignoring the verdict sitting next to it is not verification.
def _lookup(result, path):
    """Read a possibly nested field: "receipt.verified".

    The computer-use adapters nest their proof under `receipt`, while the
    declared expects named top-level fields -- so a write that genuinely
    succeeded reported failure because `verified` was one level down.
    """
    cur = result
    for part in str(path or "").split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


_SELF_REPORTED_FAILURE = frozenset({
    "UNRESOLVED", "FAILED", "FAILURE", "ERROR", "REFUSED", "BLOCKED",
    "FAIL_CLOSED", "NOT_VERIFIED", "INVALID",
})


def _check_expect(expect, result):
    """Apply the template's own proof. Unknown check types FAIL, never pass."""
    if isinstance(result, dict):
        if "pass" in result and not result.get("pass"):
            return False, "SELF_REPORTED_FAILURE:pass=false"
        for key in ("status", "outcome", "result_status"):
            value = str(result.get(key) or "").strip().upper()
            if value in _SELF_REPORTED_FAILURE:
                return False, "SELF_REPORTED_FAILURE:%s=%s" % (key, value)
    if not isinstance(expect, dict) or not expect:
        # NOTHING TO PROVE IS NOT A PROOF.
        #
        # This returned `True` and the caller turned that into `status: VERIFIED_ACTION, ok: True`. Measured
        # 2026-11-23: asking for "total the amounts by region in sales.csv and write it to summary.txt" reached
        # `CAP_FS_WRITE_V1`, which declares no `expect`, wrote a file that did not contain the requested work,
        # and the run reported VERIFIED_ACTION. The aggregation never happened and summary.txt was never
        # created. A runtime that succeeds falsely is worse than one that fails, because the failure is the
        # only thing that tells you to keep working.
        #
        # A capability that declares no postcondition is EXECUTED, and its bytes are still re-read where it
        # names an artifact -- but it is not VERIFIED. The word has to mean something.
        return False, "NO_EXPECT_DECLARED__UNPROVEN"
    field = str(expect.get("field") or "")
    kind = str(expect.get("type") or "")
    value = _lookup(result, field) if isinstance(result, dict) else None
    # A RUN THAT SAYS IT FAILED DID NOT SATISFY ANY POSTCONDITION.
    #
    # MEASURED 2026-11-23. `forged.tally.total_by` declares
    # `{"field": "adapter", "type": "field_nonempty"}` -- and the forged invoker
    # sets `adapter: "forged_invoker"` on EVERY return path, including its error
    # envelope. So the postcondition held for a run whose own result was
    # `{"ok": false, "error": "FileNotFoundError: ..."}`, and the front door
    # reported VERIFIED_ACTION for arithmetic that never ran.
    #
    # This is not only about forged rows: any adapter that echoes its own name
    # can satisfy `field_nonempty:<its own name>`. The check that has to come
    # first is the result's own verdict about itself.
    if isinstance(result, dict) and result.get("ok") is False:
        reason = str(result.get("error") or result.get("why") or "UNSTATED")
        return False, "RESULT_REPORTS_FAILURE:" + reason[:120]
    if kind == "field_nonempty":
        ok = value is not None and str(value).strip() != ""
        return ok, f"{kind}:{field}"
    if kind == "field_equals":
        ok = value == expect.get("value")
        return ok, f"{kind}:{field}={expect.get('value')!r}"
    if kind == "field_truthy":
        return bool(value), f"{kind}:{field}"
    return False, "UNKNOWN_EXPECT_TYPE:" + kind


_GOAL_STOPWORDS = frozenset({
    "the", "a", "an", "to", "from", "of", "and", "or", "with", "using", "use",
    "for", "this", "that", "into", "on", "in", "by", "as", "at", "its", "it",
    "then", "into", "canonical", "runtime", "tmp",
})



# WHAT A SENTENCE ASKS FOR, IN ITS OWN WORDS. A request that names a *total* wants a number for each group;
# a request that names an *analysis* or a *report* wants prose. This is not a topic table: it is the small set
# of arithmetic words a person uses when no prose answer would satisfy them.
_WANTS_A_COMPUTED_NUMBER = ("total", "totals", "sum", "sums", "average", "mean", "median", "count")
# A REPORT ABOUT SOMETHING IS NOT THAT SOMETHING. These are the words a scan, audit or analysis answers with.
# WHAT A RESULT SAYS ABOUT ITSELF RATHER THAN ABOUT THE QUESTION. These keys are the adapter's own
# bookkeeping -- they name the adapter, the file it wrote and whether it thinks it succeeded. They are
# evidence about the RUN and never part of the ANSWER, so they must not be delivered into a file the
# user named as the destination.
_RESULT_PLUMBING = frozenset({"adapter", "capability_id", "function", "dependency", "ok",
                              "output_path", "output_sha256", "output_bytes", "output_verified"})


_REPORT_WORDS = ("analysis_model", "finding", "finding_count", "findings", "is_security_proof",
                 "violation", "violations", "diagnostic", "diagnostics", "audit_trail")


def _answers_the_arithmetic_asked(goal, result):
    """Refuse a report substituted for a computed number.

    MEASURED 2026-11-23, and this is the worst defect the round found. Asked for

        "total the amounts by region in data.csv and write it to summary.txt"

    the machine selected `python.source.taint_flow.v1` -- a SECURITY TAINT ANALYSER -- wrote its report into
    `summary.txt`, re-read those bytes from disk, confirmed the hash, and reported VERIFIED_ACTION. The file
    contained:

        {"analysis_model": "BOUNDED_NAME_BASED_DATAFLOW", "answer": "no", "files_scanned": 1,
         "finding_count": 0, "is_security_proof": false, ...}

    Every mechanism worked. The bytes were real, the hash was right, the artifact existed at the named path.
    NOTHING EVER CHECKED THAT A TAINT REPORT IS NOT A PER-REGION TOTAL. A person opening `summary.txt` would
    find a security scan of a Python file and no totals at all.

    The check is deliberately narrow: it fires only when the sentence asks for arithmetic AND the result is a
    report about something else, and it looks only at the words the report itself uses. It cannot reject a
    capability that returns a total, and it cannot reject a sentence that asked for a report.

    Returns None when nothing is wrong, or the reason.
    """
    tokens = set(_re.findall(r"[a-z]+", str(goal or "").lower()))
    if not tokens.intersection(_WANTS_A_COMPUTED_NUMBER):
        return None
    if "report" in tokens or "analysis" in tokens or "analyse" in tokens or "analyze" in tokens:
        return None                                    # a report was what was asked for
    if not isinstance(result, dict):
        return None
    keys = set(str(k).lower() for k in result.keys())
    for nested in (result.get("result"), result.get("payload"), result.get("report")):
        if isinstance(nested, dict):
            keys |= set(str(k).lower() for k in nested.keys())
    hit = keys.intersection(_REPORT_WORDS)
    if not hit:
        return None
    return "A_REPORT_ANSWERS_A_DIFFERENT_QUESTION:" + ",".join(sorted(hit)[:3])


def _independent_artifact_check(result, root):
    """Re-read what the capability claims to have produced.

    A MUTATION NO ASSERTION CAN KILL IS NOT A CHECK. Twenty-nine of the
    seventy-four capabilities declare `expect: output_verified == true`,
    and their adapters assign that literal at the end of run(). The field
    observes nothing -- it is the proposer grading its own homework, and it
    survives every perturbation of the artifact, which is the definition of
    decoration. Mutation testing calls the alternative a killed mutant: to
    kill one, an assertion must actually observe the output.

    So this re-reads the artifact from disk. The adapter cannot influence
    what comes back, which makes it the first check in the chain that is
    genuinely independent of the proposer. It is not a strong check -- it
    proves the bytes exist and match the hash the adapter declared, not
    that the work was right -- but it can fail, and the constant could not.
    """
    if not isinstance(result, dict):
        return None
    rel = None
    for key in ("output_path", "result_path"):
        v = result.get(key)
        if isinstance(v, str) and v.strip():
            rel = v.strip()
            break
    if rel is None:
        # Computer-use adapters nest their proof under `receipt`.
        receipt = result.get("receipt")
        if isinstance(receipt, dict):
            for key in ("output_path", "path"):
                v = receipt.get(key)
                if isinstance(v, str) and v.strip():
                    rel = v.strip()
                    break
    if rel is None:
        return None
    import hashlib as _hashlib
    from pathlib import Path as _Path
    target = _Path(root) / rel
    if not target.is_file():
        return (False, "ARTIFACT_MISSING:" + rel)
    try:
        data = target.read_bytes()
    except Exception as exc:
        return (False, "ARTIFACT_UNREADABLE:" + rel + ":" + type(exc).__name__)
    if not data:
        return (False, "ARTIFACT_EMPTY:" + rel)
    claim = result.get("output_sha256")
    if not isinstance(claim, str) or not claim.strip():
        receipt = result.get("receipt")
        if isinstance(receipt, dict):
            claim = receipt.get("output_sha256")
    if isinstance(claim, str) and claim.strip():
        actual = _hashlib.sha256(data).hexdigest()
        if actual.strip().lower() != claim.strip().lower():
            return (False, "ARTIFACT_SHA256_MISMATCH:" + rel)
        return (True, "ARTIFACT_REVERIFIED:" + rel)
    return (True, "ARTIFACT_PRESENT_UNHASHED:" + rel)


# A RECEIPT THAT NEVER MENTIONS THE FILE THE PERSON NAMED IS ABOUT SOMETHING ELSE.
#
# Measured 2026-11-23. The goal was
#
#     "how many rows are in /tmp/homefile.csv"
#
# and the machine ran `python.source.definition_count.v1` -- a Python SOURCE analyser -- on a
# completely different file, got 11 definitions, and reported VERIFIED_ACTION. Every check passed,
# because every check asked "did this capability produce an artifact it can vouch for" and none
# asked "is this artifact about the thing I was told to work on". The named path was dropped during
# binding (it could not be bound, so a default was used) and NOTHING DOWNSTREAM NOTICED.
#
# The fix is deliberately narrow: when the request names a file, and the receipt mentions no path at
# all that relates to that name, the receipt cannot be an answer about that file.
# The file kinds the source/analysis adapters in this registry actually open. A directory binding is
# evidence of coverage only for these; for anything else the run looked in the right place and read
# the wrong stuff.
# WHICH KINDS OF FILE A CAPABILITY ACTUALLY OPENS, read off its own name and declared provides.
#   python.source.*   -> python and text sources, never a csv
#   document.*        -> documents and pdfs
#   zip/tar/gzip      -> archives
#   (anything else)   -> unknown, so a directory binding proves nothing
_KINDS_BY_NAME = (
    ("python.source", frozenset({".py", ".pyi"})),
    ("python.tests", frozenset({".py", ".pyi"})),
    ("python.package", frozenset({".py", ".pyi", ".toml", ".cfg", ".txt"})),
    ("document.convert", frozenset({".pdf", ".md", ".html", ".docx", ".txt", ".rst"})),
    ("pdf.", frozenset({".pdf"})),
    ("archive.", frozenset({".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz"})),
    ("zip", frozenset({".zip"})),
    ("tar", frozenset({".tar", ".gz", ".tgz", ".bz2"})),
    ("csv", frozenset({".csv", ".tsv"})),
    ("xlsx", frozenset({".xlsx", ".xls", ".csv"})),
    ("sqlite", frozenset({".sqlite", ".db", ".sqlite3"})),
)


def _capability_reads_this_kind(capability_id, extension) -> bool:
    """Does this capability's own kind include files like the one named?

    Unknown kinds answer False: a directory binding is only evidence when the capability is known to
    process files of that kind, and silence is not permission.
    """
    cid = str(capability_id or "").lower()
    for prefix, kinds in _KINDS_BY_NAME:
        if prefix in cid:
            return str(extension or "").lower() in kinds
    return False


_ADAPTER_READABLE_EXTENSIONS = frozenset({".py", ".pyi", ".txt", ".json", ".md", ".rst", ".toml",
                                          ".cfg", ".ini", ".yaml", ".yml", ".csv", ".tsv"})

_PATH_IN_REQUEST = _re.compile(
    r"(?<![\w/.~-])((?:~|/|\.{1,2}/)?[\w./~-]*[\w-]+\.[A-Za-z0-9]{1,8})(?![\w/])")


def _named_paths(goal: str) -> list[str]:
    """File names a request explicitly mentions, as a person would write them."""
    out = []
    for hit in _PATH_IN_REQUEST.findall(str(goal or "")):
        hit = hit.strip()
        # a bare word with a dot is not a path: version numbers, abbreviations, "e.g"
        if "/" not in hit and len(hit.split(".")[0]) < 3:
            continue
        if hit and hit not in out:
            out.append(hit)
    return out


def _receipt_speaks_to_named_path(result, goal, bound_inputs=None,
                                  capability_id="") -> tuple[bool, str] | None:
    """Does the receipt mention the file the request named?

    Returns None when the request named no file (nothing to check), True when the receipt
    demonstrably concerns it, and False with a reason when it plainly does not.

    Deliberately conservative: a receipt is accepted if ANY path-shaped value in it shares the
    named file's basename. A capability that renames its output (report.json for data.csv) still
    passes if it records the input it read, which every honest adapter does. This check can only
    catch a receipt that says nothing about the named file at all -- the case that produced a
    certified answer about a file nobody asked for.
    """
    named = _named_paths(goal)
    if not named:
        return None
    # A RECEIPT NEED NOT QUOTE ITS INPUT -- WHAT IT WAS HANDED IS THE BETTER EVIDENCE.
    # The first version of this check demanded the receipt mention the named file, and an honest
    # capability that returns only its answer (`{"columns": ...}`) was failed for not echoing a path
    # it was correctly given. What actually matters is that the run was BOUND to the named file; a
    # receipt is then about it by construction. So the inputs are checked first, and the receipt only
    # decides the case where binding says nothing.
    handed = ""
    try:
        import json as _json2
        handed = _json2.dumps(bound_inputs or {}, default=str).lower()
    except Exception:
        handed = str(bound_inputs or "").lower()
    for name in named:
        base = name.rstrip("/").split("/")[-1].lower()
        if base and (base in handed or name.lower() in handed):
            return (True, "BOUND_TO_NAMED_PATH:" + base)
        # A SUPERSET IS COVERAGE. A capability given the DIRECTORY that contains the named file
        # (`source_root: canonical/runtime` for a goal naming `canonical/runtime/solve_v1.py`) has
        # demonstrably worked on a set that includes it. Measured 2026-11-23: this test failed an
        # honest audit of 2417 files because its receipt summarised a directory instead of echoing
        # the file. Over-broad is a different complaint from silent, and only SILENT is a false pass.
        # A DIRECTORY CONTAINS THE FILE, BUT "CONTAINS" IS NOT "WORKED ON".
        #
        # Measured 2026-11-23: asked to count rows in csvroom/people.csv, the machine bound
        # `source_root: .../csvroom`, ran a PYTHON SOURCE analyser over that directory, and reported
        # VERIFIED_ACTION. The directory does contain people.csv -- and that is precisely why a
        # directory-level binding is not evidence: it contains everything, including things this
        # capability cannot read at all. The earlier exemption (added for an honest 2417-file audit)
        # was too generous and let this false pass through.
        #
        # The smaller claim is the safe one. A containing directory counts ONLY when the named file is
        # of a kind these adapters actually process (their own declared extensions). Otherwise the
        # run said nothing about the named file, whatever directory it looked in.
        name_low = name.lower().strip("./")
        named_ext = pathlib.PurePosixPath(name_low).suffix.lower()
        for token in handed.replace('"', " ").replace(",", " ").split():
            tok = token.strip("{}[]:;'").strip("./")
            if not tok or "/" not in tok:
                continue
            if name_low.startswith(tok.rstrip("/") + "/"):
                # WHAT THIS CAPABILITY PROCESSES IS THE QUESTION -- NOT WHAT EXTENSION THE FILE HAS.
                # A Python source analyser given a directory of .py files has NOT covered a .csv that
                # happens to sit in the same folder. The first version of this exemption asked only
                # whether the extension was one "adapters read", which is a property of the registry
                # as a whole and never of the thing that actually ran. Measured 2026-11-23: that let
                # a source analyser certify a row count on a csv, twice.
                if _capability_reads_this_kind(capability_id, named_ext):
                    return (True, "BOUND_TO_CONTAINING_DIR:" + tok)
                return (False, "CONTAINING_DIR_NOT_THIS_CAPABILITY_S_KIND:" + named_ext)
    blob = ""
    try:
        import json as _json
        blob = _json.dumps(result or {}, default=str).lower()
    except Exception:
        blob = str(result or "").lower()
    for name in named:
        base = name.rstrip("/").split("/")[-1].lower()
        if not base:
            continue
        if base in blob or name.lower() in blob:
            return (True, "RECEIPT_MENTIONS_NAMED_PATH:" + base)
    return (False, "RECEIPT_SILENT_ON_NAMED_PATH:" + named[0])


def _word_tokens(text):
    return {t for t in _re.findall(r"[a-z0-9]+", str(text or "").lower())
            if len(t) >= 3}


SHELL_ROWS = frozenset({
    "shell.command.run", "cli_command.run", "shell.run", "command.run",
})


def _rows_that_can_run_a_stated_command(registry):
    """Rows whose adapter actually executes an argv this module bound.

    A sentence that STATES a command line has already said what should run. The
    only question left is which row can run it, and exactly one shape of row can:
    the ones whose adapter takes argv and hands it to a process. Everything else
    -- a git bisect, an eight-stage pipeline, a diff security gate -- would be
    answering a different request while quoting this one's words.

    Derived, not listed: a row qualifies when its action template declares an
    `argv` argument, which is the honest structural statement that this row
    consumes a command line.
    """
    out = set()
    for cid, entry in (registry or {}).items():
        if str(cid) in SHELL_ROWS:
            out.add(str(cid))
            continue
        template = entry.get("action_template") or {}
        args = template.get("args") if isinstance(template, dict) else None
        if isinstance(args, dict) and "argv" in args:
            out.add(str(cid))
    return out


def keyword_candidates(goal, registry, k=8):
    """Route on the words the grounder is structurally blind to.

    plain_goal_bound_grounding strips GENERIC ACTION VERBS -- write, read,
    create, save -- as non-distinctive, then requires a distinctive token
    to match. So a capability whose keywords ARE those words can never be
    proposed. `CAP_FS_WRITE_V1` has keywords ["write","save","create",
    "put","output"] and was unreachable: asking the machine to write a
    file returned a capability that does something else entirely.

    This is additive -- it does not replace the grounder, it sees the
    words the grounder discards.
    """
    tokens = _distinctive_goal_tokens(goal)
    if not tokens:
        return []
    scored = []
    for cid, entry in (registry or {}).items():
        words = set(_word_tokens(cid))
        for kw in (entry.get("keywords") or ()):
            words |= _word_tokens(kw)
        for eff in (entry.get("provides") or ()):
            words |= _word_tokens(eff)
        hits = tokens & words
        if hits:
            scored.append((len(hits), str(cid)))
    scored.sort(key=lambda t: (-t[0], t[1]))
    # A STATED COMMAND NARROWS THE FIELD TO ROWS THAT CAN RUN ONE.
    #
    # "run the shell command ls | head -2" states a command line (the pipeline is
    # then refused by `extract_argv`, which cannot honour it without a shell). The
    # word "head" also happens to be a keyword of
    # `git.history.bisect_regression.v1`, which requires nothing -- so when the
    # stated command was refused, that row survived and was reported as
    # VERIFIED_ACTION. Measured 2026-11-12: a request for a shell pipeline was
    # answered by bisecting this repository's history and calling it verified.
    #
    # Score cannot fix that, because the row is not wrong about the words; it is
    # wrong about the job. Once the sentence has stated a command, only a row that
    # executes commands is eligible. Nothing is invented: if no such row is a
    # candidate the list is empty and the ordinary refusal stands.
    try:
        from canonical.runtime.composer_route_v1 import states_a_command_line as _sc
        _states_command = bool(_sc(goal))
    except Exception:  # noqa: BLE001 - no parser, no narrowing
        _states_command = False
    if _states_command:
        runnable = _rows_that_can_run_a_stated_command(registry)
        scored = [row for row in scored if row[1] in runnable]
    return [{"capability_id": cid, "combined_score": float(hits) * 10.0}
            for hits, cid in scored[:k]]


def _distinctive_goal_tokens(goal):
    """Words the user actually said, minus filler."""
    out = set()
    for tok in _re.findall(r"[a-z0-9]+", str(goal or "").lower()):
        if len(tok) >= 4 and tok not in _GOAL_STOPWORDS:
            out.add(tok)
    return out


def _candidate_tokens(survivor):
    """Words a capability uses to describe itself."""
    text = (str(survivor["capability_id"]) + " "
            + " ".join(survivor.get("provides") or ())).lower()
    return {t for t in _re.findall(r"[a-z0-9]+", text) if len(t) >= 4}



_EXT_GUESS = ((".xlsx", "xlsx"), (".docx", "docx"), (".pdf", "pdf"),
              (".json", "json"), (".yaml", "yaml"), (".yml", "yaml"),
              (".sqlite", "sqlite"), (".db", "sqlite"), (".md", "markdown"),
              (".png", "image"), (".jpg", "image"), (".csv", "csv"),
              (".py", "python"), (".tar.gz", "tar"))


def _bind_inventory_param(name, goal_paths, goal):
    """Fill one required parameter of an inventory function.

    The signature tells us exactly what it needs -- which is more than the
    registry's templates do. Paths come from the goal, or from the world;
    anything else falls back to the goal text itself.
    """
    low = str(name or "").lower()
    looks_like_path = any(k in low for k in ("path", "file", "dir", "root", "src"))
    if looks_like_path:
        for ext, kind in _EXT_GUESS:
            if kind in low or ext.lstrip(".") in low:
                for rel in goal_paths:
                    if str(rel).lower().endswith(ext):
                        return rel
        for rel in goal_paths:
            return rel
        try:
            from canonical.runtime import world_binding_v1 as WB
            found = WB._world_path_for(name, "", ROOT)
            if found:
                return found
        except Exception:
            pass
        return None
    m = _re.search(r'"([^"]*)"', str(goal or ""))
    if m:
        return m.group(1)
    # A REQUEST IS NOT A VALUE. This used to return the whole goal sentence, so `CAP_FS_WRITE_V1` was given
    # `text = "total the amounts by region in sales.csv and write it to summary.txt"` and wrote exactly that
    # into a file -- then the run reported ok=True, VERIFIED_ACTION, because bytes had appeared on disk that
    # matched what the adapter said it produced. Measured 2026-11-23. The sentence a person used to describe
    # the work is never the content of the work.
    #
    # Returning None makes the caller refuse the binding instead of inventing one, which is the same ruling
    # this repository has applied to universes, pages and manuals: no supplied value, no answer.
    return None


def _try_bridge(goal, root, goal_paths, started):
    """Escalate to the inventory. Never replaces a verified capability.

    The result carries its TIER and is never marked verified: the evidence
    file calls itself "not a true capability receipt", and a tier is a
    statement about whether a test named the function -- not about whether
    this answer is right.
    """
    try:
        from canonical.runtime import module_bridge_v1 as MB
    except Exception:
        return None
    try:
        cands = MB.candidates(goal, k=3)
    except Exception:
        return None
    for entry in cands:
        inputs = {}
        missing = []
        for param in (entry.get("required") or []):
            value = _bind_inventory_param(param, goal_paths, goal)
            if value is None or str(value).strip() == "":
                missing.append(param)
            else:
                inputs[param] = value
        if missing:
            continue
        try:
            result = MB.invoke(entry, inputs, root)
        except Exception:
            continue
        # "IT RETURNED" IS NOT "IT WORKED".
        #
        # The bridge hands back whatever the inventory produced and calls it
        # an unverified result. But a run that reports its own failure, or
        # that reports finding nothing, is not an answer at all -- and the
        # seed values that produced it came from the goal, so a failing run
        # was being offered as the machine's response to the goal. The two
        # predicates the forge already uses decide it; a failing run falls
        # through to the next candidate instead of being returned.
        try:
            from canonical.runtime import capability_forge_v1 as FG
            if isinstance(result, dict) and (FG.is_vacuous(result)
                                             or FG.self_reported_failure(result)):
                continue
        except Exception:
            pass
        # It ran once. That is the moment to make it permanent: either it
        # survives the forge and becomes a capability this machine holds,
        # or the refusal is recorded so the next goal does not repeat an
        # attempt that already failed. Until now the bridge re-derived the
        # same unverified answer every time and remembered none of it.
        forge_outcome = None
        try:
            from canonical.runtime import capability_forge_v1 as FG
            if not FG.was_refused(entry):
                rep = FG.forge_and_record(entry, root, seed_cases=[inputs])
                forge_outcome = {"admitted": bool(rep.get("admitted")),
                           "capability_id": rep.get("capability_id"),
                           "checks": rep.get("checks") or {},
                           "reasons": list(rep.get("reasons") or [])[:3]}
            else:
                forge_outcome = {"admitted": False, "checks": {},
                                "reasons": ["ALREADY_REFUSED__NOT_RETRIED"]}
        except Exception as exc:
            forge_outcome = {"admitted": False, "checks": {},
                                "reasons": ["FORGE_RAISED:" + type(exc).__name__]}
        return {
            "schema": SCHEMA,
            "ok": False,
            "status": "UNVERIFIED_INVENTORY_RESULT",
            "goal": goal,
            "capability_id": "module_fn." + entry["source_rel"] + "." + entry["function"],
            "source": "MODULE_INVENTORY",
            "inputs": inputs,
            "result": result if isinstance(result, (dict, list, str, int, float, bool)) or result is None else repr(result),
            "tier": entry.get("tier"),
            "passing_cases": entry.get("passing_cases"),
            "authority": ("NONE__SANDBOX_MEASUREMENT_OF_EXISTING_TESTS"
                          "_NOT_A_TRUE_CAPABILITY_RECEIPT"),
            "forge_outcome": forge_outcome,
            "remembered": bool(forge_outcome and forge_outcome.get("admitted")),
            "executed": True,
            "verified": False,
            "expect": "NO_EXPECT_DECLARED__TIER_IS_NOT_VERIFICATION",
            "total_ms": round((time.perf_counter() - started) * 1000.0, 2),
        }
    return None


def _resolve_goal_relative_paths(args, root):
    """A bare filename in a goal belongs to the goal's world, not to the repo root.

    MEASURED 2026-11-23: asking "total the amounts by region in data.csv ..." in a
    directory that CONTAINS `data.csv` bound the input as the bare string `"data.csv"`,
    and the adapter joined it to the REPOSITORY root -- where no such file exists -- and
    died on `FileNotFoundError`. Binding had already read the file successfully; the
    path was then thrown away and re-derived somewhere else.

    Only names that are (a) relative, (b) not found from the repo root, and (c) found
    under the goal's root are rewritten, so an absolute path and a repository path both
    behave exactly as before.
    """
    if not isinstance(args, dict) or root is None:
        return args
    out = dict(args)
    try:
        here = pathlib.Path(root)
    except Exception:
        return out
    for key, val in list(out.items()):
        if not isinstance(val, str) or not val.strip():
            continue
        if "://" in val or val.startswith(("/", "~")):
            continue
        cand = here / val
        try:
            if not cand.is_file():
                continue
        except Exception:
            continue
        try:
            if (ROOT / val).is_file():
                continue
        except Exception:
            pass
        out[key] = str(cand)
    return out


def act(goal, root=None, registry=None, verbose=False, memory=True,
        established_effects=(), extra_paths=(), bridge=True,
        computer_use=True, prefer=None):
    """`established_effects` and `extra_paths` are how one step feeds the next.

    A caller chaining steps passes what earlier steps PROVIDED and the paths
    they wrote. Both are treated as already true, because a plan is allowed
    to rely on its own earlier steps -- that is what makes a chain plannable
    before anything runs.
    """
    """Turn one plain sentence into one executed, verified capability call."""
    root = Path(root) if root is not None else ROOT
    started = time.perf_counter()
    EXP = None
    if memory:
        try:
            from canonical.runtime import experience_v1 as EXP
        except Exception:
            EXP = None
    registry = dict(registry if registry is not None else load_registry())
    # ENGINEERING WAS WALLED OFF. The 70-capability registry contains no
    # CAP_* entries at all, so the loop could inspect the machine but
    # could not write a file or run a program. The computer-use family
    # already existed, verified and zero-spend; it simply had not been
    # joined to the planner. Union, not modification.
    if computer_use:
        try:
            from canonical.runtime import h100_computer_use_registry_v1 as CU
            for cid, entry in (CU.bound_entries() or {}).items():
                if isinstance(entry, dict) and cid not in registry:
                    merged = dict(entry)
                    merged.setdefault("platforms", ["linux"])
                    registry[cid] = merged
        except Exception:
            pass

    from canonical.runtime import world_probe_v1 as WP
    from canonical.runtime import world_binding_v1 as WB

    gc = _compiler()
    binder = _binder()
    grounding_mod = _load("pgbg_action",
                          "bound_capabilities/plain_goal_bound_grounding.py")

    admissible = gc._platform_admissible_registry(registry)

    t0 = time.perf_counter()
    grounding = grounding_mod.ground(
        goal, admissible, compiler=gc, proposal_binder=binder,
        root=root, enforce_bindability=False,
    )
    ground_ms = (time.perf_counter() - t0) * 1000.0

    try:
        goal_paths = [str(p[0]) for p in gc._repo_paths(goal, root)]
    except Exception:
        goal_paths = []
    # Paths this step's OWN words name. Kept separate because a prior
    # step's output is an OFFER, not a CONSTRAINT: handing a .json from
    # step one to a docx capability made it look like a kind contradiction
    # and got the right capability rejected before it could be considered.
    own_paths = list(goal_paths)
    for extra in (extra_paths or ()):
        if str(extra) not in goal_paths:
            goal_paths.append(str(extra))

    # THE GOAL'S WORDS AGAINST THE FILE IT NAMES, BEFORE ANYTHING ELSE.
    #
    # "verify the xlsx <a.pdf>" names two things that disagree. Every
    # capability check that follows compares a capability to the file, and
    # on those terms pdf.extract.text.pypdf is a perfect match -- so the
    # machine read a PDF and called it a verified xlsx. Neither claim was
    # ever checked against the other, and both were satisfied.
    # THE SAME QUESTION ABOUT EXISTENCE, BEFORE ANYTHING IS BOUND.
    #
    # `world_binding_v1._pick_path` already refuses to bind a path the goal names that is
    # not there -- "a path the goal names that is not there is a fact, not a gap" -- but a
    # refusal is silent, and the fallbacks below it (a recorded demonstration, then a world
    # search) treat an unbound slot as an absence of opinion. Measured 2026-11-01:
    # `audit the python source canonical/runtime/NO_SUCH_DIRECTORY_HERE` was bound to
    # `canonical/runtime`, audited 2,078 files nobody asked for, and reported
    # VERIFIED_ACTION. The fact has to be answered above the fallbacks, not inside one.
    if not extra_paths:
        absent = WB.stated_paths_absent_in_workspace(goal, root, own_paths)
        if absent:
            return {
                "schema": SCHEMA, "ok": False,
                "status": "REFUSED__STATED_PATH_ABSENT_IN_THE_WORKSPACE",
                "goal": goal, "capability_id": None,
                "inputs": None, "selected_because": None,
                "absent_paths": absent[:3],
                "provides": [], "expect": None, "result": None,
                "error": None, "executed": False, "verified": False,
                "survivors": [], "rejected": [],
                "reason": "THE_GOAL_NAMES_A_PATH_THIS_MACHINE_DOES_NOT_HAVE",
            }
    if not extra_paths:
        clash = WP.goal_kind_contradiction(goal, own_paths)
        if clash:
            return {
                "schema": SCHEMA, "ok": False,
                "status": "REFUSED__GOAL_KIND_CONTRADICTS_NAMED_FILE",
                "goal": goal, "capability_id": None,
                "inputs": None, "selected_because": None,
                "asserted_kinds": clash["asserted"],
                "named_path": clash["path"],
                "provides": [], "expect": None, "result": None,
                "error": None, "executed": False, "verified": False,
                "survivors": [], "rejected": [],
                "why": "GOAL_KIND_CONTRADICTS_NAMED_FILE",
                "ground_ms": round((time.perf_counter() - started) * 1000.0, 2),
                "total_ms": round((time.perf_counter() - started) * 1000.0, 2),
            }

    orphans = WP.orphan_preconditions(admissible)

    survivors = []
    rejected = []
    seen = set()
    merged = list(grounding.get("clauses") or [])
    # Escalate to the keyword route only when the primary one is thin.
    # Running it unconditionally added candidates everywhere and cost a
    # completed chain to fresh ambiguity -- a second opinion is for when
    # the first has little to say, not a permanent extra voice.
    if sum(len(c.get("candidates") or []) for c in merged) < 2:
        extra = keyword_candidates(goal, admissible)
        if extra:
            merged = merged + [{"candidates": extra}]

    # A REMEMBERED PROCEDURE IS A CANDIDATE, NOT A DECISION.
    #
    # `recall_resolution` below can only choose among survivors the router has already
    # narrowed to, so it can never reach a task the router missed -- measured: it fires
    # (`selected_because: REMEMBERED_RESOLUTION`) and changes nothing. A learned procedure
    # that cannot rescue a miss is not learning, it is a tie-break.
    #
    # So the memory is injected HERE, before the loop, where every candidate is put through
    # the same precondition probe, the same kind-contradiction check and the same binding as
    # anything the grounder proposed. That is what makes it safe to generalise the match: a
    # looser match costs a failed verification, never a wrong answer, because the candidate
    # still has to earn its place.
    #
    # It is also why learning is restricted to VERIFIED receipts (procedure_memory_v1.learn):
    # a failure teaches nothing here, and would only add a candidate that fails again.
    if EXP is not None:
        try:
            from canonical.runtime import procedure_memory_v1 as _PM
            _remembered = _PM.recall_many(goal)
            if _remembered:
                merged = merged + [{"candidates": [
                    {"capability_id": r["capability_id"],
                     "combined_score": round(float(r["similarity"]), 4) * 10.0}
                    for r in _remembered if r.get("capability_id")]}]
        except Exception:
            pass

    # A FORGED CAPABILITY IS REGISTERED BUT NEVER PROPOSED.
    #
    # The same wall the computer-use family hit: the grounder scores
    # candidates it knows, so a capability added after the fact is in the
    # registry and out of reach, which is the same as absent. concrete_
    # execution_oracle was admitted, verified, and never once appeared
    # among the survivors. Being a candidate is not being chosen -- it
    # still has to bind, run, and verify like anything else.
    try:
        from canonical.runtime import capability_forge_v1 as FG
        forged_ids = sorted((FG.registered() or {}))
    except Exception:
        forged_ids = []
    if forged_ids:
        have = {str(c.get("capability_id"))
                for cl in merged for c in (cl.get("candidates") or [])}
        goal_low = str(goal or "").lower()
        # A CAPABILITY ID CANNOT BE UTTERED. The score below used to be
        # `100.0 if cid.lower() in goal_low else 0.0`, and an id is
        # `forged.tally.total_by` -- dotted, underscored, and containing a
        # path. No sentence a person writes contains that string, so EVERY
        # forged row scored 0.0 and the zero-score filter then dropped it
        # from the survivor set. Measured 2026-11-23: `forged.tally.total_by`
        # bound to the real `data.csv` (`missing: []`) and still lost to a
        # security taint analyser because its score was 0.000.
        #
        # A capability declares its own keywords. Those ARE utterable, and
        # they are what the row says it is for -- so read them instead of
        # asking whether a dotted identifier appears in a sentence.
        def _forged_score(cid: str) -> float:
            entry = admissible.get(cid)
            if not isinstance(entry, dict):
                return 0.0
            # ONE COMMON WORD IS NOT EVIDENCE, AND A PATH SEGMENT IS NOT A WORD.
            #
            # Measured 2026-11-23: "find all files larger than one megabyte" matched
            # `forged.tally.total_by` on the single keyword `by` -- a stopword, and part of
            # "larger than" -- giving an unrelated csv tool an 11.1 score, which then won a task
            # about file sizes. A forged row's keywords include the path it was discovered in
            # (`astra`, `canonical`, `discover1`, `py`, `runtime`, `tmp`), and those say where the
            # file lives, not what it does.
            _STOP = {"by", "a", "an", "the", "of", "to", "in", "on", "for", "and", "or", "with",
                     "from", "is", "it", "this", "that", "as", "at", "be"}
            _PLACE = {"astra", "canonical", "runtime", "tmp", "py", "v1", "brain", "src",
                      "tests", "test", "discover1", "code"}
            words = [str(w).lower() for w in (entry.get("keywords") or []) if w]
            words = [w for w in words if w not in _STOP and w not in _PLACE and len(w) > 2]
            if not words:
                return 0.0
            hits = sum(1 for w in words if w in goal_low)
            if hits < 2:
                return 0.0
            return round(100.0 * hits / float(len(words)), 4)
        pending = [{"capability_id": cid, "combined_score": _forged_score(cid)}
                   for cid in forged_ids if cid not in have]
        if pending:
            merged = merged + [{"candidates": pending}]
    for clause in merged:
        for cand in (clause.get("candidates") or []):
            cid = str(cand.get("capability_id") or "")
            if not cid or cid in seen:
                continue
            seen.add(cid)
            entry = admissible.get(cid)
            if not isinstance(entry, dict):
                rejected.append({"capability_id": cid, "why": "NOT_REGISTERED"})
                continue
            # The registry keys capabilities by id; the entry itself does not
            # carry one. Passing the raw entry downstream meant every
            # synthesised output came out as `brain_out____<hash>.json` --
            # empty slug, wrong extension -- because the capability id was
            # never there to derive them from.
            entry = dict(entry)
            entry.setdefault("capability_id", cid)

            # 1a-prior. MEMORY. A capability this machine has already
            # proved it cannot run is not a candidate. This is the whole
            # point of remembering: the second question should not cost
            # what the first one already paid to find out.
            if EXP is not None and EXP.is_suppressed(cid):
                rejected.append({"capability_id": cid,
                                 "why": "REMEMBERED_HARM_ON_THIS_MACHINE"})
                continue

            # 1a. KIND CONTRADICTION -- the capability announces what it
            # consumes; the goal names a file of a different known kind.
            # "run ocr on X.png" cannot be served by a PDF-only extractor.
            # This is a fact, so it eliminates; it does not down-rank.
            if WP.kind_contradiction(cid, WB.placeholders(entry), own_paths,
                                      declared_kinds=entry.get("declares") or ()):
                rejected.append({"capability_id": cid,
                                 "why": "INPUT_KIND_CONTRADICTS_GOAL_FILE",
                                 "goal_paths": own_paths})
                continue

            # 1a-bis. ENTITY CONTRADICTION -- the row counts one kind of thing and the
            # sentence asks for another. `kind_contradiction` above compares the FILE the
            # sentence names; this compares the ENTITY it asks about, which is the axis a
            # "count" question varies along and that nothing was checking.
            #
            # Measured 2026-11-12: eight different counting questions about one file --
            # if statements, functions, lines, classes, imports, comments, todos,
            # characters -- all returned VERIFIED_ACTION carrying the SAME number, 28.
            # Each was a correct answer to a question nobody asked.
            if WP.entity_contradiction(cid, goal):
                rejected.append({"capability_id": cid,
                                 "why": "ENTITY_ASKED_FOR_IS_NOT_WHAT_THIS_COUNTS",
                                 "asked": sorted(WP.countable_entities_in(goal))})
                continue

            # 1b. PERCEPTION
            already = set(str(x) for x in (established_effects or ()))
            need = [e for e in (orphans.get(cid) or []) if e not in already]
            t1 = time.perf_counter()
            facts = WP.established_facts(need, goal=goal,
                                         goal_paths=goal_paths, root=root)
            probe_ms = (time.perf_counter() - t1) * 1000.0
            if len(facts) != len(need):
                blocked = sorted(set(need) - set(facts))
                rejected.append({"capability_id": cid,
                                 "why": "PRECONDITION_NOT_TRUE_OF_WORLD",
                                 "blocked": blocked, "probe_ms": round(probe_ms, 2)})
                continue

            # 2. BINDABILITY
            t1 = time.perf_counter()
            binding = WB.complete_inputs(goal, root, entry, compiler=gc,
                                         goal_paths=goal_paths)
            bind_ms = (time.perf_counter() - t1) * 1000.0
            if binding["missing"]:
                rejected.append({"capability_id": cid,
                                 "why": "NOT_CALLABLE_WITH_WHAT_GOAL_PROVIDES",
                                 "missing": binding["missing"],
                                 "bind_ms": round(bind_ms, 2)})
                continue

            survivors.append({
                "capability_id": cid,
                "inputs": binding["inputs"],
                "provides": sorted({str(x) for x in (entry.get("provides") or [])}),
                "cost": float(entry.get("cost", 1) or 1),
                "score": float(cand.get("combined_score") or 0.0),
                "probe_ms": round(probe_ms, 2),
                "bind_ms": round(bind_ms, 2),
                "entry": entry,
            })

    # 3/4/5. selection: equivalence, specificity, margin, then refusal.
    chosen = None
    why = None
    margin = None
    # A MACRO IS AN OFFER, NEVER A CONSTRAINT.
    #
    # `prefer` carries the capability a remembered plan used for this
    # shape of clause. It is honoured only if that capability is still a
    # survivor -- still perceived, still bindable, still with its
    # preconditions met. If the world changed, preference is dropped and
    # selection proceeds exactly as it would have. It changes which
    # capability is chosen; it never changes whether the result is checked.
    if prefer and survivors:
        for cand in survivors:
            if cand["capability_id"] == str(prefer):
                chosen, why = cand, "REMEMBERED_MACRO"
                break
    if survivors and chosen is None and EXP is not None and len(survivors) > 1:
        # MEMORY BREAKS TIES. IT DOES NOT OVERRULE EVIDENCE.
        #
        # This block used to run unconditionally over every survivor, so a remembered route won whenever it
        # appeared -- regardless of what the current measurement said. Measured 2026-11-23 on the request
        # "git status", where the fresh evidence was unambiguous and in the opposite direction:
        #
        #     git.repository.operate.v1        28.14   <- the capability that HAS a status operation
        #     git.history.bisect_regression.v1  18.64   <- remembered from an earlier run
        #     chosen: git.history.bisect_regression.v1   why: REMEMBERED_PROCEDURE
        #
        # The lower-scoring row won and reported VERIFIED_ACTION, because it answered "which commit made this
        # slower" to a sentence about the working tree. A memory that outranks fresh measurement makes the
        # machine unable to improve: every mistake it ever records becomes permanent, and one bad run is
        # enough to fix a wrong route in place.
        #
        # So a remembered route is taken only when the measurement has NOT already decided. If the fresh
        # evidence is decisive, memory is not consulted at all.
        #
        # "DECISIVE" IS THE MODULE'S OWN CONSTANT, not a number chosen to make a test pass. `DECISIVE_MARGIN
        # _RATIO` already governs whether two scores are meaningfully apart for the ambiguity gate below; the
        # same question is being asked here. Measured 2026-11-23 on the two cases that fixed the rule:
        #
        #     "git status"              margin 1.501  -> decisive; remembering the bisect row here is the bug
        #     "convert a docx to text"  margin 1.003  -> a near-tie; memory is exactly what should break it
        #
        # The first version of this fix ignored the margin and simply required the remembered row to be
        # top-scoring, which killed a legitimate single-experience rescue: one taught run on "convert a docx
        # to text" no longer transferred to "turn a docx document into text", because the three docx rows sit
        # 0.06 apart and the remembered one is not the highest. Suppressing memory on a near-tie throws away
        # the one thing that resolves it.
        def _best(surv):
            return max(surv, key=lambda s: (s.get("score") or 0.0, -float(s.get("cost") or 0.0)))

        _top = _best(survivors)
        _top_score = _top.get("score") or 0.0
        _others = sorted((s.get("score") or 0.0) for s in survivors if s is not _top)
        _runner = _others[-1] if _others else 0.0
        # WHAT MAKES A REMEMBERED ROUTE TRUSTWORTHY IS SIMILARITY, NOT THE LEXICAL MARGIN.
        #
        # `procedure_memory_v1.similarity` is Jaccard over the question's signature components, and that
        # module says exactly what it is for: "Only used to RANK candidates, never to decide." It answers a
        # different question from the capability scores -- IS THIS THE SAME PROCEDURE BEING ASKED FOR -- and
        # that is the question that matters here.
        #
        # Measured 2026-11-23 on the two cases that set the rule:
        #     taught "git status", asked "show me the last five git commits"        similarity 0.143
        #     taught "convert a docx to text", asked "turn a docx document into text" similarity 0.500
        # The first is a different question that shares the word "git"; the second is the same task in other
        # words. A margin threshold cannot tell them apart -- it was tried and both are near-ties -- but
        # similarity separates them by more than three times.
        _decisive_id = None
        # A REMEMBERED ROUTE IS ALSO SUBJECT TO "DOES IT PROVIDE WHAT WAS ASKED FOR".
        # Otherwise memory is a second door into the same defect, and a worse one: it is the door that gets
        # easier to walk through every time the machine is wrong.
        remembered = EXP.recall_resolution(goal)
        if remembered:
            for s in survivors:
                # AN EXACT-SIGNATURE HIT IS NOT A SIMILARITY CLAIM. `recall_resolution` matches the question's
                # signature character for character, so it does not need to outscore anything -- and requiring
                # it to was the first version's bug: it narrowed `survivors` to the top row and destroyed the
                # very lookup that answers an exact repeat.
                if s["capability_id"] == remembered and (_decisive_id is None or s["capability_id"] == _decisive_id):
                    chosen, why = s, "REMEMBERED_RESOLUTION"
                    break
        if chosen is None:
            try:
                from canonical.runtime import procedure_memory_v1 as _PM
                # `recall` ALREADY REFUSES A WEAK MATCH: its own floor is 0.5, and a different question that
                # shares a word scores below that (measured 2026-11-23: "count the lines in a file" against a
                # taught "count the words in a file" is 0.333 and is not returned). A second threshold here
                # was written and then removed the same day: a mutant deleting it changed no test, because it
                # could never fire. Redundant guards are not safety; they are code that looks like safety.
                proc_hit = _PM.recall(goal)
                if proc_hit and proc_hit.get("capability_id"):
                    for s in survivors:
                        if s["capability_id"] == proc_hit["capability_id"]:
                            # A REMEMBERED ROUTE MAY NOT OUTRULE A DECISIVELY BETTER ONE.
                            #
                            # The rule three paragraphs above applies to `recall_resolution` and was
                            # not applied here, so this second memory door had exactly the defect it
                            # was written to close. Measured 2026-11-23, after a false pass was fixed
                            # at the verdict: the machine had "learned" that
                            # "count the rows in the csv <path>" was answered by a PYTHON SOURCE
                            # analyser (it had certified that run before the fix). The corrected
                            # forge then produced a real `count_rows` at 42.86 against the analyser's
                            # 17.62 -- and the remembered, wrong, now-failing route won anyway.
                            #
                            # Memory is for resolving near-ties and for repeating a good decision. It
                            # is not evidence, and it must not survive fresh measurement that
                            # contradicts it by the module's own decisive margin.
                            # WHY A REMEMBERED ROUTE IS ALLOWED TO SURVIVE A HIGHER-SCORING RIVAL.
                            #
                            # I first wrote the opposite rule here: if the top rival outscored the
                            # remembered route by the module's decisive ratio (1.25), memory would
                            # yield. Measured, it was wrong in both directions and for the same
                            # reason -- word agreement is not fit.
                            #
                            #   count_rows 42.86 vs source analyser 17.62  (ratio 2.43) -- memory
                            #     SHOULD yield; the remembered route was a false pass. The ratio
                            #     suppressed it: right answer, wrong reason.
                            #   pandoc_weasyprint 36.39 vs pypdf 28.39      (ratio 1.28) -- memory
                            #     should NOT yield; pypdf is the only route that can extract text
                            #     from a pdf, and a markdown->pdf converter merely mentions pdf.
                            #     The ratio suppressed it and broke an honest case.
                            #   tree_sitter vs python.source.audit.ast (the ast paraphrases) -- the
                            #     ratio suppressed memory on four rows that memory had been getting
                            #     right and that no fit argument condemned.
                            #
                            # No threshold separates these, because the scores measure how many goal
                            # words a capability's prose contains, and every one of the bad rivals is
                            # a capability that PRODUCES the very kind the goal asks to CONSUME.
                            # That is a fact about fit, and it is now checked directly: the kind
                            # gate (INPUT_KIND_CONTRADICTS_GOAL_FILE) eliminates a producer offered a
                            # consumer's job before scoring is consulted at all. Measured with this
                            # rule removed and the kind gate in place, every case above is correct --
                            # csv 3 rows, README unresolved, pdf remembered, all ast rows remembered.
                            #
                            # So memory keeps the decision, and the fit check does the vetoing. A
                            # numeric threshold here would be a second, weaker copy of a question
                            # already answered better elsewhere.
                            chosen, why = s, "REMEMBERED_PROCEDURE"
                            break
            except Exception:
                pass
    if survivors and chosen is None:
        # A ZERO-SCORE ROW MAY NOT GATE A MATCHED ONE.
        # A forged capability is appended with combined_score 0.0 so it can be
        # proposed when nothing else fits. It must not survive INTO the ambiguity
        # gate, where its mere presence turns a decisive match into AMBIGUOUS.
        _positive = [s for s in survivors if (s.get("score") or 0.0) > 0.0]
        if _positive:
            survivors = _positive
        else:
            # A ROW THAT SCORED ZERO HAS SAID IT MATCHES NOTHING IN THIS SENTENCE.
            #
            # Measured 2026-11-23, after forged rows became scoreable: asked to "count the lines in
            # README.md", every legitimate candidate was correctly refused
            # (INPUT_KIND_CONTRADICTS_GOAL_FILE -- they are Python auditors, not line counters) and
            # `forged.tally.total_by` was the only survivor left, at 0.0. `len(survivors) == 1` then
            # chose it as UNIQUE_SURVIVOR, it was handed a README as if it were a csv, and the run
            # reported ACTION_FAILED with the ARITHMETIC credited to a tool that had already denied
            # being relevant. A zero score is a refusal, not a tie to be broken.
            return {
                "schema": SCHEMA,
                "ok": False,
                "status": "UNRESOLVED",
                "goal": goal,
                "survivors": [{k: v for k, v in s2.items() if k != "entry"}
                              for s2 in survivors],
                "rejected": rejected,
                "why": "EVERY_SURVIVOR_SCORED_ZERO__NONE_MATCHES_THIS_SENTENCE",
                "margin": margin,
                "decisive_margin_ratio": DECISIVE_MARGIN_RATIO,
                "executed": False,
                "verified": False,
                "total_ms": round((time.perf_counter() - started) * 1000.0, 2),
            }
        if len(survivors) == 1:
            # BEING THE ONLY SURVIVOR IS NOT A REASON TO BE BELIEVED -- but it is not a reason to be refused
            # either, and this round tried three times to build a scorer that could tell the difference.
            #
            # The case that started it: "show me the last five git commits" left
            # `git.history.bisect_regression.v1` alone, and it answered with a perf-regression report while
            # reporting VERIFIED_ACTION. The fix that WORKED is not here -- it is in `world_binding_v1`,
            # where the operation is now read from `composer_route_v1.git_argv`, a prose->command reader this
            # repository has had since 2026-10-31. With the right operation bindable the right capability
            # competes and wins, and the survivor is no longer alone.
            #
            # What was tried here and removed the same afternoon, each caught by a measurement:
            #   1. count keyword overlap  -> the QR generator declares no keywords, so a QR READER beat it
            #   2. match on prefixes      -> "code" matched `code128`; 45 unrelated rows became "better"
            #   3. exact stems + a floor  -> lost the token "qr" to a length cutoff and failed the same way
            # Each was a ranking invented on the spot to replace evidence the machine already had. THE BEST
            # PART IS NO PART: a lone survivor is taken, and what stops a wrong claim is the VERIFICATION
            # below, not a guess made before running anything.
            chosen = survivors[0]
            why = "UNIQUE_SURVIVOR"
        else:
            provs = [tuple(s["provides"]) for s in survivors]
            if len(set(provs)) == 1:
                chosen = sorted(survivors, key=lambda s: (s["cost"], s["capability_id"]))[0]
                why = "EFFECT_EQUIVALENT_CHEAPEST"
            else:
                ranked = sorted(survivors, key=lambda s: (-s["score"], s["capability_id"]))
                top, second = ranked[0], ranked[1]
                margin = round(top["score"] / second["score"], 4) if second["score"] else None
                for a in survivors:
                    if any(set(b["provides"]) < set(a["provides"]) for b in survivors if b is not a):
                        chosen = a
                        why = "MORE_SPECIFIC_EFFECTS"
                        break
                # THE USER'S OWN WORDS OUTRANK A SCORE GAP.
                #
                # A clause saying "verify the docx" once selected
                # `docx.document.create_from_json_record`, because a previous
                # step's output happened to make "create" bindable and it
                # scored fractionally higher. Scores are a similarity
                # estimate; the words "verify" and "create" are a statement
                # of intent. When they disagree, the words win -- and this
                # runs BEFORE the margin gate, because a margin is only an
                # argument about which estimate to trust.
                if chosen is None:
                    tokens = _distinctive_goal_tokens(goal)
                    hits = {id(s): len(tokens & _candidate_tokens(s)) for s in survivors}
                    best = max(hits.values()) if hits else 0
                    leaders = [s for s in survivors if hits[id(s)] == best]
                    if best > 0 and len(leaders) == 1:
                        chosen = leaders[0]
                        why = "GOAL_WORD_AGREEMENT"
                if chosen is None and margin is not None and margin >= DECISIVE_MARGIN_RATIO:
                    chosen = top
                    why = "DECISIVE_MARGIN"
                if chosen is None:
                    why = "AMBIGUOUS__NO_DECISIVE_MARGIN"

    if chosen is None and bridge:
        # Escalate, never replace: only when no VERIFIED capability could
        # act does the inventory get asked.
        escalated = _try_bridge(goal, root, goal_paths, started)
        if escalated is not None:
            return escalated

    if chosen is None:
        return {
            "schema": SCHEMA,
            "ok": False,
            "status": "UNRESOLVED" if not survivors else "AMBIGUOUS",
            "goal": goal,
            "ground_ms": round(ground_ms, 2),
            "survivors": [{k: v for k, v in s.items() if k != "entry"}
                          for s in survivors],
            "rejected": rejected,
            "why": why if survivors else "NO_CANDIDATE_SURVIVED",
            "margin": margin,
            "decisive_margin_ratio": DECISIVE_MARGIN_RATIO,
            "executed": False,
            "verified": False,
            "total_ms": round((time.perf_counter() - started) * 1000.0, 2),
        }

    # EXECUTE through the Brain's own invoker: unknown routes fail closed.
    from canonical.runtime import world_binding_v1 as _WB
    if str(chosen["capability_id"]).startswith("CAP_"):
        from canonical.runtime import h100_computer_use_registry_v1 as CU
        try:
            call = _resolve_goal_relative_paths(
                _WB.render_args(chosen["entry"], chosen["inputs"]), root)
        except KeyError as exc:
            call, error = None, "TEMPLATE_ARGUMENT_UNBOUND:" + str(exc)
            result, invoked = None, False
        if call is not None:
            call.pop("capability_id", None)
            try:
                result = CU.invoke(chosen["capability_id"], call, root)
                invoked, error = True, None
            except Exception as exc:
                result, invoked, error = None, False, type(exc).__name__ + ":" + str(exc)
        expect = ((chosen["entry"].get("action_template") or {}).get("expect"))
        verified, expect_note = _check_expect(expect, result) if invoked else (False, "NOT_INVOKED")
        # A CAPABILITY'S OWN POSTCONDITION IS NOT A STATEMENT ABOUT THE QUESTION.
        # `expect` proves what the adapter says it did -- bytes written, hash matched. It cannot prove those
        # bytes answer the sentence, and measured 2026-11-23 it did not: a taint analyser wrote a security
        # report into `summary.txt`, the hash matched, and VERIFIED_ACTION was reported for a request that
        # asked for per-region totals. This is called at BOTH verification sites for exactly that reason.
        if verified:
            _wrong_question = _answers_the_arithmetic_asked(goal, result)
            if _wrong_question:
                verified, expect_note = False, _wrong_question
        independent = _independent_artifact_check(result, root) if invoked else None
        if independent is not None:
            if not independent[0]:
                verified = False
                expect_note = independent[1]
            else:
                expect_note = "%s+%s" % (expect_note, independent[1])
        return {
            "schema": SCHEMA, "ok": bool(invoked and verified),
            "status": "VERIFIED_ACTION" if (invoked and verified) else "ACTION_FAILED",
            "goal": goal, "capability_id": chosen["capability_id"],
            "inputs": chosen["inputs"], "selected_because": why,
            "provides": chosen["provides"], "expect": expect_note,
            "result": result if isinstance(result, dict) else repr(result),
            "error": error, "executed": invoked, "verified": verified,
            "ground_ms": round(ground_ms, 2), "exec_ms": 0.0,
            "survivors": [{k: v for k, v in s.items() if k != "entry"} for s in survivors],
            "rejected": rejected if verbose else rejected,
            "total_ms": round((time.perf_counter() - started) * 1000.0, 2),
        }
    from canonical.runtime.astra_runtime import _invoke_bound_capability
    try:
        args = _resolve_goal_relative_paths(
            _WB.render_args(chosen["entry"], chosen["inputs"]), root)
    except KeyError as exc:
        return {
            "schema": SCHEMA, "ok": False,
            "status": "ACTION_FAILED", "goal": goal,
            "capability_id": chosen["capability_id"],
            "error": "TEMPLATE_ARGUMENT_UNBOUND:" + str(exc),
            "executed": False, "verified": False,
            "total_ms": round((time.perf_counter() - started) * 1000.0, 2),
        }
    args["capability_id"] = chosen["capability_id"]
    t1 = time.perf_counter()
    try:
        result = _invoke_bound_capability(args, root=root)
        invoked = True
        error = None
    except Exception as exc:
        result = None
        invoked = False
        error = type(exc).__name__ + ":" + str(exc)
    exec_ms = (time.perf_counter() - t1) * 1000.0

    expect = ((chosen["entry"].get("action_template") or {}).get("expect"))
    verified, expect_note = _check_expect(expect, result) if invoked else (False, "NOT_INVOKED")
    if verified:                                   # see the note at the other verification site
        _wrong_question = _answers_the_arithmetic_asked(goal, result)
        if _wrong_question:
            verified, expect_note = False, _wrong_question
    independent = _independent_artifact_check(result, root) if invoked else None
    if independent is not None:
        if not independent[0]:
            verified = False
            expect_note = independent[1]
        else:
            expect_note = "%s+%s" % (expect_note, independent[1])

    # THE SENTENCE NAMED WHERE THE ANSWER GOES. DELIVER IT THERE, OR SAY IT WAS NOT DELIVERED.
    #
    # MEASURED 2026-11-23. "total the amounts by region in data.csv and write it to summary.txt"
    # computed the correct totals -- {north: 15.0, south: 20.0} -- and reported VERIFIED_ACTION
    # while `summary.txt` did not exist. The totals went into
    # `canonical/astra_runtime/tmp/forged_out__...json`, a path the user never mentioned. The
    # computation was right and the request was not carried out.
    #
    # `world_binding_v1.named_destination` has read this exact phrase since the previous round and
    # `act` never called it -- the third mechanism found today that exists, works, and is unwired.
    if invoked and verified:
        try:
            _dest = _WB.named_destination(goal)
        except Exception:
            _dest = None
        if _dest:
            # A DESTINATION IS ONLY DELIVERED IF THE BYTES ARE THERE AFTERWARDS, and the check is
            # a re-read from disk -- the same independence `_independent_artifact_check` insists on.
            # THE FILE SHOULD HOLD THE ANSWER, NOT THE ADAPTER'S BOOKKEEPING. Writing the whole
            # result dict put `adapter`, `output_path`, `output_sha256` and `capability_id` into the
            # user's summary.txt next to the totals they asked for. What belongs in the destination
            # is the part of the result the capability does not merely assert about itself.
            _PLUMBING = _RESULT_PLUMBING
            if isinstance(result, dict):
                _answer = {k: v for k, v in result.items() if k not in _PLUMBING}
                _body = json.dumps(_answer, indent=2, sort_keys=True, default=str)
            else:
                _body = str(result)
            try:
                _target = Path(root or ROOT) / _dest
                _target.parent.mkdir(parents=True, exist_ok=True)
                _target.write_text(_body if _body.endswith("\n") else _body + "\n",
                                   encoding="utf-8")
                _back = _target.read_text(encoding="utf-8")
                if not _back.strip():
                    raise IOError("EMPTY_AFTER_WRITE")
                expect_note = "%s+DELIVERED_TO:%s" % (expect_note, _dest)
            except Exception as _exc:
                verified = False
                expect_note = "%s+NOT_DELIVERED_TO:%s(%s)" % (
                    expect_note, _dest, type(_exc).__name__)

    # DID ANY OF THIS CONCERN THE FILE I WAS ASKED ABOUT?
    #
    # Every check above asks whether this capability can vouch for its own artifact. None asks
    # whether the artifact is an answer to the question, and that gap certified a run in which the
    # person named /tmp/homefile.csv and the machine counted definitions in an unrelated .py file.
    # A capability that never mentions the named file has not answered about it, however well it can
    # prove the bytes it wrote.
    path_verdict = (_receipt_speaks_to_named_path(result, goal, chosen.get("inputs"),
                                                     chosen.get("capability_id") or "")
                    if invoked else None)
    if path_verdict is not None and path_verdict[0] is False:
        verified = False
        expect_note = "%s+%s" % (expect_note, path_verdict[1])

    out = {
        "schema": SCHEMA,
        "ok": bool(invoked and verified),
        "status": "VERIFIED_ACTION" if (invoked and verified) else "ACTION_FAILED",
        "goal": goal,
        "capability_id": chosen["capability_id"],
        "inputs": chosen["inputs"],
        "selected_because": why,
        "margin": margin,
        "decisive_margin_ratio": DECISIVE_MARGIN_RATIO,
        "provides": chosen["provides"],
        "expect": expect_note,
        "named_path_check": ({"ok": path_verdict[0], "note": path_verdict[1]}
                             if path_verdict is not None else None),
        "result": result if isinstance(result, dict) else repr(result),
        "error": error,
        "ground_ms": round(ground_ms, 2),
        "exec_ms": round(exec_ms, 2),
        "executed": invoked,
        "verified": verified,
        "survivors": [{k: v for k, v in s.items() if k != "entry"} for s in survivors],
        "rejected": rejected if verbose else [
            {k: v for k, v in r.items()} for r in rejected
        ],
        "total_ms": round((time.perf_counter() - started) * 1000.0, 2),
    }

    if EXP is not None:
        try:
            out["learned"] = EXP.observe(goal, out)
        except Exception as exc:
            out["learned"] = {"error": type(exc).__name__ + ":" + str(exc)}
        # ONE VERIFIED RUN TEACHES A PROCEDURE. ONE FAILED RUN TEACHES NOTHING.
        #
        # `verified` is this receipt's own verdict, so a failure cannot launder itself into a
        # preference for the next sentence that resembles it. The exact-recall store above is
        # untouched: this writes to a separate `procedures` section of the same file.
        try:
            from canonical.runtime import procedure_memory_v1 as _PM
            out["procedure_learned"] = _PM.learn(
                goal, chosen["capability_id"], verified=bool(verified),
                inputs=chosen.get("inputs"))
        except Exception as exc:
            out["procedure_learned"] = {"learned": False,
                                        "error": type(exc).__name__ + ":" + str(exc)}
    return out
