from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import reached_escape_live_no_bypass_guard_v1 as g

ROOT = Path(__file__).resolve().parents[2]


def _write(root: Path, rel: str, text: str = "") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _clean_fixture(root: Path) -> None:
    _write(root, "canonical/runtime/reached_escape_state_kernel_v1.py")
    _write(
        root,
        "canonical/runtime/reached_escape_finite_totality_certificate_v1.py",
        "from canonical.runtime import reached_escape_state_kernel_v1 as kernel\n",
    )
    _write(
        root,
        "canonical/runtime/certified_reached_escape_state_constructor_v1.py",
        "from canonical.runtime import reached_escape_finite_totality_certificate_v1 as finite_totality\n"
        "from canonical.runtime import reached_escape_state_kernel_v1 as kernel\n",
    )
    _write(
        root,
        "canonical/runtime/live_brain_runtime_v1.py",
        'SURFACES=("CERTIFIED_REACHED_ESCAPE_STATE_CONSTRUCTOR_V1",)\n'
        "def f(payload):\n"
        "    from canonical.runtime.certified_reached_escape_state_constructor_v1 import construct\n"
        "    return construct(payload)\n",
    )
    _write(
        root,
        "canonical/runtime/unified_cognitive_fabric_v1.py",
        'DIRECT={"REACHED_ESCAPE_STATE": "certified_reached_escape_state_constructor_v1.construct + reached_escape_repair_cycle_v1.run"}\n'
        "from canonical.runtime import reached_escape_repair_cycle_v1 as reached_escape_repair\n"
        "def f(payload):\n"
        "    from canonical.runtime import certified_reached_escape_state_constructor_v1 as reached_escape_state\n"
        "    if payload.get('repair'):\n"
        "        out = reached_escape_repair.run(payload, provider=lambda _: None, verifier=lambda _: None)\n"
        "    else:\n"
        "        out = reached_escape_state.construct(payload)\n"
        "    return out\n",
    )


class ReachedEscapeNoBypassGuardTests(unittest.TestCase):
    def test_current_repository_static_runtime_census_passes(self):
        out = g.scan_repo(ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__STATIC_PYTHON_RUNTIME_NO_LOW_LEVEL_REACHED_ESCAPE_BYPASS",
        )
        self.assertGreaterEqual(out["runtime_python_file_count"], 1)
        self.assertEqual(len(out["live_entrypoints"]), 2)
        self.assertFalse(out["global_dynamic_no_bypass_proved"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_clean_synthetic_runtime_passes(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _clean_fixture(root)
            out = g.scan_repo(root)
            self.assertTrue(out["pass"], out)

    def test_third_runtime_raw_kernel_reference_fails_closed(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _clean_fixture(root)
            _write(
                root,
                "canonical/runtime/rogue_consumer.py",
                "from canonical.runtime.reached_escape_state_kernel_v1 import evaluate\n",
            )
            out = g.scan_repo(root)
            self.assertFalse(out["pass"])
            self.assertTrue(
                any(
                    row["code"] == "UNTRUSTED_LOW_LEVEL_REACHED_ESCAPE_REFERENCE"
                    and row["path"] == "canonical/runtime/rogue_consumer.py"
                    for row in out["errors"]
                )
            )

    def test_live_surface_cannot_import_constructor_and_still_reference_raw_kernel(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _clean_fixture(root)
            live = root / "canonical/runtime/live_brain_runtime_v1.py"
            live.write_text(
                live.read_text(encoding="utf-8")
                + "from canonical.runtime.reached_escape_state_kernel_v1 import evaluate\n",
                encoding="utf-8",
            )
            out = g.scan_repo(root)
            self.assertFalse(out["pass"])
            self.assertTrue(
                any(
                    row["code"] == "LIVE_ENTRYPOINT_LOW_LEVEL_BYPASS_PRESENT"
                    for row in out["errors"]
                )
            )

    def test_missing_live_constructor_call_shape_fails_closed(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _clean_fixture(root)
            live = root / "canonical/runtime/live_brain_runtime_v1.py"
            live.write_text(
                'SURFACES=("CERTIFIED_REACHED_ESCAPE_STATE_CONSTRUCTOR_V1",)\n'
                "def f(payload):\n"
                "    from canonical.runtime.certified_reached_escape_state_constructor_v1 import construct\n"
                "    return {'pass': True}\n",
                encoding="utf-8",
            )
            out = g.scan_repo(root)
            self.assertFalse(out["pass"])
            self.assertTrue(
                any(
                    row["code"] == "LIVE_ENTRYPOINT_CONSTRUCTOR_BINDING_INCOMPLETE"
                    for row in out["errors"]
                )
            )

    def test_missing_required_runtime_sentinel_fails_closed(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _clean_fixture(root)
            (root / "canonical/runtime/reached_escape_state_kernel_v1.py").unlink()
            out = g.scan_repo(root)
            self.assertFalse(out["pass"])
            self.assertTrue(
                any(row["code"] == "REQUIRED_SENTINEL_MISSING" for row in out["errors"])
            )


if __name__ == "__main__":
    unittest.main()
