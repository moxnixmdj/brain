# The door that was already working, and the two facts it could not see

**2026-11-12.** Base `b86e1823`. Branch `arena/52c02c27-brain`. Round 7 of the owner's question.

This round set out to test the owner's plan on **real goals from the repository's own task corpus**
rather than on sentences I invented, and it produced two results — one that vindicates him more
strongly than any previous round, and one that is a genuine defect.

**The vindication first.** I had been measuring `grounded_action_v1.act` for six rounds. The
repository has a second, stronger front door — `live_integrated_brain_v1.compile_against_live_registry`
— which does not rank over the 145-row registry at all. It **compiles the sentence into typed
actions**. On the repository's own demography task it produces:

```
action 0  fetch_json_knowledge  url=https://api.worldbank.org/.../SP.POP.TOTL?...date=2020
                               json_path=[1, 0, "value"]   authoritative=true
action 1  fetch_json_knowledge  ...date=2023
action 2  fetch_json_knowledge  ...SP.POP.GROW...date=2023
action 3  invoke_capability     math.numeric_expression.sympy
                               "100 * (((population_2023 / population_2020) ** (1/3)) - 1)"
                               variables wired to the $result of earlier cycles
```

That is a correct, complete, executable plan for a real multi-step research task, with data flow
between steps. **The owner's core claim — "the smartest actions with typed interfaces" — is not
aspirational in this repository. It is the higher of the two doors, and it works.**

The weak door, meanwhile, routes the same sentence to `docx.document.create_from_json_record`. Six
rounds of mine measured the weak door. That is a correction to my own work, not to his claim.

Authority **NONE**. One machine, no independent verifier, $0, zero model dependency.
`truth.achieved` stays `false`; no capability registered; no family flipped.

---

## 1. The two defects, both of them blindness

### 1.1 A fact that was false on a machine where it was true

```
probe_effect("network.http.available") -> true=False  how=UNDECIDABLE__NOT_ESTABLISHED
```

measured in the same sandbox where:

```
pypi.org             HTTP 200
registry.npmjs.org   HTTP 200
api.github.com       HTTP 200
```

`network.http.available` is the **only** declared precondition of
`knowledge.json.fetch.external`. So the one capability that fetches JSON from a URL was classed as
blind while the URL was fetchable.

The cause is one line. `_subjects` stripped exactly **one** qualifier:

```python
for suffix in (".file", ".corpus", ".runtime", ".text"):
```

`network.http.available` → `network.http` → not a subject → undecided. `network` was never asked
about. Any fact of the shape `subject.transport.available` had the same problem.

**But the deeper point is not the suffix list.** The machine treated *"I cannot see this"* as
*"this is false"*, because `established_facts` only returns facts confirmed true and the gate
requires every precondition to be in that set. Undecidability and absence were the same value.
That is the honest reading of the six rounds before this one: many of the "blocked" capabilities may
have been blocked by ignorance rather than by the world.

### 1.2 The URL that was silently discarded

The task sentence states a URL, a JSON path, and a destination. The binder extracted the destination
correctly, and then could not fill the URL slot — so `knowledge.json.fetch.external` was refused
`NOT_CALLABLE_WITH_WHAT_GOAL_PROVIDES` **while the URL sat in the sentence.**

The compiler already knew the rule and states it:

> `_repo_paths_uncached`: *"URL path components are not repository paths. Strip complete URLs before
> scanning for repository-local artifacts."*

The binder had no counterpart. A URL was not a path, and was not anything else, so it fell through
every branch and was dropped without a report. That is the same class of error as round 4's
substring kind and round 5's environment-blind key: **a value the system cannot classify is
discarded silently.**

## 2. The mistake I made, kept in the test

The first version of the binding rule bound the goal's URL into `url_key`. `url_key` contains "url",
so it looked like a URL slot. It is not — it means *the name of the key whose value is a URL*, which
`http.json.fetch_from_state` looks up inside a repository-local JSON file. The adapter failed
immediately with `SOURCE_JSON_REQUIRED`.

A slot that names a **key** or a **name** is a lookup, not an address. The repaired predicate
excludes them, and `test_a_lookup_key_is_not_an_address` pins the exclusion with the reason. Had I
not run it, the machine would have made a confident, wrong call — which is exactly the failure mode
this repository's governance exists to prevent.

## 3. What was built

| Change | File | Effect |
|---|---|---|
| `network` in the runtime table, decided by a short TCP connect | `world_probe_v1.py` | `network.http.available` → `network_tcp_reachable` |
| every qualifier stripped from a fact's subject | `world_probe_v1.py` | `subject.transport.available` reaches `subject` |
| URL slots bind the goal's own URL | `world_binding_v1.py` | the address in the sentence is no longer discarded |

**Why a TCP connect and not an HTTP request.** An HTTP probe conflates *no route*, *TLS broken* and
*this host dislikes my user agent* — three different facts reported as one. Only the first is what
`network.http.available` means. A connect answers exactly the question asked.

**What this deliberately is not.** It decides the *precondition*, so a plan can be formed. It grants
nothing. The adapter and the native `fetch_json_knowledge` action keep their own safety decisions
(`HTTPS_URL_REQUIRED`, `LOCALHOST_URL_REJECTED`, `PATH_OUTSIDE_REPOSITORY`) at the moment they run.
Conflating "the network is up" with "go read any URL you like" is how a sensor becomes a
vulnerability.

## 4. What 2026 says

- **Agent S4 / Evolving Agent Interfaces** (arXiv 2610.28601): the gains come from **typed
  interfaces plus the knowledge of when to use each** — which is precisely the `compile_against_live_registry`
  pattern, and the reason the strong door outperforms the ranker.
- **Life-Harness** (arXiv 2605.22166) and **HarnessX** (arXiv 2606.14249): intervention at the
  *interface and harness* layer transfers across models and environments (+88.5% rel., +14.5%
  respectively). Both are arguments for fixing the door, not the learner.
- **SkillApt** (arXiv 2609.26863): *"environment validity should be a hard precondition for
  applicability"* — a precondition the system cannot **decide** is not a precondition, it is a
  silence, and this round found one being read as a "no".

## 5. Answering the owner

**"Give it the smartest actions with stable typed interfaces."** Confirmed, and better than I had
said: this repository already has that door, and on a real multi-step research task it compiles a
correct plan with typed data flow. My previous six rounds measured the ranking door and
under-reported what the tree can do. That correction is in his favour.

**"After he does them at least once, he would learn all of those permanently."** Round 6 stands:
the one-try loop works on a compatible machine (measured, 3 successes, reuse on a different file).
What is missing is not exposure but *attributability* — 56 rows cannot say what they need, and this
round adds that the sensor also confused "unknown" with "no".

**"Instant learning in new arbitrary environments is solved."** Still half true, and now sharper:
*speed on a compatible interface* is solved; *establishing compatibility* is where the machine was
blind, twice, in two different organs, on facts it could have decided.

**"Sentient creature."** Not measured, not the objective. The relevant observation: a machine that
answers "I don't know" by acting as though the answer were "no" cannot tell its own ignorance from
the world's refusal. Fixing that is a precondition for anything one would call a mind.

## 6. Receipts and non-claims

- `canonical/tests/test_a_fact_the_machine_could_not_decide_on_a_machine_that_had_it_v1.py` — **9/9**.
- Regression: **214 pre-existing failures** in the probe/binding/compiler/route subset **before the
  change and the same 214 after**. Zero new, zero fixed by accident.
- The plan quoted in the preamble is the compiler's own output on
  `canonical/tasks/PARENT_DEMOGRAPHY_FRANCE_GROWTH_CROSSCHECK_REAL_TASK`. It was **not executed**:
  `run_raw_goal` refused it at the raw-task contract with `ROUTING_TARGET_EFFECTS_EMPTY`, which is a
  statement about the task envelope, not about the plan.

**Not claimed:** that the network sensor is verified on any machine but this one; that the four-row
`requires` gap of round 6 is closed (it is owner-protected and still open); that the strong door's
plan runs end to end (it is compiled, not executed); that undecidability is now reported everywhere —
only that this fact is decided and that the *pattern* is fixed for `subject.qualifier.available`.
The general problem — `established_facts` collapsing "false" and "unknown" into one value — is
named here and **not** fixed. That is the next thing worth doing.
