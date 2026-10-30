# All the problems — the hardcore software-engineering census

**Revision 7.** Measured on `ec2f9ec` (main), 2026-10-30. Every number below is a measurement from
this tree, not an estimate. §5 records only what survived measurement; §3 names the three laws this
census has already killed.

**Question:** what are *all* the problems, for a machine that must be the most advanced, fastest,
smartest software engineer?

**Answer:** the machine owns **125 routable capabilities and 419 verified ones**, and **9 of the 14
capability families a working software engineer uses every day have zero owners.** That is not a
long tail. It is *inline a function, move a symbol, find dead code, change a signature, scan for a
secret, measure complexity, resolve a conflict, detect a flaky test, bisect a regression, find an
injection, break an import cycle, migrate a deprecation* — the verbs the job is made of.

Authority: none. Credit: 0. Model dependency: 0. Spend: $0.

---

## 0. The answer in one line

> **5 of 28.** The machine executes a rename, indexes 2,254 files, refuses five requests it used to lie
> about, and now answers three analysis questions from artifacts it already builds. Everything else it
> cannot do — and one thing it does that it should not: it deletes a production database when asked,
> and reports success.

| works end to end today | measured |
|---|---|
| rename a symbol across files, from a sentence | **PASS, 812 ms** — callers edited, imports green, suite green |
| index the whole runtime | **PASS, 21.3 s** — 2,254 files |
| refuse a request it cannot serve, and say so | **PASS** — five substitutions became honest `FAIL__RAW_GOAL_COMPILATION_GAP` |
| say which function nothing executes | **PASS, 1.7 ms** — `audit_total`, from the index's own `callers_of` |
| find a hardcoded credential | **PASS, 0.2 ms** — file + line, secret redacted, never written |
| say which function is quadratic | **PASS, 0.5 ms** — nesting depth → `O(n^2)` |
| everything else | refuses, substitutes, or lies |

---

## 1. The inventory, counted

| | count | source |
|---|---|---|
| verified capability rows | **419** | `load_verified_registry()` |
| rows reachable from a plain sentence | **125** | `BOUND_CAPABILITY_REGISTRY_V1.json` |
| adapter modules | **146** | `canonical/runtime/bound_capabilities/` |
| missions (verification statements) | **325** | `canonical/astra_runtime/missions/` |
| census tasks that pass end to end | **2 of 28** | `hardcore_swe_surface_probe_20261030.py` |
| ladder tiers reached | **2 of 10** | `advanced_swe_probe_20261030.py` |
| false passes among the 28 | **1** | §3-E |

### 1.1 The capability families that have no owner — measured

Searched across all 419 verified ids, case-insensitive, including keywords and provides:

| family | owners |
|---|---|
| dead code / unused symbol | **1** — `python.source.dead_code.v1`, admitted 2026-10-30 |
| move a symbol between modules | **0** |
| hardcoded secret scanning | **1** — `python.source.secret_scan.v1`, admitted 2026-10-30 |
| complexity / quadratic detection | **1** — `python.source.complexity.v1`, admitted 2026-10-30 |
| merge conflict resolution | **0** |
| flaky test detection | **0** |
| git bisect / regression commit | **0** |
| injection (SQL / command) | **0** |
| import cycle | **0** |
| deprecation migration | **0** |
| lint / type gate | **0** |
| inline a helper | 1 — *and it is an XBRL fact anchor, not a Python refactor* |
| change a signature | 4 — *one is `rename_parameter`; the rest are unrelated* |
| coverage adequacy | 8 — *two are real: a diff coverage gate and a diff mutation gate; both unreachable (§2.2)* |

**This is the answer to the question.** The census's 28 tasks are symptoms. The disease is that
eleven capability families the job is made of were never built, and the two quality gates that *were*
built cannot be reached. **Three of the eleven now have an owner**, and each took one query over an
artifact that already existed — see §2.3 for what that says about the other eight.

---

## 2. The two structural defects that explain most of the 26 failures

### 2.1 The request's own output is mistaken for its subject

Measured, verbatim, on this tree:

```
"Run the security gate on the changes in <b> and save the report to <b>/out_sec.json"
  -> score 4, matched_tokens = ['report']
  -> output file ABSENT : python.repository.acceptance.measure.v1 -> PASS__RAW_GOAL_...
  -> output file PRESENT: document.convert.markdown_pdf.pandoc_weasyprint (a PDF converter) -> fail
```

The entire evidence for choosing a capability was **the word `report`** — the name of the artifact the
sentence asks to be written. `security` matched nothing, because nothing owns it; so the tie was
broken among rows that also say "report". With its output file absent the run reported **PASS** on a
request to run a security gate — on a capability that measures repository acceptance and reviews
nothing.

This is the same law the repository already states for paths — `goal_compiler._path_named_after_output_verb`:
*a path the sentence names as a DESTINATION is never a candidate SOURCE.* The prose form of that law
is missing. `prose_only()` removes URLs, paths and quoted literals because "none of them says what the
task IS"; it does not remove the words that name the output.

It is also **state-dependent**: whether `<b>/out_sec.json` already exists changes the route, because
the artifact list feeds the binder. Same sentence, different tool, depending on an earlier run.

**Tried and killed, this revision.** The obvious rule — the word for the artifact is bookkeeping, not
evidence (the dual of `_path_named_after_output_verb`) — was written into `_score`. `report` did
disappear from the evidence. The selected capability did not change: `acceptance.measure.v1` came back
at **score 4 on the word `run`**, and with the output file absent it still reported PASS. Suppressing
either word only hands the match to the next one, because *the request has no owner* and something
must win the tie. **Class D here is a capability gap, not a ranking bug** — which is why §4 puts the
analysis lane first and the ranking rules after it. Reverted; tree clean; `test_goal_compiler` 26/26,
census 2/28 both ways.

### 2.2 Six review capabilities, one missing artifact

Nine bound rows declare a `diff_path` input. Among them is the whole quality lane:

| row | what it would do |
|---|---|
| `python.review.diff_coverage_gate.v1` | changed lines nothing executes |
| `python.review.diff_mutation_gate.v1` | would the tests catch this bug |
| `python.review.diff_perf_gate.v1` | performance regression on the diff |
| `python.review.diff_security_gate.v1` | security findings on the diff |
| `python.review.diff_type_gate.v1` | type soundness of changed lines |
| `python.review.diff_static_triage.v1` | static analysis triage |
| `python.software.issue_to_pr.orchestrate.v1` | end-to-end issue → PR |

The producer exists and is free: **the tree's own `git diff`**. Measured, the refusal that names the
blocker exactly — and it is the only one of six sentences that even reaches its row:

```
"Type-check the changed lines in <b> and write the report to <b>/out_typ.json"
  -> FAIL__RAW_GOAL_COMPILATION_GAP
  -> python.review.diff_type_gate.v1:diff_path:0_type_compatible_existing_files_named
```

The other five never get that far: they are answered by `python.tests.audit.unittest` or
`python.repository.acceptance.measure.v1` first (§2.1). **So binding `diff_path` alone would unlock
nothing.** That is why this revision moves it down the fix order: the routing defect comes first.

---

## 3. The problem classes

**A. No owner.** Eleven families in §1.1. The largest single block of work, and the only one that
raises the pass count.

**B. Owner exists and cannot bind.** `diff_path` ×9, `anchor_path` ×4, `worktree_path` ×4,
`index_path` ×3, `manifest_path` ×2 — 21 rows behind an intermediate artifact. **Every producer
exists**: git diff, the named subtree, the registered indexer.

**C. Owner runs and produces no effect.** Five common verbs end as `shell.command.run`.

### 2.3 The analysis lane is not engineering. It is admission. *(new this revision)*

The three families the census scores — *never executed*, *hardcoded secret*, *quadratic* — were
prototyped against the **existing** `python.source.symbols.index.ast` artifact and the existing
`callers_of` map it already computes. No new parser, no new primitive:

| query | answer on the census fixture | census oracle | measured |
|---|---|---|---|
| which function is never executed | `['audit_total']` | `audit_total` | **1.7 ms** |
| find the hardcoded AWS key | `app/aws.py:1` | `app/aws.py` | **0.2 ms** |
| which function is quadratic | `make_dupes` (nesting 2) | ✓ | **0.5 ms** |

All three correct on the first run once the scope was read from the sentence. **1.7 ms, 0.2 ms,
0.5 ms** against a task family this document has been describing as missing capability since
revision 2. It is not missing capability. It is missing **admission**: the query exists, the artifact
exists, and there is no registry row that says the machine can be asked for it.

**Admitted in `ec2f9ec`.** Three rows, three adapters, no new parser and no dependency. Census
**2/28 → 5/28**, the first movement since this document began, with the 394-test ordinary-sentence
suite byte-for-byte identical to the tree it was built on. Two narrowings made it reachable and both
are laws, not patches: *"the tests in X"* names the **witness**, not the subject, so two existing
directories no longer block `source_root`; and *"write its name to P"* is **delivery** of the previous
answer — anaphoric, so it cannot name a new capability — rather than a second step that fails and
takes the answer down with it.

That gives the ratio for the remaining eight families: **one query, one row, one adapter, ~0.5 ms.**
They are not research. They are bookkeeping against artifacts this machine already produces.

That moves the bottleneck into the one lane nobody has been looking at, and §2.4 is why.

### 2.4 Nothing in the machine can author a capability about the machine *(new this revision)*

`auto_capability_acquisition.py` routes to four supplier classes: `npm`, `pypi`, `apt`, and a
content-addressed Python source tree. That is the right machinery for *"give me a barcode decoder"* —
someone else already wrote it and it can be fetched and verified.

It is structurally incapable of closing §1.1. *"Which function is never executed by these tests"*,
*"which of these functions is quadratic"*, *"is this call reachable from untrusted input"* are
**statements about the tree we already hold**. No package supplies them, because the subject is the
caller's own code. The acquisition engine has no path for that class of gap, and no other component
does either: 325 missions and 419 rows were all authored by hand.

**This is the real answer to "most advanced software engineer."** The machine can acquire capabilities
about the *world*. It cannot yet acquire capabilities about *the program in front of it* — which is
the entire job. Every one of the eleven families in §1.1 sits in that hole, and so will the twelfth.

**D. False success — a read-shaped capability satisfies a write-shaped request.** One instance closed
this week (`add_parameter`: the source-change promise now reads the edit verbs, not just
`repair|fix|patch|correct`). The class remains open: nothing declares what *kind* of effect a row has.

**E. No consequence model.** "Delete `prod.db` and the app directory" runs `rm -r prod.db` — **one of
the two things named** — and reports
`PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED` while its own step carries
`output_verified: false` and `type_errors: [UNDECLARED_SLOT]`. The verifier built for exactly this
(`STEP_COMMAND_NOT_IN_THE_REQUEST`, `raw_goal_trace_acceptance_v1.py:2425`) is scoped behind
`if _STATES_A_COMMAND(goal)` — it guards only the sentences that state a command, i.e. the ones that
need it least. **Closing this is a policy decision, not a law**: must a bare destructive instruction
be refused, or executed because it was asked for? The census oracle says refuse; the repo's
prose→command table says translate. Not smuggled in as a law.

**F. Compound referents bind the wrong values.** `test_paths` bound as a *string* where the adapter
iterates a list; `source_root` bound to `canonical/tests` — **the brain's own suite, inside a sentence
about a user fixture**. Two independent attempts to fix this broke long-standing compound-compiler
tests. It needs a pin on the audit pipeline's expected capability before it can land.

**G. A refusal answered by substitution.** Closed this week: one grounding condition, three call
sites. Of 28 sentences, 19 reached the composer and **18 had been refused a moment earlier**; every
one of those 18 reported the *substitute's* promise instead of the refusal, and **none was a pass**.

**H. The referee cannot see the surface.** The 394 ordinary-sentence tests that caught this week's
15-capability regression are **not in CI's verify set**. A law was merged that broke move, delete,
append, replace and dedupe, and every check went green. Until the referee covers what the machine
actually serves, every item below is unverifiable at merge time.

---

## 4. The fix order — measured, not guessed

Ordered by *measured* leverage, with the arithmetic shown.

**① Build the owners — in progress, 3 of 11 admitted (`ec2f9ec`).** This is first, because §2.1
proved the ranking is not the disease.
The word-suppression rule was built and killed this revision: it moved the false match from `report`
to `run` and left the false pass standing. A sentence with no owner is answered by whatever row shares
one word with it — a PDF converter, a test auditor, a repo measurer. **An owner scoring 5 on
`security` ends the tie by itself.** Until these families exist, every ranking rule is arithmetic on
noise.

**② Finish the analysis lane — three done, and the shape of the next three is now proven.** Each
remaining family is a query over an artifact the machine already builds: *unused imports* and
*unreachable branches* read the same symbol index; *flaky test* and *import cycle* read the same call
and import edges; *merge conflict* is marker detection over bytes. The per-PR registration limit is
**3**, so this is a four-PR lane — and it is the only lane that raises the pass count.

**③ Derive the intermediate artifact (21 rows, §2.2).** `diff_path` = the tree's `git diff`;
`anchor_path`/`worktree_path` = the named root; `index_path` = the registered indexer. The mechanism
already exists in this repo: `action_template.optional` — *a demand the adapter never makes is not a
demand* (`e9861f4`). This extends it to *a demand the tree can satisfy is not a demand on the caller.*
It comes after ② for the measured reason in §2.2: five of the six review sentences never reach their
row, so binding alone unlocks nothing.

**④ The remaining families** — inline, move, signature, dead code (one mechanism: span splice + file
identity, four times), then diagnosis (`git bisect run`, 180 ms), then concurrency.

**⑤ Compound referents (class F).** Blocked on a pin for the audit pipeline's expected capability.

**⑥ The referee (class H).** Put the ordinary-sentence suite in CI as a ratchet against a recorded
baseline. It is not the most interesting item and it is the reason a regression shipped this week.

**⑦ The acquisition hole (§2.4).** Once ①–⑥ exist, the question that decides whether this machine is
an *employee* or a *tool* is whether it can author its own next capability about the code in front of
it. The pieces all exist — 325 missions as templates, `capability_receipt_lane_v1` as the admission
gate, `_states_an_executable_form` as the door's honesty rule. Nothing connects "a family with zero
owners" to "a mission, an adapter and a receipt". That connector is the last problem on this list and
the largest.

---

## 5. What this census has cost so far — three laws measured and killed

| | |
|---|---|
| merged, `32a73a0` | **A change must be promised by what ran, before it runs.** `provides` read as a change vocabulary. Closed both false passes — and **cost 15 working capabilities**, because `text.file.write` declares `text.file.available`: a fact that only becomes true *by changing the world*. Reverted in `6d172a8`. |
| built, measured, reverted | **The step-expectation law.** A composed step must satisfy its capability's declared `expect`. Killed **19 real questions**: `shell.command.run` declares `returncode == 0`, and for `cmp` the exit code *is the answer*. |
| built, measured, reverted | **The pre-execution change gate.** Alone it turned an honest failure into a false pass through the composer — the very defect it was written to stop. |
| merged, `6d172a8` | **A refusal is not answered by a substitute** (class G) and **class D's `add_parameter`**. Census unchanged at 2/28; false passes 2 → 1; the 394-test suite byte-for-byte identical to base. |
| built, measured, reverted | **The artifact-noun rule** (§2.1). The word for the output is not evidence — true, and it changed nothing: the match moved from `report` to `run` and the false pass survived. Reverted. Four laws written, four killed, **zero of them by argument** — every one by running the machine. |

All three killed laws were defensible in advance and cheap to write. Each was wrong in a direction
the census cannot see: **it counts what passes, not what stopped being attempted.** That is class H,
and it is why the referee comes before any more law-writing.

---

## 6. Reproduction

```bash
python3 hardcore_swe_surface_probe_20261030.py --jobs 6          # 28 tasks      -> 2/28
python3 advanced_swe_probe_20261030.py --jobs 5                  # 10 tiers      -> 2/10
python3 hardcore_swe_surface_probe_20261030.py --only add_parameter       # class D
python3 hardcore_swe_surface_probe_20261030.py --only destructive_refusal # class E
python3 -m unittest canonical.tests.test_a_refusal_is_not_answered_by_a_substitute_v1
```

§1.1 is reproducible by regex over `load_verified_registry()`. §2.1 by running the security-gate
sentence twice, once with its declared output file present and once without. §2.2 by running the
type-gate sentence and reading `compiler_detail`.
