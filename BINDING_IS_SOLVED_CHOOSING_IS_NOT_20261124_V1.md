# The binder is solved; the choice of action is not

**Date:** 2026-11-24 · **Branch:** `arena/0964738f-brain` · **Base:** `c4f529eb`

Last report measured one number: **0 of 8 ordinary tasks**, all through the 447-capability
registry. That number stands. This report adds a second lane built from principle, measures it
on the same eight tasks with the same independent verifiers, and shows where the wall actually
is. It is not where I said it was.

---

## 1. What I built, and why it is not more registry

The registry answers *"which of our 447 capabilities matches these words"*. For ordinary work
that is the wrong question, and the registry cannot answer it: measured again this session,
**zero** capabilities compress anything, and `python.source.definition_count.v1` is selected for
three unrelated sentences because "count" is the only shared word.

The machine underneath already knows how to do ordinary work, and says so itself: `wc --help`
publishes `-l, --lines   print the newline counts`, `sha256sum` publishes `[FILE]...`, `gzip`
publishes `-k --keep`. `tool_census_v1` already enumerates those declarations and
`door_witness_search_v1` already proves which are drivable. What was missing is the join between
a sentence, the objects in a workspace, and one of those doors.

`canonical/runtime/grounded_binder_v1.py` (new, 0 model calls, 0 parameters, no program name and
no synonym anywhere in it):

| step | rule |
|---|---|
| named objects | a token that looks like a file **and is in the workspace** is an object; a token with an extension that is **not** there is the artifact |
| named program | a word the machine answers to (`shutil.which`) — naming is the caller choosing |
| door | one declared operation of that program, driven to exit 0 by the existing witness search |
| dependence | run the door twice, with the named object and with a byte-different object of the same name — if the answer does not change, the door does not depend on the object and is refused |
| success | exit 0 **and** the named artifact exists afterwards, or (no artifact named) the workspace changed |

The dependence test is the part worth keeping. It is language-free, needs no help text and no
flag meaning, and it kills the entire class of false positives that has been polluting the
ledger — a program describing itself is not a program doing something.

## 2. Two bugs the measurement found in my own binder

Both were found by running it, not by reading it, and both are the same mistake I had been
accusing the compiler of:

1. **I captured `--help` output into the artifact.** `gzip --stdout`, `sha256sum --version`,
   `wc --version` all exit 0, so the first version wrote a program's banner into `digest.txt` and
   called it a digest. Fixed by the dependence test with the **object excluded from the tree
   digest** — while the object was included, every command looked input-dependent and every
   plaque passed.
2. **I appended the artifact to the command as an operand** (`sha256sum --binary data.txt
   digest.txt`, exit 1 on a file that does not exist) instead of capturing standard output where
   the sentence asked. Redirection is the shell's operator; the value came from the door.

## 3. What the binder can do — verified

Three sentences, each in a fresh workspace, each judged by reading the artifact, not by exit code:

| sentence | plan | artifact | correct? |
|---|---|---|---|
| "Count the lines of data.txt with wc…" | `wc --lines data.txt` | `5 data.txt` | **yes** (5 lines) |
| "Write the sha256 of data.txt…" | `sha256sum --binary data.txt` | `31d0cdeb90cb…5bcc` | **yes** (matches `hashlib`) |
| "Compress data.txt with gzip…" | `gzip --force data.txt` | `data.txt.gz`, valid gzip | **yes** (restores exactly) |

Note the third: it compressed and **deleted the original**, which the sentence did not ask for.
The artifact check cannot see that; a verifier that reads the workspace can. Recorded, not hidden.

## 4. The gate, second lane: 0 of 8 again — and the reason is different

Same eight tasks, same verifiers, `run_task(..., lane="grounded")`:

| task | outcome | what was tried | verdict |
|---|---|---|---|
| line_count | COMPILE | routed to `ctstat`/`lnstat`; refused | `count.json` absent |
| gzip_copy | COMPILE | `gunzip` (named), `tar`, `objcopy` | no `data.txt.gz` |
| tar_gz_bundle | COMPILE | routed set had no `tar` | no `.tar.gz` |
| rename_logs | COMPILE | `rename.ul`, `dpkg-divert` | still `.log` |
| adults_from_json | WRONG | `pgrep --list-name 1` | wrote process names |
| sqlite_row | WRONG | `taskset --pid 1` | not a database |
| count_error_files | COMPILE | `egrep`/`fgrep`/`grep` refused | `hits.txt` absent |
| digest_report | COMPILE | routed to `du`/`tail` | `digest.json` absent |

**0 PASS.** Registry lane: 6 of 8 wrote into our own repository. Grounded lane: 6 of 8 refused
and 2 ran the wrong program. Both are zero, but only one of them is honest about it, and that is
the first real gain of the day: **the system now refuses rather than escaping.**

## 5. The wall, named precisely

The binder binds an action to an object. It does not choose the action, and three designs for
choosing it were measured over the machine's own published text (641 executables read in 11 s,
zero parameters):

| routing design | top-1 correct on the 8 | failure mode |
|---|---|---|
| IDF overlap over full `--help` | 2 / 8 | verbose programs win: `ld` says "read" 14 times, `[` says everything |
| IDF overlap over flag names + descriptions | 2 / 8 | identifier collisions: "number"→`split --number`, "table"→`taskset` |
| left-prefix name matching | 1 / 8 | "lines"→`lnstat`, `ctstat` |

Three designs, each defensible, each wrong. I stopped instead of writing a fourth, because a
fourth would be a rule per failure — the exact thing this project forbids. The measurement says
something stronger than "the heuristic needs tuning":

> An English word is not an identifier. "Number of lines" names `--lines` and `--number`
> depending on which program you ask; "table" is a `taskset` option and a sqlite concept. Word
> overlap cannot recover which program a person meant, because the mapping is not in the words.

That mapping is **knowledge**, not inference. It belongs in the external store, keyed on the
identifier the program publishes, and it can only be written by a verified success: (words of the
sentence, program, door id, binding shape) — inspectable, editable, removable, no weights.

## 6. What that implies for the next step (stated, not claimed)

1. **Bootstrap from sentences that name their program** — 3/3 verified above. Each verified pass
   writes one row to the store. This is single-experience learning with a real verifier, and the
   row is a *generalization* (identifier + binding shape), not a trace.
2. **Reuse is a lookup, not a guess**: a later sentence containing "lines" plus a file finds the
   `wc --lines` row instead of scoring 641 programs.
3. **Composition remains unsolved and is now the largest single block**: 4 of the 8 tasks need a
   second action (5 → `{"lines": 5}`, `wc` output → JSON, `tar -czf`, two operands). One door is
   not a plan, and no routing improvement touches this.

Nothing in §6 is measured yet. It is the next experiment, not a result.

## 7. Honest status

- Registry lane **0/8** (unchanged, receipt `TASK_GATE_BASELINE_20261124_V1.json`).
- Grounded lane **0/8** — 6 refusals, 2 wrong programs, 0 escapes.
- Named-program binding **3/3** correct artifacts, verified by reading them.
- Routing **not solved**: 3 designs, best 2/8, documented and reverted rather than tuned.
- `truth.achieved` remains `false`. Paragraph 2 is not met: the gate is still zero.
- Tests: `test_grounded_binder_v1.py` 14 passed; `test_task_gate_v1.py` 13 passed.

The finding worth carrying forward: **binding is now a solved, refusable, differentially verified
step; choosing is not, and choosing is knowledge that must be learned and stored** — which is
what this project's external store was for all along.
