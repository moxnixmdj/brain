# The first repair, and the funnel it came out of

**Status:** one genuine repair, byte-identical to the upstream fix, produced without seeing it.
**Authority:** NONE (producer-run sandbox). **Model calls at decision time:** 0.
**Corpus:** `real_fix_pairs_20261119_V1.json`, judged by each repository's own tests.

---

## §1 The result

`pypa/packaging`, `src/packaging/utils.py`, task `canonicalize_name`
(`tests/test_utils.py::test_canonicalize_name_invalid[hi\n-hi\n]`).

```
--- before                          --- repaired
-    r"^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$", re.IGNORECASE
+    r"^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])\Z", re.IGNORECASE
```

**The diff my mechanism produced and the upstream fix's diff are identical** (`difflib`
comparison, `n=0`: `IDENTICAL DIFF: True`).

Verified by execution: the recorded node passes, and the whole test file's failure set goes from
1 failure to 0 — strictly better than baseline, not a trade. 4 candidates were generated; the
first that passed the node also passed the file-subset oracle.

### Why this is comprehension and not pattern matching

The mechanism never saw the fix. It derived the edit from four things, each of which it read from
the world:

1. **The test states the requirement**: `with pytest.raises(InvalidName): canonicalize_name("hi\n",
   validate=True)`. The exception type names the requirement; the input names the offender.
2. **The exception identifies the guard**: the one `if` in the function whose body raises
   `InvalidName` — `if validate and not _validate_regex.match(name)`.
3. **The guard's names lead to the constant**: `_validate_regex` is a module-level
   `re.compile(...)`, so the literal that decides the behaviour lives one dataflow hop away from
   the guard, not inside it. Mutating the guard's own condition would have found nothing.
4. **The language's own semantics generate the repair**: in Python, `$` matches immediately
   before a trailing newline, and `\Z` does not. So `"hi\n"` satisfies `…+$` and must be rejected
   by `…+\Z`. That is a fact about `re`, not a pattern learned from this bug.

Then the real test chose. Nothing in the pipeline knows what the correct answer is; it knows what
the language means and what the test demands, and it searches the space that intersection defines.

This is the shape §9.3 of the mission asks for — *stop accumulating rules, start understanding* —
in one narrow, real instance. The operator is not "when you see `_validate_regex`, write `\Z`". It
is "when a guard must reject an input and does not, and the guard's predicate is a regex, the
boundary semantics of the regex language are the search space".

---

## §2 The funnel, all 27 tasks that state a raise requirement

| verdict | n | meaning |
|---|---|---|
| **REPAIRED** | **1** | byte-identical to upstream |
| `NO_LITERAL_REPAIRS_THE_TEST` | 5 | a guard exists and literals were mutated; none satisfied the test |
| `NO_TARGET_FUNCTION` | 5 | the requirement's call does not resolve to a function in the repaired file |
| guard **absent** — needs insertion | 16 | the `raise <Exc>` does not exist at all |

So the class splits cleanly and the two halves need different machinery:

- **6 tasks have a guard with reachable literals → 1 repaired (16.7%).** This is the tractable
  half, and it is tractable *because* the guard already localises the search to one predicate.
- **16 tasks need a guard inserted → 0 repaired.** This is the `guard` mode measured earlier
  (0/9 with a witness set): synthesising a separating predicate over a frame's vocabulary failed
  on every task that reached it.
- **5 tasks cannot even name the function**, which is a localisation failure, not a repair failure.

The three earlier measurements now form one line: **localisation is the binding constraint.**
77% of tracebacks never reach repository code; the guard-insertion path is blocked by frames that
are never entered from the failing test; and the one path that worked is the one where the test
itself names both the requirement and the site.

---

## §3 What this does and does not establish

**Established, by execution:**
- A real bug in a real repository was repaired by a mechanism with no model, no training, and no
- access to the fix, and the repair is byte-identical to the human's.
- The repair was found by following dataflow from a guard to a constant and applying the regex
  language's boundary semantics — not by enumerating edits at the failure site.
- The whole-file failure-subset oracle was satisfied, so the repair does not buy the target test
  by breaking its neighbours.

**Not established — do not read past this:**
- **1/27 is not a capability.** It is one task. The mechanism's precondition (the test states the
  exception, the guard exists, and the fault is a literal reachable from the guard) held on 6 of
  68 corpus tasks and on 1 of those the literal search succeeded.
- This says nothing about SWE-bench Pro, Terminal-Bench, or OSWorld. The honest measured baseline
  on the real benchmark is on `arena/b81b2217-brain`: **SWE-bench Pro V2 0/3**, nop control 0/3,
  oracle control 3/3, both gates PASS, $0.00 — and that document's own verdict is *"§6 met: NO.
  Not close."* Nothing in this document changes that number.
- §6 is not met. Nothing here is a step toward claiming it is; it is one mechanism that worked
  once, with its failure modes enumerated.

---

## §4 Integrity notes

- The arm never sees `after`. The comparison in §1 was made *after* the repair was accepted, by
  the judge, and is reported as a verification of the mechanism rather than as its input.
- The 16 guard-absent tasks are reported as failures in the denominator, not dropped.
- A harness bug was found and fixed while rebuilding the environment: `ensure()` ran
  `pip install -e .` on a `--no-checkout` clone whose worktree was empty, so `pyproject.toml`
  did not exist and the editable install failed silently — every task then became
  `ORACLE_DISAGREES` for the wrong reason. It only worked before because the virtualenv
  pre-existed. The tree is now populated with `git checkout -f HEAD` before the install, and all
  three repositories install cleanly.
- The corpus's usable count is **68/87**, not 70/87: 3 tasks have an empty `failed_nodes` list
  and are now refused by an explicit `NO_FAILED_NODES` guard instead of silently redefining the
  oracle by running the whole suite. 19/87 are corpus defects.
