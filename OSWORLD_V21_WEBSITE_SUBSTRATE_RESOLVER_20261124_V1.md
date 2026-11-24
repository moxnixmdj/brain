# OSWorld 2.1 Website Substrate Resolver V1

**Date:** 2026-11-24 UTC
**Branch:** `arena/6f8ac9ce-brain`
**Scope:** pinned public OSWorld-web source bytes and generated Docker Compose graph only.
**Status:** producer-side local verification complete; distinct runner-owned OIDC receipt pending.
**Truth:** `false`; §6 `NOT_MET`; no capability, family, terminal or truth credit.

## Decision-relevant question

Iteration 11 recorded a runner-owned OSWorld 2.1 blocker receipt with 27/27 pinned-release source checks and eight missing reproducibility prerequisites. It did not resolve the public website-substrate question: can the `Task-Web/OSWorld-web@osworld-v2.1` root tag, its 25 gitlink commits, its generated Compose include graph and its 24 runtime `web-compose.yml` files be bound to exact bytes and checked by `docker compose config` on a distinct public runner **without** starting containers, pulling images, deploying websites, downloading gated bodies, running an OSWorld task or claiming a score?

This iteration answers only that narrower question. It resolves a reproducible deployment-plan substrate, not a deployment and not an OSWorld evaluation.

## Route selection and live source scan

The deletion-first route reuses the existing OIDC carrier, exact-source binding, AST audit, zero-model policy shape, sanitized runner receipt and gate spine. It adds no model, GUI agent, VM boot, container deployment, hidden-task reader, gated-body download or producer-written public-runner receipt. The fastest sufficient contrast is a distinct OIDC run that binds public website source bytes and validates the Compose graph with `docker compose config --quiet` and `--format json`, both with `--no-path-resolution`, while recording zero image pulls, zero container starts, zero Docker builds and zero website HTTP responses.

Current source classes checked: inherited Brain carrier/policy, official primary OSWorld V2 and release notes, GitHub code/API registry, public OSWorld-web pinned tag and submodules, broad web/community Docker Compose validation practice, and independent OIDC runner evidence. The official OSWorld V2 repository describes self-hosting `Task-Web/OSWorld-web@osworld-v2.1` and setting `WEBSITE_HOST_SUFFIX` [1](https://github.com/xlang-ai/OSWorld-V2). The release notes describe deploying the matching website tag with pinned submodules [2](https://github.com/xlang-ai/OSWorld-V2/releases). Docker Compose `config` parses, resolves and renders a Compose file; its `--quiet` mode validates without starting services [3](https://docs.docker.com/reference/cli/docker/compose/config/). No dominating alternative was found that resolves the eight execution blockers without gated task classes, complete assets, a reachable website deployment, provider image, evaluator dependencies or maintainer verification.

## Exact pinned substrates

- Release tag: `osworld-v2.1`
- Website tag commit: `60c89fe6a8ed934668619d8d26132848239eb8ee`
- Website gitlinks: **25** (24 runtime apps plus `basesite`)
- Generated Compose runtime app includes: **24**
- App services parsed from runtime compose files: **39**
- Expected total Compose services including Caddy: **40**
- Build services in runtime compose files: **35**
- External image references in runtime compose files: **3**
- Root `docker-compose.yml` SHA-256: `53d986c0e3d406ae1c025900e81adf880c12525a5d2ebc69e095c5ff6b266a26`
- Root `docker-compose.main.yml` SHA-256: `304bd1aca0c848fab07c68bacac791c6d23890209e02d9e8e2709ce830cb647b`

### Website gitlink commits

| Submodule | Pinned commit |
|---|---|
| `awsconsole_web` | `9f39391f3b9554fe3c4ae3b464ff0c579764cec2` |
| `basesite` | `7a881f8dd766615b7c512f3e4140960d56ddc3e3` |
| `budgetwise_web` | `d7450221ba688ab50f0abb74fa1bf1dbcf8bc601` |
| `calendar_web` | `5c96a0c57265e173ef3434f1667e2523ade1ed57` |
| `careerlink_web` | `3489e34a72cb8918ed295678b14d52ce5073d52c` |
| `cloudcrm_web` | `44c1d8650a9b262d2e903dcc31ff827d1120297c` |
| `dinogame_web` | `a822adbe4ea23b48e06ae051dc14ddf5aea0b69e` |
| `eventix_web` | `4ed784f8c5ca666572e70a0e450e560617747d55` |
| `expenseflow_web` | `4e0883e3ff2486c349a0cb9409d48d77081809ee` |
| `formcraft_web` | `0b7138aeacd2ed3c89ec095ef935f3912fc95777` |
| `glbviewer_web` | `42590687cf938ea854c64c04add117df1ff19ea9` |
| `insurance_claim_web` | `36e728f8aa60bd38bcfb5f26b3963a0727aed873` |
| `interfacinglinux_web` | `86e08dc6e26501b3a56cf384fe6073af6b9152f6` |
| `mailhub_web` | `6ea8fb2e8071a53a2d23c39bd206e848957f0f67` |
| `overleaf_collab_web` | `307d7e2d0b9ab32887145725fe14001ec4180d65` |
| `overleaf_web` | `1b5c1e0c5a92861e0c9bfeebf1c2074f976b28b6` |
| `reviewsphere_web` | `aa7439663128975edcca83802d3ea8dc0ab95ca5` |
| `slidepuzzle_web` | `137952038cb9c646e3075829b575f230a1f130d3` |
| `streamview_web` | `62c879ea14b5d3950c91d232eca4041b3b0cde98` |
| `teamchat_web` | `9c50b43bb7c1b03deba31eef234ed805f8014603` |
| `travelhub_ad_web` | `9b664c60c040d4d5f709367a616bf21b2f0765ff` |
| `trippza_web` | `223e5977a57c3f1022633aa1f5d5019d3396d498` |
| `vaultbank_web` | `51dca9c6346ffa15095cfde5c1d87380cbc3bc79` |
| `visaapplication_web` | `9db18412b25f56d586d619205d32da0b72be21f6` |
| `wandb_web` | `d0cb99226f69628b93eca2f4f335cca230297ef2` |

### Runtime web-compose SHA-256 bindings

| File | SHA-256 |
|---|---|
| `awsconsole_web/web-compose.yml` | `1147345fb37cf84e31a52dde442141982bde4f917ce8d88d8bed72afb14303a6` |
| `budgetwise_web/web-compose.yml` | `47d061331a28bfaf6edb47675e61b055c58b64fde532b0599df0eb64c2ecb663` |
| `calendar_web/web-compose.yml` | `a980b4c5b75423fb6cb398b3b30cc4104bdd35358d1e43b2e723e76a7216999d` |
| `careerlink_web/web-compose.yml` | `0a30e615c901a906764e0efb3ff913bcb37cdc4b86e842d5856e7a75301ae675` |
| `cloudcrm_web/web-compose.yml` | `981fe3ee7af5327ed8b9b8723a3443c5ca00dc22b65dc112fa150b2f7b15bea5` |
| `dinogame_web/web-compose.yml` | `30ef9adf8a5c5b7326a59ac518b125ef06b92fb1392fb40447a2508664047cf7` |
| `eventix_web/web-compose.yml` | `36681e3b4e51d404936a9ad2bc2e94af53c09873ebd248fe12e5d06d16628ce3` |
| `expenseflow_web/web-compose.yml` | `2b2e808ca8a5cdf227ab536584d5c27cc6090436e02b1975918fb05a41949496` |
| `formcraft_web/web-compose.yml` | `e8e7dbe3d4e487a599d1fa2816b56eb3653b5e7f800eba63a0cef53f22cc2181` |
| `glbviewer_web/web-compose.yml` | `8cd02a183a33fb0403f31ed5deea750f46125f939d41b495e059c49dbc2dc268` |
| `insurance_claim_web/web-compose.yml` | `1aac2551e4af8a7dd1b443a5223f2e2ff0a17cea5d83cd49f2bd34dd622fae7b` |
| `interfacinglinux_web/web-compose.yml` | `fc2be436b4ca1aa3ff5582800d7447e7f3027712d4f2c5a202a757cb9bc5280c` |
| `mailhub_web/web-compose.yml` | `5850cfd2dd0a7ce01d72a47e4016e211ce2ca74c6f28f5250280f5054cc4c9f8` |
| `overleaf_collab_web/web-compose.yml` | `997d62ebb6313ca1f2225a0597018e7a726d2dbbe6f63f4ef402ae79b2d04d09` |
| `overleaf_web/web-compose.yml` | `3542983b5e179b6f0a7ddb4ad421fa859122a207ecffdb9105fbf2a27649b1da` |
| `reviewsphere_web/web-compose.yml` | `beb1fd22b99fe33e3702a8f48f454c95a018da273e0c62289727b78b0740ee3d` |
| `slidepuzzle_web/web-compose.yml` | `2561c0c64ca6aca301f9d866ac8b2b97acd6b2ed755ef2e038de6b0feadb3205` |
| `streamview_web/web-compose.yml` | `21cedc75dff46b38fac51dcbc78299bea560e6479ced5fa56af37dafd6e96191` |
| `teamchat_web/web-compose.yml` | `03cd60b170f69b13e91360e92caf9a18eceddb7f678aed6dec2052472e6b9592` |
| `travelhub_ad_web/web-compose.yml` | `6fa82d7bb71db0e832a1be9e82110663ebc493a4d23ec019e67e3403a8b9ab9e` |
| `trippza_web/web-compose.yml` | `87f9d4acdfec939cc332f30a237bf8ebfa0234b75d9303de8574414117353a32` |
| `vaultbank_web/web-compose.yml` | `21f62a3c5a5f53fc3f3fca7c8d13e7f74c5714b4e1aa1e50b165b99e4fb00b75` |
| `visaapplication_web/web-compose.yml` | `f240fd8114e1d443478908665f5e40604456fae4d34facbefa65c45a5fc1d286` |
| `wandb_web/web-compose.yml` | `509bc363b45a9ea69658f128c3843f7349d4eea9933c53242f91525ef6d347b0` |

One public runtime-asset URL literal exists in `interfacinglinux_web/web-compose.yml` as a Compose default. It is a configuration literal only: the workflow does not fetch that body, does not set `OSWORLD_FILE_BASE_URL`, does not use an HF token and makes zero gated-dataset status probes. No raw benchmark task, hidden test, solution, verifier output, gated task-class body or gated complete-asset body is saved in the workspace.

### Brain-owned source SHA-256 bindings

- `canonical/harbor/osworld_v21_website_substrate_policy_v1.py` — `83003680f6d72beda2fbf8fdfc15b8225b4473035e441e304e0d7d5a095d1724`
- `canonical/tests/test_osworld_v21_website_substrate_policy_v1.py` — `6b8c22cac8eee2c90e203e6c0f13b3f9f483813260d013b05a337432a246e589`
- `.github/workflows/zero-model-osworld-v21-website-substrate-v1.yml` Git blob — `163ed1a32d8df3893c1c9225b743ccd559ceb0bf`

## Local producer checks

Nine new policy tests pass. A local workflow checker parses the workflow YAML, compiles all five embedded Python blocks, checks the exact two-source SHA-256 binding, replays the pinned website source verification against a fresh `/tmp` clone of `Task-Web/OSWorld-web@osworld-v2.1`, verifies 25 gitlink commits, two root Compose hashes and 24 runtime `web-compose.yml` hashes, then runs the zero-model policy on a sanitized local probe. It prints `OSWORLD_V21_WEBSITE_SUBSTRATE_SOURCE_REPLAY_PASS 13 checks 25 gitlinks 24 web-compose hashes` and `OSWORLD_V21_WEBSITE_SUBSTRATE_DECISION_LOCAL_PASS 9 blocked reasons no score no credit`. Full selected gates and a distinct runner-owned receipt are pending.

## Honest boundary

`docker compose config` validation is not `docker compose up`. A 40-service Compose graph is not 40 running websites. A local `HOST_SUFFIX=localhost` interpolation is not a reachable `WEBSITE_HOST_SUFFIX` deployment. Verified public website source bytes are not gated task classes, complete assets, provider VM image, pinned evaluator dependencies or a maintainer-style verifier. No OSWorld task, reward vector, aggregate score, §6 verification, capability credit, family credit, terminal credit or terminal truth change exists. `truth.achieved=false` and §6 remains `NOT_MET`.
