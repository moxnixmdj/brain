"""Task-bound cross-file rename/move using existing Brain kernels.

Accept either an explicit edits task or a supported natural-language issue.
Reuse symbol indexing, strict issue binding, isolated issue-to-PR choreography,
fixed-point checks, impact-selected tests, and a full pytest regression run.
Original source is not promoted or intentionally edited. This is NOT general
repair synthesis, hostile-code confinement, or independent verification.

The legacy source-root-only registry template refuses: imports alone are not
a cross-file repair. Normal entry binds the explicit staged-report grammar
through crossfile_task_binding_v1 without changing the shared registry.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import keyword
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

from canonical.runtime.canonical_tree_attestation_v1 import tree_manifest
from canonical.runtime import crossfile_task_binding_v1 as binding
from canonical.runtime.swe_task_artifacts_v1 import confined_path, fresh_output, publish_report

SCHEMA = "PROJECT_BRAIN_SOFTWARE_REPAIR_CROSSFILE_CHOREOGRAPH_V1"
CAPABILITY_ID = "software.repair.choreograph.crossfile.v1"
PROVIDES = ["software.repair.choreography.verified", "software.patch.crossfile.atomic"]
REQUIRES = ["python.fault.localization.symbol_ranked", "python.source.symbols.index.ast"]


def _task(payload, source):
    if not isinstance(payload, dict) or not str(payload.get("issue_id") or "").strip():
        raise ValueError("ISSUE_ID_REQUIRED")
    edits = payload.get("edits")
    if not isinstance(edits, list) or not 1 <= len(edits) <= 32:
        raise ValueError("BOUNDED_EDITS_REQUIRED")
    for edit in edits:
        if not isinstance(edit, dict):
            raise ValueError("EDIT_MUST_BE_OBJECT")
        op = edit.get("op")
        allowed = ({"op", "module", "name", "new_name"} if op == "rename_symbol" else
                   {"op", "module", "qualname", "to_module"} if op == "move_symbol" else set())
        if not allowed or set(edit) != allowed:
            raise ValueError("UNSUPPORTED_OR_INCOMPLETE_EDIT")
        for key in ("module", "to_module"):
            if key not in edit:
                continue
            raw = edit[key]
            if (not isinstance(raw, str) or "\\" in raw or Path(raw).is_absolute()
                    or ".." in Path(raw).parts or not raw.endswith(".py")):
                raise ValueError("EDIT_PATH_INVALID")
            target = (source / raw).resolve()
            if source not in target.parents:
                raise ValueError("EDIT_PATH_OUTSIDE_SOURCE")
        for key in allowed - {"op", "module", "to_module"}:
            value = edit[key]
            if not isinstance(value, str) or not value.isidentifier() or keyword.iskeyword(value):
                raise ValueError("EDIT_IDENTIFIER_INVALID")
    return {k: payload[k] for k in ("issue_id", "title", "body", "edits") if k in payload}


def _regression(worktree, junit, timeout):
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             "--junitxml=" + str(junit), "."],
            cwd=worktree, capture_output=True, timeout=timeout)
        root = ET.parse(junit).getroot()
        cases = list(root.iter("testcase"))
        skipped = sum(c.find("skipped") is not None for c in cases)
        failed = sum(c.find("failure") is not None or c.find("error") is not None for c in cases)
        completed = len(cases) - skipped
        return {"pass": proc.returncode == 0 and completed > 0 and failed == 0,
                "returncode": proc.returncode, "completed": completed,
                "failed": failed, "skipped": skipped,
                "stdout_tail": proc.stdout[-4000:].decode("utf-8", "replace"),
                "stderr_tail": proc.stderr[-4000:].decode("utf-8", "replace")}
    except subprocess.TimeoutExpired:
        return {"pass": False, "status": "REGRESSION_TIMEOUT", "completed": 0}
    except (OSError, ET.ParseError):
        return {"pass": False, "status": "REGRESSION_EVIDENCE_UNAVAILABLE", "completed": 0}



def _exact_emitted_diff(source, worktree, before, candidate, changed, emitted):
    """Ensure the emitted diff represents the tree actually tested.

    Selected tests run inside the legacy orchestrator. They must not silently
    add candidate changes that are absent from its previously emitted diff.
    """
    original = {r["path"]: r["sha256"] for r in before["files"]}
    staged = {r["path"]: r["sha256"] for r in candidate["files"]
              if r["path"] not in {".orchestrate_plan.json", ".orchestrate_stage.diff",
                                     ".orchestrate_testselect.json"}}
    if set(original) - set(staged):
        return None
    actual = sorted(p for p, digest in staged.items() if original.get(p) != digest)
    if actual != sorted(changed):
        return None
    chunks = []
    patches = []
    for rel in actual:
        old = (source / rel).read_text(encoding="utf-8") if rel in original else ""
        new = (worktree / rel).read_text(encoding="utf-8")
        chunk = "".join(difflib.unified_diff(
            old.splitlines(keepends=True), new.splitlines(keepends=True),
            fromfile="a/" + rel if rel in original else "/dev/null", tofile="b/" + rel))
        chunks.append(chunk)
        patches.append({"relative_path": rel, "unified_diff": chunk,
                        "original_sha256": hashlib.sha256(old.encode()).hexdigest(),
                        "candidate_sha256": hashlib.sha256(new.encode()).hexdigest(),
                        "created": rel not in original})
    return patches if "".join(chunks) == emitted else None

def run(args, root):
    repo = Path(root).resolve()
    source = confined_path(repo, args.get("source_root"))
    if not source.is_dir():
        raise ValueError("SOURCE_ROOT_NOT_DIRECTORY")
    modes = [k for k in ("issue_path", "task_path") if args.get(k)]
    if len(modes) != 1:
        raise ValueError("EXACTLY_ONE_ISSUE_OR_TASK_REQUIRED")
    input_path = confined_path(repo, args[modes[0]])
    input_bytes = input_path.read_bytes()
    payload = json.loads(input_bytes)
    output = fresh_output(repo, args.get("output_path"), "canonical/tmp_choreograph_repair.json")
    if output == source or source in output.parents:
        raise ValueError("OUTPUT_OVERLAPS_SOURCE")
    timeout = args.get("timeout_s", 60)
    if type(timeout) is not int or not 1 <= timeout <= 120:
        raise ValueError("TIMEOUT_MUST_BE_BOUNDED_INTEGER")
    before = tree_manifest(source)
    if before["pass"] is not True:
        raise ValueError("UNSUPPORTED_SOURCE_TREE_ENTRY")
    if "request_binding" in args:
        binding.validate_binding(args, repo, before)
    # Reject symlinks even inside ignored metadata: copytree follows links.
    if any(p.is_symlink() for p in source.rglob("*")):
        raise ValueError("SOURCE_SYMLINK_REJECTED")
    if any(p.name.startswith(".orchestrate_") for p in source.iterdir()):
        raise ValueError("SOURCE_RESERVED_STAGE_FILE")
    if modes[0] == "task_path":
        payload = _task(payload, source)  # reject unsafe ops BEFORE creating scratch
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = {}
    regression = {"pass": False, "completed": 0, "status": "NOT_EXECUTED"}
    diff = ""
    changed = []
    candidate_sha = None
    candidate_content_sha = None
    patches = []
    candidate_unchanged = False
    reason = ""
    parse = None
    with tempfile.TemporaryDirectory(prefix=".crossfile-", dir=output.parent) as raw:
        scratch = Path(raw)
        rel = lambda p: p.relative_to(repo).as_posix()
        try:
            if modes[0] == "issue_path":
                from canonical.runtime.bound_capabilities import python_source_symbol_index as indexer
                from canonical.runtime.bound_capabilities import python_issue_nl_parse_edit_intent as nlp
                # Fresh index outside source avoids the parser's fixed probe
                # filename and cannot overwrite any pre-existing source file.
                frozen_issue = scratch / "issue.json"
                frozen_issue.write_bytes(input_bytes)
                index = scratch / "index.json"
                index_data = indexer.build_index(".", source)
                index_data["source_root"] = rel(source)  # cache's declared search root
                index.write_text(json.dumps(index_data), encoding="utf-8")
                parsed = scratch / "parsed.json"
                parse = nlp.run({"source_root": rel(source), "issue_path": rel(frozen_issue),
                                 "index_path": rel(index), "output_path": rel(parsed)}, repo)
                payload = json.loads(parsed.read_bytes())
                if parse.get("complete") is not True:
                    raise ValueError("ISSUE_NOT_COMPLETELY_BOUND")
                if any(r.get("parsed_as") == "prose" for r in payload.get("evidence", [])):
                    raise ValueError("UNSUPPORTED_ISSUE_PROSE_NOT_DISCARDED")
                payload = _task(payload, source)
            from canonical.runtime.bound_capabilities import python_issue_to_pr_orchestrate as orch
            task = scratch / "task.json"
            task.write_text(json.dumps(payload), encoding="utf-8")
            worktree = scratch / "candidate"
            summary = scratch / "summary.json"
            patch = scratch / "change.diff"
            intent = scratch / "pr.json"
            stage = orch.run({"task_path": rel(task), "source_root": rel(source),
                              "worktree_path": rel(worktree), "output_path": rel(summary),
                              "diff_path": rel(patch), "pr_intent_path": rel(intent),
                              "python_executable": sys.executable, "timeout_s": timeout}, repo)
            # Inspect actual artifacts, not merely the returned booleans.
            summary_bytes = summary.read_bytes()
            diff = patch.read_text(encoding="utf-8")
            pr = json.loads(intent.read_bytes())
            changed = pr["body"]["changed_files"]
            if (hashlib.sha256(summary_bytes).hexdigest() != stage.get("output_sha256")
                    or stage.get("diff_sha256") != hashlib.sha256(diff.encode()).hexdigest()
                    or stage.get("verified") is not True
                    or stage.get("applied_op_count") != len(payload["edits"])
                    or not changed or not diff.strip()
                    or pr["body"]["proof"].get("fixed_point_verified") is not True):
                raise ValueError("STAGED_CHANGE_NOT_VERIFIED")
            candidate = tree_manifest(worktree)
            candidate_sha = candidate["tree_sha256"]
            if candidate["pass"] is not True:
                raise ValueError("CANDIDATE_MANIFEST_INVALID")
            patches = _exact_emitted_diff(source, worktree, before, candidate, changed, diff)
            if patches is None:
                patches = []
                raise ValueError("TESTED_TREE_DIFF_MISMATCH")
            for row in patches:
                row["source_path"] = rel(source / row["relative_path"])
            candidate_content_sha = binding.content_manifest(candidate)["tree_sha256"]
            regression = _regression(worktree, scratch / "regression.xml", timeout)
            after_candidate = tree_manifest(worktree)
            candidate_unchanged = (after_candidate["pass"] is True
                                   and after_candidate["tree_sha256"] == candidate_sha)
        except (SystemExit, ValueError, RuntimeError, OSError, KeyError, TypeError,
                subprocess.TimeoutExpired) as exc:
            reason = type(exc).__name__ + ":" + str(exc)[:2000]
    after = tree_manifest(source)
    source_unchanged = after["pass"] is True and before["tree_sha256"] == after["tree_sha256"]
    input_unchanged = input_path.is_file() and input_path.read_bytes() == input_bytes
    accepted = (not reason and stage.get("verified") is True and regression["pass"] is True
                and source_unchanged and input_unchanged and candidate_unchanged)
    report = {
        "schema": SCHEMA, "capability_id": CAPABILITY_ID,
        "adapter": "software_repair_crossfile_choreograph_v1",
        "status": "PASS__STAGED_CROSSFILE_CHANGE_TESTED" if accepted else "OPEN__CROSSFILE_CHANGE_NOT_ACCEPTED",
        "pass": accepted, "verified": accepted, "choreography_verified": accepted,
        "verification_mode": "EXPLICIT_RENAME_MOVE_FIXED_POINT_SELECTED_AND_FULL_PYTEST",
        "source_root": rel(source), "source_tree_sha256": before["tree_sha256"],
        "source_unchanged": source_unchanged, "input_unchanged": input_unchanged,
        "input_sha256": hashlib.sha256(input_bytes).hexdigest(),
        "candidate_tree_sha256": candidate_sha, "candidate_unchanged_during_regression": candidate_unchanged,
        "candidate_content_sha256": candidate_content_sha,
        "patches": patches if accepted else [],
        "request_binding": args.get("request_binding"),
        "request_binding_sha256": args.get("request_binding_sha256"),
        "planned_edits": payload.get("edits", []) if isinstance(payload, dict) else [],
        "changed_files": changed, "unified_diff": diff,
        "diff_sha256": hashlib.sha256(diff.encode()).hexdigest(),
        "stages": {k: v for k, v in stage.items() if k not in {"output_path", "seconds"}},
        "issue_binding": ({k: v for k, v in parse.items() if k != "output_path"} if parse else None),
        "regression": regression, "reason": reason,
        "source_promotion_performed": False, "independent_semantic_oracle_credit": False,
        "model_dependency_count": 0, "incremental_spend_usd": 0,
    }
    return publish_report(repo, output, report)
