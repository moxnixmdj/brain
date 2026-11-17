# What is real, what is not, and why "let it experience each action once" did not happen

**Date:** 2026-11-16 · **Base:** `e2fff59b` · **Branch:** `arena/99dc5a50-brain` · **Cost:** $0 · zero model calls · authority NONE

The question, in the owner's words:

> "Instant learning + instant learning in new arbitrary environments — we already solved those perfectly.
> Doesn't this mean this is a perfect solution for all the problems and any computer use?"
>
> "We were trying to make our model a sentient creature. Is this true, or are there things that are wrong?
> What is real and what is not, and what are the smartest things we can do?"

This round did not argue about it. It ran the machine and read what came back. The answer is in four parts:
one thing that is **real and better than the claim**, one thing that was **fantasy**, one **defect found and
repaired**, and one **honest boundary**.

---

## 1. The fantasy I had to throw away first

The previous round's recommendation was to *build a synthetic twin substrate whose environments genuinely
share a machine*. That was the wrong move and the owner's own standing rule kills it: tests must be real.
A synthetic substrate would have been a model of a computer, tested against a model of a computer.

The real substrate was already in the tree:

```
canonical/runtime/computer_env_v1.py     ComputerEnv: a real temp directory, real subprocesses,
                                          real reset/snapshot/restore, actions discovered from PATH
canonical/runtime/transfer_learning_v1.py recall-then-execute; "a recalled plan is a HYPOTHESIS"
canonical/runtime/environment_reuse_v1.py replay_then_repair()
```

So the round ran on the real thing: this machine, its 603 installed programs, real files, real disk.

## 2. What is real — and it is stronger than the claim

The claim was that the machine learns an action by doing it once. Measured on this machine, for real goals:

```
$ python3 -c "computer_env_v1.discover(goal, budget=60, seed_file=...)"
'compress input.txt into out.gz'     closed=True  PASS__RECALLED_AND_REVERIFIED  plan=['run_gzip']       (0s)
'compress input.txt into out.bz2'    closed=True  PASS__RECALLED_AND_REVERIFIED  plan=['run_bzip2']      (0s)
'hash input.txt into out.sha256'     closed=True  PASS__RECALLED_AND_REVERIFIED  plan=['run_sha256sum']  (0s)
'encode input.txt into out.base64'   closed=False OPEN__EFFECT_NOT_VERIFIED       plan=[]                 (0s)
```

The right program, chosen by acting, with the output opened and checked before anything is called a success.
`discover()` does not ask whether a file appeared — it calls
`program_synthesis_v1.verify_round_trip`, which has a round-trip table, magic signatures, and a
`CONTAINER_MISMATCH` negative test. That machinery was built before this round and it works.

**So: instant learning of an action is real.** Not claimed — observed, correct, and cheap.

## 3. What was fantasy — and I caught myself doing it

I spent the first part of this round proving that the environment is "wrong 94% of the time." The
measurement was real, and the conclusion was wrong.

I had bypassed `discover()` and judged actions against the naive predicate `out.bin` *exists*. Under that
predicate, 17 actions "compress a file" and exactly one does:

```
run_arch       writes "arch (GNU coreutils) 9.1"        <- its own version banner
run_basename   writes "out.bin"                          <- its own argument, echoed
run_bzless     writes "------> out.bin <------"          <- its own banner
run_b2sum      writes a 140-byte checksum                <- a hash, not the file
run_bzip2      writes 65 bytes that bunzip2 restores     <- the actual job
```

`94%` false credit — against a predicate **the real path does not use**. The lesson is not that the machine
is broken. The lesson is that a measurement of the wrong predicate is not a measurement of the machine, and
"a file appeared" is exactly the kind of observable that makes a wrong action look right. I wrote a module
to fix this (`goal_truth_v1`), then found `verify_round_trip` already did it, and **deleted my module**. The
best part is no part.

## 4. The defect that *is* real, found and repaired

Asking the route for thirteen unrelated goals left thirteen rows in the permanent store. Every one recorded
`reached=True`. The plans were:

```
goal -> run_iconv                  (an encoding converter)
goal -> run_gp-display-src         (a Ghostscript source dumper)
goal -> run_x86_64-linux-gnu-cpp   (the C preprocessor)
goal -> run_unexpand               (a whitespace tool)
goal -> run_bzip2                  (this one really did compress)
```

Twelve different jobs, twelve confident permanent successes, mostly pointing at programs that do not do the
job. The cause was one line:

```python
# canonical/runtime/computer_env_v1.py:1526
gkey = "goal"          # every goal, one memory key
```

The fingerprint correctly excludes the target — a fingerprint is a fact about the *programs*, and the comment
there cites a measured reason: including the target turned every new filename into a cache miss at ~1,268 ms
each. That reasoning is sound. The error was that the goal's identity then appeared **nowhere**, so recall
matched across goals and wrote false successes to disk.

What kept this from producing wrong *answers* is that `_verify_plan` re-executes a recalled plan against the
target actually asked for. A stale memory costs one trial, not a wrong result. But every other reader of the
store — audits, similarity scoring, episode counts, the evidence bonus in `transfer_learning_v1.recall` —
was reading a plan labelled correct that was not.

**The repair** keys the memory on what the goal asks for, which the route has already parsed:

```python
gkey = "effect|target=%s|suffix=%s" % (target, suffix or "")
```

Two facts, both already computed, zero added cost. The words of the goal are deliberately **not** used:
"compress X into out.gz" and "gzip X into out.gz" are the same job, and keying on prose would rebuild the
paraphrase-cache-miss problem the fingerprint change was made to remove.

**Evidence.** `canonical/tests/test_learned_success_is_remembered_under_its_own_goal_v1.py` — 3 tests, each
running the real `_discover_impl` and reading what it wrote. Mutating `gkey` back to `"goal"` kills them:

```
AssertionError: 1 not greater than 1 : two different goals were remembered under one key: {'goal'}
FAILED (failures=2)
```

An earlier version of this test re-derived the key with its own helper and **survived that same mutation** —
it was testing the test. It was deleted and rewritten to drive the module. That mistake is recorded here
because it is the same species of error as the 94% figure: a check that cannot fail is not a check.

## 5. The boundary — where the claim actually stops

`composer_route_v1.extract_argv` is what decides which command to run. Nine real goals, real files, an
objective answer stated in advance:

```
RIGHT    sort the lines of words.txt            -> sort words.txt
RIGHT    show words in alphabetical order       -> sort words.txt
RIGHT    reverse the lines of words.txt         -> tac words.txt
WRONG    sum the second column of probe.csv     -> cut -s -f 2 probe.csv    [got '']
WRONG    print the first column of probe.csv    -> cut -s -f 1 probe.csv    [got '']
WRONG    largest number in the second column    -> cut -s -f 2 probe.csv    [got '']
WRONG    count the lines of probe.csv           -> wc -l probe.csv          [got '4 probe.csv', not 4]
REFUSED  count how many times apple appears     -> None
REFUSED  total the qty column                   -> None
```

**Of the 7 goals it chose to answer, 4 were wrong — 57%.** And every wrong one reported success: `cut -s`
suppresses lines without the delimiter, so it printed **nothing at all**, and nothing-at-all was accepted.

This is the boundary, and it is not a shortage of actions:

```
recall of a verified procedure   ->  permanent                                    REAL
producing the procedure for a NEW goal                                            NOT THERE
```

The machine has 603 programs and can run any of them. What it cannot reliably do is *choose*. "Sum a column"
becomes `cut -f 2` because the words match, and nothing in that path checks that a sum was ever computed.
This is the **synthesis–verification asymmetry** doing what it always does: composing two verified steps is
cheap, and knowing that the composition answers the question asked is not.

## 6. "Sentient creature" — the honest answer

No. Nothing measured in this round produces an action. Every gain came from removing an obstacle between a
decision and an effect, or from correcting a record of what happened. The 57% is not a failure of will or
experience: it is a router matching words, with no machinery that could tell it the answer was empty.

The one thing that looked most like a mind this round was the memory of success — and its most impressive
property, thirteen confident permanent lessons, was a bug that made it remember successes that were not.

A creature that cannot move its hand is not less sentient, and neither is a machine that cannot tell an
empty answer from a right one. Neither is fixed by more experience. Both are fixed by connecting the nerve.

## 7. What the smartest next move is

One change, and it subsumes the rest. **Make a pass require an effect about the thing that was asked for.**

The evidence is already in hand:

- `cut -s -f 2` printed **nothing** and was accepted. Empty output is not an answer.
- `wc -l` printed `4 probe.csv` when the goal asked "count the lines" — right tool, unparsed answer.
- `_single_step` already refuses `NO_VERIFIER_FOR_FORMAT` and `MAGIC_MISMATCH`; the shell path has no such
  check, so `returncode == 0` is doing the work of a verifier.

Order matters, and the order is: **judge first, then decide.** A router taught to balance quotes and handle
awk while `empty output == success` still holds will produce *confident empties* instead of honest refusals —
strictly worse, because a refusal is information and a confident empty is not.

The second move, only after the first is in place: **widen the verifier from a table to the machine.** The
round measured this and the honest number is small — of 36 formats examined, the hand-written table covers
15, magic signatures 5, and the machine's own decoder programs add **2** the table lacks (`.base64`,
`.base32`). `discover()`'s most common refusal is `OPEN__EFFECT_NOT_VERIFIED`, and the table is why. But a
2-format gain is exactly the incremental improvement the owner does not want, so this is not the next move —
the judge is.

## 8. One line

**Instant learning is real; it is recall, not production; and this round found that it was recording
successes that were not successes, and that the chooser is wrong more often than it is right and always
sounds sure.** The machine does not need a mind. It needs to be stopped from calling an empty file an answer.

---

### Receipts

| What | Where |
|---|---|
| The repair | `canonical/runtime/computer_env_v1.py` (`gkey`, one line + the measurement above it) |
| The tests | `canonical/tests/test_learned_success_is_remembered_under_its_own_goal_v1.py` (3 tests, ~265 s — they run real programs) |
| Mutation kill | `gkey = "goal"` → `FAILED (failures=2)`, message names the collision |
| What was deleted | a `goal_truth_v1` module that duplicated `program_synthesis_v1.verify_round_trip` |
| Store state | polluted episode file reverted; probes write to temp stores |
| Integrity guard | `repo-integrity-guard: base=e2fff59b rules=17 violations=0 -> PASS` |
| Load-bearing admission | 8/8 ok |
| Regression | `test_computer_env_v1`: **81 run, 3 failed — all 3 fail identically at baseline**, see below |

**The three pre-existing failures, named so they are not mistaken for this round's work.** All three raise
`FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT`, which is the *stale pin registry* measured
at the start of this round (`LEGACY_VERIFIED_SITE_DISAPPEARED` — the pins are keyed on
`(module, lineno, api)` and the lines moved). Verified by reverting `gkey` to `"goal"` and re-running
`TransferTests`: **the same 3 tests fail, with the same names, at baseline.** So this round neither caused
nor hid them.

**One test in that suite hangs and is not mine either:** `test_a_goal_no_program_can_reach_is_reported_not_invented`
(`discover("turn the input into out.png")`) ran >420 s at baseline and >420 s with this change — it is an
exhaustive search for a goal nothing can reach. It is excluded from the run above and **left unfixed on
purpose**: a timeout on a search that is supposed to fail is a real defect (the search has no bound), and
bounding it belongs in the round that fixes the judge, not in a one-line memory-key repair.

Authority: **NONE**. No weights, no model calls, no network, no benchmark or sentience credit. `$0`.
