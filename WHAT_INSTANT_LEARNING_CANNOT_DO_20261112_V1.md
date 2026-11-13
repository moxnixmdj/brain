# Instant learning: what is real, what is not, and what the boundary actually is

**Date:** 2026-11-12 · **Base:** `a89c5bb5` (PR #6813, merged) · **Cost:** $0 · zero model calls

The claim under test, in the owner's words:

> "Instant learning + instant learning in new arbitrary environments — we already solved those perfectly."
> "We were trying to make our model a sentient creature."

This round asked the only question that can settle it: **is it true, and if not, exactly where does it stop?**
It was settled by measurement, not argument. The measurement found a real defect and closed it. It also
found the wall, and named it precisely.

---

## 1. The answer, in one paragraph

Instant learning is **real, durable and cheap** — the machine does permanently internalise a procedure it
has performed once. What it is **not** is generative. Today's measurement put the boundary in a place the
claim does not cover: `shell.command.run` is a verified capability, it requires **nothing**, it scored
**highest of every candidate (20.0)** for the sentence "run a shell command" — and **every single sentence
that named a command was refused.** The machine could not reach a capability it had already verified, could
not run a command it had already proven it could run. Four independent defects sat in series between the
sentence and the shell. Each one was repaired. **Six of the ordinary tasks that were refused a round ago
are now performable** — but only when the sentence *states* the command. The thing the machine still
cannot do is **decide** the command.

That is the exact boundary: **instant learning makes an action permanent; it does not produce the action.**

---

## 2. What was found — four defects, in series

At the start of this round the claim "the capability is missing" had already been refuted once. This round
found something worse: **the capability existed, was verified, and was unreachable.**

```
shell.command.run        requires: []        status: VERIFIED_BOUND_CAPABILITY
keywords: shell, command, exec, run, terminal, bash, ... sort
keyword_candidates("run a shell command") -> 20.0   <-- highest of all candidates
act("run a shell command")  ->  NOT_CALLABLE_WITH_WHAT_GOAL_PROVIDES:['argv']
act() then reported:  AMBIGUOUS__NO_DECISIVE_MARGIN
survivors:  forged.agency_finite_portfolio_generator      0.0
            forged.automationbench_mutation_compiler      0.0
```

The failure report pointed at **routing**. The cause was **binding**. That misdirection is itself a
finding: `act()` reported only zero-score forged rows as survivors, hiding the one rejection that
mattered. Any future audit must print `rejected` before concluding "coverage gap".

The capability itself was healthy — proven by calling it directly:

```
cli_command.run({'argv': ['awk','-F,','{s+=$2} END {print s}','probe.csv'],
                 'output_path': '.../sum.txt', 'write_stdout_to_output': 'true'}, '.')
-> {'returncode': 0, 'stdout': '10\n', 'output_verified': True}     # 3+5+2, correct
```

### The four defects

| # | Layer | What was wrong | Why the refusal was *correct* |
|---|---|---|---|
| 1 | **binding** | `complete_inputs` had no `argv` notion; it dropped any slot it had no branch for | the adapter cannot run a command it was not given |
| 2 | **rendering** | `"${input.argv}"` is a whole-value placeholder; it was stringified | the adapter got `"['ls', '-la']"` and rightly refused `CLI_ARGV_REQUIRED` |
| 3 | **declaration** | a row could not say an output is *not required*, so a destination nobody asked for was synthesised, then demanded | the adapter could not verify an artifact that did not exist |
| 4 | **registry** | the row declared `python_stdlib` with **no modules** | acquisition raised `BOUND_PYTHON_STDLIB_MODULE_REQUIRED` |

Each refusal was correct — **each was refusing a value that had been mangled or invented upstream.** This
is the general shape of the failure and the reason it survived so long: every layer reported honestly
about the wrong input, so no single layer ever looked wrong.

### Two more, exposed only by making commands runnable

Once a command could finally execute, two ways of **running the wrong thing** became visible:

- **Shell syntax was misdispatched.** The adapter passes argv to a program with *no shell* — deliberately,
  because a shell is how an argv becomes something other than the argv that was checked. So
  `cat a > b` became `['cat','a','>','b']`: it printed **both files instead of writing one**, and
  reported success. Pipelines and redirections are now refused. The guard reads the **command body only**
  — a quoted regex `'a|b'` is a pattern, not a pipe, and scoping the guard to the whole sentence broke
  `egrep 'a|b'` (a live regression, caught and fixed).
- **A word in a tool name rerouted the request.** `ls | head -2` matched the keyword `head` on
  `git.history.bisect_regression.v1`, which requires **nothing** — so it survived and answered
  `VERIFIED_ACTION` **by bisecting this repository's history**. A request for a pipeline was answered by a
  history bisect and called verified. Now: once a sentence *states* a command, only rows that can execute
  one are eligible — derived from each row's own `argv` template argument, not from a hand-written list.

---

## 3. What is real now — measured, not asserted

```
run the shell command cat probe.csv            VERIFIED_ACTION   'name,qty\napple,3\npear,5\nplum,2\n'
run the shell command sort probe.csv           VERIFIED_ACTION   'apple,3\nname,qty\npear,5\nplum,2\n'
run the shell command diff probe.csv probe.csv VERIFIED_ACTION   (exit 1 is the answer, not a failure)
run the shell command ls -la                   VERIFIED_ACTION
sort the lines of probe.csv                    VERIFIED_ACTION   <-- refused last round
run a shell command                            AMBIGUOUS         (nothing stated -> nothing executed)
run the shell command ls | head -2             AMBIGUOUS         (cannot be honoured -> refused)
run the shell command cat probe.csv > out.txt  AMBIGUOUS         (cannot be honoured -> refused)
audit the python source structure              VERIFIED_ACTION   python.source.audit.ast (unchanged)
```

**The safety rule that governs all of it:** a command the sentence does not state is **never invented**,
because an invention executes. That rule is not reimplemented — it is `composer_route_v1.extract_argv`,
reused. Forking it would fork the safety property.

**Regression evidence.** Over the **37 test files that touch this path**: **284 failing before, 275
after, zero new failures.** The narrowness of the `optional` rule is load-bearing: the first version
withdrew every declared-optional key and broke **5** existing tests, because seven rows still interpolate
`${input.X}` for a key they also declare optional. `canonical/tests/test_stated_command_reaches_the_shell_v1.py`
— 26 tests.

---

## 4. What is *not* real — the boundary, stated exactly

Every one of the six ordinary tasks refused a round ago is performable by a **stated** shell command this
machine can now run. What it cannot do is **decide** which command to run.

```
learning:   experience one verified run  ->  the procedure is permanent     REAL
generation: given a new goal            ->  produce a procedure that never existed
```

Instant learning sits entirely on the left of that arrow. It is **recall of verified procedures**, not
production of new ones. It makes a generated action permanent; it does not generate the action. The owner's
claim is true about memory and false about generation, and today's measurement was taken exactly at that
line: the machine had the procedure, had verified it, ranked it first — and still could not reach it.

**And a fifth defect, recorded rather than hidden:** a program that needs quotes of its own is still
mangled. `awk -F, '{s+=$2} END {print s}' f` is cut at the first closing quote, binds `['awk','-F,']`,
runs it, produces **empty output**, and — because the row's postcondition is only `returncode == 0` —
reports `VERIFIED_ACTION`. That is the same failure this round removed, one layer out: *a pass with
nothing behind it.* `WhatThisDoesNotYetDoTests` pins today's behaviour so it fails loudly when fixed,
instead of being quietly forgotten.

---

## 5. Why "sentient creature" is not the right frame — and what is

Nothing in this round found a mechanism that produces an action. Every gain came from **removing an
obstacle between a decision and an effect**. That is the honest description of what the system is: a
machine that gets steadily better at *not losing* the capabilities it has verified. Its intelligence, such
as it is, lives in the selection — and the selection was already working (11/11 paraphrase routing).

The three defects that mattered this round were not intelligence failures. They were **plumbing failures
wearing intelligence's clothes**: a system that reports `AMBIGUOUS` while holding the exact capability it
needs is not confused, it is *disconnected*.

> A sentient creature that cannot move its hand is not less sentient. It is just a creature that cannot
> move its hand. The fix is not more sentience. It is connecting the nerve.

---

## 6. What the smartest next move is

1. **Make `VERIFIED_ACTION` require an effect about the named object.** The awk case above is the proof:
   `returncode == 0` is not an answer. This is the single highest-leverage change available and it is
   already partly built — `UNJUDGED` exists in the code and is unused.
2. **Teach the parser to balance quotes** — a one-function change that turns the fifth defect into a
   passing case (awk, sed, perl all become reachable).
3. **Then** re-run the ordinary-task census, now separating **coverage gaps** (no capability exists) from
   **binding gaps** (one exists and cannot be reached). Conflating those two is what hid this whole round.

Order matters: (1) before (2), because a parser that balances quotes while `VERIFIED_ACTION` still accepts
an empty result will produce *confident empties* instead of *confident refusals*.

---

## 7. One line

**Instant learning is real and it is only recall.** It makes a verified procedure permanent — and this
round proved it by repairing four layers between a verified procedure and the sentence that named it. What
it does not do, and what today measured it does not do, is *produce* the procedure. The system does not
need to become a creature. It needs to be wired to its own hands.
