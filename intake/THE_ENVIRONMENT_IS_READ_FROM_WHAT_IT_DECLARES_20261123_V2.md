# The Environment Is Read From What It Declares — And A Refusal Is Not A Verdict

**Date:** 2026-11-23 · **Branch:** `arena/dbe08398-brain` · **Base:** `68bf0400` (contains #7048)
**Authority:** NONE__PRODUCER_RUN_SANDBOX · **Model calls:** 0 · **Weights:** unchanged

This is round 2 over `intake/THE_GUIDE_IS_THE_ENVIRONMENTS_OWN_DECLARATION_20261123_V1.md`.
That round named one secondary bottleneck and left it open:

> `run-tests` assumes `<venv>/bin/python -m pytest -q`. Repositories whose suite is a tox
> environment, a Makefile target, or a non-pytest runner are refused, and that refusal is
> honest but not yet a capability.

That is the bottleneck this round attacked. It is now closed, measured on five repositories
this code had never met, and closing it exposed a second, worse defect: the broker was
**reporting refusals about the environment for facts that were about the project.**

---

## 1. Five unseen repositories, armed from their own declarations

`canonical/tools/env_ready_live_trial_v1.py`, clean root, full git history
(`--filter=blob:none`, tags present), receipt
`intake/RECEIPT_ENV_READY_LIVE_20261123_V2.json`:

| repository | cold arm | warm (from memory) | suite after arming |
|---|---|---|---|
| psf/requests | `ENVIRONMENT_BROKERED` 40.80 s | `ENVIRONMENT_BROKERED_FROM_MEMORY` 0.944 s | `ENVIRONMENT_BROKERED` **619 passed** |
| pallets/flask | `ENVIRONMENT_BROKERED` 15.70 s | `…_FROM_MEMORY` 0.367 s | `ENVIRONMENT_BROKERED` **494 passed** |
| psf/black | `ENVIRONMENT_BROKERED` 52.74 s | `…_FROM_MEMORY` 1.273 s | `ENVIRONMENT_BROKERED` **800 passed, 61 subtests** |
| python-attrs/attrs | `ENVIRONMENT_BROKERED` 19.23 s | `…_FROM_MEMORY` 0.721 s | `REFUSE__VERIFICATION_FAILED` **1408 passed, 1 failed** |
| tox-dev/tox | `ENVIRONMENT_BROKERED` 96.09 s | `…_FROM_MEMORY` 1.229 s | `REFUSE__VERIFICATION_FAILED` **4253 passed, 1 failed, 3 errors** |

All five arm. No repository is refused. The two refusals are the honest kind: the suite ran
inside the armed environment and some of it did not pass.

The two remaining failures are **not environment facts**, and both were confirmed by hand:

- attrs `tests/test_converters.py::TestPipe::test_wrapped_annotation` — a genuine upstream
  failure on Python 3.11. The environment is correct; the project's test is not passing.
- tox `tests/docs/test_manpage.py` — three errors, each `FileNotFoundError: 'man'`. The
  suite shells out to the **system binary** `man`, which this sandbox does not install. Not a
  Python dependency, not a declaration env-ready can satisfy, and not claimed.

---

## 2. What the declarations actually turned out to be

The round-1 reader understood `pyproject.toml`, `tox.ini` commands, Makefile targets and
workflow fragments. Five unseen repositories found four shapes it did not understand. Each
one was a real miss that produced a real failure, not a hypothetical:

| shape | repository | what broke without it |
|---|---|---|
| `[project.optional-dependencies]` installed as `.[d]` by the project's own test env | black | suite refused: needs aiohttp, declared nowhere else |
| `[dependency-groups]` with `{include-group = …}` | attrs | test-only deps invisible |
| marker with an inner quoted comparison: `typing-extensions…python_version<'3.13'` | tox | regex reader desynchronised on a quote — replaced by `tomllib` (`declared_table()`) |
| `extras = [ "completion" ]` in **`tox.toml`** (extras as data, not inside a command string) | tox | suite could not be collected: `No module named 'argcomplete'` |

The last one is the instructive one. `argcomplete` *is* declared — under the `completion`
extra — and tox's own `tox.toml` asks for that extra in five places. The reader only scanned
command strings, so it saw `pip install -e .[completion]`-shaped text and never looked at
TOML data. The fix reads `[env.*].extras` as data, intersected (as always) with the extras
the manifest actually declares. Regression test:
`test_extras_declared_as_data_in_tox_toml_are_read`.

---

## 3. A plugin is armed by its host, and the final gate had to be told

`black` needs `pytest`; `matplotlib-inline` is not needed by anything until matplotlib
imports it. The round-1 rule — `PLUGIN_ARMED_IMPORTED_BY_HOST` — was applied while arming
each dependency, but the **final** gate still demanded that every declared dependency import
successfully. A plugin whose import is its host's job therefore passed the plugin rule and
was refused one statement later. It is reproducible in three lines of probe output:

```
records: toyplug  PLUGIN_ARMED_IMPORTED_BY_HOST  deferred-to-host pytest
verdict: REFUSE__VERSION_CHECK_FAILED   detail: declarations not satisfied after arming: toyplug
```

The gate now exempts exactly the records marked deferred, and nothing else. A plugin is still
required to have metadata-readable version, to be spec-satisfied, and to be verified by
execution when the suite runs — it is only the *import* that belongs to the host.

`declared_entry_point_hosts()` reads the host from what the distribution's own bytes say:
source hooks first, then non-script entry-point groups. Measured:
`detect_test_pollution → pytest`, `matplotlib_inline → matplotlib.backend`,
`attrs → None`, `click → None`.

---

## 4. The worse defect: refusals about the environment for facts about the project

This round's real finding. `run-tests` had one way to fail:

```
REFUSE__NO_RUNNER_EXECUTED_CLEANLY   — every candidate check command failed
```

That sentence is a claim about the **environment**. But attrs (1408 passed, 1 upstream
failure) and tox (4253 passed) were both being reported with it. The environment was
perfect; the project's suite was not green. Reporting that as an environment refusal is
false, and it makes the whole result untrustworthy — a reader cannot tell "I could not arm
this" from "I armed it and the tests disagree with you."

Now:

- `REFUSE__NO_RUNNER_EXECUTED_CLEANLY` — nothing ran: no runner, or it could not
  import/collect (tox before the `completion` extra was read).
- `REFUSE__VERIFICATION_FAILED` — the suite **ran** in the armed environment and did not exit
  cleanly. `detail` names how many passed, and says in words that this is a result about the
  project, not a refusal about the environment.

Three supporting fixes were needed to make that distinction real, all found by measurement:

1. **`run-tests` must judge the isolation.** It used to fall back to the host interpreter
   after the isolation failed. The host has no `pytest`, so the fallback failed for a reason
   that says nothing about the arming — and its tail was the only thing the refusal
   reported (`/usr/bin/python3: No module named pytest` masked a 1408-pass run). When an
   isolation exists it is now the only thing asked.
2. **The runner environment must not shadow the installed copy.** Putting the repo's own
   `src/` ahead of site-packages made tox fail with `No module named tox.version` while the
   same isolation imported it fine — because `hatch-vcs` *generates* `tox/version.py` at
   build time and it does not exist in the checkout. The tree goes on `PYTHONPATH` only when
   the tree is the thing being run (no isolation); otherwise only `tests/` is added.
3. **`TIMEOUT = 180 s` was a verdict, not a bound.** tox's suite takes ~175 s on this host, so
   a slow suite was reported as `NO_RUNNER_EXECUTED_CLEANLY` after being killed mid-run
   (`exit_code: null`). Raised to 600 s, and a timeout now says it is a timeout: "a bound of
   ours, so it says nothing about the environment or the project."

---

## 5. What the trial itself was getting wrong

The harness was measuring itself, not the broker. Three defects, all fixed:

- **Shallow clone, no tags.** `git clone --depth 1` carries no tags, so a project whose
  version is derived from history cannot produce its own version module. Made worse by a
  **wrong label**: `4.67.16.dev4+g794908a7f` is a *correct* git-derived version (four commits
  past tag `4.67.15`), but it was recorded as "dynamic version fell back", which sent this
  round chasing a cache bug that did not exist for several cycles. History now enters the
  evidence digest (`.git-state`, from `rev-parse HEAD` + `describe --tags`), so an
  environment armed without tags is a *different* environment and is re-derived rather than
  answered from a record about the old one.
- **A receipt that hid its own attempts.** `runner_attempts` was computed but not serialised,
  so every refusal was undiagnosable from the artifact. It is now kept, with the tail
  widened to 600 characters.
- **Rotation order.** The `install_project` path can generate files; the trial's read-only
  clean-up fought virtualenv's permission-locked caches. Trials now use a fresh root.

---

## 6. Status

- **Tests:** 40 offline tests across the two broker suites, 0 failures — 31 in
  `test_broker_env_ready_v1.py` (24 from round 1 plus 7 new: dev-bound sorting, marker
  exclusion for this interpreter, plugin arming by host, standard-parser reading, the
  project's own declared test command, extras declared as data in `tox.toml`, and the plugin
  exemption in the final gate, which rides on the arming test) and the 9 pre-existing
  `test_the_environment_broker_v1.py` tests.
- **Live:** five unseen repositories, table in §1, receipt
  `intake/RECEIPT_ENV_READY_LIVE_20261123_V2.json`, 820 s wall clock on a cold root.
- **Warm path:** the trial also tampers with a cached record and confirms it is caught and
  re-derived (`tamper` block per repo) — a warm answer is re-executed, never believed.
- **Honest failures:** 1 upstream failure (attrs, py3.11), 3 errors from a missing system
  binary (`man`, tox). Neither is offered as a capability.
- **Model calls:** 0. `inference_endpoint_files=0`. `truth.achieved` stays **false** —
  every number here is producer-measured; independence is still open.

## 7. Still missing, named not fixed

- **System binaries are not declarations.** `man`, `node`, `gcc` are requirements no
  `pyproject.toml` states. env-ready currently discovers them only by watching a suite fail.
  The honest next step is a declared-by-observation tier for executables, verified by
  `which`+`--version` the same way imports are verified now — the same contract shape with a
  different evidence source, exactly as GUI/DOM arming was named in round 1.
- **GUI/DOM arming** (unchanged from round 1): no display in this sandbox.
- **Independence.** No independent verifier has reproduced any of these numbers.
