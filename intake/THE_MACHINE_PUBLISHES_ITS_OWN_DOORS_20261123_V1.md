# The Machine Publishes Its Own Doors

**Date:** 2026-11-23 · **Branch:** `arena/24a52a6b-brain` · **Base:** `b4fdd79e`
**Authority:** NONE__PRODUCER_RUN_SANDBOX · **Model calls:** 0 · **Parameters:** 0
**Receipt:** `canonical/verification/THE_MACHINE_PUBLISHES_ITS_OWN_DOORS_20261123_V1.json`
**Tool:** `canonical/tools/the_machine_publishes_its_own_doors_v1.py` ·
**Module:** `canonical/runtime/tool_census_v1.py` · **Tests:** 23 new, 85 green with the prior suites

---

## 1. Requirements confirmed, and the §2 contradiction

The message asks four things: that the model be a perfect algorithm entering any unknown
environment; whether it should be goal-directed or learn everything; that it scan the
environment and diff against memory; and that memory save generalised learning rather
than raw experience. It restates the standing laws: own model only, zero model calls at
runtime, every parameter calculated, no knowledge house, instant knowledge from outside
the weights, and *"the best part is no part"*.

**§2 resolution (unchanged from the previous round, and now load-bearing):** knowledge
lives in an external, inspectable store the system computes with; the weights hold only
computed mechanisms. The default stands because no evidence against it appeared. What
this round adds is a sharper line: the store may hold **what a machine publishes about
itself** (a program's own declaration), because that is inspectable, deletable, and
re-derivable — never a memorised fact about the world.

Most of the four ideas were already answered, with measurements, in the rounds that
precede this one:

| the question | where it was answered | the answer |
|---|---|---|
| goal-directed or learn everything? | `THE_VOCABULARY_IS_THE_ARTIFACT_20261125_V1.md` | explore broadly, persist narrowly |
| what is saved, what is not? | `PERFECT_ALGORITHM_MODEL_VERDICT_20261122_V1.md` | priors (facts) and admitted rules (hypotheses); never raw traces |
| scan, diff, fetch the unknown? | `THE_GUIDE_IS_THE_ENVIRONMENTS_OWN_DECLARATION_20261123_V1.md` + round 2 | local guide first, web as fallback |
| does one experience generalise? | `LEARN_ONCE_KEEP_FOREVER…`, `ONE_EXPERIENCE_IS_ENOUGH…` | retention yes, transfer conditional |

What none of them had answered is the first step of all of it, and this round is that.

---

## 2. The bottleneck: the action list was hand-written

`perfect_algorithm_v1.scan(env, actions)` is the Perfect Algorithm's own entry point.
It enumerates the actions you give it. On the five machines of
`the_vocabulary_is_the_artifact_v1`, "the actions you give it" means this:

```python
Machine("FILESYSTEM", root, (
    Atom("FS_A1", ((_write_via_sh("{content}", "{name}"), None),)),
    Atom("FS_A2", ((("rm", "-f", "{name}"), None),)),
    ...
```

A person wrote that, per machine. The loop is general about the **world** and entirely
dependent on a human about the **doors**. So the claim *"go into any new environment and
ask the right question"* had an unmeasured precondition: somebody must first hand it the
list of things that can be done there. Nobody was going to be there.

This is also exactly what the frontier measures. Terminal-Bench 2.0's error analysis
(ICLR 2026, 3,800 sampled failures) puts **"command not found" at 24.1%** of every
failure — and the reading of that paper is precise: those failures are *"an agent
guessing what exists on a machine"*, a failure of knowing the machine, not of knowing
Linux. The hardest open board is failing on the step this project could not take.

---

## 3. The idea this round tests

Every computer already publishes its doors. A program's `--help` is a contract it writes
about itself: which flags exist, what each does, which subcommands it has, which operands
it requires. If that contract is enough to enumerate the doors **and to run each one and
see what the tree says happened**, then the action list stops being an input and becomes
a measurement.

Nothing in the parsing path names a program, a flag, or a subcommand. The only constants
are the *shapes* a help text is allowed to take, and each shape is one measured here:

| shape | machine | what it looks like |
|---|---|---|
| GNU/long-option column | tar, base64, gzip | `  -c, --create               create a new archive` |
| usage line with positionals | coreutils | `Usage: base64 [OPTION]... [FILE]` |
| subcommand tree | git, ruff | `   clone     Clone a repository into a new directory` |
| clap, description below | ruff | a lone `--config <X>` with its prose on the next line |
| bare-column table | openssl | `asn1parse   ca   ciphers   cmp` |
| **no usage line at all** | zip | a hand-written banner (treated as unbound, not guessed) |

---

## 4. What the measurement says

36 programs present on this machine, **2,134 operations read from their own
declarations**, each one run for real on a disposable tree that is restored afterwards:

| class | count | what it means |
|---|---|---|
| **DOOR** | **76** | ran, exited cleanly, and moved the tree — with the *kind* of move recorded |
| **SENSOR** | **1,098** | ran, exited cleanly, computed a value, moved nothing (`wc --lines`) |
| **UNBOUND** | **960** | the program's own usage line says it cannot run as invoked |

Change kinds actually seen: `CREATES 97`, `RENAMES 19`, `REWRITES 17`,
`REWRITES_BINARY 11`, `DELETES 6`, `REWRITES_TEXT 1`. Every trial restored the tree
exactly (`all_restored: true`). Whole census: **54 s**, single-threaded, zero network.

Doors by program, and the honest reason the others are not doors:

| program | doors | why, in the program's own terms |
|---|---|---|
| git | 40 | judged in a real repository it was never told about; `commit --amend`, `add --force`… |
| gzip | 12 | in-place compression: 11 `RENAMES`, 1 `CREATES` |
| split | 8 | writes the pieces it declares |
| xz | 7 | in-place compression |
| tar | 4 | exactly the four flags that create an archive (`--create`, `--append`, `--catenate`, `--update`) |
| sort, sed, find, patch | 1 each | the one flag that writes a file (`-o`, `--in-place`, `-delete`, `-o=`) |
| **jq, wc, cut, tr, base64, md5sum, grep** | **0** | they write to **stdout** and name no artifact — 1,098 sensors, correctly |

**The decisive proof** (`scan_proof` in the receipt): gzip's 12 doors were discovered by
the census, and `perfect_algorithm_v1.scan(env, env.action_names)` then walked that
environment — **5 states, 12 transitions, 0.028 s** — with
`action_list_written_by_a_person: false`. The loop that could not take a first step
without a human took one.

---

## 5. The six defects this round produced, and how each was caught

Every one of these made the census **lie**, and every one was found by disbelieving a
number rather than by a test I had already written.

1. **Prose admitted as subcommands.** Scanning every column of `tar --help` produced
   `extracting`, `gnu`, `posix`, `clocale` as "subcommands" and attributed 876
   operations to them. A name is the *first* column.
2. **The program answering about itself.** `tar option -h` prints tar's own help, so a
   detector that asks "is this help?" admits `pax` and `posix`. A word is a subcommand
   only when the program answers with something *other than* its own help. tar now
   refuses 23 candidates with recorded reasons.
3. **An error message mistaken for a manual.** `git --help` on a machine without `man`
   prints `fatal: no man viewer handled the request`. A grep for `--word` accepted it.
   A help text must **declare** (a usage line, or an option in a column), not merely
   mention an option.
4. **A door is one door.** `-c, --create` was enumerated once per spelling, doubling
   every documented flag and producing duplicate ids (`tar_c` twice) — a census whose ids
   identify nothing cannot be indexed or aimed at.
5. **`958 of 998 "doors" were one false positive.** `gzip.compress` stamps the current
   time into its header, so the retry loop's own seed write was read as the *operation*
   changing the tree; ten of jq's thirteen operations were credited with rewriting a
   binary that jq writes to stdout and never opens. Seeds are now byte-stable and the
   retry is judged against the form's own baseline. jq: 13 sensors, 0 doors — true.
6. **Litter is not a capability.** `tar --delete --file=out.bin in.txt` exits 2 with
   *"in.txt: Not found in archive"* and, in failing, contains an empty `out.bin`. That
   was recorded as `CREATES` and inflated tar from 4 real doors to 98. A failed run that
   leaves a file behind is now `LITTER` and is never a door.

Two more, found the same way: `base64 --wrap` was handed a filename where it declares a
count (`extra operand 'in.txt'`), and `_kinds` read only top-level files, so
`git commit --amend` — which writes objects and a ref under `.git/` — reported the kind
`NOTHING` while the digest said the tree had changed. Two readers of one tree disagreeing
is how a corruption gets recorded as a success.

---

## 6. What is now possible that was not

- **The scan has no human in front of it.** `as_environment(commit)` turns the census's
  own verdict into the action list `scan()` requires, and only operations the tree
  confirmed are offered (`NO_EFFECT` is excluded by construction, so a budget cannot be
  spent on a door painted on a wall).
- **Depth two is measured, not assumed.** `ruff --help` documents two trivial flags and
  ten subcommands; its real options exist only under `ruff check --help`. git is starker:
  **all 40 of its doors are at depth two**, and its depth-one census yields zero
  operations. A census that stops at depth one reports a machine you cannot use.
- **A sensor is a first-class answer.** `A_SENSOR_REQUEST_IS_COMPUTABLE_20261120_V1`
  already said a request can be a computation; the census now produces 1,098 of them and
  does not file them as failures.
- **An unbound operation names its blocker.** `diff` needs two FILES, `grep` needs
  PATTERNS, `openssl` needs a subcommand, `zip` publishes no usage line at all. Each is
  recorded verbatim, so the next round has a work list instead of a mystery.

---

## 7. Honest limits, stated plainly

- **This is not competence.** Knowing 76 doors is not knowing which one a request wants.
  The census answers "what can be done here"; it does not answer "what should be done".
  That is the next bottleneck and this file does not touch it.
- **960 operations are *uncharacterised*, not dead.** The census supplies what a usage
  line declares (a seed operand, a carrier flag, a script slot). A room with two files, a
  genuine patch, or a committed change is a *stated decision* it does not yet make. The
  number is a work list, not a verdict.
- **`git commit --all` is knowingly mis-bound.** git only says *"paths with -a does not
  make sense"* in its **error**, not in its description, so the binder cannot read it
  without inventing a word list — which this project forbids. It is reported as a failed
  run, not as a door.
- **A room is a decision.** `git` is judged inside a repository the census builds;
  changing which rooms exist changes the door count, so the room is stated per tool in
  the receipt rather than hidden.
- **A GUI has no `--help`.** The same method needs a different evidence source there —
  the accessibility tree, the DOM, window titles — and this sandbox has no display, so
  that is named and not claimed. `man` is also absent here, which is why `--help` is the
  only declaration tier measured.
- **Producer-run only.** No independent identity re-ran any of it. `truth.achieved`
  stays **false**.

---

## 8. The next bottleneck, named

> **Seventy-six doors and no way to choose among them.** The census answers *what can be
> done here*. A request arrives as a goal — "make the report sortable", "this archive
> is missing a member" — and nothing yet connects a goal to the door whose recorded
> *kind of change* serves it.

The project already owns the two halves of that connection and has not joined them:
`the_vocabulary_is_the_artifact_v1` decides which relation moved, and this census now
records, for every door, exactly which kind of move it made (`CREATES`, `RENAMES`,
`REORDERS`, `REWRITES_TEXT`, `DELETES`). The join is: state the goal as a relation the
tree can be read for, and pick the door whose measured kind produces it. That is the
crossing to attempt next, and it is falsifiable on the same 36 programs.
