# Site-general expression synthesis: producer measurement

**Status: in-sample experiment, not an independent verification or a capability claim.**
The answer keys for the four example-searchable hard-open tasks were inspected during
construction of the grammar. The solver's fresh task directory does not contain answer
keys, but the grammar was designed with knowledge of their fixes. For these tasks the
corpus pytest uses the same published examples as the search; passing it does not establish
correctness on unseen inputs.

The tool `canonical/tools/site_general_expression_synthesis_v1.py` observes locals at return,
for-iterable and conditional sites, constructs a capped set of expressions, checks the examples,
and uses the corpus pytest as the final gate. An unsuccessful capped search is reported as
`NO_EXPRESSION_WITHIN_BUDGET`, not proof that no solution exists. The process executes Python
code directly; its timer is **not a security sandbox**. Run only trusted code.

## Measurement

On QuixBugs commit `4257f44b0ff1181dedaedee6a447e133219fcebf`, with Python and pytest in a
virtual environment, the eight previously identified hard-open tasks were evaluated. Previously
known wins were not re-evaluated. The machine-readable producer receipt, including the command,
interpreter version, candidate counts, output hashes and pytest results, is
`canonical/verification/SITE_GENERAL_EXPRESSION_SYNTHESIS_20261117_V1.json`. Its
`historical_run_command` is provenance for a past producer run, not a declared verification
predicate; renaming this metadata field did not change the historical results.

| Task | Outcome | Chosen site | Corpus pytest |
|---|---|---|---|
| kheapsort | example-passing candidate | for iterable | 4 passed |
| possible_change | example-passing candidate | if guard | 10 passed |
| powerset | example-passing candidate | return | 5 passed |
| subsequences | example-passing candidate | early return | 12 passed |
| shortest_path_length | no published JSON examples | — | not run |
| shortest_path_lengths | no published JSON examples | — | not run |
| shortest_paths | no published JSON examples | — | not run |
| topological_ordering | no published JSON examples | — | not run |

No inference is made for the four tasks without examples; no overall 40-task repair rate is
claimed. The measurement loaded the implementation before documentation and positive-budget
validation edits; an exact hash of the measured source was not captured. Re-run the receipt
command to reproduce with the current tree. Tests of constructed examples and timeout handling
are in `canonical/tests/test_site_general_expression_synthesis_v1.py`.
