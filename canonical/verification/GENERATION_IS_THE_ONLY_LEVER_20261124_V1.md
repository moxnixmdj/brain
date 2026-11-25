# Generation is the only lever left

**Measured 2026-11-24.** Sweeps: `THE_FINAL_SWEEP_RECEIPT_20261124_V3.json`,
`THE_FINAL_SWEEP_RECEIPT_20261124_V4.json`. Classifier: this session's ad-hoc
`/tmp` scripts, reproduced below in prose so they can be rebuilt.

## The one number that decided the last three sessions

`GENERATED_NOT_ATTEMPTED = 0` across all 37 unsolved rows.

Every row the engine fails, it fails because the human's fix was **never generated**
(37/37) — never because a correct answer was generated and then ranked too low. That
kills, structurally, every re-ranking idea in the plan: the store, prior weighting,
admission filtering, cross-row transfer. None can promote a hypothesis that was never
created. See `THE_STORE_CEILING_IS_ZERO_20261124_V1.md`.

So the build's question stopped being "how do we choose better" and became "what do we
fail to see". Two probes were run against that question; both changed the plan.

## Probe 1: is the evidence missing, or is the reading missing?

For the 11 rows that read **no relation at all** from a run that genuinely failed, the
literals the human's fix introduces were extracted and looked up in (a) the failing test
file, (b) the source file under repair.

- **1/11** has every new literal present in the failing test.
- **6/11** introduce **no new literal at all**.

Those six are not vocabulary gaps. They are: `head` → `head.copy()`; `hasattr(x, k)` →
`getattr(x, k, None)`; `if final:` → `if not static:`. No relation over the run's
literals can ever produce `head.copy()`, because the token `copy` appears nowhere in any
evidence the run emits. This is the honest ceiling of a literal-vocabulary vocabulary,
and it is measured, not asserted.

## Probe 2: what shape are the 37?

Single-line replacements classified by what changed:

| shape | rows | derivable from a run? |
|---|---|---|
| `CALL_OR_EXPR_CHANGE` | 14 | partly — see below |
| `NEW_LITERAL` | 11 | yes, when the literal is in the test or the actual value |
| `BOOLEAN_STRUCTURE` | 9 | yes — already the best-performing family here |
| `INSERT_COPY` | 1 | **no** — `copy` is nowhere in the evidence |
| `ATTR_LOOKUP_FORM` | 1 | **no** — a default-value choice, not a read |

Reading all 37 by hand (the only way to write this table honestly) sorts them again:

- **Genuinely underivable from the failing run**: version/spec tables
  (`DEFAULT_PBKDF2_ITERATIONS` 260000→600000→1_000_000), `code: int = 302`→`303`,
  `"edge"`→`"edge|edg"`, header-name lists (`["Authorization"]`→`["Cookie"]`),
  a type-change guard (`isinstance(default_value, str)`). A run cannot distinguish 302
  from 303; it can only tell you the value is wrong. **These are not engine failures and
  should stop being counted as such.** A single-line-fix corpus built from git history
  contains commits that are the product of knowledge no test run exposes.
- **Derivable but unread**: `split`→`rsplit` (08bb0477), `if final:`→`if not static:`
  (3a408edf), `for x in a:`→`for x in a + b:` (6abdcf6c), `while not closed(fp):`
  →`... or len(buf)` (4714836a).

## What was built from probe 2, and what it earned

One relation, not eight. `SPLIT_FROM_THE_WRONG_END`, read when the actual value contains
**more** instances of the split separator than the expected value does — i.e. the
separator survived the strip because the wrong side was taken. Measured on packaging
08bb0477: fired once, on line 86, as the only hypothesis, and **VERIFIED on the first
attempt** (`netloc.split("@", 1)` → `netloc.rsplit("@", 1)`, 6.6 s).

The relation is deliberately narrow: two negative controls (equal separator counts;
separator absent from the actual) both produce nothing. A relation that fires on both
the failing and the passing case is not reading a relation.

## The structural fix that came out of tripping over the same bug twice

Twice now a new relation was added to one of `relations_for`'s two entry paths — the
sampled path and the import-time, sample-less path — and not the other. First
`END_ANCHOR`'s added-anchor repair (which cost `0625596e` a session), then
`SPLIT_FROM_THE_WRONG_END` on the very row it was written for. Both paths are reached by
different rows, so the bug is invisible from either side.

`SPLIT_FROM_THE_WRONG_END` is now emitted **above the fork**, before `if not samples:`
returns. `END_ANCHOR`'s repairs are applied on both paths explicitly. The duplication is
itself the defect, and it is the kind this build keeps making: an edit that looks local
and is not.

## What this changes about §6

§6 asks for "single-experience learning" and memory ablations. The measurement above says
the store cannot learn anything from this corpus because **nothing is there to be
chosen between**. That is a property of a 45-row corpus whose fixes are 80% one-off, and
it is the strongest evidence yet that the corpus is the binding constraint, not the
memory. A memory system needs a task distribution with recurring structure. This corpus
has almost none: 45 rows, and the only repeated repair family is regex anchoring, of
which 4 rows exist and 3 are now solved by one relation.

Therefore the honest statement of §6 progress is: **the store is not the bottleneck and
this corpus cannot show whether the store works.** Demonstrating §6 requires a task
distribution with repetition — which is what "never-seen environments" and "hardest
current benchmarks" actually mean — and that remains blocked on Docker for the
container-based ones. Step-1-class work on this corpus is now near saturation:
what remains inside it is mostly underivable.
