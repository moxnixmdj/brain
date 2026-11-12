# Problem 2: the router already generalizes. The ceiling is capability, not matching.

**2026-11-12.** Base `53c80d83`. Branch `arena/d003a8bf-brain`. Round 11.

You named the target precisely — *"Problem 1 exact recall SOLVED, Problem 2 similar tasks NOT
WORKING"* — and asked for Problem 2 solved, perfectly, by the fastest route. This round measures
where it actually stands, builds the mechanism, **and reports honestly that the mechanism cannot
lift the ceiling**, because the ceiling is not where the framing puts it.

Authority **NONE**. One machine, $0, zero model dependency in the producer path.
`truth.achieved` stays `false`. No capability registered. Registry read, never written.

---

## 1. Three measurements, and only one of them is about matching

| Question | Measured |
|---|---|
| Does the router already answer paraphrases? | **11 of 11** with memory **OFF** |
| Can a remembered procedure rescue what it misses? | **0 testable** — nothing to rescue |
| Of the tasks it refuses, how many have **no capability at all**? | **4 of 6** |

**The generalization you reported missing is already happening**, and it is the router doing it:
"turn probe_b.yaml into json with yq", "export … as json", "transform … to json", "produce json
from …", "make … into json", "translate … into json", "serialize … as json" — **all answered, with
no memory at all.**

That forces the harder question. If paraphrases already work, where does "similar tasks do not
work" come from? Measured: **from tasks whose capability does not exist.**

## 2. The ceiling, named

Six tasks the door refuses. For each, I asked the registry whether a capability could serve it:

| Task | Would need | Capability exists? |
|---|---|---|
| sum a column of numbers in a csv | csv + sum | **no** |
| make a zip archive of a directory | zip | **no** |
| read a spreadsheet and sum a column | xlsx + sum | **no** |
| convert a docx to text | docx + text | **no** |
| diff two files | diff | yes (`evidence.claim_spec…`) |
| sort the lines of a file | sort | yes (`shell.command.run`) |

**Four of six are not matching failures.** "Sum a column of numbers in a csv" came back
`AMBIGUOUS` among `sqlite.table.create_from_json_records`, `xlsx.table.create_from_json_records`
and `sqlite.table.verify_against_json_records` — three *creators* that cannot compute a sum,
because **nothing in the 145-row registry sums a CSV column.** The registry is 58/145 Python
source analysis: excellent at reading code, nearly empty at ordinary file work.

A capability that does not exist cannot be remembered. That is why no matcher, no embedder and no
amount of experience changes these four rows — and why claiming "Problem 2 solved" on a matching
technique would have been false.

## 3. What I did build, and the defect it repairs

Two defects in the exact-recall key, both measured before fixing:

**a) It cannot tell opposites apart.** `signature_of` sorts the distinctive words, so

```
"convert yaml to json"  ->  convert|json|yaml
"convert json to yaml"  ->  convert|json|yaml      <- identical
```

Teaching the first makes the second a **confident hit on the wrong capability**. Sorting a sentence
destroys the one relation a conversion task is made of.

**b) Memory could not rescue a miss.** In `act` the remembered id is consulted only inside
`if survivors and len(survivors) > 1`, so it chooses among candidates the router already narrowed
to. Measured: it fires (`selected_because: REMEMBERED_RESOLUTION`) **and changes nothing**.

`canonical/runtime/procedure_memory_v1.py` adds a second section to the same store (nothing
existing is migrated):

| Generalization | Why it is real, not a guess |
|---|---|
| formatting verbs | convert / turn / export / make / produce / serialize / render → one token |
| inflection | `files`≡`file`, `yamls`≡`yaml`, `entries`≡`entry`, `cases`≡`case` |
| fillers | `the`, `using`, `with`, a file **literal** — a typed argument, not the question |
| **direction** | `(verb, source, target)` preserved **in order**, appended as its own component |

**The two rules that make a looser match safe** — and they are not the matching:

1. **A remembered procedure is a CANDIDATE, never a decision.** It is injected *before* the
   candidate loop, where it must pass the same precondition probe, the same kind-contradiction
   check, the same binding, and the same verification as anything the grounder proposed.
2. **Only a VERIFIED receipt may teach.** `learn(..., verified=False)` records nothing. A failure
   is not a lesson about the next sentence that resembles it — the capability may have been wrong,
   the argument missing, or the tool absent.

With those two in place, a looser match costs **a failed verification, never a wrong answer** —
which is what makes it defensible to loosen the match at all. Without them, generalizing recall
would just make the machine confidently wrong faster: the literature calls it **skill shadowing**
(a similar-looking skill crowds out the right one), and reports retrieval precision collapsing
from **29.6% to 3.3%** as skill pools grow. Token overlap beating dense embeddings for
distinguishing similar skills is the same finding from the retrieval side.

## 4. My own errors this round, kept

1. **I three times "fixed" a singular ruleset that still returned `fil` for `files`.** The `es`
   branch fired before the single-`s` branch; then a floor on the *stem* fixed nothing because
   `fil` is three characters; then `boxes`/`cases` broke separately. Four attempts, one `_stem`
   function, each attempt verified by running it.
2. **I nearly reported a memory win that measured nothing.** My first rescue benchmark said
   "REACHED 4/4" — but the router had answered all four *without* memory, so the memory was
   credited for the router's work. The fix is the `testable` filter: only paraphrases that
   **fail without memory** can test memory.
3. **I mis-stated my own earlier claim.** I attributed "5 of 30 ordinary tasks verify" to round 10;
   it was **2 of 30 verified there (30 failed), and 5 verified after** the zero-score-gate fix —
   of which **1 answered its question**. Precision matters when the subject is measurement error.

## 5. Answering you

**"Is Problem 1 solved?"** Yes, on the exact match — `8.13x`, and this round did not disturb the
path. But it was **not durable**: `yq` and `pyyaml` installed last round were **gone today**, which
is precisely the non-durability already found once in the one-shot learner. Anything a `pip
--user` install puts on this box dies with the interpreter.

**"Is Problem 2 solved?"** No — and, measured, **it is not a matching problem where capabilities
exist.** In this tree the paraphrases work unaided; the failures are capabilities that were never
built. Calling that "generalization not working" mistakes a coverage ceiling for a similarity
failure, and the wrong fix (a better matcher) would have cost the round.

**"What is the smartest thing to do?"** Not a better matcher. The measured order is:

1. **Build the four missing capabilities** (`csv` column arithmetic, `zip`, `xlsx` column
   arithmetic, `docx`→text). They are ordinary, small, stdlib-or-wheel, and each one converts a
   permanent `AMBIGUOUS` into a candidate. This is the only item that raises the ceiling.
2. Then the memory earns its keep: téach once on the new capability and paraphrases route to it.
   The mechanism is built and tested; it has nothing to carry until (1) exists.
3. Keep the two safety rules. Without them, step 1 plus this memory makes wrong answers faster.

**"Sentient creature."** Unchanged and unmeasured. The honest note: I spent four attempts fixing a
stemmer and got it wrong three times, then nearly credited myself for the router's work. The gap
between *doing the thing* and *knowing what you did* is the whole subject of this exercise, and
this round I was on the wrong side of it twice.

## 6. Receipts and non-claims

- `canonical/runtime/procedure_memory_v1.py` — the generalized memory, with the two safety rules.
- `canonical/runtime/grounded_action_v1.py` — memory injected **before** the candidate loop; learning
  only on `verified`.
- `problem_2_generalization_benchmark_v1.py` — the three measurements, re-runnable, **declaring**
  the tool substrate instead of assuming it.
- `canonical/tests/test_problem_2_generalization_v1.py` — **7 passed, 2 skipped** (skips state
  `tool substrate absent`, never a false pass).

**Not claimed:** that the new memory improves routing today — it has **zero testable targets**
until a missing capability exists. Not claimed: that 4-of-6 is the ceiling forever; it is the
ceiling on this commit's registry. Not claimed: that token matching is sufficient for real
generalization — it is sufficient for the paraphrases measured, and the literature is clear that
retrieval precision degrades as a skill pool grows, which is an argument for the safety rules, not
against them.

**Still owed from round 6:** the four-row `requires` diff (`image.qr.generate.qrencode`,
`image.code.decode.zbarimg`, `sqlite.table.create_from_json_records`,
`sqlite.table.verify_against_json_records`) — proposed, never applied; the registry is
CODEOWNERS-protected.
