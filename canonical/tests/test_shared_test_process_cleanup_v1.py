"""Real process lifetime probes; ordinary descendants must not outlive a test."""
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest
from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as runner


@unittest.skipUnless(os.name == 'posix', 'owned POSIX process-group checks')
class SharedTestProcessCleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory(prefix='brain_test_cleanup_')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def test_timeout_kills_ordinary_descendant_before_late_write(self):
        child="import time;from pathlib import Path;time.sleep(.6);Path('late').write_text('escaped')"
        parent=("import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',"+repr(child)+"]);"
                "print('started',flush=True);time.sleep(5)")
        result=runner._run_tests(self.root,[sys.executable,'-c',parent],.2)
        self.assertTrue(result['timed_out'])
        self.assertIsNone(result['returncode'])
        time.sleep(.7)
        self.assertFalse((self.root/'late').exists())
        self.assertIsInstance(result['stdout'],str)
        self.assertIn('started',result['stdout'])

    def test_success_also_cleans_silent_background_descendant(self):
        child="import time;from pathlib import Path;time.sleep(.5);Path('late').write_text('escaped')"
        parent=("import subprocess,sys;subprocess.Popen([sys.executable,'-c',"+repr(child)+"],"
                "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);print('done')")
        result=runner._run_tests(self.root,[sys.executable,'-c',parent],2)
        self.assertEqual(result['returncode'],0)
        self.assertFalse(result['timed_out'])
        self.assertIn('done',result['stdout'])
        time.sleep(.6)
        self.assertFalse((self.root/'late').exists())

    def test_detached_pipe_holder_cannot_make_timeout_drain_unbounded(self):
        child=("import os,time;from pathlib import Path;os.setsid();"
               "Path('escaped.pid').write_text(str(os.getpid()));time.sleep(5)")
        parent=("import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',"+repr(child)+"]);"
                "print('started',flush=True);time.sleep(5)")
        try:
            result=runner._run_tests(self.root,[sys.executable,'-c',parent],.4)
            self.assertTrue(result['timed_out'])
            self.assertTrue(result['output_incomplete'])
            self.assertEqual(result['process_cleanup_scope'],'POSIX_PROCESS_GROUP')
            self.assertIsInstance(result['stdout'],str)
            self.assertIn('started',result['stdout'])
            self.assertLess(result['elapsed_s'],4)
        finally:
            # This intentionally escaped the runner's documented boundary.
            # The fixture, not the production runner, owns its cleanup.
            pid=self.root/'escaped.pid'
            if pid.exists():
                import signal
                try: os.kill(int(pid.read_text()),signal.SIGKILL)
                except ProcessLookupError: pass

    def test_normal_failure_preserves_returncode_output_and_environment(self):
        result=runner._run_tests(self.root,[sys.executable,'-c',
            "import os,sys;print(os.environ['BRAIN_CLEANUP_CONTROL']);print('error',file=sys.stderr);sys.exit(7)"],
            2, {'BRAIN_CLEANUP_CONTROL':'visible'})
        self.assertEqual(result['returncode'],7)
        self.assertFalse(result['timed_out'])
        self.assertIn('visible',result['stdout'])
        self.assertIn('error',result['stderr'])


if __name__ == '__main__': unittest.main()
