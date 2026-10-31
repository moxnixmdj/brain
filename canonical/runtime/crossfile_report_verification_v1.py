"""Reconstruct and test the cross-file report's actual diff, not its flags.

This is local reinspection/replay, not independent semantic-oracle credit or
hostile-code confinement. No source promotion or registry updates occur here.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from canonical.runtime import crossfile_task_binding_v1 as binding
from canonical.runtime.canonical_tree_attestation_v1 import tree_manifest
from canonical.runtime.swe_task_artifacts_v1 import confined_path


def inspect_report(args, result, root):
    try:
        root = Path(root).resolve()
        spec = binding.validate_binding(args, root)
        source = confined_path(root, spec["source_root"])
        if any(p.is_symlink() for p in source.rglob("*")):
            raise ValueError("SOURCE_SYMLINK_REJECTED")
        output = confined_path(root, spec["output_path"])
        raw = output.read_bytes()
        if hashlib.sha256(raw).hexdigest() != result.get("output_sha256"):
            raise ValueError("REPORT_HASH_MISMATCH")
        report = json.loads(raw)
        if (report.get("capability_id") != binding.CAPABILITY_ID
                or report.get("request_binding") != spec
                or report.get("request_binding_sha256") != binding.digest(spec)
                or report.get("source_tree_sha256") != spec["source_tree_sha256"]
                or report.get("input_sha256") != spec["input_sha256"]
                or report.get("source_root") != spec["source_root"]
                or report.get("source_promotion_performed") is not False
                or report.get("independent_semantic_oracle_credit") is not False
                or any(report.get(k) is not True for k in
                       ("pass", "verified", "source_unchanged", "input_unchanged",
                        "candidate_unchanged_during_regression"))):
            raise ValueError("REPORT_NOT_BOUND_OR_ACCEPTED")
        patches = report.get("patches")
        if not isinstance(patches, list) or not 1 <= len(patches) <= 256:
            raise ValueError("BOUNDED_PATCH_LEDGER_REQUIRED")
        relatives = [p["relative_path"] for p in patches]
        if sorted(set(relatives)) != sorted(relatives) or relatives != sorted(report.get("changed_files", [])):
            raise ValueError("PATCH_LEDGER_PATHS_INVALID")
        if ("".join(p["unified_diff"] for p in patches) != report.get("unified_diff")
                or hashlib.sha256(report["unified_diff"].encode()).hexdigest() != report.get("diff_sha256")):
            raise ValueError("PATCH_LEDGER_DIFF_MISMATCH")
        for patch in patches:
            rel = patch["relative_path"]
            if (not isinstance(rel, str) or Path(rel).is_absolute() or ".." in Path(rel).parts
                    or "\\" in rel or not rel.endswith(".py")):
                raise ValueError("PATCH_PATH_INVALID")
            original = (source / rel).resolve()
            if source not in original.parents or patch["source_path"] != original.relative_to(root).as_posix():
                raise ValueError("PATCH_PATH_OUTSIDE_SOURCE")
            created = patch.get("created")
            if type(created) is not bool or created == original.exists():
                raise ValueError("PATCH_CREATION_PREIMAGE_INVALID")
            preimage = b"" if created else original.read_bytes()
            if hashlib.sha256(preimage).hexdigest() != patch["original_sha256"]:
                raise ValueError("PATCH_PREIMAGE_HASH_MISMATCH")
        from canonical.runtime.bound_capabilities import python_issue_to_pr_orchestrate as orch
        from canonical.runtime.bound_capabilities import software_repair_crossfile_choreograph_v1 as workflow
        payload = json.loads(confined_path(root, spec["input_path"]).read_bytes())
        with tempfile.TemporaryDirectory(prefix=".crossfile-verify-", dir=output.parent) as td:
            scratch = Path(td)
            if spec["input_key"] == "issue_path":
                from canonical.runtime.bound_capabilities import python_source_symbol_index as indexer
                from canonical.runtime.bound_capabilities import python_issue_nl_parse_edit_intent as nlp
                index = indexer.build_index(".", source)
                index["source_root"] = spec["source_root"]
                cache = scratch / "index.json"
                cache.write_text(json.dumps(index), encoding="utf-8")
                payload, _ = nlp._parse_issue(root, source, spec["source_root"], cache, payload)
                if (payload.get("complete") is not True
                        or any(r.get("parsed_as") == "prose" for r in payload.get("evidence", []))):
                    raise ValueError("ISSUE_REQUIREMENTS_NOT_COMPLETELY_BOUND")
            task = workflow._task(payload, source)
            if task["edits"] != report.get("planned_edits"):
                raise ValueError("REQUESTED_EDITS_SUBSTITUTED")
            candidate = scratch / "candidate"
            shutil.copytree(source, candidate,
                            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".pytest_cache"))
            diff = scratch / "change.diff"
            diff.write_text(report["unified_diff"], encoding="utf-8")
            env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
            env.update({"GIT_CEILING_DIRECTORIES": str(scratch),
                        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
            applied = subprocess.run(["git", "apply", "-p1", str(diff)], cwd=candidate,
                                     capture_output=True, timeout=10, env=env)
            if applied.returncode != 0:
                raise ValueError("EMITTED_DIFF_DOES_NOT_APPLY")
            manifest = tree_manifest(candidate)
            content = binding.content_manifest(manifest)
            if manifest["pass"] is not True or content["tree_sha256"] != report.get("candidate_content_sha256"):
                raise ValueError("RECONSTRUCTED_CANDIDATE_HASH_MISMATCH")
            for patch in patches:
                actual = (candidate / patch["relative_path"]).read_bytes()
                if hashlib.sha256(actual).hexdigest() != patch["candidate_sha256"]:
                    raise ValueError("PATCH_CANDIDATE_HASH_MISMATCH")
            # Rebuild the exact requested transformation, without running its
            # tests. Name-presence checks alone would accept a forged patch
            # that also changed function behavior or weakened assertions.
            from canonical.runtime.bound_capabilities import python_crossfile_edit_choreograph as choreograph
            expected = scratch / "expected"
            orch._copy_tree(source, expected)
            for operation in task["edits"]:
                if operation["op"] == "move_symbol":
                    target = expected / operation["to_module"]
                    if not target.exists():
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_text("", encoding="utf-8")
            choreograph.run({"source_root": ".", "edits": json.dumps(task["edits"]),
                             "output_path": ".orchestrate_plan.json"}, expected)
            plan = json.loads((expected / ".orchestrate_plan.json").read_bytes())
            if (plan["refused_op_count"] or plan["ambiguous_site_count"]
                    or plan["planned_op_count"] != len(task["edits"])
                    or len(plan["plans"]) != len(task["edits"])):
                raise ValueError("REQUESTED_TRANSFORMATION_NOT_DECISIVE")
            for operation, planned in zip(task["edits"], plan["plans"]):
                apply = orch._apply_rename if operation["op"] == "rename_symbol" else orch._apply_move
                apply(expected, operation, planned)
            expected_manifest = tree_manifest(expected)
            if (expected_manifest["pass"] is not True
                    or binding.content_manifest(expected_manifest) != content):
                raise ValueError("DIFF_IS_NOT_THE_EXACT_REQUESTED_TRANSFORMATION")
            applied_ok, _ = orch._verify_application(candidate, task["edits"])
            if not applied_ok:
                raise ValueError("REQUESTED_OPERATION_NOT_APPLIED")
            replay = workflow._regression(candidate, scratch / "replay.xml", 60)
            reported = report.get("regression") or {}
            if (replay["pass"] is not True or reported.get("pass") is not True
                    or any(type(reported.get(k)) is not int for k in ("completed", "failed", "skipped", "returncode"))
                    or any(reported.get(k) != replay.get(k) for k in ("completed", "failed", "skipped", "returncode"))):
                raise ValueError("REPLAY_DOES_NOT_CONFIRM_REPORTED_TESTS")
            after = tree_manifest(candidate)
            if after["pass"] is not True or binding.content_manifest(after) != content:
                raise ValueError("REPLAY_MUTATED_CANDIDATE")
        binding.validate_binding(args, root)  # source/input drift during replay also refuses
        return True, "", {"request_binding_sha256": binding.digest(spec),
                          "candidate_content_sha256": content["tree_sha256"],
                          "patches_reconstructed": len(patches), "tests_replayed": replay["completed"],
                          "source_promotion_performed": False,
                          "independent_semantic_oracle_credit": False}
    except (OSError, ValueError, KeyError, TypeError, AttributeError, SystemExit,
            RuntimeError, subprocess.TimeoutExpired) as exc:
        return False, "CROSSFILE_REINSPECTION_FAILED:" + type(exc).__name__ + ":" + str(exc)[:400], {}
