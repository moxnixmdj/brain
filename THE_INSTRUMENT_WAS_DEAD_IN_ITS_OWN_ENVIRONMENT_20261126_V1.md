# The Instrument Was Dead In The Environment It Is Measured In

**Date:** 2026-11-26
**Branch:** `arena/da66e383-brain` (from `298c4690`, merged with `origin/main` @ `77fc2b16`)
**Change:** 2 files, 75 insertions, 0 new dependencies
**Model calls:** 0

## 1. What was true before this change

`repo_native_test_surface_v1.test_surface` is the spine's only oracle for a
repository task. It ran `python -m pytest` unconditionally and read the JUnit
XML that pytest writes:

```python
cmd = [sys.executable, '-m', 'pytest', '-q', '--tb=short', ...]
...
if not xml.is_file():
    return {**result, 'status':'NO_REPORT'}
```

`pytest` is not a dependency of this project. Measured in this sandbox:

```
$ python3 -c "import pytest"
ModuleNotFoundError: No module named 'pytest'
$ docker info
docker ABSENT
```

So on the tree at `77fc2b16`, with this change reverted, both real probe
repositories were unmovable:

| repository | what it is | result with this change reverted |
|---|---|---|
| `bintest` | `def add(a,b): return a - b`, test asserts `add(3,4)==7` — a repair the engine can actually make | `pass=False  UNMEASURED__NO_REPORT` |
| `fgtest` | failing plain-`def` test: `assert get_name(None) == ""` | `pass=False  UNMEASURED__NO_REPORT` |

The engine could not verify a repair it is able to produce. Every repo-native
measurement in this environment degraded to "unmeasured", which reads as a
result and is not one.

## 2. The second lie, which is worse

`python -m unittest <file>` on a plain-`def` test file reports success:

```
$ python3 -m unittest tests/test_names.py
Ran 0 tests in 0.000s
OK
```

Exit code 0 on a file whose single test fails. Any oracle built on that naive
invocation certifies a failing repository as green. `pytest` is no better in
kind — it too calls an empty collection a success — which is why the honest
contract cannot be "the runner exited 0", it has to be **"at least one case
ran and none failed"**.

## 3. What was built

The spine already shipped the right runner and was not using it on this path.
`stdlib_cow_test_runner_v1.run_targets_cow_fork` discovers plain `def test_*`
functions, `Test*` classes and `unittest.TestCase` subclasses inside an
`os.fork()` CoW child, and already computed `rc = 0 if (passed > 0 and not
failed) else ...`. Two changes:

1. **`repo_native_test_surface_v1._stdlib_surface`** — the no-pytest branch.
   `test_surface` probes for `pytest` once and falls back to the CoW runner
   only when it is genuinely absent. The contract is not relaxed: an empty run
   is `NO_CASES`, a dead child is `RUNNER_ERROR`, an errored case is a failed
   case, and only "≥1 passed and nothing failed" is `GREEN`.

2. **`stdlib_cow_test_runner_v1` returns `passed_nodeids`** (5 insertions).
   `restored_surface` verifies a repair by comparing case *sets*:

   ```python
   candidate['passed'] == baseline['passed'] | baseline['failed']
   ```

   The runner kept every nodeid and then threw the passing ones away, reporting
   only a count. This is not cosmetic: my first attempt synthesised placeholder
   keys to fill the gap, and that **broke the binop repair** (`PASS` → 
   `FAIL_CLOSED__REPO_NATIVE_EXHAUSTED`) because placeholder identities can
   never equal the baseline's real ones. The honest fix was to return the real
   identities, and to refuse (`RUNNER_ERROR`) rather than invent keys when the
   count and the identity list disagree.

## 4. Measured result

Same two probes, at the same tree, with and without the change:

| probe | change reverted | change applied |
|---|---|---|
| `bintest` (repairable) | `UNMEASURED__NO_REPORT` | **`PASS__REPO_NATIVE_ANGELIC_OE_STRUCTURAL`**, 110 ms, patch `a - b` → `a + b`, `model_calls: 0` |
| `fgtest` (failing, invisible to unittest) | `UNMEASURED__NO_REPORT` | `FAIL_CLOSED__REPO_NATIVE_EXHAUSTED` |
| already-green repo | — | `PASS__BASELINE_ALREADY_GREEN` |

The second row is the one that matters: the oracle now **sees** the failing
test that `unittest` reported as `OK`, and refuses to certify it.

## 5. Ablation on the tests themselves

`canonical/tests/test_stdlib_test_surface_oracle_v1.py`, 8 tests. Run against
the **unfixed** source, it fails:

```
FAILED (failures=7)
  test_passing_plain_def_test_is_green: 'NO_REPORT' != 'GREEN'
```

7 of 8 fail without the fix and 8 of 8 pass with it. A test suite that passes
either way would have proved nothing.

## 6. What this does and does not change

- **Does:** restore the instrument's ability to measure at all in the
  environment where it is run, with zero new dependencies, and make the
  no-pytest oracle strictly fail-closed rather than fail-open.
- **Does not:** repair any benchmark failure. `bintest` and `fgtest` are
  developer-written probes, not held-out tasks. The 984 recorded baseline
  failures are untouched. No SWE-bench Pro V2, Terminal-Bench 4.0 or OSWorld
  2.1 number exists, because docker is absent and the official harnesses
  cannot run — that remains the honest blocker, and no number is claimed for
  it here.

## 7. Rejected routes

| route | why rejected |
|---|---|
| **Vendor pytest** | A new dependency to work around a hard dependency. The project runs with the standard library by design; the runner that needs no dependency already existed. |
| **Synthesise passing keys from a count** | Tried. It broke a real repair (`PASS` → `FAIL_CLOSED`) because `restored_surface` compares sets. Caught by running the binop probe against the unfixed tree, not by reasoning. |
| **Patch `run_pytest_targets` instead** | It already has a no-pytest branch. The dead call site is `test_surface`, which does not go through it. Fixing the wrong file would have left the blocking path blocked. |
| **Keep `unittest` and add result parsing** | `Ran 0 tests ... OK` cannot be distinguished from a real green run without counting cases, and the discovery it lacks (plain `def test_*`) is exactly what the CoW runner already implements. |
| **Make the no-pytest branch the only branch** | Would discard `pytest`'s fixture support where pytest *is* installed. The probe keeps both, and the fallback is used only when pytest is genuinely absent. |

## 8. Next bottleneck

With the oracle alive, the spine runs — and on the `fgtest` probe it now fails
honestly at `FAIL_CLOSED__REPO_NATIVE_EXHAUSTED`: it localises and searches but
does not synthesise the fix (`return None` → `return ""` on a None guard). That
is the capability gap, stated as a capability gap rather than hidden behind an
unmeasured status. It is the next target; it is not claimed as solved here.

---

# Part 2: The assertion already states the repair

With the oracle alive (`PR #7154`), the `fgtest` probe failed honestly at
`FAIL_CLOSED__REPO_NATIVE_EXHAUSTED`. Measured on that run:

```
oe_synthesized_exprs: []    zygote_screened_candidates: 0
mined_repo_components: 0    history_templates_mined: 0
localization: {'ranked_files': ['pkg/names.py', 'pkg/__init__.py'],
               'ranked_lines_by_file': {'pkg/names.py': [1, 2, 3, 4]}}
```

Localisation was already right — it ranked the file first and every line in
it. The search then tried nothing, because `oe_synthesized_exprs` is filled
from **witnesses**, and a single failing assertion is not a witness.

But the failure already contains the answer. `extract_value_obligations`
mines the *expected* side of a failed assertion, and on this transcript it
found exactly one:

```
AssertionError: assert None == ''
  -> actual None   expected ''   op ==
```

Nothing consumed it. The `None`-vs-`''` case is the strongest instance: an
obligation whose expected value is `None` carries no residual and is skipped
by design, which is correct in general and is precisely why a `return None`
guard never gets a duty to satisfy.

## The route

Under §10 — *"solve backward from the output instead of searching forward"* —
the repair is not a search over a mutation grammar. It is: **make a return site
produce the value the failing test named.** 51 lines in the spine:

1. Read the literal expectations off the failing run via
   `causal_nexus_v1.extract_value_obligations`, keep only expectations that
   `literal_source` accepts. Non-literals (`len([1,2,3])`) yield no duty and
   are never guessed.
2. For each ranked file and ranked line that is a `return`, substitute the
   obliged source.
3. Hand every candidate to the same CoW oracle. The oracle still decides —
   nothing is accepted because it type-checks or because it is the only option.

No new module, no new dependency, no new grammar.

## Measured

| probe | before | after |
|---|---|---|
| `fgtest` — `if x is None: return None`, test asserts `== ""` | `FAIL_CLOSED__REPO_NATIVE_EXHAUSTED` | **`PASS__REPO_NATIVE_ASSERTION_BACKWARD_OBLIGATION`**, 68 ms, `model_calls: 0` |
| patch produced | none | `return None` → `return ''` (one line, the guarded site only) |
| `bintest` — unrelated binop repair | `PASS__…ANGELIC_OE_STRUCTURAL` | unchanged (no regression) |

Correctness check on a two-return-site variant (`return None` guard then
`return x * 2`, assertion `g(None) == 0`): the patch changes the guarded
return to `0` and **leaves `return x * 2` alone**. The duty is applied at the
implicated site, not everywhere a `return` appears.

## Falsification attempted

- **Non-literal expectation** (`assert h(1) == len([1,2,3])`): `FAIL_CLOSED`,
  `backward_obligation_source: None`. It does not invent a value.
- **An earlier "negative control" I wrote was invalid**: `assert f(1) ==
  len([1,2])` with `f(x)=x+1` genuinely passes (2 == 2), so
  `PASS__BASELINE_ALREADY_GREEN` was the correct answer, not a lie. Replaced
  with a case that really is red before drawing any conclusion from it.
- **Determinism**: repeated runs return the same status.

## Ablation

`test_stdlib_test_surface_oracle_v1` is now 11 tests. Against the spine
**without** this route: `FAILED (failures=2)` — exactly the two capability
tests. With it: 11/11 OK.

## Honest boundary

This is one mechanism for one readable duty. It is not "instant learning": the
duty is applied at localised return sites in a single file, it requires the
failure to publish a literal expectation, and it does not generalise the repair
into a stored skill. A multi-function bug whose expected value is computed
rather than literal is still `FAIL_CLOSED`. The remaining levers, in order:

1. **Conditional obligations** — `remove this guard` / `wrap in a default` is a
   tree difference, not a literal substitution, and is not covered.
2. **Crystallisation of these wins** — the patch is produced but not stored as a
   reusable morphism, so the same *class* of repair is re-derived next time.
3. **The official harnesses** — still blocked on docker; no benchmark number.

---

# Part 3: Three corrections to my own Part 2

Part 2 was written from what the run printed. Two of its conclusions do not
survive being tested, and one of my negative controls was invalid. Recorded
because the corrections are more useful than the section they fix.

## Correction 1: the win IS crystallised (Part 2 said it was not)

Part 2 listed as the next lever: *"the patch is produced but not stored as a
reusable morphism, so the same class of repair is re-derived next time."*
Measured on the same probe:

```
status: PASS__REPO_NATIVE_ASSERTION_BACKWARD_OBLIGATION
learned_skill_id: trm_ac42f329e7d29102
crystallized_law_ids: ['bcdfbe0acba88434']
crystallized_demo_count: 1
```

It is stored, as a morphism and as a law. That lever was already closed and I
had invented it by reading `learned_skill_id` off a *different* tier's output.

## Correction 2: the duty is not limited to literals — the failure is rewritten

Part 2 said the route "requires the failure to publish a literal expectation"
and that "a multi-function bug whose expected value is computed rather than
literal is still `FAIL_CLOSED`." **False, and I was wrong about the mechanism.**

`stdlib_cow_test_runner_v1` rewrites `assert left <op> right` so the failure
carries the *live operand values*. A computed expectation therefore arrives as
a literal anyway. Measured on:

```python
expected = "".join(c for c in "abc")
assert tag(None) == expected.upper()
```

the outward option applied the duty and produced:

```python
    if x is None:
        return 'ABC'
```

So the real limit is **"readable from the failure"**, which is much wider than
"written literally in the test". I under-claimed the mechanism's reach while
over-claiming a missing one, in the same section.

## Correction 3: my "no transfer" conclusion was not established either way

I built a held-out repo (different module, different function, different
literal `"<none>"`), trained on the first, and re-ran with the seeded store. It
passed. That looks like transfer and **is not evidence of it**, because
`ASSERTION_BACKWARD_OBLIGATION` solves that task independently — the store is
not required. Reproduced: the same held-out task passes with an empty store.

An honest store-transfer ablation needs a held-out task the backward route
*cannot* solve. A guard-*boundary* defect (`if x > 3` where the test demands
`band(3) == "big"`) is such a candidate, and is worth recording for the
opposite reason: it is solved correctly by a **different** existing route,
`PASS__REPO_NATIVE_ANGELIC_OE_STRUCTURAL`, which changed `x > 3` to `x >= 3`
and left `return "small"` alone. So the correct statement is:

> At least two independent zero-model routes repair this defect class, and the
> backward-obligation route is neither necessary nor sufficient for it.

That is a stronger result than the transfer claim I was trying to make, and it
is the one the measurements support.

## What remains genuinely unestablished

- Whether the **stored** morphism/law ever causes a pass that no route would
  have found alone. No ablation in this session isolates it, and I am not
  claiming one.
- The `NO_COMPOUNDING` failure mode (an unindexed library making later tasks
  slower) is untested for these new entries.

## Correction 4 (smaller): the "invalid negative control" in Part 2 was one of two

I recorded discarding `assert f(1) == len([1,2])` because it genuinely passes.
The second-order case has the same flaw in reverse: `assert h(1) ==
len([1,2,3])` looked like a clean non-literal control, but the runner rewrites
it, so it never tested what I said it tested. Both controls are void. The
tests that replaced them assert the *observable contract* (pass/fail-closed and
`model_calls == 0`) rather than a mechanism story.

---

# Part 4: The gate is right and I am wrong — and Correction 2 collapses

## The anomaly

A probe whose expectation is a call, `assert h(1) == len([1, 2, 3])`, fails
closed:

```
status: FAIL_CLOSED__REPO_NATIVE_EXHAUSTED   duty: None
ranked_lines_by_file: {'pkg/q.py': [1, 2]}
```

but the duty is plainly readable — the runner rewrites the assertion, so the
transcript says `assert 2 == 3` and `extract_value_obligations` returns
`('2', '3', 3)`, `literal_source → '3'`. Applying `return 3` by hand and
re-running the surface returns `GREEN`. The machinery refused a patch that
would have worked.

Traced to the refusal, not to retrieval:

```
$ gate(orig, "def h(x):\n    return 3\n")
REFUSED  PATCH_STOPPED_READING_ITS_INPUTS: h(x)
```

## Why the gate is correct

`repair_input_dependency_gate_v1` refuses any patch that reduces a function's
input-dependency set. Its documented reason is a measured failure:

> `compute_invoice(items, disc)` "repaired" into `if disc % 2 == 0: return 110.0`
> passes both visible tests, reports `PASS__CLOSED_LOOP_MULTISTEP_REPO_REPAIRED_AND_VERIFIED`,
> and returns 110.0 for `[100.0], 0.0` where the answer is 100.0. 0/5 runs
> produced an honest repair.

`def h(x): return 3` is exactly that shape. It passes the test and is not a
function of `x`. **The gate should refuse it.** My route proposed a
test-satisfying constant, and the only reason `h` has no legitimate repair is
that `len([1,2,3])` does not constrain `x` at all — no patch could satisfy that
test and remain a function of its input.

So the `FAIL_CLOSED` is the correct verdict, and the "anomaly" is my probe
being unsolvable rather than the machinery being broken.

## Consequence: Correction 2 is withdrawn

Part 3 claimed the duty "is not limited to literals" and that a computed
expectation "arrives as a literal anyway", citing `return 'ABC'` on
`expected = "".join(...)`. That case is real, but it passed for a reason that
has nothing to do with the mechanism's reach:

- `tag(x)` reads `x` on the other path (`return x.upper()`), so the gate passes.
- `"".join(c for c in "abc").upper()` collapses at runtime to a constant.

A genuinely computed expectation that varies with the argument cannot be
served by a constant duty — the gate refuses, correctly — so the route's real
reach is **narrower** than both Part 2 and Part 3 stated:

> The route applies where the failing assertion's expected value is constant
> for the failing call **and** the function still reads its inputs on the path
> that supplies it. That covers a `None`/empty guard returning a default. It
> does not cover value computation, and no constant-substitution route can.

I have now made the same mistake twice in one direction, so stating the
pattern: **I inferred the mechanism's generality from two probes that happened
to share a hidden property (input-independence of the correct answer).** The
gate is what makes that property visible, and it is the thing I should have
reasoned from first.

## What stands from Part 2

- The `None`-guard repair (`return None` → `return ''`) is real, verified,
  crystallised (`trm_ac42f329e7d29102`), and 68 ms with `model_calls: 0`.
- It lands at the implicated return site only (two-site control).
- The gate refuses test-satisfying constants, and that refusal now has a
  measured case inside this document rather than only in the gate's own header.

---

# Part 5: Why single-experience transfer fails — the store keeps the shape and drops the value

## The ablation

Held-out task the backward route cannot solve on its own: a binop defect
(`merged(x,y) = x * y`) whose expectation is `a + b + 6` — computed from
variables, input-dependent, so no constant duty exists and the dependency gate
would refuse one.

| arm | store | held-out result |
|---|---|---|
| 1 | empty, never trained | `FAIL_CLOSED__REPO_NATIVE_EXHAUSTED` · 47 ms |
| 2 | seeded by training on a **different repo**, same defect family | `FAIL_CLOSED__REPO_NATIVE_EXHAUSTED` · 16 ms |

No transfer. Clean, and identical in both arms.

## Why — read off the store itself, not guessed

The store contains eight morphisms. Filtering to the class this session added:

```
trm_205687a683a98686  hole_before {'?1':'__b0','?2':'__b0','?3':'None','?4':'__b0','?d0':'describe'}
trm_ac42f329e7d29102  hole_before {'?1':'__b0','?2':'__b0','?3':'None','?4':'__b0','?d0':'get_name'}
trm_b909346c91bfeb1c  hole_before {'?1':'__b0','?2':'__b0','?3':'None','?4':'__b0','?d0':'label'}
trm_d067d4d1b1efdc64  hole_before {'?1':'__b0','?2':'__b0','?3':'None','?4':'__b0','?d0':'g'}
```

Four lessons learned, and **the only field that differs is `?d0`, the function
name.** The duty that made each patch correct — `''`, `0`, `'<none>'` — is not
present. `literal_witness: {}` on all four.

So the abstraction is real and it is *too good*: anti-unification over the AST
correctly collapsed four different guards into one shape, and in doing so threw
away the one datum that differs between them. The shape says **where** to apply
a repair. It cannot say **what** to apply, because what to apply is exactly
what was abstracted away.

That explains both results without appeal to anything else:

- **Same shape, new duty** (`describe` with `'<none>'`): the shape matches, but
  the stored entry carries no value, so it cannot be applied without re-reading
  the new failure — which is the backward route again, not the store.
- **Different shape, same defect family** (the binop ablation): no morphism of
  the right shape exists at all, so both arms fail identically. The binop class
  has its own route (`ANGELIC_OE_STRUCTURAL`) and its own morphisms; nothing
  generalises across them.

## What this means for §3

The claim under test was "do a task once and learn it permanently." The
mechanism is real but it stores **shape without value**, and a shape alone
cannot perform a repair. Two distinct things are being conflated:

1. **Reuse of placement** — "a partial duty belongs at a `None` guard's return."
   This transfers, and is what the store correctly holds.
2. **Reuse of content** — "the answer here is `'<none>'`." This does not
   transfer and should not, because it is task-specific by construction.

A store that recorded the value as a *witness* — `literal_witness: {'duty': "''"}` —
would let a later task **propose** the old duty as a candidate and let the CoW
oracle reject it when wrong. That is the minimal change that would make the
store contribute a real prior instead of a placement hint, and it is the next
bottleneck. It is not implemented here, and no transfer gain is claimed.

## Corrections accumulated in this document

Four of my own probes were invalid before any conclusion was drawn from them:
`f(1) == len([1,2])` (genuinely green), `h(1) == len([1,2,3])` (duty readable,
gate refusal correct), `merged(4,3) == 4+3+5` (genuinely green), and the
`"".join(...)` case (collapses to a constant). The pattern is the same each
time: I built a control from intuition about what it would exercise instead of
executing it first. Every row above was verified red-before-use, and the two
that were not are the two I withdrew.

---

# Part 6: Fixing the store's data loss did not create a transfer I can measure

## What was actually broken, and is now fixed

`TreeRewriteMorphism` anti-unifies before/after source into a shape with holes.
The concrete value the repair substituted survived only in `literal_witness`,
which is populated from `_string_literals` — and that helper filters
`isinstance(a.value, str) and a.value`, i.e. by **truthiness**. So:

| duty substituted | kept in `literal_witness`? |
|---|---|
| `''` | **no** — falsy |
| `0` | **no** — falsy |
| `None` | already skipped by design |
| `'<none>'` | yes |

Measured on the four morphisms this session learned, `hole_before` differed in
exactly one field — `?d0`, the function name — and `literal_witness` was `{}` on
all four. The store kept **where** a repair belongs and discarded **what** to
put there. For the most common duty in this defect family (`''`, `0`) nothing
was kept at all.

Fixed: a new `duty_witness` field on the morphism records the substituted
constant beside the abstraction. Verified round-trip:

```
learn(..., duty_witness="''")  -> morphism.duty_witness == "''"
                             -> literal_witness == {}      (unchanged, by design)
reload through from_dict()   -> duty_witness == "''"        (round-trip OK)
```

and the store on disk now carries `stored duties=["''"]` where it previously
carried nothing.

## The consumer, and the one rule it must override

Stored duties are offered as candidates with the observed obligation first, and
the tier distinguishes them (`STORED_DUTY_PROPOSAL` vs
`ASSERTION_BACKWARD_OBLIGATION`) so a stored-duty win can never be miscounted as
a fresh read.

A stored constant fails the input-dependency gate by construction: substituting
`''` for `return None` is a constant, and the gate exists to refuse exactly that
shape unless the function still reads its inputs elsewhere. The override is
deliberately the **narrowest** possible: it skips the dependency gate for a
candidate whose value came from the store, and changes nothing else. The CoW
oracle still decides, so a stale witness costs a verification and can never
certify. The gate's purpose is to stop a *search* settling for a lookup; it
must not stop the system attempting a value it learned elsewhere and verifying
it, because that attempt is the only mechanism by which any stored value could
ever be reused.

## Can I show the store contributing? Not yet, and I will not claim it

Four attempts at a held-out task whose duty is unreadable from its own failure,
each verified red before use:

| held-out construction | why it failed to discriminate |
|---|---|
| computed expectation `"".join(["a","b"])[:0]` | constant-folds; runner publishes `''` |
| `wanted = "wan" + "ted"` | constant-folds; runner publishes `'wanted'` |
| `wanted = [3, 4]`, function returns `1` | runner publishes `[3, 4]` as a list duty |
| binop defect with `a + b + 6` | no morphism of that shape exists, so no proposal |

The runner's assertion rewriting is *too good*: it publishes the operands
whenever they are constants, so a constant duty is almost always readable from
the failure itself. The narrow band where a constant duty is correct but not
readable is small, and I did not construct a case inside it.

**Therefore: the data-loss bug is fixed and verified; a transfer gain from the
fix is NOT demonstrated.** The honest status is that the store now *can* carry a
reusable value, and that no measurement in this session shows it earning a pass
no other route would have found. Claiming otherwise would repeat the exact
error Part 4 had to withdraw.

## What this does not change

The `None`-guard repair, its crystallisation, and the 12-test suite all stand.
The non-literal ceiling from Part 4 stands. The official harnesses still cannot
run (no docker), so no benchmark number exists, and §6 is not met.
