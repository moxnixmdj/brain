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
    doc = json.loads((ROOT / REGISTRY_PATH).read_text(encoding="utf-8"))
    caps = doc.get("capabilities")
    if not isinstance(caps, dict) or not caps:
        raise RuntimeError("REGISTRY_INVALID")
    return caps


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
        return True, "NO_EXPECT_DECLARED"
    field = str(expect.get("field") or "")
    kind = str(expect.get("type") or "")
    value = _lookup(result, field) if isinstance(result, dict) else None
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


def _word_tokens(text):
    import re as _re
    return {t for t in _re.findall(r"[a-z0-9]+", str(text or "").lower())
            if len(t) >= 3}


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
    return [{"capability_id": cid, "combined_score": float(hits) * 10.0}
            for hits, cid in scored[:k]]


def _distinctive_goal_tokens(goal):
    """Words the user actually said, minus filler."""
    import re as _re
    out = set()
    for tok in _re.findall(r"[a-z0-9]+", str(goal or "").lower()):
        if len(tok) >= 4 and tok not in _GOAL_STOPWORDS:
            out.add(tok)
    return out


def _candidate_tokens(survivor):
    """Words a capability uses to describe itself."""
    import re as _re
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
    import re as _re
    m = _re.search(r'"([^"]*)"', str(goal or ""))
    if m:
        return m.group(1)
    return str(goal or "").strip() or None


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
            "executed": True,
            "verified": False,
            "expect": "NO_EXPECT_DECLARED__TIER_IS_NOT_VERIFICATION",
            "total_ms": round((time.perf_counter() - started) * 1000.0, 2),
        }
    return None


def act(goal, root=None, registry=None, verbose=False, memory=True,
        established_effects=(), extra_paths=(), bridge=True,
        computer_use=True):
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
            if WP.kind_contradiction(cid, WB.placeholders(entry), own_paths):
                rejected.append({"capability_id": cid,
                                 "why": "INPUT_KIND_CONTRADICTS_GOAL_FILE",
                                 "goal_paths": own_paths})
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
    if survivors and EXP is not None and len(survivors) > 1:
        # Asked once, answered once. Memory removes the need to ask, never
        # the need to check -- the action is still verified below.
        remembered = EXP.recall_resolution(goal)
        if remembered:
            for s in survivors:
                if s["capability_id"] == remembered:
                    chosen, why = s, "REMEMBERED_RESOLUTION"
                    break
    if survivors and chosen is None:
        if len(survivors) == 1:
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
            call = _WB.render_args(chosen["entry"], chosen["inputs"])
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
        args = _WB.render_args(chosen["entry"], chosen["inputs"])
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
        result = _invoke_bound_capability(args)
        invoked = True
        error = None
    except Exception as exc:
        result = None
        invoked = False
        error = type(exc).__name__ + ":" + str(exc)
    exec_ms = (time.perf_counter() - t1) * 1000.0

    expect = ((chosen["entry"].get("action_template") or {}).get("expect"))
    verified, expect_note = _check_expect(expect, result) if invoked else (False, "NOT_INVOKED")
    independent = _independent_artifact_check(result, root) if invoked else None
    if independent is not None:
        if not independent[0]:
            verified = False
            expect_note = independent[1]
        else:
            expect_note = "%s+%s" % (expect_note, independent[1])

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
    return out
