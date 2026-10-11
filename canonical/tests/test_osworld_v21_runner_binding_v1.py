from types import SimpleNamespace

from canonical.runtime.osworld_v21_runner_binding_v1 import install


class Agent:
    def __init__(self):
        self.bound = None
    def bind_environment(self, env):
        self.bound = env
    def set_result_dir(self, path):
        self.result_dir = path


def test_install_binds_before_exact_delegate():
    calls = []
    def original(agent, env, value):
        calls.append((agent.bound is env, value))
        return "ok"

    module = SimpleNamespace(run_single_example=original)
    receipt = install(module)
    env = object()
    agent = Agent()
    out = module.run_single_example(agent, env, 7)
    assert out == "ok"
    assert calls == [(True, 7)]
    assert receipt["evaluator_changed"] is False
    assert receipt["scoring_changed"] is False


def test_install_is_idempotent():
    module = SimpleNamespace(run_single_example=lambda agent, env: None)
    first = install(module)
    wrapped = module.run_single_example
    second = install(module)
    assert first["status"] == "INSTALLED"
    assert second["status"] == "ALREADY_INSTALLED"
    assert module.run_single_example is wrapped


def test_install_binds_native_result_dir_before_delegate():
    seen = []
    def original(agent, env, example, max_steps, instruction, args, result_dir, scores):
        seen.append((agent.bound is env, agent.result_dir, result_dir))
        return "ok"

    module = SimpleNamespace(run_single_example=original)
    install(module)
    env = object()
    agent = Agent()
    out = module.run_single_example(
        agent, env, {}, 500, "task", SimpleNamespace(), "/tmp/result", []
    )
    assert out == "ok"
    assert seen == [(True, "/tmp/result", "/tmp/result")]
