# The refusal is the other half of the operator

*Round dated 2026-11-19. Receipt: `canonical/verification/THE_REFUSAL_IS_THE_OTHER_HALF_20261119_V1.json`.
Tool: `canonical/tools/the_refusal_is_the_other_half_v1.py`. Tests: 12, all green. Ten real actions driven by ten
real binaries on this machine, 19 coordinates, 38 refusals, 48 executions, 0.6 s. No model, no parameters, no
network.*

---

## 0. The answer, in the form the question was asked

> *"Give the model the most advanced coding actions, let it experience each once, and it learns them permanently.
> Doesn't that solve all of computer use?"*

**Half right, and the missing half is exactly what makes an action usable.**

Take one real action and one real success — `mkdir files/nodir/sub` in a directory where that is legal. It works.
What has the agent learned? Enumerated exhaustively over the facts of that action, a single success leaves **16
hypotheses alive out of 56**, and **4 distinct behaviours** that all explain the same success. It knows the action
ran. It does not know *when* it will run. That is not a gap of effort: a success says *"this state is in the
domain"* — a point. Applicability is a *boundary*, and a point never shows a boundary.

Now remove one fact and run again. Without the parent directory: `mkdir: cannot create directory 'files/nodir/sub':
No such file or directory`. With `sub` already there: `mkdir: cannot create directory 'files/nodir/sub': File
exists`. Two states, two different messages, and the case for each is *named by the program itself*.

Measured on ten real actions and nineteen coordinates:

| | one success (the plan in the question) | one refusal per coordinate (this round) |
|---|---|---|
| executions | 10 | 48 |
| hypotheses alive | 16 (of 56) | 1 |
| distinct behaviours alive | **4** | **1** |
| actions whose precondition is identified | **0** | **10 / 10** |

And the refusals cost nothing to take: **36 of 38 left the tree byte-identical**, and the two that did not wrote only
`patch`'s own `files/a.txt.rej` — **zero objects changed by any refusal**. A refusal is not an experiment on the
world. It is a *statement about* the world, issued by the only authority that holds the precondition.

> **A try is not the unit of learning. The operator has two halves: its effect, which a success shows, and its
> precondition, which only a refusal can show. The schedule is 1 success + k refusals — not 1 try — and the
> refusals are free, so the boundary costs no effect.**

## 1. Why a success cannot do it, in one line of arithmetic

A hypothesis about a precondition is a conjunction of facts. A success is consistent with every hypothesis true in
that state — it removes nothing *below* itself. A refusal removes everything true in the violated state — an entire
down-set. Only a cut partitions. With `k` coordinates the k-th is invisible until it is the one removed, so
identification needs `k` cuts, and there is no schedule that buys them with successes.

The project had already measured both directions of this without putting them together:

| already measured | where | value |
|---|---|---|
| one success identifies applicability | `what_a_success_teaches_20261112.py` | **0 / 200** |
| chosen failures identify it | same | **25 / 25 in 2.76 demonstrations** |
| the precondition is not in the trace | `THE_PRECONDITION_IS_NOT_IN_THE_TRACE_20261126_V1.json` | 10 actions, **160 states**, `identified_ever: 0`, `best_accuracy: 1.0` |
| one demonstration's precision | `ONE_DEMONSTRATION_IDENTIFIES_20261116_V1.json` | **0.069**, 297 dangerous errors of 319 |
| the reach ceiling of experience | `WHY_ONE_EXPERIENCE_IS_NOT_ENOUGH_20261116_V1.md` | **18.7%** asymptote, 75.2% of 2,178 fix pieces rebuilt by no operator any other task produced |

Note the shape of the third row: a rule with **accuracy 1.0 that is never identified**. That is the trap this
project keeps meeting — agreement without identification — and it is why 160 interventions failed where 19
refusals succeed. The facts were sufficient to *predict*; they were not sufficient to *separate*. A refusal
separates, because it is a cut and not a sample.

## 2. What makes the refusal a declaration rather than a hint

The claim this round tests is structural, and it is tested without reading English:

* **injectivity** — distinct violated coordinates produce distinct messages: **10 / 10 actions**;
* **invariance** — the same coordinate under a *different distractor* (other names, other contents, other files)
  produces the *same* message: **10 / 10 actions**.

A function that is injective on causes and invariant to everything else is a function *of the cause*. That is what
makes it usable as a fact-name rather than as prompt text: `File exists` and `No such file or directory` are not
prose to be interpreted, they are the two branches of a predicate, and they were measured to be exactly that on ten
independent programs.

The witnesses, one pair per action, are in the receipt. A few:

```
mkdir   absent  → mkdir: cannot create directory 'files/nodir/sub': File exists
mkdir   parent  → mkdir: cannot create directory 'files/nodir/sub': No such file or directory
rmdir   empty   → rmdir: failed to remove 'files/dir': Directory not empty
rmdir   exists  → rmdir: failed to remove 'files/dir': No such file or directory
gzip    gzip    → gzip: files/x.gz: not in gzip format
gzip    exists  → gzip: files/x.gz: No such file or directory
git     stash   → No stash entries found.
git     clean   → error: Your local changes ... would be overwritten by merge
```

The only hand-written part is the rewrite that strips paths and distractor names before comparison — one part,
counted as one, and a test asserts it does not also strip the distinguishing words.

## 3. Three places where a check is not the fact — all measured, none hidden

The refusal is reliable at naming the fact it dropped. The *checks* the same programs publish are a different
matter, and this round caught three distinct failures of them:

1. **`tar -tzf` accepts a gzip whose payload is not a tar archive** — exit **0**, no output. The check is
   narrower than the fact it is used for ("is this an archive?"), and it is the check-mode lever of the previous
   round's own limits, found in the wild.
2. **`git stash list` exits 0 on an empty list** — the exit status carries *success of the query*, not the fact
   asked. A sensor built on the exit code alone is always true.
3. **`patch` writes a `.rej` before refusing** — a refusal with a side effect, so "failures are free" is a measured
   claim with a named exception rather than an assumption.

None of these is a bug in the tools. Each is the same law this project has been circling: **a check, a message, or
a report is a claim with a scope, and the scope must be measured, never assumed.** Which is why the schedule is
*cuts from refusals, verified on states* — not trust in declarations.

## 4. What the frontier is doing, and the part it has not measured

The 2026 answer to "should the agent see its failures?" is yes, and it is called *early experience*: *"the agent also
explores what happens when it clicks different buttons or fills forms incorrectly, observing error messages, page
changes, and other outcomes. These observations become learning signals without explicit rewards."* [1] The same
signal is used mechanistically in precondition-error re-prompting [2], and in 2026 the practitioner's loop for
coding agents is exactly this: run it, read the failure, repair the precondition, keep the check.

The frontier therefore *uses* refusals as supervision. What is missing from that literature is the property that
makes refusals enough for our purpose: **a refusal is not a soft training signal, it is an exact function of the
violated fact** — injective and invariant, measured above. Because it is exact, one refusal per coordinate replaces
a version space of 160 states and the assistant needs no gradient. That is the difference between "failure data
improves a policy" (statistical, unbounded, expensive) and "a refusal names the missing predicate" (exact, `k`
observations, zero effect on the world).

## 5. The single bottleneck, now that four of them are closed

The chain this project has measured, in order:

| link | state | evidence |
|---|---|---|
| the decision to act | closed: a free attempt decides it under a judge | `THE_FAILED_ATTEMPT_IS_FREE` |
| the goal's last bit | closed: an agreement is not an equivalence; a proof decides | 983 runs, 0 disagreements, 1 equivalent statement |
| the effect's name | closed: computed from the signature, 0 extra trials | 44 cells, 5 names × 2 preimages |
| the precondition | **closed here**: 1 refusal per coordinate, 10/10, free | this receipt |
| composition | closed over measured cells | 16 requests, 14 solved, 0 prediction mismatches |
| **the fact vocabulary** | **open** | 0/10 identified *without* it, 10/10 *with* it |

So the answer to the question that matters — *what one fix unlocks the most capability* — is now unavoidable and
narrow:

> **The bottleneck is the columns, not the rows.** An action can be tried any number of times and still be
> unusable, because using it requires a predicate the agent can *evaluate*. Everything else in the chain is
> arithmetic; the fact vocabulary is the one thing nobody can sample, refuse, or prove into existence. A refusal
> names a missing fact in words, and turning those words into a decidable predicate is a **construction** — the
> sensor. Each sensor is a new column, and reach is exactly the number of columns: 18.7% over 500 real tasks
> because 75.2% of real fix pieces needed an operator that no amount of experience of the existing columns produced.

This is the same law as the last two rounds, at the last layer. The goal's last bit was a *statement* that had to be
proved rather than guessed; the effect was a *name* that had to be computed rather than written; the precondition is
a *fact* that has to be constructed rather than sampled. In all three cases **the representation is the artifact,
and experience only fills it in.**

## 6. What this means for the model we are building

Not "store what `cp` does". The weights are for two universal translations, both *calculated*, both verified by a
probe:

1. **declaration → operator**: a contract (usage line, options, error template, schema, docstring) into roles,
   preconditions and effects. The environment supplies the text; the model computes the operator; one conformance
   probe checks the implementation against it.
2. **refusal → fact-name**: a message into the predicate it names. Measured here to be well-posed (injective,
   invariant), so this is a *translation* task with an exact target, not a vibe.

Everything else — which facts exist, what each action does, whether they compose — lives in instant knowledge as a
table that a probe wrote and a proof sealed. The parameters hold no knowledge house; they hold the two translators.
That is the governing law applied literally: the schedule is `1 + k`, the table is a fold over measurements, and
the parts you would have had to *design* — a vocabulary, a learner, a reward — are the parts that are not there.

## 7. What is real, what is not

**Real.** One success leaves 4 behaviours alive; 19 refusals collapse it to 1 on all ten actions; the refusal is
injective and invariant over ten independent programs; refusals change no object; the schedule is 48 executions and
0.6 s, with 0 model calls, 0 parameters, 0 network.

**Not real.** "Experience each action once and it is learned." "A refusal is a soft signal to be averaged." "A
published check means the fact it names." The first is half an experiment, the second throws away exactness, the
third is false on this machine in three separate ways.

**Limits.** Ten actions, one machine, one producer. The fact vector is hand-written, and that is the bottleneck
named above, not a detail. Identification is *up to the states measured*: one behaviour over these states, not over
the world. The message rewrite is a declared part. A refusal names a missing fact; it does not say how to obtain it,
and nothing here builds the remedy.

## 8. Next step, pre-registered

**Construct one column.** Take a refusal whose named fact is *not* in the vocabulary — `git` saying
`fatal: not a git repository`, `ssh` saying `Permission denied (publickey)`, or `tar` saying
`Cannot open: No such file or directory` on a path the agent believed existed — and measure the cost of turning that
message into a decidable predicate:

1. the predicate must be **decidable without the failed action** and non-intervening (state unchanged);
2. it must be **sound and complete on held-out states** for that action, i.e. it decides applicability exactly —
   `accuracy 1.0` *and* a single surviving behaviour, not merely high accuracy;
3. it must be **expressible from what the machine already offers** (an `ls`, a `git rev-parse`, a `stat`, a
   `--dry-run`) with no new binary and no new fact beyond the named one;
4. and the number of such constructions needed per real task must be counted, so the reach ceiling is *priced per
   column* instead of quoted as an asymptote.

Falsifiers: if a named fact cannot be turned into a decidable predicate at all, the bottleneck is not construction
but expressiveness, and the claim collapses to "some refusals are unusable" — which would need its own count; if the
constructed predicate reaches accuracy 1.0 with more than one surviving behaviour, then the refusal was not exact
and this round's injectivity result is narrower than claimed; if the construction needs a fact the machine cannot
decide, the column is not in the environment and no schedule reaches it.

---

## Sources

1. *Agent Learning via Early Experience* (arXiv 2510.08558v3, May 2026) — reward-free supervision from the agent's
   own interaction, explicitly including the outcomes of doing things incorrectly and observing error messages.
2. *CAPE: Corrective Actions from Precondition Errors* — injecting the parsed precondition error into the next
   planning step; the mechanism this round makes exact.
3. Retained from the merged rounds: OpenAI Frontier Evals' retirement of SWE-bench Verified (23 Feb 2026);
   *The SWE-Bench Illusion* (63–76% file-ID from issue text); Leavens & Pigozzi on behavioural equivalence versus
   behavioural provability; *Cross-substrate execution identity* (identity factors through the behavioural
   quotient); *Adaptive state-action abstractions via rate-distortion* (refine when abstraction error dominates).
