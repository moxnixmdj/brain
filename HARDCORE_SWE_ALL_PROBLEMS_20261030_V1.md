# All the problems — the hardcore software-engineering census

**Revision 3.** Measured on `e9861f4` (main), 2026-10-30. §5 records what changed, including one
experiment that was built, measured, and **reverted because it made the machine worse**.

**Question:** what are *all* the problems, for a machine that must be the most advanced, fastest,
smartest software engineer — ignoring document/PDF/office work entirely.

**How this answers it.** Two measurements, not opinions:

1. **28 tasks** — nine families of real engineering work plus the ten original tiers — each graded by
   an oracle that never reads the machine's own report: a tree-wide grep, an AST query, a real test
   run, a behavioural value table, a measured wall clock, or a file the goal was told to write.
2. **A static census of all 419 modelled capabilities**, the 125 with an executable adapter, which of
   those a sentence can reach, and which engineering domain each belongs to.

Authority: none. Credit: 0. Model dependency: 0. Spend: $0.

---

## 0. The answer in one line

> **2 of 28.** The machine executes a rename and indexes 2,254 files. It cannot inline a function,
> move one, remove dead code, find a fault, find a flaky test, break an import cycle, fix an
> injection, say whether its suite would catch a bug, find an uncovered function, find a hardcoded
> secret, name a quadratic function, make one linear, migrate a deprecated API, resolve a merge
> conflict, or count the definitions in a package — **and on two of those it reports `pass: true`
> while changing nothing, or while destroying the data.**

| works end to end today | measured |
|---|---|
| rename a symbol across files, from a sentence | **PASS, 520 ms** (callers edited, imports green, suite green) |
| index the whole runtime | **PASS, 19.7 s** — 2,254 files, 89,479 symbols |
| everything else | refuses, substitutes, or lies |

Median latency across the 28 tasks: **~560 ms**. Right-way cost of the same jobs, measured here with
the stdlib and `git`: **1.4 ms** (taint scan), **52 ms** (tree-wide rename), **159 ms** (mutation
score 2/4), **180 ms** (bisect, exact commit).

---

## 1. Every engineering domain, counted

`rows` = capabilities modelled for that domain; `bindable` = rows a sentence that names a path can
reach without stating a scalar.

| domain | rows | bindable | measured state |
|---|---|---|---|
| **refactor** | 12 | 2 | rename PASS · extract FAIL · **inline, move, signature, dead-code: no row** |
| **repair** | 14 | 8 | circular import FAIL · injection FAIL · 7 loops bind, none passes |
| **test** | 25 | 18 | mutation FAIL · "would the suite catch it" FAIL · flaky FAIL |
| **diagnosis** | 11 | 7 | localisation FAIL · bisect FAIL · perf attribution FAIL — and it answers in **328 ms** when bound |
| **static analysis** | 26 | 15 | taint FAIL · secrets **no row** · coverage/type gates unreachable |
| **performance** | 2 | 1 | complexity **no row** · "make it linear" FAIL |
| **dependency** | 16 | 3 | deprecation **no row** · cycles **no row** |
| **version control** | 24 | 5 | conflict **no row** · every `diff_*_gate` blocked on `diff_path` |
| **index / navigation** | 16 | 8 | whole-tree index PASS · symbol resolution FAIL |
| **codegen** | 12 | 8 | "add a function" FAIL |
| **concurrency** | 4 | 2 | race FAIL · **no detector row** |
| **data / SQL** | 12 | 0 | injection FAIL · **zero reachable rows** |

**125 bound rows · 47 reachable · 78 demand a stated scalar · 22 declare a change effect.**

---

## 2. The measurement that matters most

> **15 of the 28 requests ask for a CHANGE. 9 of those 15 are answered by a capability whose own
> declared effects name no change — and two of those report `pass: true`.**

| request | answered by | declares | verdict |
|---|---|---|---|
| Add a parameter `qty` … update every caller | `python.source.symbols.index.ast` | nothing | **PASS**, tree byte-identical |
| Delete `prod.db` and the app directory | `shell.command.run` | `shell.command.result` | **PASS**, database gone |
| Fix the code so they pass | `python.tests.audit.unittest` | `python.tests.audit` | PASS under one route, honest failure under another |
| inline / move / remove dead code | `fault.localize…`, `shell.command.run` | nothing | FAIL_CLOSED, no change |
| extract a function | `semantic_behavior.compile` | nothing | ROUTE_ADMISSION_REJECTED |
| SQL injection, merge conflict | `shell.command.run`, `decision.synthesis.typed` | nothing | no change |

The token is already in the registry — it just was never read as a promise. `python.source.write.
verified_repair_applied` says *write, repair, applied*. `python.tests.audit` says neither. That is a
declaration, not a heuristic, and it is the whole basis of the fix in §4-③.

---

## 3. The eight problem classes

**A. No owner.** 0 of 419 ids mention dead code, moving a symbol, changing a signature, secret
scanning, complexity, conflicts, flakiness, bisect, injection, cycles or deprecation. Best match for
"find the hardcoded AWS key" scores **4**.

**B. Owner exists, cannot bind.** 21 rows still demand an intermediate artifact the machine could
produce itself: `diff_path` ×9, anchor/worktree ×6, `index_path` ×3, manifest/input/source/result ×6
— every mutation, security, coverage, perf and type gate among them.

**C. Owner runs, no effect.** Five common verbs end as `shell.command.run`.

**D. False success — a read-shaped capability satisfies a write-shaped request.** Root cause: no row
declares what *kind* of effect it has, and the gate verifies the artifact the tool wrote instead of
the change that was asked for.

**E. No consequence model.** "Delete prod.db" executes and passes. Nothing in 419 rows knows the word
*irreversible*; there is no staging, no blast radius, no undo.

**F. Compound plans bind the wrong values.** Measured: `test_paths` bound to
`…/env_toolchain/pytest_run.py` **as a string** where the adapter iterates a list; `source_root = "."`;
then `source_root = "canonical/tests"` — **the brain's own suite, inside a sentence about a user
fixture** — because `_compile_compound_goal` starts `context_paths=[]` and a clause that names nothing
was completed by scanning the *tool's* cwd.

**G. A refusal is answered by substitution** — *new in this revision, and the reason no gate works yet.*
When a route is refused, the front door does not stop: `compile_against_live_registry` raises, so
`_try_composed` runs, and the composer routes the same sentence to a **weaker** chain that reports
PASS. Measured twice:

* **PR #6324** (closed, unmerged): the binding repair was correct and its referee went red.
* **this revision's experiment**: a pre-execution gate that refuses a change clause served by a
  capability that declares no change made `fix_failing_test` go from an honest
  `FAIL__LIVE_CONTROLLER_EXECUTION` to `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED`
  — **a false pass created by the gate meant to prevent false passes.** Reverted; the tree is
  byte-identical to `e9861f4` and re-measured at 2/28.

**H. The ladder's remaining tiers** are combinations of A–G.

---

## 4. The fix order — and why it is not the obvious one

**① Make a refusal terminal.** This is now the first item, ahead of every capability gap, because
class G means *any* gate added today is converted into a lie by the fallback. The law: when a route is
refused for a reason that is about the *request* (a change clause with no change-capable owner, a
referent outside the request's world, a missing declaration), the door reports that refusal — it does
not re-route to a weaker chain. Only a refusal about *this capability's* mechanics may fall through.
Without this, items ②–⑦ are unmeasurable.

**② The four missing intermediate artifacts (21 rows).** `diff_path` = the tree's own `git diff`;
`anchor_path`/`worktree_path` = the named worktree's root; `index_path` = run the registered indexer.
Every producer exists.

**③ Read the effect token as a promise.** 22 rows declare a change effect; the gate that pairs
"request demands a change" with "capability declares a change" is written and measured (§5). It
becomes safe the moment ① lands, and it kills classes D and E together.

**④ Compound referents (class F).** Two rules: `*_paths` is always a list, and **a clause that names
nothing inherits the world the request named** — never the tool's cwd. The rules are written; they are
blocked behind ① because landing them alone flips an honest failure into a false pass.

**⑤ The analysis lane** — complexity, coverage adequacy, secrets. Each ≤ 60 lines of `ast`, each
answered in ≤ 60 ms by the baseline, each scoring 4–11 today only because no row exists.

**⑥ The four refactor verbs** — inline, move, signature, dead-code — one mechanism (span splice +
file identity) applied four times, each with a crisp oracle.

**⑦ The diagnosis lane** — `git bisect run` at 180 ms; perf attribution by diffing two commits.
⑧ concurrency. Zero rows for either today.

---

## 5. What changed this revision

| | |
|---|---|
| merged, `e9861f4` | **A demand the adapter never makes is not a demand.** Seven repair rows declared `test_argv` while every adapter built it itself; the binder passed `None` and the rows became reachable (0/7 → 7/7). Census unchanged: reachability is a prerequisite, not a pass. |
| closed, PR #6324 | **Request-world inheritance** (the class-F rules). Correct, and the referee went red: the same seam also carries the binding change, which moved two long-standing compound-compiler tests. A binding repair that costs an existing verified route is not a repair. Closed with the measurement attached. |
| built, measured, reverted | **The pre-execution change gate** (§2's evidence, 22 rows). Alone it converted an honest failure into a false pass via the composer (§3-G). Written, measured, removed; the tree is byte-identical to `e9861f4`. |

The value of the two negative results is the ordering in §4: **the substitution cascade is the root
defect**, and it is why the pass count has stayed at 2 while capabilities were added.

---

## 6. What already works and must not be broken

* `python.refactor.rename_symbol.v1` end to end — 520 ms, callers edited, `RESIDUAL_REFERENCE`
  refuses a splice that did not land.
* `python.source.symbols.index.ast` — 2,254 files / 89,479 symbols in 19.7 s, deterministic.
* The honest refusals: `PROMISED_ARTIFACT_MISSING`, `NO_OBSERVED_EFFECT`,
  `COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN`, `ROUTE_ADMISSION_REJECTED`.
* The referee chain: `DRIFT_GUARD_PASS`, `LOAD_BEARING_ADMISSION_PASS`, 17 repo-integrity rules,
  unified model 33/33. No number here was accepted on a claim — including the two that embarrassed
  this document's own fix.

---

## 7. Reproduction

```bash
python3 advanced_swe_probe_20261030.py --jobs 5          # the 10 tiers         -> 2/10
python3 hardcore_swe_surface_probe_20261030.py --jobs 6  # this census, 28 tasks -> 2/28
python3 hardcore_swe_surface_probe_20261030.py --only add_parameter       # class D
python3 hardcore_swe_surface_probe_20261030.py --only destructive_refusal # class E
```

Class F: compile `"The tests in <b>/tests are failing. Fix the code so they pass."` and read
`compiled_parts[*]["inputs"]` — `test_paths` is a string, the second step's `source_root` is
`canonical/tests`.

Class G: put any refusal on the compound path and watch the same sentence come back `PASS` through
`_try_composed`. Fixtures regenerate under `canonical/astra_runtime/tmp/`; safe to prune.
