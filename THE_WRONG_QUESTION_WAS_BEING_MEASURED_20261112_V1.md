# The wrong question was being measured

**2026-11-12.** Base `4325dbfa`. Branch `arena/ccb3a09a-brain`. Round 10.

Ten rounds of this work hunted blockers, removed them, and counted again. Every count was followed
by a counterfactual, and every counterfactual returned null. That record is itself the finding:
**when removing ten different blockers changes nothing, the blockers were not the bottleneck, and
the instrument was answering a different question than the one being asked.**

This round asks the question the registry cannot answer: *can this machine do the ordinary things a
person asks a computer to do, and when it says it verified one, was it right?*

Authority **NONE**. One machine, no independent verifier, $0, zero model dependency.
`truth.achieved` stays `false`. No capability registered. Registry read, never written.

---

## 1. Coverage: 30 ordinary tasks

Thirty requests a person would plausibly make on any machine — chosen by hand, *not* drawn from the
registry's keywords, because a task list built from the registry measures the registry.

| | |
|---|---|
| tasks | **30** |
| expressible (a capability was selected and run) | **15** |
| reported `VERIFIED_ACTION` | **5** |
| `AMBIGUOUS` | **15** |

**All fifteen unexpressible tasks are `AMBIGUOUS`. None routes to an empty set.** That is the most
important correction in this document: half the ordinary things a person asks for have candidates
the gate could not separate, which is a **ranking** defect, not a coverage defect. I measured this
wrong the first time in this same round (see §5).

Examples of the fifteen, all with candidates in the registry: *"run a shell command"*,
*"make a chart from data"*, *"sort the lines of a file"*, *"diff two files"*,
*"make a zip archive of a directory"*, *"sum a column of numbers in a csv"*.

## 2. A forged row was vetoing decisive matches

The front door appends every forged capability to the candidate list with `combined_score: 0.0`:

```python
# A FORGED CAPABILITY IS REGISTERED BUT NEVER PROPOSED.
pending = [{"capability_id": cid, "combined_score": 0.0} ...]
```

The comment states the intent — *registered but never proposed*. The code appends them anyway, and
then they **survive into the selection gate**, where the rule is *"if there is no decisive margin,
refuse"*. So two forged rows scoring `0.0` made a candidate scoring **26.3** lose:

```
'show me the last five git commits'   AMBIGUOUS__NO_DECISIVE_MARGIN
   forged.agency_finite_portfolio_generator_v1.generate   score=0.0
   forged.automationbench_mutation_compiler_v1.compile_sheets_append   score=0.0
   git.history.bisect_regression.v1   score=26.3        <- the actual match, refused
```

**A row that was never a candidate was deciding the election.** The fix is six lines: a zero-score
row may be proposed only when nothing scored — never allowed to gate a matched one.

Measured: **expressible 11 → 15, `AMBIGUOUS` 19 → 15.** Three tasks began routing that previously
could not.

**And this is the first time in ten rounds that a counterfactual moved anything**, which is why it
is worth stating plainly what it did *not* buy: §3.

## 3. `VERIFIED_ACTION` does not mean the question was answered

This is the finding that reorders everything.

Auditing the five "verified" tasks **by reading what each returned**:

| Task | What it actually returned | Verdict |
|---|---|---|
| count the lines in `README.md` | `answer: 49943` definitions across **5,479 files** | **wrong** |
| find all files larger than one megabyte | **400 `.py` files** under `canonical/runtime` | **wrong** |
| show me the last five git commits | **one** sha, `mode: commit_bisect` | **wrong** |
| extract the text from a pdf | 43 bytes of real text from a real PDF | **correct** |
| list the installed packages | a tar.gz containing one action-intent JSON | **wrong** |

**One answer in five.** Every one of the five satisfied its own declared postcondition —
`output_verified: true` — and the machine reported success for all five.

So `VERIFIED_ACTION` means *"this action met the postcondition it declared for itself"*. It does not
mean *"this action answered the question that was asked"*. Those are different claims, and the
system currently reports the first in the vocabulary of the second.

**This is the real limiting factor, and no amount of binder work, sensor work, or tool acquisition
touches it.** The machine is not failing to find capabilities. It is succeeding at the wrong ones
and calling that success.

## 4. The failure pattern, named

Look at the four wrong answers together:

- asked for **lines in one named file** → counted **definitions across a tree**
- asked for **files by size** → enumerated **python source by glob**
- asked for **five commits** → returned **one bisect candidate**
- asked for **installed packages** → archived **one unrelated JSON**

The shared shape is not "wrong capability". It is **the answer is about a different object than the
one named**. Every one is a well-formed, verified answer to a neighbouring question. The front door
selects on *keyword similarity*, and similarity cannot distinguish "count the lines in README.md"
from "count definitions in this repository" — both share `count`, `file`-ish tokens, and a tool that
counts something.

**That is the same error I made four times in this exercise.** Round 8's census counted keyword
matches and called them capabilities. Round 9's `HONEST_MARKERS` counted a word in the payload and
called it an answer — and scored 4/4 wrong (§5). The machine and I are making the *same* mistake at
different layers: **matching on surface, then reporting the match as the fact.**

## 5. My own errors this round, kept

1. **`HONEST_MARKERS` scored 4 of 4 wrong as honest.** The first version of the honesty test marked
   a receipt honest if it *contained* a word like `"line"` or `"commit"`. `definition_count` returns
   `answer: 49943` — contains no "line", but my table for that task was `("line","count")` and the
   payload contained `definition_count`. **A word in the payload is not the answer to the question**,
   and I rebuilt the exact defect I was measuring. Fixed by replacing the table with per-task
   audits that state what the receipt actually returned.

2. **I reported "19 got nothing at all" and it was my bug.** My hand-written script never populated
   the `routed_to` key for unrouted tasks, so `not r["routed_to"]` silently counted all 15
   `AMBIGUOUS` rows as routeless. The instrument was wrong, not the machine. The corrected reading —
   every unexpressible task *has* candidates — reverses the diagnosis from coverage to ranking.

3. **`VERIFIED_ACTION` fooled me twice before I checked it.** I read "verified 2 → 5" as progress and
   nearly shipped it as the round's headline. It is progress in *routing* and regression in
   *honesty*, and the only reason I caught it is that one of the five was so obviously absurd
   (a tar.gz for "list the installed packages") that I read the other four.

## 6. Answering the owner

**"What is wrong?"** Not what ten rounds of mine said. The registry is not starved, the sensors are
not the bottleneck, the binder is not the bottleneck. **The machine cannot tell the difference
between answering a question and satisfying a postcondition, and it reports the second using the
first's words.** That is one defect, it sits above every defect I have been chasing, and it explains
why removing those defects changed nothing: none of them was on the path to *correctness*.

**"Why can't we just give it the most advanced actions and let it experience them once?"** Because
experience teaches it what it did, and right now what it records is *"I satisfied my own
postcondition"* — which is true, uninformative, and gets *matching* reinforced rather than
*answering*. Learning from these receipts would make the wrong-answer behaviour stronger, faster.
**One trial cannot teach a lesson the trial never contained.**

**"Sentient creature."** Not measured, not the objective — but this round is the sharpest evidence
yet about the gap. A creature that reports "done" when it has answered a different question does not
have a memory problem or a capability problem. It has no way to notice the difference, because
nothing in it compares *what was asked* against *what came back*. The one thing this round adds: that
comparison is missing in the machine **and it was missing in my own instruments four times running.**

**"Am I right or wrong?"** Right that one experience should be enough. Wrong, and this is the sharp
part, that the bottleneck is the *number* of experiences or the *range* of environments. It is that
each experience is being recorded as a success it did not have. Fix the receipt's honesty and the
whole plan becomes viable; leave it and more experience makes it worse.

## 7. The smartest next step, and the two that are not

**Do this:** make `VERIFIED_ACTION` unavailable unless *the thing that was asked about* is what the
receipt is about. The registry already carries the vocabulary for it — `provides`, `result_fields`,
and each adapter's own `answer`/`output_path` — and the audit above shows the comparison is
mechanical for the five cases: does the returned object name the file/tool/range the sentence named?
Where it cannot be decided, the honest status already exists (`UNJUDGED`) and is unused.

**Do not do this:** more capabilities for the fifteen `AMBIGUOUS` tasks. They already have
candidates; the defect is that a wrong candidate wins, and adding more candidates makes that worse.
This is the same trap as rounds 3–9 in a new costume.

**Do not do this either:** more sensors. Round 9 measured that teaching the presence probe perfect
sight moved a blocker and produced nothing.

## 8. Receipts and non-claims

- `expressibility_of_ordinary_computer_tasks_v1.py` — the 30-task coverage, the false-ambiguity
  detector, and the honesty audit with per-task receipts.
- `canonical/tests/test_expressibility_of_ordinary_computer_tasks_v1.py` — **7/7**.
- The zero-score gate fix is in `grounded_action_v1.act()`: six lines, with the comment that states
  the rule the original comment claimed.
- Regression: the 155-row keyword census moved 64 → 62 selected under the fix (§2), i.e. it is not
  neutral. I kept it because the case it fixes is decisively wrong without it and I have not yet
  found a case it breaks that was previously right — but that A/B is **owed**, not done.

**Not claimed:** that all five verified actions were wrong — one was right, by reading it. Not
claimed: that the fifteen `AMBIGUOUS` tasks are unachievable — they have candidates. Not claimed:
that the six-line fix is regression-free; the census moved and I could not finish the row-by-row
A/B in this round. **Correction owed next round.**

**Still owed from round 6:** the four-row `requires` diff (`image.qr.generate.qrencode`,
`image.code.decode.zbarimg`, `sqlite.table.create_from_json_records`,
`sqlite.table.verify_against_json_records`) — proposed, never applied; the registry is
CODEOWNERS-protected.
