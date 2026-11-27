# SWE-bench Pro V2 (HARD-51, 51 tasks) — engine eval (measured run)

- upstream/eval commit recorded by CI: `e4cd1fbcc023b3ab2f129a482f4e58f751d80070`
- Resolve decisions come from each task's own verifier inside the official container image.
- `nop` must resolve 0/N and `oracle` must resolve N/N or the causal number is not interpretable.

- Measured under: `engine_timeout_s=900`, `eval_commit=e4cd1fbcc023b3ab2f129a482f4e58f751d80070`, `n_shards=18`
| arm | resolved | tasks | resolve % | model calls | cost USD | trial wall s (total) | engine s (total) | missing trials |
|---|---|---|---|---|---|---|---|---|
| causal | 0 | 51 | 0.0 | 0 | 0.0 | 4241.34 | 848.879 | 33 |
| nop | 0 | 51 | 0.0 | 0 | 0.0 | 2447.72 | None | 33 |
| oracle | 18 | 51 | 35.29 | 0 | 0.0 | 2308.05 | None | 33 |

## Harness gates

- `oracle_gate_pass`: **FAIL**
- `nop_gate_pass`: **FAIL**

## Shard diagnostics (harness truth: did harbor even start trials?)

| artifact | harbor exit | log lines kept | last line |
|---|---|---|---|
| `causal-s0.meta.json` | 0 | 34 | `` |
| `causal-s1.meta.json` | 0 | 28 | `` |
| `causal-s2.meta.json` | 0 | 28 | `` |
| `causal-s3.meta.json` | 0 | 28 | `` |
| `causal-s4.meta.json` | 0 | 28 | `` |
| `causal-s5.meta.json` | 0 | 28 | `` |
| `nop-s0.meta.json` | 0 | 27 | `` |
| `nop-s1.meta.json` | 0 | 27 | `` |
| `nop-s2.meta.json` | 0 | 27 | `` |
| `nop-s3.meta.json` | 0 | 27 | `` |
| `nop-s4.meta.json` | 0 | 27 | `` |
| `nop-s5.meta.json` | 0 | 27 | `` |
| `oracle-s0.meta.json` | 0 | 28 | `` |
| `oracle-s1.meta.json` | 0 | 28 | `` |
| `oracle-s2.meta.json` | 0 | 28 | `` |
| `oracle-s3.meta.json` | 0 | 28 | `` |
| `oracle-s4.meta.json` | 0 | 28 | `` |
| `oracle-s5.meta.json` | 0 | 28 | `` |

## Per-task (causal arm)

| task | reward | resolved | agent status | engine status | engine pass | files | harness error |
|---|---|---|---|---|---|---|---|
| `instance_NodeBB__NodeBB-8168c6c40707478f71b8af60300830fe` | 0.0 | no | NO_AGENT_REPORT | None | None | 0 |  |
| `instance_ansible__ansible-40ade1f84b8bb10a63576b0ac320c1` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_ansible__ansible-b748edea457a4576847a1027567812` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_ansible__ansible-c1f2df47538b884a43320f53e78719` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_ansible__ansible-d33bedc48fdd933b5abd65a77c0818` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_ansible__ansible-d62496fe416623e88b90139dc79170` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_ansible__ansible-d72025be751c894673ba85caa063d8` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_ansible__ansible-de5858f48dc9e1ce9117034e0d7e76` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_ansible__ansible-e9e6001263f51103e96e58ad382660` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_element-hq__element-web-5dfde12c1c1c0b6e48f17e3` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_element-hq__element-web-66d0b318bc6fee0d17b54c1` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_element-hq__element-web-772df3021201d9c73835a62` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_element-hq__element-web-ecfd1736e5dd9808e87911f` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_flipt-io__flipt-2ca5dfb3513e4e786d2b037075617cc` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_flipt-io__flipt-3d5a345f94c2adc8a0eaa102c189c08` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_flipt-io__flipt-524f277313606f8cd29b299617d6565` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_flipt-io__flipt-c1728053367c753688f114ec26e703c` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_flipt-io__flipt-c188284ff0c094a4ee281afebebd849` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_flipt-io__flipt-cd18e54a0371fa222304742c6312e9a` | 0.0 | no | EDITS_UPLOADED | PASS | True | 1 |  |
| `instance_flipt-io__flipt-e2bd19dafa7166c96b082fb2a59eb54` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_future-architect__vuls-5af1a227339e46c7abf3f281` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_future-architect__vuls-ca3f6b1dbf2cd24d1537bfda` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_future-architect__vuls-e1fab805afcfc92a2a615371` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_future-architect__vuls-ef2be3d6ea4c0a13674aaab0` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_gravitational__teleport-1316e6728a3ee2fc124e2ea` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_gravitational__teleport-2b15263e49da56259225815` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_gravitational__teleport-65438e6e44b6ce51458d09b` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_gravitational__teleport-7744f72c6eb631791434b64` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_gravitational__teleport-eda668c30d9d3b56d9c6919` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_gravitational__teleport-f432a71a13e698b6e1c4672` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_internetarchive__openlibrary-0dc5b20fa186f9714f` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_internetarchive__openlibrary-322d7a46cdc965bfab` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_internetarchive__openlibrary-53d376b148897466bb` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_internetarchive__openlibrary-630221ab686c64e75a` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_internetarchive__openlibrary-6e889f4a733c9f8ce9` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_internetarchive__openlibrary-7cbfb812ef0e1f9716` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_internetarchive__openlibrary-a48fd6ba9482c52760` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_internetarchive__openlibrary-b67138b316b1e9c11d` | 0.0 | no | HARNESS_ERROR | None | None | 0 | Error: [('/tmp/causal_engine_tree_3z3ob3m6/repo/ |
| `instance_navidrome__navidrome-69e0a266f48bae24a11312e9ef` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_navidrome__navidrome-874b17b8f614056df0ef021b5d` | 0.0 | no | EDITS_UPLOADED | PASS | True | 1 |  |
| `instance_navidrome__navidrome-bf2bcb12799b21069f137749e0` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_protonmail__webclients-08bb09914d0d37b0cd6376d4` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_protonmail__webclients-5f0745dd6993bb1430a951c6` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_protonmail__webclients-715dbd4e6999499cd2a576a5` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_protonmail__webclients-c5a2089ca2bfe9aa1d85a664` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_protonmail__webclients-e65cc5f33719e02e1c378146` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_qutebrowser__qutebrowser-3e21c8214a998cb1058def` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_qutebrowser__qutebrowser-c09e1439f145c66ee3af57` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_qutebrowser__qutebrowser-deeb15d6f009b3ca0c3bd5` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_qutebrowser__qutebrowser-e70f5b03187bdd40e8bf70` | None | no | NOT_RUN | None | None | 0 |  |
| `instance_tutao__tutanota-f373ac3808deefce8183dad8d167298` | None | no | NOT_RUN | None | None | 0 |  |

**35 of 51 causal trials are not attributable to the engine** (harness error, blocked upload, or no trial read). The measured rate stays 0/51 as a benchmark number — a run counts what actually ran, failures included — but the engine-attributable denominator is 16, and that is the number to quote about the engine.

### Why the trials ended the way they did (engine's own account, not ours)

`UNSOLVED`×7, `FAILED`×6, `CAUSAL_GO_SWE`×2, `CAUSAL_ANGELIC_JS_SWE`×1.

What the engine did across the causal arm (behaviour, not a score): `EDITS_UPLOADED`×2, `HARNESS_ERROR`×1, `NOT_RUN`×33, `NO_AGENT_REPORT`×1, `NO_EDITS`×14. Resolve rate is decided only by each task's own verifier.

