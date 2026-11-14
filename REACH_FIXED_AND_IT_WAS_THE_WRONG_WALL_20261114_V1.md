# I fixed the bottleneck I named last round. It was not the one I thought.

**Measured 2026-11-14 on the same 8 pull requests nobody has ever looked at — 230 real pairs, 44 of
which the taught-edit organ altered. $0, no model calls, no network, no test harness.** Record:
`canonical/verification/OBSERVABLE_SURFACE_ON_NEW_PULL_REQUESTS_20261114_V1.json` (`authority: NONE`).

Last round ended with a clean sentence: *a taught edit needs a single, value-driven, loadable function
before any oracle can ask anything, so the constraint is reach, not learning speed.* This round I built
the reach layer, pointed it at the wall, and the wall moved 18 of 19 times. Then it turned out to be
partly the wrong wall. Here is the whole sequence, including the two places I was wrong.

---

## 1. What I built

`canonical/swe_kernel/observable_surface_v1.py` — an observer that answers one question per file:
*which surfaces of this can I build, drive, and compare?*

Seven kinds. Four are **executed** (`FUNCTION`, `METHOD`, `STATE`, `CLASS_ATTRIBUTE`) and three are
**declarations read as written** (`SIGNATURE`, `DECLARED_FIELD`, `IMPORT_SET`). Execution is observed
as the **path** taken — line offsets relative to the function's first line, or the exception class — never
as the returned value, because `return 1` and `return 2` are the same behaviour and comparing values
reported every faithful copy as wrong last round.

Three rules it holds to, each of which cost a defect to learn:

- **A class that cannot be built is `unreachable` with a cause, never agreement.** 19 of the 20
  unobservable targets last round were class bodies; a fabricated "no difference" on an unbuilt object
  would be worse than no answer.
- **An address is not a value.** Any observation still carrying a memory address is reported as
  `UNOBSERVABLE`, never as a difference.
- **A file that will not import says so.** 29 of the 41 unvisitable files in the corpus name a
  third-party module (`pandas`, `boto3`, `jax`), 7 use relative imports, 5 read an attribute at import
  time. Strict mode claims no executed surface for them. Lenient mode moves a definition into its own
  module *and says that is what it did*, because a difference found that way is evidence about text,
  not about behaviour.

## 2. The measurement — the same 44 real pairs

| | old reader | widened observer |
|---|---:|---:|
| pairs the organ altered | 44 | 44 |
| the edit **moved an observation** among the 19 it could not reach | **0** — it had nothing to watch | **18 / 19** |
| the edit moved an observation among the 25 it could reach | 11 could be *asked* (2 confirmed) | **23 / 25** |
| pairs where the difference is **behavioural** | 11 | **0** (strict), 3 (lenient) |
| pairs where the difference is **declarative** | 0 | **41** (strict) |

That last row pair is the whole result and it is uncomfortable.

## 3. Where I was wrong, twice

**Wrong once: reach was not the binding constraint.** I predicted class-body observation would make
the 20 unobservable targets probeable. It made them *surfaceable* — and the edit still moved nothing,
0 of 19, even with `pandas` and `boto3` actually installed (`file now imports: 3`,
`the edit MOVED one: 0`). Widening what I can watch solved nothing on its own.

**Wrong twice: my first explanation was too coarse.** I classified the 19 as 10 "types only" / 9
"reaches code" by stripping annotations. Two independent instruments then disagreed, and the
disagreement was the finding:

- Comparing **function bodies' code objects**: 43 of 44 edits changed *no function body* at all.
- Comparing **whole-file bytecode**: 41 of 44 changed *something executable*.
- Both are right. The change is not inside a function — it is at the **declaration** level, which
  Python evaluates at `def` time and never at call time.

`Optional[str]` → `str | None`. `List[str]` → `list[str]`. `from typing import List` disappearing.
A docstring's `Returns:` becoming `Returns`. This is what real pull requests contain, and **no amount
of calling, instantiating, driving or state-signing can ever see it.** That is structural, not a bug
in my instrument.

## 4. So what is the bottleneck now

While I was measuring, the corpus answered a question I had not asked. Of the 331 changes the
developers made, the organ reproduced **98 (29.6%)**; of the ones it got wrong, the reasons were about
reach and form. But when I went through the still-unseen pairs one at a time, the thing that actually
blocked the remaining ones was neither:

- `parser.py`: `open(file_path, "r", encoding="utf-8")` → `open(file_path, encoding="utf-8")` — a
  **call-site** change inside a method body. My observer drives `_strip_inline_comment(0)` and gets
  `TypeError` on line 3, long before line 41. Driving it correctly needs an input the diff never
  carries.
- `test_template_file.py`: `"...".format(...)` → `f"..."` — the value is identical, so it is invisible
  to behaviour *and* to declarations.
- 8 of 10 unobservable edited targets have **no call site anywhere in the patch** that supplies
  arguments.

So the honest bottleneck statement, revised: **the organ can only be checked where a diff carries
enough to rebuild the argument. That is rare, because a diff shows the change and not the caller.**

That is precisely where the previous corpus already looked and where the 2026 literature is stuck:
POSTCONDBENCH measures **completeness 0.292** against correctness 0.822, with 78% of the missing
specification being return-value behaviour; VeriContest had a model produce a *verified* binary search
against the postcondition `result.len() == 2`. Confirmation is cheap. Knowing what to confirm is the
frontier, and it is not a reach problem.

## 5. What this does to last round's answer

Nothing in the verdict table changes, and one number now has a sharper reading:

- **Instant learning is real but not general** — 29.6% on unseen code, unchanged.
- **"Show it once and it learns permanently"** — the permanence half is fine; the generality half is
  where this round landed, and the wall is *what a demonstration carries*, not what my observer can
  watch.
- **The revolution is verification, not speed** — strengthened. The interesting discovery is that
  real edits are mostly **declarative**, so the honest verification surface for them is a *declaration
  comparison*, not an execution one. An agent that only tests behaviour is blind to most of what
  actually changed in a real pull request.

## 6. What I killed

- **Widening inputs until a witness appears.** The remaining unseen pairs would be "probeable" if I
  fabricated arguments; that is the integer-grid mistake from the previous round and I did not repeat
  it.
- **Reporting declaration differences as behaviour differences.** They are reported in separate
  counters and never summed into one "the lesson was learned" number.
- **A stub base class**, so that `class X(ABC)` could be instantiated. A stub makes a *different*
  class, and every observation of it would be a fabrication.
- **Re-deriving the corpus.** This doc adds one measurement and one corrected bottleneck to
  `SHOW_IT_ONCE_*`, `WHAT_INSTANT_LEARNING_CANNOT_DO_*`, `ONE_SHOWING_IS_LITERAL_*` and
  `SETTLED_TAUGHT_ADMISSION_MEASURED_*`; it does not restate them.

## 7. The one thing worth doing next, and the decision it forces

The leverage is no longer observation breadth. It is **input provenance**: an agent that can reason
about *what the caller would pass* turns the remaining method bodies into checkable surfaces without
any new observation kind. That is derivable from the repositories already in the corpus and needs no
parameters and no external model — which means it does not force the decision the literature forces
(the only lever 2026 shows reaching unseen tasks is weight training, and the law here forbids
parameters as a knowledge house). That decision stays open; it is stated, not smuggled.

`truth.achieved` stays `false`.
