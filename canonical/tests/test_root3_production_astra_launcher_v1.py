from types import SimpleNamespace
from unittest import mock

from canonical.runtime import root3_production_astra_launcher_v1 as launcher


def test_installs_root3_before_importing_astra():
    order = []

    def fake_install(authorizer, *, authority_id):
        order.append(("install", authorizer, authority_id))
        return {"run_guard_active": True, "popen_guard_active": True}

    fake_astra = SimpleNamespace(__file__="/tmp/astra_runtime.py", main=lambda: 0)

    with (
        mock.patch.object(launcher.bootstrap, "install_current", side_effect=fake_install),
        mock.patch.object(
            launcher.bootstrap.mediator,
            "status",
            return_value={"run_guard_active": True, "popen_guard_active": True},
        ),
        mock.patch.object(
            launcher.importlib,
            "import_module",
            side_effect=lambda name: order.append(("import", name)) or fake_astra,
        ),
    ):
        got = launcher.load_astra_after_root3_install()

    assert got is fake_astra
    assert order[0][0] == "install"
    assert order[0][1] is launcher.attempt_authorizer.authorize
    assert order[0][2] == launcher.attempt_authorizer.AUTHORITY_ID
    assert order[1] == ("import", launcher.ASTRA_MODULE)


def test_fail_closed_if_install_does_not_activate_both_guards():
    with mock.patch.object(
        launcher.bootstrap,
        "install_current",
        return_value={"run_guard_active": True, "popen_guard_active": False},
    ):
        try:
            launcher.install_root3_before_astra_import()
        except launcher.ProductionBootstrapError as exc:
            assert "POPEN_GUARD_NOT_ACTIVE" in str(exc)
        else:
            raise AssertionError("missing fail-closed bootstrap rejection")


def test_fail_closed_if_astra_import_replaces_guard():
    fake_astra = SimpleNamespace(__file__="/tmp/astra_runtime.py", main=lambda: 0)
    with (
        mock.patch.object(
            launcher.bootstrap,
            "install_current",
            return_value={"run_guard_active": True, "popen_guard_active": True},
        ),
        mock.patch.object(
            launcher.importlib,
            "import_module",
            return_value=fake_astra,
        ),
        mock.patch.object(
            launcher.bootstrap.mediator,
            "status",
            return_value={"run_guard_active": False, "popen_guard_active": True},
        ),
    ):
        try:
            launcher.load_astra_after_root3_install()
        except launcher.ProductionBootstrapError as exc:
            assert "RUN_GUARD_LOST_AFTER_ASTRA_IMPORT" in str(exc)
        else:
            raise AssertionError("guard replacement must fail closed")


def test_main_preserves_sys_argv_and_runs_bound_mission():
    seen = {}
    fake_astra = SimpleNamespace(__file__="/repo/canonical/runtime/astra_runtime.py")

    def fake_main():
        seen["argv"] = list(launcher.sys.argv)
        return 7

    fake_astra.main = fake_main
    old = list(launcher.sys.argv)
    with mock.patch.object(launcher, "load_astra_after_root3_install", return_value=fake_astra):
        assert launcher.main(["canonical/astra_runtime/missions/x.json"]) == 7
    assert seen["argv"] == [
        "/repo/canonical/runtime/astra_runtime.py",
        "canonical/astra_runtime/missions/x.json",
    ]
    assert launcher.sys.argv == old
