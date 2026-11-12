# Problem 2: 11 tested paraphrases route; broader generalization remains open

**2026-11-12.** Base `53c80d83`. Branch `arena/d003a8bf-brain`. Round 11.

This report measures a narrow slice of the owner's Problem 2: paraphrases for two capabilities
already in the registry, plus six refused tasks checked for missing operations. It does not test
whether a procedure learned from one execution transfers across arbitrary tasks or environments,
and it does not show that broad Problem 2 is solved.

Authority **NONE**. One machine, $0, zero model dependency in the producer path.
`truth.achieved` stays `false`. No capability registered. Registry read, never written.

---

## 1. Three measurements, and only one of them is about matching

| Question | Measured |
|---|---|
| Does the router answer the tested paraphrases? | **11/11 in the recorded run with required tools installed; 3/11 in the current sandbox** |
| Can a remembered procedure rescue a miss? | **Not established here** — current yq/PyYAML substrate is absent, so the 8 YAML failures are untestable; the supported-substrate run had 0 testable misses |
| Of six refused tasks, how many have **no registered serving capability**? | **4/6 in the measured registry** |

**In the recorded supported-substrate run, the router answered 11 paraphrase probes with memory
off** for two existing capability families. That is evidence about wording tolerance in this
specific request set—not evidence that an agent learned a procedure from experience or will adapt
to arbitrary similar tasks. In the current sandbox, both `yq` and PyYAML are absent: only 3/11
probes route and the eight YAML requests return `ACTION_FAILED`. Those eight failures do not
measure matching or memory transfer because their required tools are unavailable.

The six separate refused tasks expose another limit in the recorded registry: **four need
operations for which no serving capability was found.** For those rows, changing the matcher cannot
supply the missing operation. This is a bounded finding about the measured set, not a claim that
every failure is a capability gap.

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

These rules are intended to keep a looser match from becoming an unverified decision, **assuming the
shared verifier is sound for the actual goal and the verification path runs correctly**. This
benchmark has zero testable memory-rescue targets, so it does not demonstrate that those safeguards
produce successful transfer in practice. Without a sound discriminator, generalizing recall can
make a machine confidently wrong faster: the literature calls this **skill shadowing** (a
similar-looking skill crowds out the right one). The numerical retrieval claims cited above are
external results and are not measurements from this repository.

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

**"Is Problem 2 solved?"** No. In the recorded run with the required tools installed, the router
handled 11 paraphrases of two existing capabilities without memory; this sandbox cannot reproduce
the YAML portion because `yq` and PyYAML are absent. Separately, four of six refused tasks had no
serving capability in the measured registry. These bounded findings do not establish how often
matching, rule expressivity, applicability, or verification limit broader coding and computer-use
tasks.

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

**Not claimed:** that the new memory improves routing. In the supported-substrate run there were
zero testable paraphrase misses; in this sandbox the eight YAML failures are confounded by absent
tools and therefore do not test memory transfer. Not claimed: that 4-of-6 is the ceiling forever;
it is the ceiling on the measured registry. Not claimed: that token matching is sufficient for
real generalization; only the specific supported-substrate paraphrases were measured.

**Still owed from round 6:** the four-row `requires` diff (`image.qr.generate.qrencode`,
`image.code.decode.zbarimg`, `sqlite.table.create_from_json_records`,
`sqlite.table.verify_against_json_records`) — proposed, never applied; the registry is
CODEOWNERS-protected.
