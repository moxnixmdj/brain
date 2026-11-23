# The Guide Is The Environment's Own Declaration

**Date:** 2026-11-23 · **Branch:** `arena/064509e0-brain` · **Base:** `d2c31c22`
**Authority:** NONE__PRODUCER_RUN_SANDBOX · **Model calls:** 0 · **Weights:** unchanged

This answers the four ideas in the message that opened this round, with measurements
instead of agreement. It is the continuation of
`intake/THE_WORLD_IS_A_GUIDE_BUT_THE_GUIDE_IS_NOT_THE_WORLD_20261122_V1.md`, which named
two gaps and one bottleneck, and of `intake/WHAT_TO_SAVE_20261121_V1.md`, which answered
what should be remembered. The gaps are now closed; a third one was found and closed; a
fourth is named and left open honestly.

---

## 1. What was asked, and what was done

The message asked four things:

**(a)** The model should be a perfect algorithm entering any unknown environment, asking the
right questions, and pulling what it needs from instant knowledge and the web, because
everything on a computer already has a guide.

**(b)** Should it be goal-directed — know what it should know — or learn everything in every
environment and hope to generalise?

**(c)** Scan the environment, diff against memory, fetch the unknowns instantly.

**(d)** Memory must save generalised learning, not raw experience. Decide what to save.

(b) and (d) were already answered with measurements in this project: goal-directed beats
learn-everything by 400× (`intake/THE_BOTTLENECK_IS_NOT_LEARNING_20261121_V1.md`), and what
transfers is the typed fact and the named refusal, keyed by evidence — never chains, bytes,
or names (`intake/WHAT_TO_SAVE_20261121_V1.md`; the host sweep of 635 programs, the 53.5%
stale / 31.1% corrupt append-only stores, the 56-candidate predicate corpus that produced 0
verified rules).

The honest gap for (a) and (c) was not an idea. It was that the system's web arm had **never
been exercised end to end**, and its goal had only one kind, so "GOAL is a measured object"
could not be answered. That gap is what this round closed.

---

## 2. What was built: one contract, no new organ

The broker had one closed contract, `run-tests`: it answers "does this environment's suite
pass", and it refuses by name when it cannot. Every real repository it met produced the same
refusal — and the refusal was never about the task. It was about the environment not being
the environment the project expects.

So the broker gained a second contract, `env-ready`, in front of the first:

> A dependency this environment declares is **ready** when, inside the isolated interpreter
> this environment will be asked in, its distribution imports at a version satisfying the
> environment's own declaration — and anything the isolation did not already have came from
> the machine-readable registry, with the bytes we hashed equal to the digest the registry
> published.

Six decisions, each traceable to a measurement:

**Host-first.** A dependency already in the isolation costs a metadata read and an import —
about 7 ms. A registry round trip is ~255 ms measured. So the isolation is asked first and,
in the host-first test, the registry is not contacted at all: the proof is that the stub
registry recorded zero calls.

**Two independent readers.** We hash the bytes; the registry states what the hash should be.
A disagreement is a refusal (`REFUSE__DIGEST_DISAGREE`), not a warning, and nothing is
installed. This is the same law that produced the 11-22 finding that an unpinned web is not
an oracle.

**The install is not the arbiter; the import is.** After installing, the interpreter is asked
again and the module is imported. All of this was forced by live failure, not designed in
advance (see §4).

**Transitives from the verified bytes.** A wheel's METADATA is inside the hash we checked,
and it states what that wheel needs; markers are evaluated against this interpreter. A
resolver's whole-tree plan is another model of the registry, and this system does not need a
second model of a registry it can read directly.

**The project installs itself, from a copy.** The project's own distribution metadata is
part of the environment its tests expect. Building from a staged copy means the tree is
byte-identical afterwards — a build artifact inside a repository is a change to the
repository.

**Memory is keyed by evidence and never believed.** One record per (goal, evidence digest).
A warm run re-reads every version and re-imports every module. If anything disagrees, the
record is discarded and re-derived. A tampered memory is a claim; the interpreter is a fact.

---

## 3. What the live trials measured

Two repositories this project had never brokered, cloned fresh at pinned commits, with the
isolation wiped before the cold run so a cold claim is really cold:

| | `pallets/flask` `49943b5a9441` | `psf/requests` `3c7baaa05ab4` |
|---|---|---|
| cold `env-ready` | **11.22 s** | **27.87 s** |
| artifacts fetched, hashed, installed | 14 | 32 |
| bytes transferred | 2.46 MB | 10.59 MB |
| warm `env-ready` | **0.33 s** | **0.78 s** |
| warm registry requests / downloads | **0 / 0** | **0 / 0** |
| `run-tests` after arming | **494 passed, exit 0** | **619 passed, exit 0** |
| tampered memory | caught, re-derived | caught, re-derived |

Receipt: `intake/RECEIPT_ENV_READY_LIVE_20261123_V1.json`.

Reading these honestly: the two repositories now work from a cold, unseen state to a passing
suite with zero model calls and zero pre-existing knowledge of either project. The warm path
costs a third of a second and no network at all. That is the shape (c) asked for — scan,
diff against memory, fetch only the unknowns — with the diff being the declaration itself.

What is **not** claimed: this is Python only, wheels only, and the registry must be
reachable. Named limits are listed in the receipt, not buried.

---

## 4. What the trials caught that design did not

Every one of these was found by running against a real repository, after the offline tests
were already green. They are recorded because they are the evidence that the tests were
insufficient — which is the useful fact.

1. **A wheel-tag check accepted an aarch64 wheel on an x86_64 host.** pip caught it at
   install. A compatibility check that defers to the installer is not a check.
2. **`--no-deps` left `pluggy` absent while pytest reported 9.2.0.** Arming declared success
   on an environment whose test runner could not import. Version-presence is not readiness.
3. **Distribution name ≠ module name.** `MarkupSafe`→`markupsafe`, `pytest-xdist`→`xdist`,
   `python-dotenv`→`dotenv`, each found one at a time. The fix was not a naming rule but
   reading the module list the wheel publishes about itself.
4. **A parent was import-checked before its children were armed.** Ordering, not knowledge.
5. **flask's own metadata was missing.** 246 tests passed and one failed with "No package
   metadata was found for flask." The environment was declared-ready and still not the
   environment the project expects.
6. **`requests[socks]` was read as a self-reference and dropped**, leaving 8 proxy tests
   failing for want of `PySocks` while arming claimed success. The project naming its own
   extra is a declaration of what its tests need.

Each is a different way for "the environment is ready" to be false while the code was
self-consistent. That is the pattern worth remembering: **readiness is a property of the
environment plus its own claims, verified by execution — not a property of our reasoning
about them.**

---

## 5. What this says about ideas (a) and (c)

**(c) scan → diff → fetch is right, and the diff is cheaper than expected.** The environment
already states what it needs: `pyproject.toml`, `requirements*.txt`, test groups, its own
extras, build requires, and — inside each artifact — that artifact's own dependencies. The
"unknowns" are not discovered by scanning everything and inferring gaps; they are *declared*.
That is why the cold path is seconds rather than the learn-everything sweep that OOMed twice.
The scan answers a different question: where in the tree is the evidence.

**(a) right questions beat total knowledge, and the right question is set by the contract.**
`env-ready` is a question this system can fail visibly. It produces a named refusal for every
way it can fail — 14 of them — and each refusal is a fact about the environment, not an
opinion. A guide exists for everything on a computer, as the message says; but the guide that
saved the most work here was not documentation. It was the environment's **own machine-
readable statement about itself**, which no reading comprehension can improve on.

That is the single most transferable finding of this round and it generalises: **prefer the
declaration over the description.** Documentation is a description; a manifest is a
declaration; a registry digest is a declaration about bytes; an exit code is a declaration
about the run. Each step down that list is cheaper, more current, and harder to fake.

---

## 6. What is still missing (named, not fixed)

**The third goal is not a manifest.** For GUIs and browsers, nothing declares itself in
`pyproject.toml`. The equivalent declarations must be *derived from observation* — window
titles, the accessibility tree, DOM, the process's own help output — and then verified by
execution exactly as this round verified imports. That is the same contract shape with the
evidence source moved from file to observation.

It is blocked here, not skipped: this sandbox has no display, and `run-tests`-shaped honesty
means not claiming a GUI result that was never run. It routes through a GitHub Actions
workflow. It is named as `next_step` in
`canonical/action_intents/ENVIRONMENT_BROKER_ENV_READY_CONTRACT_20261123_V1.json`.

**Secondary, measured:** `run-tests` assumes `<venv>/bin/python -m pytest -q`. Repositories
whose suite is a tox environment, a Makefile target, or a non-pytest runner are refused, and
that refusal is honest but not yet a capability. That is the next bottleneck inside the
contract that already exists.

---

## 7. Status

- **Verified here:** 24 new offline tests (33 in the two broker suites, 0 failures); the live
  receipt above; the model-call audit over the broker closure (`inference_endpoint_files=0`,
  `canonical/verification/MODEL_CALL_AUDIT_ENV_READY_20261123_V1.json`).
- **Unverified:** independence. Every number above is producer-measured. `truth.achieved`
  stays **false**.
- **Failed and fixed:** the six trial findings in §4.
- **Not attempted:** GUI/DOM arming (no display in this sandbox).
