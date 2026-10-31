# All the problems — tier D: the door lies about what the machine cannot do

**Measured 2026-10-28 on branch `arena/4ca3a720-brain`.** Every number below was produced by
running the machine; every experiment that failed is reported with the number that killed it.

V3 answered *what the machine cannot do* (38 missing verbs). This adds the part that matters
more: **what the machine says when it is asked for one of them.**

Instrument: `execution_guard/hardcore_se_missing_verb_probe_v1.py` — 43 ordinary-English sentences,
one per absent act, each run through the live front door against a real two-commit scratch
repository, judged on whether an artifact was written and whether the door reported PASS.

```
python3 execution_guard/hardcore_se_missing_verb_probe_v1.py --json /tmp/missing.json
```

---

## The measurement at HEAD (`8d03c0b`), reproduced twice, identical both times

| verdict | count | meaning |
|---|---|---|
| **SILENTLY_WRONG** | **18** | a capability ran, wrote a credible artifact, and the door said PASS — for an act the brain does not have |
| **HONEST_REFUSAL** | 23 | failed closed |
| **WRONG_TOOL** | 2 | a capability was chosen and executed, then failed — a missing capability looks like a broken one |
| answered by a capability that does not own the act | **36 of 43** | the substitution happened even when the artifact check saved it |
| refusals that name the missing act | **0 of 23** | the refusal never says which verb the brain lacks |

The 18 hollow passes: `git_blame, git_stash, interactive_debug, complexity_metric, duplication,
dead_code, fuzz, differential_test, vulnerability_audit, lint, format, type_check, async_audit,
exception_audit, retry_design, inline_function, change_signature, api_compatibility`.

This is the worst failure class in the system. A refusal is a fact the caller can act on; a hollow
pass costs the caller everything downstream of a wrong artifact.

### The mechanism, named exactly

`goal_front_compiler_v1` rule **F3_ARTIFACT_WRITERS_PREFERRED** fires whenever the sentence names a
future artifact: only candidates that can write a file may decide. When no capability performs the
requested act, F3 does exactly what it was built to do — it prefers the artifact writers — and a
generic writer that merely shares a *medium* word with the sentence (`source`, `tree`, `python`)
wins and writes the report. The artifact is real, the promise is kept, the act never happened.

Direct confirmation (`lint`, head-on, no door in between):

```
sel=source.candidates.enumerate.stdlib
rules=[F2_SENTENCE_FINAL_PERIOD_REMOVED, F4_ZERO_INPUT_TOOLS_NOT_ROUTABLE, F3_ARTIFACT_WRITERS_PREFERRED]
```

### Two contributing defects found by the same instrument

1. **Registry keyword pollution.** `python.source.change_impact.testselect.v1` declares `blame` as
   a keyword. It does not blame. `git blame` therefore selects it and the door passes. A keyword
   is a claim about what the capability does, and a false one is not repairable by a ranker.
2. **A write escaped its destination.** On one run, probe artifacts appeared under
   `<repo>/home/user/brain/canonical/astra_runtime/tmp/...` — the stated absolute path mirrored
   inside the repository root: the same file written twice, once where it was asked for and once
   relative to the repo. The files were removed. The probe now *reports* this
   (`escaped_writes` in its JSON) instead of hiding it; the final clean run reproduced **0**, so it
   is intermittent and depends on pre-existing state — which makes it worse, not better: it is
   filed as an open path-joining defect rather than a closed one.

---

## Three candidate fixes, measured, two rejected

| candidate fix | effect on the 18 hollow passes | effect on the rest of the machine | verdict |
|---|---|---|---|
| **A.** treat the medium as non-distinctive (`source, tree, code, module, repo, report, json, run, using` added to `GENERIC_MATCH_TOKENS`) | 18 → 12 | not isolated (see C) | held, not shipped |
| **B.** morphological matching of plurals (`tests`→`test`, `lines`→`line`) | folds into A | not isolated | held, not shipped |
| **C.** act admission: the selected capability must itself name the sentence's head verb, else refuse with `GOAL_ACT_NOT_IN_THE_CAPABILITY_SET` (`goal_front_compiler_v1`) | **18 → 6**, and 0 wrong-tool, with the 22-task reachability probe still at **22/22 bind, 22/22 select, 22/22 pass** | goal-compiler suites go from **17 failing / 149 passing** (baseline, measured with the change stashed) to **27 failing / 139 passing**, and to **35 / 131** with the medium-token change reverted | **rejected** |

C is the honest rule and it is also the one that breaks working routes: `test_every_capability_is_reachable_BY_PROSE_alone` requires that every capability can be reached by a sentence about itself, and a head-verb admission rule is a *lexical* test applied to *semantic* routing. Ten to eighteen working
routes die to buy twelve honest refusals. That is not a trade worth making by heuristic.

### The residual 6, and why they survive C

`git_blame, differential_test, vulnerability_audit, async_audit, exception_audit, change_signature`.
In every one, the winning capability's own keyword list contains the sentence's head verb
(`blame`, `run`, `audit`, `audit`, `audit`, `change`). The verb is *claimed*; the **object** is not
— `Audit the dependencies`, `Audit the concurrency`, `Audit the exception handling` all land on
`python.source.audit.ast`, whose object is the AST of a python source tree. Acting on that means
requiring the direct object too; that was implemented and measured, and it refused working
requests (object vocabulary such as `unit` is not declared by the entry that owns the act), so it
was removed rather than tuned until the number looked good.

---

## The correct fix, in order

1. **A declared act vocabulary per capability.** Each entry states the verbs and objects it
   performs (`acts: [{verb: audit, object: source_structure}]`) and the front door admits a
   selection only when the request's verb *and* object are in that declaration. This is a schema
   addition to the registry, it is checkable at registration time, and it makes both the hollow
   pass and the false keyword impossible by construction. Nothing heuristic survives contact with
   a 125-entry vocabulary; a declaration does.
2. **Stop F3 from substituting an unrelated act.** An artifact writer may satisfy the *artifact*
   clause of a request, never the *act* clause. If no candidate owns the act, the request is one
   step of a plan whose first step is missing, and the honest answer is that step's name.
3. **Prune the false keywords** (`blame` on test selection is the measured one; a scan for the rest
   is `python.source.audit.ast`'s word list against its adapter).
4. **Make every refusal name the act.** 0 of 23 do today. The refusal object already carries a
   `detail`; nothing downstream is expected to read it as prose, and the caller is left guessing.
5. **Then build the missing verbs** in the V3 leverage order: version control (11), supply chain
   (5), coverage/memory/complexity measurement (5), refactoring beyond rename+extract, fuzzing /
   differential / flakiness.

---

## What did ship this unit

- `execution_guard/hardcore_se_missing_verb_probe_v1.py` — the instrument above. It classifies
  honestly: a FAIL with no capability credited and no artifact written is a **refusal**, not a
  wrong tool, because a vague refusal and a wrong tool are different defects and must not be
  counted as one. It also records, per row, whether the answering capability even owns the act,
  and whether the refusal names it — the two numbers that make this table possible.
- The stable, reproducible baseline this tier is defined against: **18 / 23 / 2**, twice, byte-identical.
- A rejected fix (C) with its full before/after, so nobody spends a day re-deriving it.

## How to reproduce

```bash
# tier D: what the door does with the 43 absent acts
python3 execution_guard/hardcore_se_missing_verb_probe_v1.py --json /tmp/missing.json

# the 22-task reachability probe, unchanged at 22/22 with the runtime untouched
python3 execution_guard/hardcore_se_reachability_v1.py --json /tmp/se_reach.json

# the baseline the rejected fix was measured against (stash the runtime changes first)
python3 -m pytest -q canonical/tests/test_goal_front_compiler_v1.py \
  canonical/tests/test_front_door_selection_parity_v1.py \
  canonical/tests/test_the_write_lane_runs_the_capability_the_sentence_asked_for_v1.py \
  canonical/tests/test_a_refusal_names_the_capability_that_was_asked_for_v1.py \
  canonical/tests/test_capability_naming_rule_v1.py \
  canonical/tests/test_goal_compiler_world_binding_v1.py \
  canonical/tests/test_a_request_is_read_by_the_words_it_uses_v1.py
```
