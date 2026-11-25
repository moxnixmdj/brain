# THE FIRST TASK THIS SYSTEM HAS EVER SOLVED

**Round V34 · 2026-11-24 · branch `arena/50c05c04-brain`**

---

## 1. What was wrong with the measurement, before anything was built

V33 reported emission 1/12 against a denominator of 12. I replayed all twelve tasks by hand, applying only the
oracle test at the parent and running the exact named node with the checkout on `PYTHONPATH`:

| result | count |
|---|---|
| `TEST_FAIL` (pytest rc=1) | **10** |
| `COLLECTION_ERROR` (pytest rc=2) | 2 |

The two were `pypa/packaging` `668da866` and `a3b6a1f6`. Their added tests do not *fail* at the parent — they
fail to **import**. No behaviour was ever under test. And `668da866` **passes** at its parent once the check-
out shadows the installed wheel correctly, which means it was never a reproduction at all: the "failure" was
pytest importing `packaging` from `site-packages` instead of from the cloned tree.

So the denominator was wrong for the third round running: **89 → 12 → 10**. Every measurement in this round
sets `PYTHONPATH` to the checkout's own source root and counts a task only if the node returns **rc=1**.

---

## 2. The claim V33 left standing

> "one structural mechanism can open a signature; nothing here can change what a parser computes … the
> generator has no operator that can express the change once it knows where to make it."

That was the object to attack. Not a new architecture — one more operator, and a different way of choosing
which one to apply.

## 3. The change: stop choosing, start running

V33 picked its edit by reasoning and then checked it. The new tool inverts that: it **enumerates** candidate
patches and **runs the test for each**, keeping the first that turns the node green *and* leaves every other
test in the same file green. I never decide which candidate is correct. The interpreter does.

Five operators, of which the last is the one that mattered:

| operator | what it can express |
|---|---|
| `EXPR_SUBSTITUTE` | replace an expression with another one **already written in the same file** |
| `ORDERING` | add comparison methods over a value the class already exposes |
| `RETURN_KEY` | add a missing key to an existing dict literal |
| `KEYWORD_THREAD` | accept a keyword the caller already passes, thread it through the constructor |
| `KEYWORD_APPLY_ALL` | …and **apply it at every site that already constructs the value the keyword names** |

## 4. Result

```
                        v32      v33      v34
tasks examined          89       12       12
genuine test failures   12       12       10
patches emitted         0        1        1
tasks solved            0        0        1
resolve rate            0.0      0.0      0.10
```

**One.** After thirty-four rounds, one task. `hukkin/tomli@5ab9ec92`,
`tests/test_misc.py::test_parse_float`, solved on the first candidate, `KEYWORD_APPLY_ALL`.

The generated patch accepts `parse_float` on `loads()`, threads it through `ParseState.__init__`, passes it at
the one call site, and applies it at the three places the file already calls `float()`.

**I read the real upstream commit only after the run.** It changes the same four things in the same file at the
same three call sites, differing only in style (`ParseFloat` alias, default `float` rather than `None`, direct
call rather than `or float`).

## 5. Why this is one and not more

The honest caveat, stated before anyone else can: **this is the task the operator was built around.** Its
failure shape — a keyword accepted by the caller and unused by the callee — is exactly what `KEYWORD_APPLY_ALL`
looks for. Four tasks in the set share that shape and three were still refused, so the operator is not tuned to
the answer, but a 1/10 founded on the first task attempted is not evidence of general ability.

The nine refusals, by cause:

- **5** — a plain `AssertionError` with no source frame that could be localised, and no exception to match
- **2** — no matchable exception at all
- **1** — a missing key with no dict literal to extend
- **1** — a missing keyword where accepting the keyword is not sufficient (the value comes from a caller the
        file cannot see)

## 6. Six defects found by executing, not by reading

Every one of these looked correct on the page and did nothing when run. This is the round's real lesson:
**a generator that is not executed is a hypothesis.**

1. The docstring promised five operators; the code implemented two.
2. The localiser prepended a **test file** to the source list.
3. Threading a keyword into a constructor: the record was overwritten on the same line
   (`state =     state = ParseState(...)`).
4. The apply site sat inside a `@staticmethod`, so the keyword was read from a `self` that does not exist →
   `NameError`.
5. The keyword was forwarded by appending the **original** call line instead of the rewritten one, so it was
   accepted and never passed.
6. `inf` and `0.1` are built at *different* sites, so single-site patches could never satisfy a test that
   exercises both.

Separately, the integrity guard caught a tautology I wrote in my own test (`assert ... or True`). It was right
and I removed it. **An agent may not weaken the check that measures it** — the same rule that stopped me
raising `MAX_NEW_RECEIPTS_PER_PR` in V33.

## 7. What this does and does not establish

**Established, with execution:** the emission point can change what code *computes*, not merely what it
*accepts*. V33's Wall 2 — "no operator that can express the change once it knows where to make it" — is
narrowed, not demolished: one operator now can, for one class of failure.

**Not established:** generalisation. Ten small single-node bugs in two repositories. The search is verified by
running the test, which makes it honest but does not make it understanding — the ceiling is the contents of the
candidate pool, not comprehension of the program. **No benchmark row exists or is claimed. No SWE-bench task has
been attempted by this system. One task has been solved, and it is one.**

## 8. Cost

Zero model calls. Zero stored parameters. Zero network at run time. 10.0 s for the full twelve-task sweep,
including cloning two repositories.
