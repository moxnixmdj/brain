"""The browser surface must resolve its CDP driver however it is loaded.

``browser_v1.bind()`` used to do a bare ``import osworld_v21_browser_cdp_v1``.
That resolves only when ``canonical/runtime`` happens to already be on
``sys.path`` -- which is true today purely because ``autonomous_v1`` and
``regression_sweep_v1`` put it there as a side effect of their own imports.
Nothing guarantees it. The runtime's own loader,
``goal_compiler._load_sibling_runtime_module``, loads modules by file path and
does not add their directory to ``sys.path``, so under that loader the bare
import raised ``ModuleNotFoundError`` and every entry point that drives a
browser -- ``bind``, and therefore ``state`` and ``act`` -- failed even with a
live Chromium on the port.

These tests need no browser. They assert resolution, which is the part that was
broken; launching Chromium is covered by the regression sweep, which skips when
no browser is present.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

RUNTIME = pathlib.Path(__file__).resolve().parents[1] / "runtime"


def _load_by_path(name):
    """Load a runtime module the way the runtime does: by file path."""
    spec = importlib.util.spec_from_file_location(name, RUNTIME / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class TestBrowserDriverResolution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browser = _load_by_path("browser_v1")

    def test_the_driver_resolves_without_the_runtime_directory_on_the_path(self):
        """The regression: a bare sibling import needs the directory on sys.path."""
        saved = list(sys.path)
        sys.path[:] = [p for p in sys.path if not p.endswith("canonical/runtime")]
        sys.modules.pop("osworld_v21_browser_cdp_v1", None)
        try:
            # This is what the old code did, and it is what fails.
            with self.assertRaises(ImportError):
                import osworld_v21_browser_cdp_v1  # noqa: F401
            driver = self.browser._load_cdp_driver()
        finally:
            sys.path[:] = saved
        self.assertTrue(hasattr(driver, "BrowserCDP"))

    def test_the_driver_is_the_real_module_not_a_stub(self):
        driver = self.browser._load_cdp_driver()
        self.assertEqual(driver.__name__, "osworld_v21_browser_cdp_v1")
        self.assertEqual(driver.SCHEMA, "PROJECT_BRAIN_OSWORLD_V21_BROWSER_CDP_V1")

    def test_resolution_is_idempotent(self):
        first = self.browser._load_cdp_driver()
        second = self.browser._load_cdp_driver()
        self.assertIs(first, second)


if __name__ == "__main__":
    unittest.main()
