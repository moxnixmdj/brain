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
