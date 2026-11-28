# SWE-bench Pro V2 (HARD-51, 51 tasks) — engine eval (measured run)

- upstream/eval commit recorded by CI: `c2f0e3911e79b6a96490c2b66c93f329cc93abf1`
- Resolve decisions come from each task's own verifier inside the official container image.
- `nop` must resolve 0/N and `oracle` must resolve N/N or the causal number is not interpretable.

- Measured under: `engine_timeout_s=900`, `eval_commit=c2f0e3911e79b6a96490c2b66c93f329cc93abf1`, `n_shards=6`
| arm | resolved | tasks | resolve % | model calls | cost USD | trial wall s (total) | engine s (total) | missing trials |
|---|---|---|---|---|---|---|---|---|
| causal | 0 | 51 | 0.0 | 0 | 0.0 | 9291.38 | 1787.976 | 0 |
| nop | 0 | 51 | 0.0 | 0 | 0.0 | 7132.52 | None | 0 |
| oracle | 51 | 51 | 100.0 | 0 | 0.0 | 7742.4 | None | 0 |

## Harness gates

- `oracle_gate_pass`: **PASS**
- `nop_gate_pass`: **PASS**

## Shard diagnostics (harness truth: did harbor even start trials?)

| artifact | harbor exit | log lines kept | last line |
|---|---|---|---|
| `causal-s0.meta.json` | 0 | 28 | `` |
| `causal-s1.meta.json` | 0 | 28 | `` |
| `causal-s2.meta.json` | 0 | 28 | `` |
| `causal-s3.meta.json` | 0 | 28 | `` |
| `causal-s4.meta.json` | 0 | 28 | `` |
| `causal-s5.meta.json` | 0 | 120 | `` |
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
| `instance_NodeBB__NodeBB-8168c6c40707478f71b8af60300830fe` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_ansible__ansible-40ade1f84b8bb10a63576b0ac320c1` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_ansible__ansible-b748edea457a4576847a1027567812` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_ansible__ansible-c1f2df47538b884a43320f53e78719` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_ansible__ansible-d33bedc48fdd933b5abd65a77c0818` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_ansible__ansible-d62496fe416623e88b90139dc79170` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_ansible__ansible-d72025be751c894673ba85caa063d8` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_ansible__ansible-de5858f48dc9e1ce9117034e0d7e76` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_ansible__ansible-e9e6001263f51103e96e58ad382660` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_element-hq__element-web-5dfde12c1c1c0b6e48f17e3` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_element-hq__element-web-66d0b318bc6fee0d17b54c1` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_element-hq__element-web-772df3021201d9c73835a62` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_element-hq__element-web-ecfd1736e5dd9808e87911f` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_flipt-io__flipt-2ca5dfb3513e4e786d2b037075617cc` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_flipt-io__flipt-3d5a345f94c2adc8a0eaa102c189c08` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_flipt-io__flipt-524f277313606f8cd29b299617d6565` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_flipt-io__flipt-c1728053367c753688f114ec26e703c` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_flipt-io__flipt-c188284ff0c094a4ee281afebebd849` | 0.0 | no | EDITS_UPLOADED | PASS | True | 1 |  |
| `instance_flipt-io__flipt-cd18e54a0371fa222304742c6312e9a` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_flipt-io__flipt-e2bd19dafa7166c96b082fb2a59eb54` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_future-architect__vuls-5af1a227339e46c7abf3f281` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_future-architect__vuls-ca3f6b1dbf2cd24d1537bfda` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_future-architect__vuls-e1fab805afcfc92a2a615371` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_future-architect__vuls-ef2be3d6ea4c0a13674aaab0` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_gravitational__teleport-1316e6728a3ee2fc124e2ea` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_gravitational__teleport-2b15263e49da56259225815` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_gravitational__teleport-65438e6e44b6ce51458d09b` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_gravitational__teleport-7744f72c6eb631791434b64` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_gravitational__teleport-eda668c30d9d3b56d9c6919` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_gravitational__teleport-f432a71a13e698b6e1c4672` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_internetarchive__openlibrary-0dc5b20fa186f9714f` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_internetarchive__openlibrary-322d7a46cdc965bfab` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_internetarchive__openlibrary-53d376b148897466bb` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_internetarchive__openlibrary-630221ab686c64e75a` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_internetarchive__openlibrary-6e889f4a733c9f8ce9` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_internetarchive__openlibrary-7cbfb812ef0e1f9716` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_internetarchive__openlibrary-a48fd6ba9482c52760` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_internetarchive__openlibrary-b67138b316b1e9c11d` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_navidrome__navidrome-69e0a266f48bae24a11312e9ef` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_navidrome__navidrome-874b17b8f614056df0ef021b5d` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_navidrome__navidrome-bf2bcb12799b21069f137749e0` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_protonmail__webclients-08bb09914d0d37b0cd6376d4` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_protonmail__webclients-5f0745dd6993bb1430a951c6` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_protonmail__webclients-715dbd4e6999499cd2a576a5` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_protonmail__webclients-c5a2089ca2bfe9aa1d85a664` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_protonmail__webclients-e65cc5f33719e02e1c378146` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_qutebrowser__qutebrowser-3e21c8214a998cb1058def` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_qutebrowser__qutebrowser-c09e1439f145c66ee3af57` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_qutebrowser__qutebrowser-deeb15d6f009b3ca0c3bd5` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_qutebrowser__qutebrowser-e70f5b03187bdd40e8bf70` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_tutao__tutanota-f373ac3808deefce8183dad8d167298` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |

### Why the trials ended the way they did (engine's own account, not ours)

`FAILED`×20, `NO_QUALIFIED_REPRODUCER`×17, `CAUSAL_ANGELIC_JS_SWE`×11, `UNSOLVED`×2, `CAUSAL_GO_SWE`×1.

What the engine did across the causal arm (behaviour, not a score): `EDITS_UPLOADED`×1, `NO_EDITS`×50. Resolve rate is decided only by each task's own verifier.

