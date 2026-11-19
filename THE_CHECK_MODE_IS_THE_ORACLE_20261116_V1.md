# The check mode is the oracle

*Round dated 2026-11-16. Receipt: `canonical/verification/THE_CHECK_MODE_IS_THE_ORACLE_20261116_V1.json`.
Tool: `canonical/tools/the_check_mode_is_the_oracle_v1.py`. Tests: 14, all green. No model, no weights, no
parameters, no network at run time. The systems under test are git, GNU tar, gzip, chmod and patch,
executed; nothing here is a model of them.*

---

## 0. The answer on one page

The question this round was handed was the previous receipt's own next step: for every action whose
deciding fact is invisible to the cheap vocabulary, **construct the observable** and see whether the price
of a correct decision falls to the price of one observation. It does — but only for half the actions, and
only about the input.

Ten real actions. Sixteen real states each, reached by running real programs on a real repository. The
check mode is **discovered, never written**: read the program's own page for this action, rewrite the
action's own command line with the options that page prints, keep the candidates whose exit status agrees
with the action's real behaviour on states the search is allowed to see, and refuse any candidate that
changes a byte.

```
git_rebase_abort       git rebase --show-current-patch        held-out 1.0   read-only
git_rm_cached_tracked  git rm --cached -n README.rst          held-out 1.0   read-only
tar_extract            tar -tzf bundle.tgz                    held-out 1.0   read-only
gzip_decompress        gzip -l payload.gz                     held-out 1.0   read-only
patch_apply_real       patch --dry-run --forward -p1 -i ...   held-out 1.0   read-only
```

Five of ten, exact on states the search never saw, each one a command line the program itself printed.
The three actions the previous round could not state in its sensor vocabulary — `tar_extract`,
`gzip_decompress`, `patch` — are exactly three of these five. The missing half of that round was not a
vocabulary. It was a question the program was always willing to answer.

And the other half is the finding:

```
git_stash_pop             no rewrite of its argv agrees at all            (6 candidates, 0 read-only)
git_merge_abort           no rewrite of its argv agrees at all          (101 candidates, 0 read-only)
git_checkout_feature      every agreeing rewording performs the effect   (56 candidates, 16 moved)
git_branch_delete_feature every agreeing rewording performs the effect   (98 candidates, 14 moved)
chmod_exec                every agreeing rewording performs the effect   (14 candidates, 11 moved)
```

Then the trap, which is the reason this is a measurement and not a slogan. Take a state where the archive,
the gzip stream and the patch are all perfectly valid, and make the directory the *effect* needs to write
into read-only. All three checks say yes. All three actions fail:

```
tar   -tzf  exit 0   |  tar   -xzf  exit 2
gzip  -l    exit 0   |  gzip  -d    exit 1
patch --dry-run exit 0 | patch ...    exit 2
```

Three of three wrong, in the only place it matters. A check mode decides whether **the input is intact**.
It cannot decide whether **the world will accept the effect**, because it never spends what the action
spends. So the decision is free, exact, and blind at the same boundary for every action in the set.

That is the whole round: **the oracle is not missing. It is in the program, and it is partial, and its
partiality begins exactly where reading stops and acting starts.**

## 1. What was actually built, and what "discovered" means here

The previous round's source says why it stopped:

> "Nothing here is a validity probe of the thing the action consumes (no `tar -tf`, no `gzip -t`, no patch
> test-apply), because those are the actions themselves."

This round had to earn the right to use those probes without smuggling them in. Four steps, all mechanical:

1. **Read the page.** For each action, execute the program's own help, most specific page first:
   `git rm -h` before `git --help`; `tar --help` for tar. The page is an *execution*, not a table.
2. **Rewrite the action's own argv with the page's own tokens.** Three declared rewrites: change one
   character of a short-option cluster (`-xzf` → `-tzf`), substitute one long option
   (`--forward` → `--dry-run`), insert one option after the program or after the git subcommand. At most
   320 candidates, in a fixed order. Nothing in the grammar knows what any token means.
3. **Require read-only.** Any candidate that changes one byte — content *or* mode — on any training state
   is the action wearing an extra flag, and is inadmissible. This is the criterion that makes the result a
   mechanism: a check that performs the effect is not a check.
4. **Rank by agreement on training states, score on held-out states.** Odd indices train, even indices are
   held out, per class. No candidate is privileged, and the winner is recorded with the page it came from.

The tool contains no mapping from an action to a guard. A test parses its own AST and asserts that no
discovered guard token appears as a string constant anywhere outside the docstring. `tar -tzf` is an
output of this round; it is not an input to it.

## 2. Four ways this could have shipped a false result

This section is the round's centre of gravity, because every one of these was in a run that printed a
plausible table.

**(a) The reader took the longest page instead of the right one.** `git --help` is longer than
`git rm -h`, so the vocabulary for `git rm` was a page of top-level git options. `-n` was never a
candidate. Four git actions came back `UNGUARDABLE`. The fix is specificity, and with it `git rm -n` and
`git rebase --show-current-patch` appear.

**(b) The reader accepted a failure as the interface.** Without a man viewer, `git merge --help` answers
98 bytes of `fatal: no man viewer handled the request`. The next run printed `page_bytes: 98`, zero
tokens, and called `git merge`, `git rebase`, `git branch` and `git rm` unguardable — a false negative
produced entirely by the reader. A page prints a usage line or at least three options; an error message
prints neither.

**(c) A mode change was invisible.** The state digest hashed names and contents and not permissions, so
`chmod +x` moved nothing and the action was reported `EFFECT_INVISIBLE`. Hashing `st_mode` fixed the
measurement and changed the action's class to `EVERY_AGREEING_CANDIDATE_PERFORMED_THE_EFFECT` — the true
one.

**(d) The action scored 1.0 against itself.** Before the read-only requirement, the winners were

```
git branch -d -d feature        agreement 1.0, held-out 1.0
chmod -R +x script.sh           agreement 1.0, held-out 1.0
git -P rm --cached -q README.rst  agreement 1.0, held-out 1.0
```

All three agree with the action perfectly and are worthless: they *are* the action. Had the round stopped
at agreement, it would have reported a perfect oracle for seven of ten actions and shipped the primitive
answer the user forbade — a relabelled action sold as an observation.

There is also a fifth, subtler thing, which is not a bug but a fact about states: **on the unarmed family,
`tar -xzf` changed no byte**, because the archive packs a file that is already in the tree. Extraction was
idempotent, so the effect was unobservable and no check could be told from the action. Making the effect
observable required a declared, mechanical arming — set every mode to 0644, or remove every regular file
the argv does not name — and the first arming that made the action change a byte without changing its
truth is the one recorded (`remove_every_regular_file_not_named_in_the_argv` for tar). The precondition
is only observable on a state where the action would actually do something. That is not a trick of this
tool; it is why the previous round's vocabulary was empty where it was needed.

## 3. The census, and what it costs

| action | candidates | read-only survivors | held-out decision | what it decides |
|---|---|---|---|---|
| git_rebase_abort | 131 | 1 | 1.0 | a rebase is in progress |
| git_rm_cached_tracked | 34 | 4 | 1.0 | the path is in the index |
| tar_extract | 320 (cap) | 7 | 1.0 | the archive is intact |
| gzip_decompress | 48 | 8 | 1.0 | the gzip stream is intact |
| patch_apply_real | 168 | 2 | 1.0 | the patch applies to these files |
| git_stash_pop | 6 | 0 | — | nothing agrees |
| git_merge_abort | 101 | 0 | — | nothing agrees |
| git_checkout_feature | 56 | 0 | — | only the effect agrees |
| git_branch_delete_feature | 98 | 0 | — | only the effect agrees |
| chmod_exec | 14 | 0 | — | only the effect agrees |

Cost: 60 s of sandbox, 0 model calls, 0 parameters, 0 network calls. The search is one page read and at
most 320 command lines per action — done once per machine, on states the search never sees again.

Two honest limits, both in the receipt. The winner among agreed read-only candidates is **not unique**:
`gzip -t` and `gzip -l` both decide the gzip stream and both score 1.0, and the tie was broken by
candidate order. What experience identifies is the *class* of read-only decision procedures, not one flag.
And the grammar is three rewrites of the action's own argv, so "unguardable" here means "no rewrite of this
command line reaches a check", not "no check exists": `git stash list` is a perfectly good read-only probe
of `git stash pop`'s precondition, and it is a different subcommand, so this grammar cannot reach it.

## 4. The price of a correct decision, on this machine

```
guess from the state vocabulary      0 executions     0.7647 accuracy   (previous round, quoted)
run the action and watch             1 execution      1.0000            the effect has already happened
run a discovered check               1 execution      1.0000            blind to the environment
```

The middle row is what the previous round measured and what the user's question assumed: if you are
allowed to re-run, every decision is free and exact. The third row is the improvement: the same accuracy
without spending the effect. The fourth thing that is *not* in the table is the one that decides whether
instant learning scales: for five of ten actions there is no third row, and for all three traps the third
row is wrong.

## 5. What is real, what is false, and the single bottleneck

**Real.**

- A read-only decision procedure for 5 of 10 real actions is *printed by the program*, and a mechanical
  reader finds it with zero hand-written rules and zero model calls.
- It generalises on held-out states at this scale: 5 of 5 guards reached training agreement 1.0 and
  held-out agreement 1.0, including the three actions a sensor vocabulary could not express.
- An agreeing candidate that changes a byte is the action wearing a flag. This is now a *criterion* of
  the machine, not an observation about one action.
- A check mode tests the input. On three held-out environment refusals it was wrong three times.

**False.**

- *"Give the model the most advanced coding actions once and it learns them permanently, so all computer
  use follows."* Half of a real action set — including `checkout`, `chmod`, `merge --abort`, `stash pop`
  and `branch -d` — has no pre-act reading that any rewording reaches. For those, the only way to know
  whether the action applies is to have already done it, and "learned once" is therefore not a licence to
  act, it is a licence to have acted.
- *"Instant learning is solved because a demonstration plus one trial identifies the action."* What is
  instant is the *decision*, and only where a check exists; the *effect* remains unforgiven, and the
  environment's acceptance is not in the check.
- *"The oracle is the missing part."* The oracle is present and partial. What is missing is a reading of
  the world that costs less than the act — the previous rounds' identifiability limit, restated in the only
  form that survived contact with execution.

**The single bottleneck.** Not learning speed, not vocabulary, not the model: **nothing observes the
world's acceptance before the act.** Every formulation of the remaining problem that this project has
measured — repair-after-failure, verification cost, the resettable-vs-not distinction, and the user's
question about sentience — ends in the same place: to decide before acting you need a reading of a state
that the act itself would create. The program's check mode is the closest thing to a free lunch in this
space, it is real, it is discoverable, and it stops exactly at the boundary between reading the input and
spending the effect.

That is also the honest answer to *"is this the route to sentience?"*: this round measures one action's
applicability from the outside. A system that could read its own next state before producing it would need
the object that failed three traps here. No test in this round touches that question, and the receipt says
so instead of implying an answer.

## 6. Why this is the ultimate mechanism and not the incremental one

The primitive answer is: build a sensor vocabulary, or a predictor, or a model of each program, and learn
which features precede which action. That is the round that returned `0.7647` and, three rounds earlier,
30 proposals and 0 solved tasks. The ultimate answer removes the part: **ask the program.** No vocabulary
to design, no weights, no parameters, no predictor, no training set — one page read and a bounded search
over the program's own words, and the oracle is the exit status of a command line the program printed
itself. "The best part is no part": the part that was removed is our own language for the state.

## 7. The next step, and its falsifier

Spend the same trick on the side the traps exposed. For each of the five guarded actions, ask whether a
read-only probe exists that fails **exactly when the environment refuses the effect** — a probe that spends
the same currency the action spends without spending it: write-permission and free-space checks in the
target directory, an extraction into a scratch copy followed by a rename, a lock taken and released. The
prediction, stated before the run: at least two of the three traps close, and the closure is a property of
the *environment*, not of the input, so the probe must be re-discovered per machine rather than per program.

Falsifier: if no read-only probe in the grammar's reach separates "valid input, world refuses" from "valid
input, world accepts" for at least two of the three traps, then the boundary measured here is not a
property of this tool but of pre-act observation itself, and the claim "a correct decision is available for
whatever the vocabulary cannot see" must be withdrawn to the narrower "for whatever the *program* can
check".
