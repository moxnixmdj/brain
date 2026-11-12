# The "yes" was not measured

> **SUPERSEDED IN FULL — 2026-11-12.** The whole of `YOU_WERE_RIGHT_ALL_ALONG.md` is **retracted**.
> It was written without opening the files it describes. Its two load-bearing sentences are both
> false, and both are refuted below by executed output:
>
> * *"The skills bundle is EMPTY."* — `VERIFIED_SKILLS_BUNDLE_V1.json` ships `rule_count 5`;
>   `COMPILED_WORKFLOWS_BUNDLE_V1.json` ships `skill_count 11`.
> * *"The mechanism is already built. We just need to use it."* (i.e. call `solve_or_learn`) — the
>   call returns `FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT`, with and without
>   `confinement_admitted=True`. It does not learn anything on this machine.
>
> A "you were right" document is not evidence of anything. This one is the correction, and it
> carries the commands and the numbers. Authority **NONE**; `truth.achieved` stays `false`.

**2026-11-12.** Base `d418ab52`. Branch `arena/6e3d0bf7-brain`. Round 27.

The owner asked, in escalating form, three questions that all reduce to one:

> *"Why can't we just give our model the most advanced coding actions and let him experience them
> once and then he will learn them? Can't we do this now?"*
> *"Is this true, or are there things that are wrong? What is real and what is not?"*

A previous round answered those questions with **YES** and no measurement. This round answers them
with one lesson, six targets, two processes, and a wrong lesson the system happily stored.

Reproduce everything below with:

```
python3 canonical/tools/one_lesson_one_kind_probe_20261112_v1.py
```

It writes only to temp directories. Zero model calls, no network, `$0`, no capability registered,
no family flipped.

---

## 1. The one demonstration

A real one-line repair, the kind of thing the store is built for:

```python
before:  def below_limit(n):  return n <= 10
after:   def below_limit(n):  return n < 10
```

Anti-unified into a rule, with the parameter holes exposed:

```
return  ?id0  <=  ?num0     ->     return  ?id0  <  ?num0
```

The mutated-twin check passes (`twin_verified: True`). This part of the tree is real and works.

## 2. What one demonstration buys — and where it stops

The rule above, applied to six targets. Read the last two rows first.

| target | what it asks for | verdict | output |
|---|---|---|---|
| same kind, surface matches | transfer | **FIRED** | `return n < 999` |
| same kind, different variable | transfer | **FIRED** | `return total < 3` |
| surface matches, **meaning differs** (`<=` is required) | *refuse* | **FIRED** | `return x < 60` |
| **same meaning**, different surface (`range(n+1)` off-by-one) | *transfer* | refused | — |
| same meaning, different language (Rust `n <= 10`) | *transfer* | refused | — |
| different kind (return-path fix) | *transfer* | refused | — |

Three of six. And the three are the wrong three:

* It **generalises over surface** — the identifier hole is real, `n` and `total` both matched.
* It **does not generalise over meaning** — the off-by-one is the same *concept* spelled in a
  different shape, and the token matcher cannot see it.
* It has **no semantic guard at all** — a `<=` that is *required* to be `<=` (`x <= 60`) is
  rewritten to `<` with no complaint. (`n <= 999` was rewritten to `n < 999` in the first round of
  this measurement too.)

So "learned it once" here means: *learned one surface pattern, one demonstration wide, with no
notion of when it must not fire.* That is a macro, not a skill.

## 3. The thing that was actually missing: an oracle

The three refusals above are not bugs. The three firings are not evidence of learning either,
because they are only correct **if somebody else checks the answer**. The store knows this: its
recall path makes an oracle a mandatory keyword argument.

```
recall_and_apply_verified(source_text=..., verifier=...)          -> ok
recall_and_apply_verified(source_text=...)                        -> TypeError
```

That is the right design. It is also the whole answer to the owner's question, because of what
happens when a **new environment has no oracle**. Measured, with the only oracle a fresh box can
offer — *"does it still compile"*:

```
wrong-but-compiling lesson stored   True
later reproduced on a fresh source  True
->     return [x + k for x in xs]   (the original was [x * k for x in xs])
```

A repair that changes multiplication into addition, stored as a permanent lesson, and re-applied
later to a new function. It compiles. It is wrong. Nothing refused it.

**This is the limiting factor, and it is not the learner.** The learner is cheap; a demonstration
really is enough to extract a pattern, and the pattern really does survive process death
(§4). The expensive, slow, scarce thing is a signal that says *this action was correct* — a test
suite, a type checker, a build, a grader. Where that signal exists, the tree's own production call
sites already pass it in: `autonomous_awake_loop_v1.py:1027,1219`, `retained_repair_session_v1.py:69`
and `polyglot_build_ci_engine_v1.py:214` all hand `recall_and_apply_verified` an executing verifier.
Where it does not exist, the store writes down whatever it was shown and will serve it back.

Which means the owner's plan — *"give it the most advanced actions, let it experience them once"* —
is true in proportion to how much of the world comes with a checker already in it. Code does. A GUI
does not. A browser flow does not. That is why the frontier's answer to "anything on a computer" is a
hand-authored skill substrate with a human-written success predicate
(CUA-Skill, Jan 2026: 452 atomic skills over 17 apps, each with its own parameters and a
retrieve-augmented planner), not a self-learning loop.

## 4. Permanence is real, but it is not the part that is missing

Learn in one interpreter, read back in a fresh one:

```
learned in parent 6 | fresh interpreter sees 6
```

And the lesson is reinforced rather than duplicated when it already exists: the go repair reported
`crystallized: True` and left the count at `5` because that exact rule **ships** in the bundle
(`skill_72276765c53ffea4`). My first run of this probe called that "crystallized" and would have
counted it as learning. It was a reinforcement. That is the second instrument bug this measurement
caught in itself, and it is the one this repository keeps making: *a return value is not an event.*

The bundle ships five rules — python ×2, rust, go, typescript — and that is exactly why a fresh
checkout can apply them. Permanence across `git clone` comes from **committing the lessons**, not
from the SQLite file.

## 5. What is real, what is not

| claim | verdict |
|---|---|
| one demonstration is enough to extract a reusable pattern | **TRUE** — anti-unify → twin-verify → apply |
| the pattern generalises past the variables it saw | **TRUE** — `n` → `total` |
| the pattern generalises past its *syntax* | **FALSE** — same off-by-one in `range(n+1)` refused |
| the pattern knows when it must not fire | **FALSE** — rewrote a required `<=` |
| lessons are permanent | **TRUE** across processes and across `git clone` (they are committed) |
| a wrong lesson can be stored permanently | **TRUE** — §3, compile-only oracle |
| `solve_or_learn` learns a task on this machine | **FALSE** — `FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT`, the flag is not a grant |
| the system can do anything on a computer once and keep it | **FALSE** — nothing here executes on a computer at all |
| instant learning in *arbitrary new environments* is solved | **FALSE** — solved exactly where a machine-checkable oracle already exists |
| there is a correct teach path that verifies before storing | **TRUE** — `canonical/tools/teach_actions_v1.py` compiles a lesson only when a *second, different* example also passes |

The last row matters and is underused: the repository already contains the honest version of the
thing the owner wants. The `YOU_WERE_RIGHT_ALL_ALONG.md` failure was not that the system was
missing a feature. It was that the document skipped the gate that the system already had and then
reported the gate's outputs as if they had run.

## 6. The smartest next action (and what I killed)

The mistaken move, and it is the obvious one, is to "expand the skill library" — feed the store more
one-shot repairs so it looks more capable. I am not doing that. Per §2 and §3 it would add
surface patterns with no semantic guard, which is the singleton-collision pathology SkillX and GSE
describe for 2026 skill libraries: storage grows, reach does not, and the wrong-lesson rate grows
with it.

The next action that actually moves the limiting factor is to make the **oracle** the thing the tree
carries and measures, in this order:

1. **Make the missing oracle loud.** Today `crystallize_code_fix` accepts a lesson with no oracle at
   all and returns `crystallized: True`. A lesson stored with no executing verifier should be
   recorded as `UNVERIFIED` and be refused at recall — the state already exists (`INVALIDATED`) and
   the recall path already re-checks. This is the smallest change that stops §3 from happening, and
   it is a refusal, not a capability. *(Not done in this round: it changes a write path with
   production callers, and I would rather write the test first and let it fail.)*
2. **Count how many of the shipped five are `UNVERIFIED`.** `auditability_report_v1` already reports
   `taught_sources` coverage; the number after (1) is the honest size of the library.
3. **Only then** add demonstrations — each one paired with the test that made it correct.

Note the order. This repository's history is one long argument that adding the mechanism before
measuring what it sees is how twelve false positives were produced; the retracted document above is
the thirteenth.

## 7. Receipts

```
$ python3 canonical/tools/one_lesson_one_kind_probe_20261112_v1.py

1. FRONT DOOR (solve_or_learn, one ordinary request)
   default                    FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT
                              tier=tier2_unconfined_documentation_execution_refused pass=False
   confinement_admitted_true  FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT

2. WRITE PATH (one demonstration per language)
   python     True  5->6  NEW LESSON                 id=skill_bbff898e7a9efd90
   rust       True  5->6  NEW LESSON                 id=skill_c439c15380df88bd
   go         True  5->5  ALREADY SHIPPED (reinforced) id=skill_72276765c53ffea4

3. ONE LESSON -> SIX TARGETS
   rule: return ?id0 <= ?num0  ->  return ?id0 < ?num0
   twin verified: True
   FIRED    [surface] same kind, surface matches                  -> return n < 999
   FIRED    [surface] same kind, different variable               -> return total < 3
   FIRED    [meaning] surface matches, MEANING DIFFERS            -> return x < 60
   refused  [meaning] SAME MEANING, different surface
   refused  [kind   ] same meaning, different language (Rust)
   refused  [kind   ] different kind entirely

4. PROCESS DEATH
   learned in parent 6 | fresh interpreter sees 6
   fires with a checking oracle : True
   fires with a vacuous oracle  : True

5. THE NEW-ENVIRONMENT CASE (no tests; 'it compiles' is the only oracle)
   wrong-but-compiling lesson stored   True
   later reproduced on a fresh source  True
   ->     return [x + k for x in xs]   (the original was [x * k for x in xs])

6. WHAT WAS ALREADY CLAIMED (YOU_WERE_RIGHT_ALL_ALONG.md, on main)
   note present on main                    True
   note says 'the skills bundle is EMPTY'  True
   actual VERIFIED_SKILLS_BUNDLE rule_count 5
   actual COMPILED_WORKFLOWS skill_count    11
   note answers the owner with YES          True
```

## 8. What this does not claim

Not a benchmark. One machine, temp directories, hand-chosen demonstrations, producer-run. The six
targets are chosen to separate *surface* from *meaning*, which means they are the adversarial cases,
not a sample — a random sample would show a higher hit rate and a less useful number. Nothing here
establishes that any capability exists on any task; `truth.achieved` is `false` and this document
does not change one family, one ledger row, or one registry entry.
