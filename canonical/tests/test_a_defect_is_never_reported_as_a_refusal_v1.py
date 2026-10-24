"""A defect is never reported as a refusal, and a refusal is never reported as a defect.

``failure_reason`` (PR #6104) answers *why* a goal failed.  It does not answer
*whose fault it is*, and those are not the same question.  A refusal means the
system behaved correctly; an adapter fault means the system has a bug.  Both were
reported as ``LIVE_CONTROLLER_EXECUTION_OR_VERIFICATION_FAILURE``, so a caller --
and the learning loop -- could not tell them apart, and a real defect could hide
inside a wall of legitimate refusals.

Measured on d1ad8da over the 72 verified capabilities, every stated input supplied,
through ``solve()``: 12 pass, 49 fail as contract refusals, 11 as environment
blockers, 0 unknown.  And with nine hostile-but-valid fixtures across the whole
live surface (392 clean outcomes) exactly ONE site crashes:
``evidence_decision_verify.py:101``, reachable as ``decision.synthesis.verify.stdlib``,
given a document whose top level is a list, null or a number.

That site cannot be repaired here.  Its exact bytes are pinned as the capability's
``verifier_git_blob``, and the single adapter invocation point in
``astra_runtime.py`` is pinned as ``subject.astra_runtime.git_blob_sha``.  So the
defect cannot be removed by this change -- only LABELLED, which is the least that is
true and the precondition for anyone acting on it.
"""
import importlib.util
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
for _p in (str(ROOT), str(ROOT / "canonical/runtime")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from canonical.runtime.live_brain_route_admission_v1 import (   # noqa: E402
    failure_kind, failure_reason,
    FAILURE_KIND_ADAPTER_FAULT, FAILURE_KIND_CONTRACT,
    FAILURE_KIND_ENVIRONMENT, FAILURE_KIND_UNKNOWN,
)

WORK = ROOT / "canonical/astra_runtime/tmp/defect_kind_probe"


def _real_adapter_fault_reason():
    """The exact AttributeError text the frozen adapter produces, obtained by running
    the crashing function, so this test cannot drift from reality.

    ``verify(problem, result)`` at evidence_decision_verify.py:101 is the site.  It is
    called through ``run``, whose own ``_safe`` rejects a scratch-directory path with
    PATH_OUTSIDE_REPOSITORY before the crash can be reached, so the function is
    invoked directly -- that is the layer that actually dies.
    """
    path = ROOT / "canonical/runtime/bound_capabilities/evidence_decision_verify.py"
    spec = importlib.util.spec_from_file_location("frozen_adapter_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        module.verify({"x": 1}, [{"id": "a"}])
    except (AttributeError, TypeError) as exc:
        return "%s:%s" % (type(exc).__name__, exc)
    except Exception:                        # noqa: BLE001 - repaired upstream
        return None
    return None


class DefectIsNeverReportedAsARefusalTest(unittest.TestCase):

    def test_the_frozen_adapter_really_does_still_crash(self):
        """Records the defect this change labels.  If a future PR repairs the frozen
        file this returns None and the rest of the class is exercised on the literal
        instead -- the assertion is on the CLASSIFIER, not on the bug persisting."""
        reason = _real_adapter_fault_reason()
        if reason is not None:
            self.assertRegex(reason, r"^(AttributeError|TypeError):")
            self.assertEqual(failure_kind({"reason": reason}), FAILURE_KIND_ADAPTER_FAULT)

    def test_an_adapter_fault_is_its_own_kind(self):
        for reason in (
            "AttributeError:'list' object has no attribute 'get'",
            "TypeError:'int' object is not subscriptable",
            "KeyError:'records'",
            "IndexError:list index out of range",
            "UnboundLocalError:cannot access local variable 'out'",
            "NameError:name 'manifest' is not defined",
        ):
            self.assertEqual(failure_kind({"reason": reason}), FAILURE_KIND_ADAPTER_FAULT, reason)

    def test_a_named_contract_error_is_never_called_a_defect(self):
        """The 355 RuntimeError raise sites and 72 ValueError sites are the adapters'
        contract vocabulary.  Classifying any of them as a defect would be worse than
        no classifier at all."""
        for reason in (
            "RuntimeError:MANIFEST_RECORDS_REQUIRED",
            "RuntimeError:JSON_DOCX_SPEC_UNRESOLVED",
            "RuntimeError:SACCR_INPUT_SHAPE_REJECTED:needs records",
            "RuntimeError:URL_KEY_NOT_UNIQUE:0",
            "RuntimeError:ARCHIVE_MEMBER_SET_MISMATCH:{...}",
            "ValueError:EXTRACTION_SCHEMA_INVALID",
            "TOOL_REPORTED_PASS_FALSE:python.software.request.semantic_behavior",
            "pdf.extract.text.pypdf:contract_not_stated:pdf_path",
            "web.browser.rendered.capture.chromedriver:0",
        ):
            self.assertEqual(failure_kind({"reason": reason}), FAILURE_KIND_CONTRACT, reason)

    def test_a_missing_dependency_is_the_machines_problem_not_the_brains(self):
        for reason in (
            "Blocker:BOUND_APT_METADATA_NOT_FOUND:zint",
            "ModuleNotFoundError:No module named 'PIL'",
            "Blocker:BOUND_PYPI_INSTALL_FAILED:ERROR",
        ):
            self.assertEqual(failure_kind({"reason": reason}), FAILURE_KIND_ENVIRONMENT, reason)

    def test_a_reason_with_no_name_at_all_is_unknown_not_guessed(self):
        """The classifier must not invent a verdict for a genuinely nameless failure;
        that is exactly the case PR #6104 exists to eliminate."""
        self.assertEqual(failure_kind({"reason": "something nobody named"}), FAILURE_KIND_UNKNOWN)

    def test_the_marker_needs_a_colon_so_a_path_cannot_trigger_it(self):
        """A bare substring match would call an ordinary path a defect."""
        self.assertNotEqual(
            failure_kind({"reason": "RuntimeError:PATH_OUTSIDE_REPOSITORY:TypeError_fixtures"}),
            FAILURE_KIND_ADAPTER_FAULT)

    def test_it_reads_the_same_field_precedence_as_failure_reason(self):
        """failure_kind must not reintroduce the bug #6104 fixed by reading one field."""
        result = {"compiler_detail": "", "reason": "AttributeError:'list' object has no attribute 'get'"}
        self.assertEqual(failure_reason(result).split(":")[0], "AttributeError")
        self.assertEqual(failure_kind(result), FAILURE_KIND_ADAPTER_FAULT)

    def test_the_whole_live_surface_is_fully_classified(self):
        """Whole class, and the number that moved.  With every stated input supplied,
        no failure across the 72 verified capabilities is left UNKNOWN.  Measured 17
        of 60 UNKNOWN with the first marker-list version of this classifier."""
        reg = json.loads(
            (ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())["capabilities"]
        target = ROOT / "canonical/astra_runtime/tmp/defect_kind_probe/sample.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps([{"id": "a", "name": "alpha", "status": "PASS"}]))
        rel = "canonical/astra_runtime/tmp/defect_kind_probe/sample.json"
        from canonical.runtime.live_brain_route_admission_v1 import solve
        tmpl = re.compile(r"\$\{input\.([A-Za-z0-9_]+)\}")
        owned = ("output_path", "result_path")
        unknown = []
        failures = 0
        for index, (cid, entry) in enumerate(sorted(reg.items())):
            roles = sorted(set(tmpl.findall(json.dumps(entry.get("action_template") or {}))))
            need = [r for r in roles
                    if r not in owned and not r.endswith(("_output_path", "_result_path"))]
            stem = re.sub(r"\.py\.auto\.v\d+$", "", cid.rsplit("/", 1)[-1])
            goal = "Run the %s %s." % (
                stem.replace("_", " ").replace(".", " "),
                " ".join("with %s %s" % (r.replace("_", " "), rel) for r in need))
            result = solve({"task_id": "KIND%02d" % index, "goal": goal})
            if result.get("pass") is True:
                continue
            failures += 1
            if failure_kind(result) == FAILURE_KIND_UNKNOWN:
                unknown.append((cid, failure_reason(result)[:60]))
        self.assertGreaterEqual(failures, 50, "only %d failures; probe changed shape" % failures)
        self.assertEqual(unknown, [], "unclassified failures: %s" % (unknown,))


if __name__ == "__main__":
    unittest.main(verbosity=2)
