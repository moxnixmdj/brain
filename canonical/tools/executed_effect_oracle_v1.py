#!/usr/bin/env python3
"""A capability's declaration is a prediction; running it is the test; the artifact decides.

Why this is the first layer that can be wrong about the world
-------------------------------------------------------------
Nine logs of work in this repository have all been about the system's records of itself. Every
verdict came from a book the system holds: a blob sha, a derived count, a routing decision. A
closed book never says no, so no amount of inference over it becomes a creature.

This module opens the book. It takes a capability the registry already ships, builds a world
around it, lets it run, and then asks the only question that has an answer the system does not
control:

    did the artifact do what this capability's own declaration promised?

The declaration is `action_template.expect` -- `{"field": "output_verified", "type":
"field_equals", "value": true}` -- plus the recomputable part of `verification.observed_effect`.
That is a *prediction* the registry wrote down in advance. The verdict here never reads it as
evidence; it reads the filesystem.

The defect this found on its first run
--------------------------------------
`archive.tar_gz.create_from_manifest` accepts a manifest listing `verification_paths`, archives
them, and reports `output_verified: true`. Given a manifest naming plain repository files
(`notes.txt`) it archives **nothing the caller asked for** -- the bundle contains only the
manifest itself -- and still reports `output_verified: true`, `member_count: 1`.

    asked for : ['notes.txt']
    archive   : ['m.json']
    reported  : output_verified = True

`_manifest_paths` silently drops every path that does not start with `canonical/`. A silent drop
with a success claim is the exact shape this repository's laws exist to stop, and no test in the
tree caught it because every test passes `canonical/`-prefixed paths. Measured 2026-11-04.

Two verdicts that must never be merged
--------------------------------------
    INPUTS_IGNORED_SILENTLY   the caller's inputs are absent from the artifact and the adapter
                              said it verified. A lie about the world.
    REFUSED_AS_DECLARED       the adapter raised a named error. That is the "no" a closed book
                              cannot give, and it is a *good* outcome, not a failure.

Learning that changes behaviour
-------------------------------
Each execution writes an experience record. A capability whose self-report has contradicted its
own artifact loses its standing: `distrust` is persisted, and from then on the system does not
accept that capability's `expect` field as evidence at all -- it requires the independent
recomputation. That is a behaviour change produced by a consequence, which is the only kind of
learning that is not decoration.

What this oracle cannot see, stated up front
--------------------------------------------
It checks that the artifact reflects the inputs it was given, or that the adapter refused. It
does **not** check that the capability did the semantically right thing -- a bundle containing
the right files in the wrong order would pass. `INDEPENDENT_CHECK_KIND` is recorded per verdict
so nobody has to guess what was actually established.

Usage::

    python3 canonical/tools/executed_effect_oracle_v1.py            # measure
    python3 canonical/tools/executed_effect_oracle_v1.py --write    # write artifact + experience
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_EXECUTED_EFFECT_ORACLE_V1"
ARTIFACT = "canonical/verification/EXECUTED_EFFECT_ORACLE_V1.json"
EXPERIENCE_ARTIFACT = "canonical/verification/EXECUTION_EXPERIENCE_V1.json"
ADAPTER_DIR = ROOT / "canonical/runtime/bound_capabilities"

INDEPENDENT_CHECK_KIND = "ARTIFACT_REFLECTS_SUPPLIED_INPUTS"
# How many independent confirmations restore a demoted capability's word. One is not enough:
# a single pass can be the same input that already failed, and this repository has been bitten
# before by a check that could be satisfied by repeating itself.
RESTORE_AFTER_CONFIRMATIONS = 2
VERDICTS = {
    "REFUSED_AS_DECLARED": "the adapter raised a named error instead of pretending",
    "EFFECT_HELD": "the artifact contains what the caller supplied and the report agrees",
    "INPUTS_IGNORED_SILENTLY": "the caller's inputs are absent from the artifact while the "
                               "adapter reported success -- a claim about the world that the "
                               "world does not support",
    "SELF_REPORT_CONTRADICTS_ARTIFACT": "the adapter reported a verified effect that is not on "
                                        "disk",
    "UNVERIFIABLE_BY_THIS_ORACLE": "the effect this capability declares is not one this oracle "
                                   "can recompute",
}


# --------------------------------------------------------------------------- execution
def load_adapter_from_source(source: str, label: str):
    """Execute a capability from given source text rather than from the tree.

    This is what makes a before/after claim about a repair *reproducible* instead of
    remembered: the same situation can be replayed against the adapter as it was at any commit,
    and the verdict recomputed.
    """
    module = type(sys)(f"_oracle_replay_{label}")
    module.__dict__["__file__"] = str(ADAPTER_DIR / f"{label}.py")
    exec(compile(source, f"<{label}>", "exec"), module.__dict__)
    return module


def git_show(rev: str, path: str) -> str | None:
    import subprocess
    try:
        return subprocess.check_output(["git", "show", f"{rev}:{path}"], cwd=ROOT,
                                       text=True, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None


def load_adapter(module_name: str):
    path = ADAPTER_DIR / f"{module_name}.py"
    if not path.is_file():
        raise FileNotFoundError(module_name)
    spec = importlib.util.spec_from_file_location(f"_oracle_adapter_{module_name}", path)
    if spec is None or spec.loader is None:
        raise ImportError(module_name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "run"):
        raise AttributeError(f"{module_name} declares no run()")
    return module


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def archive_members(path: Path) -> list[str]:
    try:
        with tarfile.open(path) as handle:
            return handle.getnames()
    except (tarfile.TarError, OSError):
        return []


# --------------------------------------------------------------------------- situations
class Situation:
    """One world, one capability, one prediction -- and the inputs the caller supplied.

    `supplied` is the load-bearing field: it is what the caller asked to be reflected in the
    artifact, so it is what the independent check looks for. Without it a successful run and a
    silently-ignored run are indistinguishable from the outside.
    """

    def __init__(self, *, name: str, capability_id: str, build: Callable[[Path], dict],
                 supplied: Callable[[Path], list[str]],
                 artifact: Callable[[dict, Path], list[Path]],
                 expects_effect: bool = True) -> None:
        self.name = name
        self.capability_id = capability_id
        self.build = build
        self.supplied = supplied
        self.artifact = artifact
        self.expects_effect = expects_effect

    def as_dict(self) -> dict:
        return {"situation": self.name, "capability": self.capability_id}


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _manifest(root: Path, paths: list[str], name: str = "m.json") -> None:
    _write(root, name, json.dumps({"records": [{"verification_paths": paths}]}))


def situation_prefixed_archive() -> Situation:
    """The case every existing test covers: paths that the adapter will keep."""

    def build(root: Path) -> dict:
        _write(root, "canonical/a.txt", "alpha\n")
        _write(root, "canonical/b.txt", "beta\n")
        _manifest(root, ["canonical/a.txt", "canonical/b.txt"])
        return {"manifest_path": "m.json", "output_path": "bundle.tar.gz"}

    return Situation(
        name="archive_of_prefixed_paths",
        capability_id="archive.tar_gz.create_from_manifest",
        build=build,
        supplied=lambda root: ["canonical/a.txt", "canonical/b.txt"],
        artifact=lambda args, root: [root / args["output_path"]],
    )


def situation_plain_relative_archive() -> Situation:
    """The case nobody tests: ordinary repository files that do not start with `canonical/`.

    This is not a contrived input. "Bundle these files" is the request; the prefix is an
    implementation detail of this repository's layout.
    """

    def build(root: Path) -> dict:
        _write(root, "notes.txt", "notes\n")
        _write(root, "report.md", "report\n")
        _manifest(root, ["notes.txt", "report.md"])
        return {"manifest_path": "m.json", "output_path": "bundle.tar.gz"}

    return Situation(
        name="archive_of_plain_repository_files",
        capability_id="archive.tar_gz.create_from_manifest",
        build=build,
        supplied=lambda root: ["notes.txt", "report.md"],
        artifact=lambda args, root: [root / args["output_path"]],
    )


def situation_missing_input_archive() -> Situation:
    """A manifest naming a file that does not exist. The honest answer is a refusal."""

    def build(root: Path) -> dict:
        _manifest(root, ["canonical/absent.txt"])
        return {"manifest_path": "m.json", "output_path": "bundle.tar.gz"}

    return Situation(
        name="archive_of_a_path_that_does_not_exist",
        capability_id="archive.tar_gz.create_from_manifest",
        build=build,
        supplied=lambda root: ["canonical/absent.txt"],
        artifact=lambda args, root: [root / args["output_path"]],
        expects_effect=False,
    )


def situation_verify_good_archive() -> Situation:
    """Producer then verifier: the verifier must agree with an archive the producer made."""

    def build(root: Path) -> dict:
        _write(root, "canonical/a.txt", "alpha\n")
        _manifest(root, ["canonical/a.txt"])
        create = load_adapter("archive_tarfile")
        create.run({"manifest_path": "m.json", "output_path": "bundle.tar.gz"}, root)
        return {"archive_path": "bundle.tar.gz", "manifest_path": "m.json"}

    return Situation(
        name="verify_an_archive_that_was_just_created",
        capability_id="archive.verify.tar_gz.gnu",
        build=build,
        supplied=lambda root: ["canonical/a.txt"],
        artifact=lambda args, root: [root / args["archive_path"]],
    )


SITUATIONS: list[Situation] = [
    situation_prefixed_archive(),
    situation_plain_relative_archive(),
    situation_missing_input_archive(),
    situation_verify_good_archive(),
]


# --------------------------------------------------------------------------- the oracle
def _inputs_reflected(supplied: list[str], members: list[str], root: Path) -> dict:
    """Did the artifact contain what the caller supplied? Recomputed, not reported."""
    present = [p for p in supplied if p in members]
    return {"supplied": supplied, "present": present,
            "missing": [p for p in supplied if p not in members],
            "reflected": bool(supplied) and len(present) == len(supplied)}


def run_situation(situation: Situation, *, root: Path | None = None,
                  adapter_source: str | None = None,
                  adapter_label: str = "replay") -> dict:
    """Execute once and judge from the artifact. The returned dict is never an argument."""
    scratch = Path(root or tempfile.mkdtemp(prefix="oracle-"))
    try:
        args = situation.build(scratch)
        supplied = situation.supplied(scratch)
        module = (load_adapter_from_source(adapter_source, adapter_label)
                  if adapter_source else load_adapter(_adapter_module(situation.capability_id)))
        started = time.time()
        reported: Any = None
        refusal: str | None = None
        try:
            reported = module.run(dict(args), scratch)
        except Exception as exc:                                    # noqa: BLE001
            refusal = f"{type(exc).__name__}:{exc}"
        elapsed = round(time.time() - started, 3)

        artifacts = [p for p in situation.artifact(args, scratch) if p.exists()]
        check: dict = {"kind": INDEPENDENT_CHECK_KIND}

        # Only archive-shaped artifacts can be interrogated for input fidelity today.
        if artifacts and artifacts[0].suffixes[-2:] == [".tar", ".gz"]:
            members = archive_members(artifacts[0])
            check.update(_inputs_reflected(supplied, members, scratch))
            check["members"] = members
            check["artifact_sha256"] = _sha256(artifacts[0])
        elif artifacts:
            text = artifacts[0].read_text(errors="replace") if artifacts[0].is_file() else ""
            check.update({"reflected": all(Path(p).name in text or p in text
                                           for p in supplied) if supplied else None,
                          "artifact_sha256": _sha256(artifacts[0])})
        else:
            check.update({"reflected": None, "members": [], "artifact_sha256": None})

        claim = None
        if isinstance(reported, Mapping):
            claim = {k: reported.get(k) for k in ("output_verified", "verified",
                                                  "member_count", "status")
                     if k in reported}

        verdict = _verdict(refusal, artifacts, check, supplied, situation, claim)
        return {
            "situation": situation.name,
            "capability": situation.capability_id,
            "supplied": supplied,
            "refusal": refusal,
            "self_report": claim,
            "independent_check": check,
            "artifacts": [p.name for p in artifacts],
            "verdict": verdict,
            "elapsed_s": elapsed,
        }
    finally:
        if root is None:
            shutil.rmtree(scratch, ignore_errors=True)


def _verdict(refusal, artifacts, check, supplied, situation, claim) -> str:
    if refusal:
        # A named refusal is the system saying no to a world that does not fit its contract.
        # That is a legitimate outcome and not a failure to be scored against it.
        named = refusal.split(":", 1)[-1]
        looks_named = named.replace("_", "").isalnum() and named.isupper()
        return "REFUSED_AS_DECLARED" if (looks_named or not situation.expects_effect) \
            else "UNVERIFIABLE_BY_THIS_ORACLE"
    if not artifacts:
        return "SELF_REPORT_CONTRADICTS_ARTIFACT"      # claimed an output, wrote none
    claimed_success = isinstance(claim, Mapping) and any(
        v is True for k, v in claim.items() if k in ("output_verified", "verified"))
    reflected = check.get("reflected")
    if reflected is None:
        return "UNVERIFIABLE_BY_THIS_ORACLE"
    if reflected:
        return "EFFECT_HELD"
    return "INPUTS_IGNORED_SILENTLY" if claimed_success else "SELF_REPORT_CONTRADICTS_ARTIFACT"


def _adapter_module(capability_id: str) -> str:
    registry = load_registry()
    entry = registry.get(capability_id) or {}
    module = entry.get("adapter_module")
    if not module:
        raise KeyError(capability_id)
    return module


def load_registry() -> dict:
    doc = json.loads((ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json")
                     .read_text(encoding="utf-8"))
    return doc["capabilities"] if "capabilities" in doc else doc


# --------------------------------------------------------------------------- learning
def load_experience(path: Path | None = None) -> dict:
    path = path or (ROOT / EXPERIENCE_ARTIFACT)
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    return {"schema": SCHEMA + "_EXPERIENCE", "executions": [], "distrust": {},
            "consequences": []}


def save_experience(doc: dict, path: Path | None = None) -> None:
    path = path or (ROOT / EXPERIENCE_ARTIFACT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def record(experience: dict, row: Mapping[str, Any]) -> dict:
    """Write the experience, and demote any capability whose report contradicted its artifact.

    The demotion is the point. A capability that reports success over an artifact that does not
    contain what was asked for has demonstrated that its own `expect` field is not evidence.
    From then on the system must recompute; it may not take the capability's word.
    """
    experience.setdefault("executions", []).append(
        {k: row[k] for k in ("situation", "capability", "verdict", "supplied",
                             "self_report", "refusal", "elapsed_s")})
    distrust = experience.setdefault("distrust", {})
    if row["verdict"] == "EFFECT_HELD" and row["capability"] in distrust:
        # Distrust is evidence-weighted, not penance. A capability that keeps passing the
        # independent check has earned its word back; leaving it demoted forever would be a
        # grudge rather than a belief.
        prior = distrust[row["capability"]]
        prior["confirmations_since_demotion"] = int(
            prior.get("confirmations_since_demotion", 0)) + 1
        if prior["confirmations_since_demotion"] >= RESTORE_AFTER_CONFIRMATIONS:
            prior["strikes"] = max(0, int(prior.get("strikes", 1)) - 1)
            if prior["strikes"] == 0:
                del distrust[row["capability"]]
                experience.setdefault("consequences", []).append(
                    {"capability": row["capability"], "situation": row["situation"],
                     "consequence": "SELF_REPORT_RESTORED_AFTER_%d_INDEPENDENT_CONFIRMATIONS"
                                    % RESTORE_AFTER_CONFIRMATIONS})
    if row["verdict"] == "INPUTS_IGNORED_SILENTLY":
        prior = distrust.get(row["capability"], {"strikes": 0, "why": [], "situations": []})
        prior["strikes"] = int(prior.get("strikes", 0)) + 1
        prior["situations"] = sorted(set(list(prior.get("situations", []))
                                         + [row["situation"]]))
        prior["why"] = ["reported a verified effect whose artifact did not contain the "
                        "supplied inputs"]
        distrust[row["capability"]] = prior
        experience.setdefault("consequences", []).append(
            {"capability": row["capability"], "situation": row["situation"],
             "consequence": "SELF_REPORT_DEMOTED_REQUIRE_INDEPENDENT_RECOMPUTATION"})
    return experience


def may_trust_self_report(experience: Mapping[str, Any], capability_id: str) -> bool:
    """The behaviour the demotion changes: may this capability's own word count as evidence?"""
    return not (experience.get("distrust") or {}).get(capability_id)


# --------------------------------------------------------------------------- measure
def measure(*, write: bool = False, situations: list[Situation] | None = None) -> dict:
    situations = situations if situations is not None else SITUATIONS
    experience = load_experience()
    rows = [run_situation(s) for s in situations]
    before = dict(experience.get("distrust") or {})
    for row in rows:
        experience = record(experience, row)
    after = dict(experience.get("distrust") or {})

    registry = load_registry()
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1

    return {
        "schema": SCHEMA,
        "authority": "NO_CAPABILITY_CREDIT_EXECUTION_MEASUREMENT_ONLY",
        "instrument": "DECLARATION_IS_A_PREDICTION_THE_ARTIFACT_IS_THE_VERDICT",
        "independent_check_kind": INDEPENDENT_CHECK_KIND,
        "corpus": {
            "capabilities_in_registry": len(registry),
            "situations_built": len(situations),
            "situated_capabilities": len({r["capability"] for r in rows}),
            "cannot_situate": len(registry) - len({r["capability"] for r in rows}),
            "why_not": "no fixture builder exists for them in this sandbox; several need "
                       "third-party libraries that are not installed (tree_sitter, docx, PIL) "
                       "and several need live network or credentials",
        },
        "verdicts": counts,
        "rows": rows,
        "learning": {
            "executions_recorded": len(experience.get("executions", [])),
            "capabilities_demoted_now": sorted(set(after) - set(before)),
            "capabilities_distrusted_total": sorted(after),
            "consequences": [c for c in experience.get("consequences", [])
                             if c["capability"] in after],
            "restore_rule": "%d independent confirmations" % RESTORE_AFTER_CONFIRMATIONS,
            "behaviour_this_changes": "for a demoted capability the system no longer accepts "
                                      "its `expect` field as evidence and requires the "
                                      "independent recomputation",
        },
        "what_this_cannot_see": [
            "semantic correctness: a bundle with the right files in the wrong order passes",
            "effects that are not reflected in a file on disk",
            "capabilities with no fixture builder here",
        ],
        "non_claims": [
            "NO_CAPABILITY_CREDIT_RUNNING_ONE_CAPABILITY_IS_NOT_CAPABILITY",
            "A_REFUSAL_IS_A_GOOD_OUTCOME_AND_IS_NOT_SCORED_AS_A_FAILURE",
            "THIS_ORACLE_CHECKS_INPUT_FIDELITY_NOT_SEMANTIC_CORRECTNESS",
        ],
    }


def regress(*, rev: str, paths: list[str] | None = None) -> dict:
    """Replay every situation against the adapters as they were at `rev`, then as they are.

    A repair is only a repair if the same world now says so and used to say otherwise.
    """
    paths = paths or ["canonical/runtime/bound_capabilities/archive_tarfile.py",
                      "canonical/runtime/bound_capabilities/archive_verify_gnu_tar.py"]
    rows = []
    for path in paths:
        old = git_show(rev, path)
        if old is None:
            continue
        module = Path(path).stem
        for situation in SITUATIONS:
            if _adapter_module(situation.capability_id) != module:
                continue
            before = run_situation(situation, adapter_source=old,
                                   adapter_label=f"{module}_at_{rev[:8]}")
            after = run_situation(situation)
            rows.append({"situation": situation.name, "capability": situation.capability_id,
                         "at": rev[:8], "before": before["verdict"],
                         "after": after["verdict"],
                         "before_artifact": before["independent_check"].get("members"),
                         "after_artifact": after["independent_check"].get("members"),
                         "changed": before["verdict"] != after["verdict"]})
    return {"rev": rev, "rows": rows,
            "changed": sum(1 for r in rows if r["changed"]),
            "note": "the repair was authored by the agent; the DETECTION and the verdict came "
                    "from the oracle reading the artifact"}


def main(argv: list[str]) -> int:
    report = measure(write="--write" in argv)
    c = report["corpus"]
    print("executed effect oracle  (the declaration predicts; the artifact decides)")
    print(f"  registry capabilities     : {c['capabilities_in_registry']}")
    print(f"  situated here             : {c['situated_capabilities']} "
          f"({c['situations_built']} situations)")
    print(f"  cannot situate            : {c['cannot_situate']}")
    print(f"    -- {c['why_not']}")
    print()
    for row in report["rows"]:
        print(f"  {row['verdict']:34s} {row['capability']}")
        print(f"    situation : {row['situation']}")
        print(f"    supplied  : {row['supplied']}")
        if row["independent_check"].get("members"):
            print(f"    artifact  : {row['independent_check']['members']}")
        if row["self_report"]:
            print(f"    reported  : {row['self_report']}")
        if row["refusal"]:
            print(f"    refused   : {row['refusal'][:96]}")
    print()
    learn = report["learning"]
    print(f"  executions recorded       : {learn['executions_recorded']}")
    print(f"  demoted by this run       : {learn['capabilities_demoted_now']}")
    print(f"  distrusted total          : {learn['capabilities_distrusted_total']}")
    for con in learn["consequences"][-2:]:
        print(f"    ! {con['capability']} :: {con['consequence']}")
    print()
    print("  Note: running a capability is not capability. What is new here is that the")
    print("  verdict now comes from a world the system does not write.")
    if "--regress" in argv:
        rev = argv[argv.index("--regress") + 1] if len(argv) > argv.index("--regress") + 1 \
            else "HEAD~1"
        got = regress(rev=rev)
        print("regression replay  (the same world, before and after the repair)")
        for row in got["rows"]:
            mark = "CHANGED" if row["changed"] else "same   "
            print(f"  {mark} {row['situation']}")
            print(f"          at {row['at']}: {row['before']:32s} artifact {row['before_artifact']}")
            print(f"          now      : {row['after']:32s} artifact {row['after_artifact']}")
        print(f"  verdicts changed: {got['changed']}")
        print(f"  {got['note']}")
        if "--write" in argv:
            out = ROOT / "canonical/verification/EXECUTED_EFFECT_REGRESSION_V1.json"
            out.write_text(json.dumps(got, indent=1, sort_keys=True) + "\n", encoding="utf-8")
            print(f"  written: {out.relative_to(ROOT)}")
        return 0

    if "--write" in argv:
        (ROOT / ARTIFACT).write_text(json.dumps(report, indent=1, sort_keys=True) + "\n",
                                     encoding="utf-8")
        save_experience(load_experience())
        print(f"  written: {ARTIFACT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
