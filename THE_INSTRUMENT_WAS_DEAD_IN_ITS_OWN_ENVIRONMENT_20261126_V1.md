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
