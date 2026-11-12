# One real migration: experience, refusal, and a near miss

**Status:** exploratory, producer-run diagnostic; not independently verified, not a benchmark estimate, and not evidence of autonomous general coding. The experiment is a retrospective selection from an existing corpus, designed and run after inspecting the tasks. It was not preregistered. No new Brain ability or verified experience is registered by this work.

## Question and setup

Can Brain's existing `edit_by_example_v1` strict repetition transfer one human code change to a related change in another project, and what goes wrong when the apparent match is misleading? We compare three deterministic, intentionally narrow procedures, each starting from a separate copy of the same target:

1. **No memory:** leave the target unchanged. This is a do-nothing lower bound, not an unaided coding agent.
2. **Hand-adapted raw reference:** manually write a task-specific literal `self.assertRegexpMatches(` → `self.assertRegex(` replacement after reading the demonstration. This is not an autonomous raw-trajectory agent. Its advantage reflects both the reference and human adaptation, so the experiment does not isolate the effect of raw versus distilled memory.
3. **One-example strict lesson:** `learn_all` followed by `repeated`, the repository's existing demonstration learner. The one rule is created once from the same full before/after file and held fixed across both target files. It remains in process; this pilot did not test persistence or restart. The lesson's restriction to shown use shapes is part of the method.

The single example is the real [CoralNet commit c3691cb](https://github.com/coralnet/coralnet/commit/c3691cba7fa03a655c89cefdf6ec79268307e1d6), parent `384dcc7332d16227b6668fdc7aa8e14190a334bd`, `project/lib/tests/test_middleware.py`. It changes two three-argument calls to the deprecated unittest assertion. The target is [Lizard commit f44f796](https://github.com/Nielsen642/lizard/commit/f44f7969c592ecbc1752827cb27dd44e79e1e75e), parent `fc8a14e84acd8a4baa2d98bdec4e7ac18ed137a5`, two files `test/testOutputCSV.py` and `test/testOutputHTML.py`, with three two-argument calls. Different projects but one migration task, not independent task samples. Both commits are in the existing `canonical/tools/edits_repeated_across_projects_commits_v1.json` corpus; that corpus does not itself execute project tests. The human commit is provenance/context, not supplied to the learner. The manually written target oracle reflects knowledge of that commit and is not blind.

A pass requires both (a) all seven tests in these two upstream modules to run successfully with *this assertion's* deprecation warning treated as an error, and (b) a separate AST check that all `self` references to the old method are renamed with no other structural changes. This is an externally added task check, not the original project configuration. It checks the desired migration as well as observed tests, but not all project behaviors. Since these are test files, edits and checks are not fully independent: a harmful test edit can weaken its own test. The AST guard reduces, but does not eliminate, that concern. Upstream code is executed in temporary copies, not a security sandbox.

## Observed results (Python 3.11)

| Procedure | Existing selected tests | AST migration check | Overall task |
|---|---:|---|---|
| No memory | 7 run, 3 errors | 0/2 files | fail |
| Hand-adapted raw reference | 7 run, 0 errors | 2/2 files | pass |
| One-example strict lesson | 7 run, 3 errors | 0/2 files | fail |

The strict learner extracted `self.assertRegexpMatches -> self.assertRegex` but refused each target file because the target calls have two arguments and the example has three. This is a *false refusal for this task*, not a failed test silently accepted. The hand-adapted reference changed three calls, and the AST check found no other structural change in the two files. The other four selected tests still passed, but this is not a whole-project regression suite.

**Wrong applicability, synthetic:** the probe also executes a deliberately constructed non-`unittest.TestCase` class where the same three-argument spelling exists but the two methods return different values. No-memory preserves behavior; both the hand-adapted reference and the strict lesson change `legacy` to `different`. Thus the strict use-shape guard did not guard receiver identity or semantics. This example is constructed, not an observed real-world regression; it demonstrates a concrete danger, not a population rate.

## Cost and limitations

The sole teacher pair totals 5,702 UTF-8 bytes; the raw substitution is two manually specified literal strings, while the strict method parses and learns the pair. Each arm runs the same single selected suite (seven tests); there are no model calls, paid services, or independent validation runs. Counts and bytes are reported rather than noisy subsecond timings. This does **not** establish end-to-end speed or cost advantage, because authoring time, selection, wider testing, validation and amortization are unmeasured. This does not test `repeat_tried`, automatic generalization, interleaving, multiple independent targets, frozen persistent lesson reload, or the full Lizard suite. The two existing test modules require third-party `mock` and `jinja2`; see below. No lesson memory or dependency is installed into the repository.

The central finding is that these controls expose both sides of the tradeoff: the existing strict learner refuses a real legitimate unseen shape, but accepts a synthetic same-shape wrong receiver. Passing tests alone would not establish the rule is safe. A stronger next experiment would use preselected independent projects, freeze all arms before examining held-out targets, run unmodified project suites plus separately authored/mutation-tested behavior checks, include negative receiver cases, and use the same autonomous solver and budgets for the memory arms.

## Reproduce

Requires Python 3.11, `gh` authenticated for GitHub API downloads, network access to GitHub and PyPI, and a trusted execution environment. Pinning the four important source files by SHA-256 detects accidental source drift; the rest of the extracted project and transitive package artifacts are not hash-locked. No upstream code is run merely by download, but **running the probe executes upstream code locally without OS sandboxing**. Inspect/trust it first. Use a throwaway directory; do not run this against an untrusted checkout.

```sh
D=/tmp/brain_reuse_experiment
mkdir -p "$D/lizard" "$D/deps"
gh api repos/Nielsen642/lizard/tarball/fc8a14e84acd8a4baa2d98bdec4e7ac18ed137a5 > "$D/lizard.tar.gz"
tar -xzf "$D/lizard.tar.gz" -C "$D/lizard" --strip-components=1
gh api -H 'Accept: application/vnd.github.raw' 'repos/coralnet/coralnet/contents/project/lib/tests/test_middleware.py?ref=384dcc7332d16227b6668fdc7aa8e14190a334bd' > "$D/teach_before.py"
gh api -H 'Accept: application/vnd.github.raw' 'repos/coralnet/coralnet/contents/project/lib/tests/test_middleware.py?ref=c3691cba7fa03a655c89cefdf6ec79268307e1d6' > "$D/teach_after.py"
python3 -m pip install --target "$D/deps" 'mock==5.2.0' 'jinja2==3.1.6' 'MarkupSafe==3.0.4'
python3 -m unittest -v test_real_commit_experience_probe_20261112
python3 real_commit_experience_probe_20261112.py --project "$D/lizard" --teacher-before "$D/teach_before.py" --teacher-after "$D/teach_after.py" --dependencies "$D/deps" --json "$D/result.json"
```

The JSON includes per-file refusal, AST evidence, complete test output and synthetic near-miss behavior. A zero process exit means the measurement executed, not that any arm passed. The results are intentionally not counted as independent verification.
