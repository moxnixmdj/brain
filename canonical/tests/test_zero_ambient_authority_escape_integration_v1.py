import pathlib
import subprocess
import tempfile
import unittest

from canonical.runtime.zero_ambient_authority_launcher_v1 import docker_argv

ALPINE = "alpine@sha256:5291449c3df73caf6ed85e649dec1b9e818b39a5d8c871e97afc13e9cd5e8fa8"


def parse_lines(text):
    out = {}
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


class EscapeIntegrationTests(unittest.TestCase):
    def test_zero_ambient_authority_negative_canaries(self):
        with tempfile.TemporaryDirectory() as td:
            pathlib.Path(td, "marker").write_text("input", encoding="utf-8")
            script = r"""
set +e
touch /root_escape_probe >/dev/null 2>&1
echo root_write_blocked=$([ $? -ne 0 ] && echo 1 || echo 0)
echo mutated >/input/probe_mutation 2>/dev/null
echo input_write_blocked=$([ $? -ne 0 ] && echo 1 || echo 0)
wget -T 3 -qO- https://example.com >/dev/null 2>&1
echo network_blocked=$([ $? -ne 0 ] && echo 1 || echo 0)
echo uid=$(id -u)
echo capeff=$(awk '/CapEff:/ {print $2}' /proc/self/status)
test ! -e /dev/sda
echo host_block_device_absent=$([ $? -eq 0 ] && echo 1 || echo 0)
echo pid_namespace_private=$([ $$ -eq 1 ] && echo 1 || echo 0)
if [ -r /sys/fs/cgroup/pids.max ]; then echo pids_max=$(cat /sys/fs/cgroup/pids.max); fi
if [ -r /sys/fs/cgroup/memory.max ]; then echo memory_max=$(cat /sys/fs/cgroup/memory.max); fi
env | grep -Eiq '(TOKEN|SECRET|PASSWORD|CREDENTIAL|API_KEY|PRIVATE_KEY)='
echo secret_like_env_absent=$([ $? -ne 0 ] && echo 1 || echo 0)
"""
            policy = {
                "image": ALPINE,
                "argv": ["/bin/sh", "-c", script],
                "input_dir": td,
                "env": {"LANG": "C", "PYTHONDONTWRITEBYTECODE": "1"},
                "limits": {
                    "pids": 32,
                    "memory_mb": 512,
                    "cpus": 1,
                    "wallclock_s": 20,
                    "scratch_mb": 64,
                },
            }
            proc = subprocess.run(
                docker_argv(policy), text=True, capture_output=True, timeout=40
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            got = parse_lines(proc.stdout)
            self.assertEqual(got.get("root_write_blocked"), "1", got)
            self.assertEqual(got.get("input_write_blocked"), "1", got)
            self.assertEqual(got.get("network_blocked"), "1", got)
            self.assertEqual(got.get("uid"), "65534", got)
            self.assertEqual(got.get("capeff"), "0000000000000000", got)
            self.assertEqual(got.get("host_block_device_absent"), "1", got)
            self.assertEqual(got.get("pid_namespace_private"), "1", got)
            self.assertEqual(got.get("secret_like_env_absent"), "1", got)
            if "pids_max" in got:
                self.assertEqual(got["pids_max"], "32", got)
            if "memory_max" in got:
                self.assertEqual(got["memory_max"], str(512 * 1024 * 1024), got)
            self.assertFalse(pathlib.Path(td, "probe_mutation").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
