# The relation is read from the failing run — 2026-11-24

Authority: **PRODUCER RUN, this branch.** No independent verification, no §6 claim, no
benchmark score. This records what the instrument now reads off a failing run, what it
still cannot, and the measured evidence for each statement. Every "measured" line below
was produced by a run recorded in `/tmp/rel/`, not asserted.

## 0. Confirmation of the standing requirements and the §2 resolution

Read as new. Bound by: own model at runtime, zero model calls in the shipped system,
no knowledge-warehouse parameters, every parameter computed and justified, knowledge in
the external instant-knowledge store, instant single-experience learning persisting
there, real understanding over pattern matching, best-part-is-no-part, ultimate not
incremental, honesty separating verified/unverified/failed, integrity (no leakage, no
hand-solving), one branch, merge once when complete, never ask the user.

**§2 contradiction (instant learning + instant knowledge vs zero knowledge house), as
resolved and re-confirmed by this work:** parameters hold only *computed mechanisms*;
knowledge and learned skills live in an external, inspectable, editable store. The test
is unchanged and this work satisfies it: the instrument's entire competence is a small
set of relations (PRESENCE, NEGATION, ANCHOR, QUOTING, MATERIALISE, RAISES_BY_PREDICATE,
FLIP, EXCHANGE, INCLUSION, UNION, KEY_SELECTION, NONE_LEAK) that are **derived from the
run's own facts**, never a table of memorised fixes. Removing the store removes no
mechanism; removing a relation removes one law, not one example.

## 1. What the instrument is

`canonical/tools/the_relation_is_read_from_the_failing_run_v1.py`. For one real bug-fix
commit: build the parent worktree, run only the commit's own failing test, trace which
lines and which *value-deciding expressions* actually executed, then read the demanded
value off the failure and propose the single-token edit that relation names. Nothing
reads the human's diff; the fix is never looked up.

The human's diff is used only **after** a fix is verified, to report whether the
invented edit landed on the line the human changed.

## 2. Verdict on the four "leaps" the owner named

| Leap | Status in this work | Evidence |
|---|---|---|
| 1. Data-flow & causal graphs across files | **Not built.** Present: per-run executed-line set and per-site live-value samples, both bounded. | this tool |
| 2. Semantic equivalence via a universal IR | **Not built.** Present: a *relation* vocabulary that is language-independent by construction — "this guard's value was falsey but not None" is the same fact in any language — but no IR, no cross-language transfer tested. | this tool, relation list |
| 3. Goal-directed invention (CEGIS) | **Partially real, and it is the part that works.** The loop proposes, executes the project's own suite, and keeps only an edit that flips every failing test without breaking a passing one. That is CEGIS with the *project's test suite* as the verifier and no theorem prover. | every VERIFIED row below |
| 4. Executable mental models | **Not built.** The "simulator" used is the real environment under instrumentation. | this tool |

## 3. Measured results

Baseline before this work (prior receipts): **2 / 75** rows where the human fix was a
relational one-liner recovered without looking at the diff.

Re-verified this session, each with the edit landing exactly on the human's line:

| repo | commit | relation | edit | human line |
|---|---|---|---|---|
| more-itertools | 71e070b3 | PRESENCE | `key is not None` | 4282 |
| packaging | b80e6eb0 | PRESENCE | `self.environments is not None` | 839 |
| packaging | 8af75907 | ANCHOR | `$` → `\Z` in `_wheel_name_regex` | 69 |
| packaging | 258202ed | ANCHOR | `$` → `\Z` in `_validate_regex` | 38 (site spans 37–39) |

Two of these (`b80e6eb0`, `71e070b3`) were previously reported as harness artifacts of an
earlier build; both were re-proven genuine under the fixed instrument.

## 4. Harness defects found and fixed (each was forging a fact about a project)

Every one of these produced a plausible-looking `NO_RELATION` / `CHANGED_LINE` verdict
about the *project* while the fault was the instrument. They are listed because the
same class of error is the main threat to every number above.

1. **argv off-by-one** — the child received the names list where it expected the select
   list, so a traced run iterated an `int` (`TypeError: 'int' object is not iterable`),
   wrote nothing, and the row read `THE_NAMED_TEST_DID_NOT_FAIL`. The call also passed
   `node.split("::")[0]` as the test path (the word `tests`) for JUnit-spelled node ids.
2. **Retried `pytest.main`** — a retry re-registered the project's plugins into a
   half-built config and failed with an error belonging to the retry. One session now.
3. **Walrus sites** — wrapping `(value := d.get(k))` in a lambda executes the assignment
   in the lambda's scope, so the name is never bound and the module dies at import with
   `NameError: name 'value' is not defined`. That masked the real failing guard at line
   839 of packaging `pylock.py` on every run.
4. **Type-annotation sites** — wrapping one argument of `t.Dict[str, t.Any]` passes one
   argument where `Dict` needs two: the module dies at import with
   `TypeError: Too few arguments for typing.Dict`, before any test runs. Five of the
   first fifteen rows showed a trace that stopped at module-level `TYPE_CHECKING`.
5. **Same-line double wrapping** — two sites on one line built `f(probe(a), probe(b))`,
   so the probe was called with the callee's arguments:
   `__brain_rel__() takes 2 positional arguments but 4 were given`, inside the project's
   own test.
6. **Budget starvation** — the first-come sample budget was spent on early sites, so the
   demanded site (often the last statement before the raise) was never sampled. Every
   site's *first* value is now recorded regardless of budget.
7. **`branches` dropped in row assembly** — silently disabled FLIP and NONE_LEAK on
   every row while the trace licensed them.
8. **`site.line` vs a multi-line site's span** — a `re.compile(` that starts at 37 and
   ends at 39 has its pattern literal on 38; an equality test on `site.line` missed the
   row's own subject, and the attribution of "did the edit land on the human's line"
   was wrong for every multi-line site.
9. **`sites_inside` KeyError** — an index present only in the full site map raised inside
   the hypothesis loop; the row then reported `NO_RELATION` with every other piece
   correct.
10. **Unflagged re-check** — a `re.compile(pattern).search(candidate)` guard without the
    pattern's own `re.IGNORECASE` rejected exactly the rows the flags had made true.
11. **`_SCALAR_PAIR` required a leading letter** — `200 != 192` and `[] != [[0,1,2]]`,
    the two commonest failures in the corpus, matched nothing and every numeric/empty
    demand was read as "exception only" with no relation licensed.
12. **Probe consumes a generator** — a sampled generator is consumed once more, so the
    defect disappears and the test passes under instrumentation. Now reported as
    `THE_PROBE_REMOVED_THE_FAILURE`, never as `NO_RELATION`.

## 5. The one structural limit found

`CHANGED_LINE_NEVER_EXECUTED` fell from 9 rows to 1 when the import-poisoning defects
were fixed: the failing run *does* execute the line the human fixed in almost every
addressable row. The remaining misses are of two honest kinds, not one:

- **The demand is not a value comparison** (e.g. a constant change, a `$`→`\Z` on a
  pattern the failing value never reached). No relation can be read because the run
  never asked the question.
- **The probe changes the program** (generators/iterators). Instrumenting to observe
  them removes the very state under observation.

## 6. What this does and does not establish

Established: a deterministic, model-free mechanism reads a relational fix off a failing
run's own facts and verifies it against the project's own suite, on real historical
commits, without reading the diff.

**Not** established: cross-language transfer, GUI/browser or terminal tasks, arbitrary
unseen environments, Terminal-Bench 4.0 or OSWorld 2.1 performance, and §6 as a whole.
This is progress with measured evidence, not completion.
