# The oracle that cannot choose

**Round 16 · 2026-11-24 · branch `arena/80a7e8eb-brain`, base `c4f529eb` · 0 model calls, 0 parameters, $0**

Round 15 ended on a question it could not answer, and was honest that it could not:

> what signal prefers one **arrangement** of atoms the project already holds over another, without the hidden tests?

This round answers it, and the answer is that the one oracle an agent is permitted to consult **cannot choose**.

---

## 1. The question, sharpened

Round 15 measured that the material is never the problem: of 26 sampled changed files on SWE-bench,
**23 introduce no name the project does not already hold** and **none need the standard library**.
The material is present. The *arrangement* is missing.

An agent solving a task may consult: the issue text, the source tree, the repository's own tests,
the conventions of neighbouring code. It may not consult the task's new tests — those are hidden,
and using them is leakage.

So the only question that matters is: **does the repository's own test suite select the change that
was asked for?**

Nobody in this project had ever asked it. Every repair measurement in the tree was on small
synthetic corpora. That is the gap this round closes, on the real benchmark.

---

## 2. How it was asked (and why the answer cannot be an artefact of leakage)

New tool: `canonical/tools/can_the_visible_suite_select_v1.py`

It builds **arrangements from a file's own atoms** — four families, each generated *from the program*,
not from a list of known fixes:

| family | what it is |
|---|---|
| `leaf` | a name becomes another name the same file spells |
| `operator` | one operator for another of its class |
| `bind` | a name is rebound to a built-in applied to itself — at the top of its function, **or immediately before the statement that consumes it** |
| `put_in` / `take_out` | one statement of the function copied beside another, or removed |

Then it asks each arrangement the only question a permitted oracle can answer: *do the repository's
own tests still pass?*

**The integrity line.** The search and the green filter run on a **pristine** tree — the task's tests
never applied. The hidden tests are applied only **afterwards**, to a separate copy, to score the set
the search produced. The tool derives the module labels its own suites live in from the test patch,
but `measure()` never receives the fail-to-pass list. That is test-locked
(`test_the_search_function_never_receives_the_fail_to_pass_list`), because a claim this inconvenient
must not be able to become true by accident.

---

## 3. The measurement

### `django__django-16527` — the expert change is one leaf

`and has_change_permission` → `and has_add_permission` in `submit_row`.

```
space (arrangements of the file's own atoms)     7,945
sampled (evenly, stride 99)                         80
GREEN under the repository's own 7-test module      34   (42.5%)
   ... the expert's change is one of them:  leaf:has_change_permission->has_add_permission
GREEN that ALSO pass the hidden new test             0 of 34
hidden oracle is valid:  with the expert change True / unmodified False
```

### `django__django-15741` — the expert change is one inserted line

`format_type = str(format_type)`, immediately before the statement that consumes it.

```
space                                            24,924
sampled (evenly, stride 311)                         80
GREEN                                                 8   (10.0%)
   ... the expert's change is one of them:  bind:get_format:format_type=str@115
GREEN that ALSO pass the hidden new test              0 of 8
hidden oracle is valid:  with the expert change True / unmodified False
```

---

## 4. What this means

The expert's change was **green** — the repository's tests never rejected it. So were 33 and 7 others.
Not one of those alternatives passes the hidden test, and the hidden oracle is shown valid on both
tasks. The green set is a mixture of the right answer with wrong answers *this oracle cannot separate*.

The wall is therefore **not** where three rounds have been looking:

- **not generation** — both expert changes are produced by a generator that reads only the file;
- **not style** — the first version let `ast.unparse` reformat, so every style test rejected
  everything; after that was fixed the expert's change went green;
- **not that the green candidates are broken** — they are *genuinely* green, the suite really passes;
- **information** — the hidden test is the only thing that separates 34 survivors, and an agent may
  not see it.

The repository's own suite is a **regression** oracle. "Run the tests and keep what passes" — the loop
this project has proposed three times — keeps what does not *break*, which is a different and much
larger set than what was *asked for*.

---

## 5. Seven defects this round found in its own instrument

Recorded because each one produced, at some point, a plausible and wrong number:

1. the replacement pool was the file's first 24 names alphabetically, so the expert's target
   (`has_add_permission`, 25th) was never tried — 0 of 0 rather than 0 of 1;
2. `NodeTransformer` over a shared tree mutated it in place, so candidate N carried candidates 1..N−1
   — 205 candidates, every one naming the target;
3. comparing candidates to the expert by **bytes** reported "not reachable" for a change that was;
4. `ast.unparse` over the module, then the function, reformatted quoting — a one-name exchange
   arrived as a 134-line diff and every style test rejected it;
5. the `bind` family inserted **into the function's docstring**, because it took the first line of an
   unparsed body;
6. the insertion site was computed once, for the wrong name, so the "before the consumer" site never
   fired;
7. a run cut off by the sandbox's time limit **left a wrong candidate in the tree**, and the next run
   reported 0 green of 80 against 34 — a plausible number that was entirely the previous run's
   litter. The tool now restores on every exit path, including a kill.

Defects 5–7 are pinned by tests.

---

## 6. Honest standing

**Verified** — both numbers above, with a valid hidden oracle on both tasks; the expert's change is
generated and green on both; 0 of the green sets pass the hidden test; 12 tests pass; no leakage path
from the hidden tests into the search.

**Unverified** — that these two tasks are typical. They are two. The claim is about the *kind* of
oracle and does not rest on the count, but no rate over SWE-bench is claimed.

**Failed / not done** — no task resolved, no capability gained, `capability_credit_delta` 0. No ranker
is proposed. An in-function-only probe (leaf swaps restricted to the changed function) was attempted
twice and exceeded the time budget both times; it is listed as open, not as done.

**Carried correction from round 15** — "zero dollars" was never verified there; what was established
was *0 model calls, 0 parameters*. This round spends nothing and claims only that.

---

## 7. The next bottleneck

A signal that separates *"this arrangement is the change that was asked for"* from *"this arrangement
breaks nothing"*. It cannot come from the tests, from the patch shapes other tasks used, or from the
issue's quoted code — all three are measured. Three untested candidates, each cheap:

1. the issue text's description of **absent** code — feature requests describe behaviour rather than
   quote a line;
2. the convention of the **immediately neighbouring** code, as a prior over which atom belongs in
   which slot;
3. whether **any existing test touches** the changed behaviour at all — a suite that passes is worth
   less than one test that touches the line.
