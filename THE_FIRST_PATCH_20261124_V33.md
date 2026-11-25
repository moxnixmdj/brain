# THE FIRST PATCH — an emission point exists, and it cannot change what a parser computes
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters

> **Requirements restated.** Own model, zero runtime model calls, no parameter warehouses world facts, every
> parameter derived and justified, instant knowledge external and removable, project then web, name the real
> limiting factor, kill the idea first, verified / unverified / failed with evidence, hardest real tests,
> never ask the user, one branch. §2 boundary unchanged.

V32 established the denominator (12 provably fail-to-pass tasks) and the blocker: **the system had no emission
point**. This round builds one and runs it on exactly those 12 tasks.

---

## 1. Result

| | v32 baseline | v33 |
|---|---|---|
| patches emitted | 0 / 12 | **1 / 12** |
| tasks solved | 0 / 12 | **0 / 12** |
| changes to what the code computes | — | **0** |

One number moved: emission. Resolution did not. That is the whole result, and it is worth more than the
previous thirteen rounds because it is the first time the system has produced a patch at all.

## 2. Why the baseline emitted nothing

`solve()` returns a capability envelope (`status`, `routing`, `required_inputs`). `build_goal()` asks for
`{"actions":[{"type":"terminal_exec",…}]}`. No code path connected them, so every task stopped at
`CAPABILITY_INPUTS_MISSING` before anything was attempted. The emission point closes that gap directly: it
takes the failing node, reads pytest's output, and returns a unified diff.

## 3. What it is allowed to see

Only what a developer sees: the checkout at the buggy commit, the failing node, and pytest's exception type,
message, assertion operands and traceback. The localisation comes from the traceback the interpreter produced.
It never reads the fix commit, its diff or its message, and the instruction text is pytest's own output — no
prose from me, because these commits carry no issue text and anything I wrote would be my summary of the fix.

## 4. The mechanisms, and the two that survived

Each is keyed on the reported exception. None mentions a repository, a task, or a bug.

| mechanism | precondition | what it does | outcome |
|---|---|---|---|
| `MISSING_KEYWORD` | `TypeError: f() got an unexpected keyword argument 'k'` | add `k` keyword-only to `f`, **and thread it to the state class that consumes it** | emitted, still failing |
| `MISSING_ATTRIBUTE` | `AttributeError: 'C' object has no attribute 'a'` | initialise `a` from the sibling collection `C` already maintains | refused |
| `MISSING_ORDERING` | `TypeError: '<' not supported between …` | add the four ordering methods over the class's own key | refused |
| `WRONG_STRING` | a string assertion with a near-miss | strict prefix/suffix rewrite of the format literal | refused |
| `WRONG_CONSTANT` | a scalar assertion with a literal | replace that literal | refused |

The one emission, `hukkin/tomli@5ab9ec92`, produced:

```diff
-def loads(s: str) -> Dict[str, Any]:
+def loads(s: str, *, parse_float: Any = None) -> Dict[str, Any]:
-    state = ParseState(s)
+    state = ParseState(s, parse_float=parse_float)
 class ParseState:
-    def __init__(self, src: str):
+    def __init__(self, src: str, parse_float: Any = None):
+        self.parse_float = parse_float
```

Correct structure, correct threading, and the test still fails — because the parameter is **stored and never
applied**. Changing that means editing the number-production path inside the parse loop.

## 5. What the eleven refusals say

| reason | tasks |
|---|---|
| the failure states a fact about a **value** the code produced, not a structure | 5 |
| no exception matched at all (mock-call mismatch, assertion with no signature) | 3 |
| the class holds no sibling attribute to derive from | 1 |
| the class's comparison key lives in an attribute the mechanism could not locate | 1 |
| the only candidate edit was inside a test file, which the writer refuses | 1 |

**This is Wall 2, stated properly.** It is not that the generator cannot *reach* the program — the traceback
localises the site in every case. It is that there is no **operator** that can express the change once the
site is known. Adding a signature is a structural edit; changing what a parser computes is a behavioural one.
The project's synthesis machinery has structural operators and no behavioural ones.

## 6. An integrity defect I introduced and caught

The first version localised two tasks into `tests/test_misc.py` and `benchmarks/resolver.py` **and edited
them**, because pytest's short traceback names the test frame. It also reported `git diff` across the whole
tree, so the "produced patch" contained the oracle test applied to make the node runnable.

That is the exact violation this project refuses: *a patch to the test is a patch to the oracle*. Both defects
are fixed at the writer (`is_writable` refuses any path under `tests/`), the localiser excludes test frames,
and the reported diff is scoped to the edited file. A test now fails if any recorded diff touches a test.

It is recorded here, not quietly removed, because the first version looked like a **33% emission rate** and
was contaminated.

## 7. Verified / unverified / failed

**Verified by execution:** 12 tasks run end to end on real checkouts; 1 patch emitted and confirmed to apply;
0 solved; the per-task reason for all 12; the writer refuses `tests/` and `conftest.py`; no recorded diff
targets a test file; 6 new tests pass.

**Failed, mine, this round:** the first generator version (oracle editing, contaminated diff, a `git diff` that
included the oracle patch); the first `_thread_keyword` (threaded into `TOMLDecodeError`, then double-applied
into a `SyntaxError`); the first `WRONG_STRING` (substring coincidence: matched `'2.5'` against a version
constraint in `benchmarks/resolver.py`). Three self-inflicted defects, each found by running it.

**Unverified:** whether a behavioural operator, once built, would lift these 12. That is the next experiment,
not a claim.

**Still not producible:** any SWE-bench Pro / Terminal-Bench / OSWorld row, and no comparison to any frontier
model. Twelve small single-node bugs in two repositories.

## 8. The single next object

**A behavioural operator.** The traceback already names the site in 9 of 12; what is missing is the ability to
change the value that flows out of it. The smallest such operator that covers the largest share of these
failures is *replace the expression that produces the wrong value with the expression the assertion implies* —
general, sourced entirely from pytest's `assert produced == expected` rendering, and it would cover the five
`value` failures plus the four ordering/attribute ones if expressed over the AST rather than over strings.

## 9. Cost and tests

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0
network_during_build: two git clones · duration 8.2 s for all 12 tasks
```
