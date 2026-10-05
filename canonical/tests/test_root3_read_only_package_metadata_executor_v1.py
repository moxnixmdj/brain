from __future__ import annotations
import pathlib, subprocess, unittest
from canonical.runtime import root3_read_only_package_metadata_executor_v1 as pkg

class PackageMetadataExecutorTests(unittest.TestCase):
    def ctx(self,key,argv,api="subprocess.run",**kwargs):
        defaults={"text":True,"capture_output":True,"timeout":30}
        defaults.update(kwargs)
        return {
            "effect_class":"READ_ONLY_DECLARED_QUERY",
            "callsite":{"module_path":key[0],"lineno":key[1],"process_api":api},
            "args":(argv,),
            "kwargs":defaults,
        }

    def ex(self):
        return pkg.make_executor(popen_impl=subprocess.Popen)

    def bash_version(self):
        p=subprocess.run(["dpkg-query","-W","-f=${Version}","bash"],text=True,capture_output=True,check=True)
        return p.stdout.strip()

    def small_contents(self):
        rows=[]
        for p in pkg.current_contents_index_files():
            try: rows.append((pathlib.Path(p).stat().st_size,p))
            except OSError: pass
        if not rows: self.skipTest("no apt Contents index")
        return min(rows)[1]

    def test_supported_is_exactly_ten_sites(self):
        expected={
          ("canonical/runtime/astra_runtime.py",918,"subprocess.run"),
          ("canonical/runtime/astra_runtime.py",940,"subprocess.run"),
          ("canonical/runtime/capability_discovery.py",267,"subprocess.run"),
          ("canonical/runtime/capability_discovery.py",359,"subprocess.run"),
          ("canonical/runtime/capability_discovery.py",368,"subprocess.run"),
          ("canonical/runtime/capability_discovery.py",428,"subprocess.run"),
          ("canonical/runtime/capability_discovery.py",446,"subprocess.run"),
          ("canonical/runtime/capability_discovery.py",468,"subprocess.run"),
          ("canonical/runtime/capability_discovery.py",581,"subprocess.run"),
          ("canonical/runtime/capability_discovery.py",605,"subprocess.Popen"),
        }
        self.assertEqual(set(pkg.SUPPORTED),expected)

    def test_astra_apt_show_real_confined(self):
        v=self.bash_version()
        key=("canonical/runtime/astra_runtime.py",918,"subprocess.run")
        p=self.ex()(self.ctx(key,["apt-cache","show","bash="+v]))
        self.assertEqual(p.returncode,0)
        self.assertIn("Package: bash",p.stdout)

    def test_astra_dpkg_query_real_confined(self):
        key=("canonical/runtime/astra_runtime.py",940,"subprocess.run")
        p=self.ex()(self.ctx(key,["dpkg-query","-W","-f=${Version}","bash"]))
        self.assertEqual(p.returncode,0)
        self.assertEqual(p.stdout.strip(),self.bash_version())

    def test_discovery_apt_search_real_confined(self):
        key=("canonical/runtime/capability_discovery.py",267,"subprocess.run")
        p=self.ex()(self.ctx(key,["apt-cache","search","bash"],timeout=20))
        self.assertEqual(p.returncode,0)
        self.assertIn("bash",p.stdout.lower())

    def test_discovery_apt_policy_real_confined(self):
        key=("canonical/runtime/capability_discovery.py",359,"subprocess.run")
        p=self.ex()(self.ctx(key,["apt-cache","policy","bash"],timeout=10))
        self.assertEqual(p.returncode,0)
        self.assertIn("Candidate:",p.stdout)

    def test_discovery_apt_show_real_confined(self):
        v=self.bash_version()
        key=("canonical/runtime/capability_discovery.py",368,"subprocess.run")
        p=self.ex()(self.ctx(key,["apt-cache","show","bash="+v],timeout=15))
        self.assertEqual(p.returncode,0)
        self.assertIn("SHA256:",p.stdout)

    def test_index_targets_files_real_confined(self):
        key=("canonical/runtime/capability_discovery.py",428,"subprocess.run")
        p=self.ex()(self.ctx(key,["apt-get","indextargets","--format","$(FILENAME)"],timeout=20))
        self.assertEqual(p.returncode,0)
        self.assertIn("/var/lib/apt/lists/",p.stdout)

    def test_apt_helper_cat_real_confined(self):
        path=self.small_contents()
        key=("canonical/runtime/capability_discovery.py",446,"subprocess.run")
        p=self.ex()(self.ctx(key,["/usr/lib/apt/apt-helper","cat-file",path],timeout=30))
        self.assertEqual(p.returncode,0)
        self.assertGreater(len(p.stdout),100)

    def test_dumpavail_real_confined(self):
        key=("canonical/runtime/capability_discovery.py",468,"subprocess.run")
        p=self.ex()(self.ctx(key,["apt-cache","dumpavail"],timeout=35))
        self.assertEqual(p.returncode,0)
        self.assertGreater(len(p.stdout),1_000_000)
        self.assertIn("Package:",p.stdout[:1000])

    def test_contents_indextargets_real_confined(self):
        key=("canonical/runtime/capability_discovery.py",581,"subprocess.run")
        p=self.ex()(self.ctx(key,["apt-get","indextargets","--format","$(IDENTIFIER)\t$(FILENAME)"],timeout=20))
        self.assertEqual(p.returncode,0)
        self.assertIn("Contents",p.stdout)

    def test_popen_cat_file_stream_real_confined(self):
        path=self.small_contents()
        key=("canonical/runtime/capability_discovery.py",605,"subprocess.Popen")
        p=self.ex()(self.ctx(key,["/usr/lib/apt/apt-helper","cat-file",path],api="subprocess.Popen",
                      capture_output=False,timeout=None,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,errors="replace"))
        count=0
        for line in p.stdout or []:
            count += 1
        if p.stdout: p.stdout.close()
        self.assertGreater(count,0)
        self.assertEqual(p.wait(timeout=10),0)

    def test_apt_search_option_injection_denied_before_spawn(self):
        key=("canonical/runtime/capability_discovery.py",267,"subprocess.run")
        calls=[]
        ex=pkg.make_executor(popen_impl=lambda *a,**k: calls.append((a,k)))
        with self.assertRaisesRegex(pkg.PackageMetadataDenied,"QUERY_INVALID"):
            ex(self.ctx(key,["apt-cache","search","--names-only"]))
        self.assertEqual(calls,[])

    def test_cat_file_outside_metadata_roots_denied_before_spawn(self):
        key=("canonical/runtime/capability_discovery.py",446,"subprocess.run")
        calls=[]
        ex=pkg.make_executor(popen_impl=lambda *a,**k: calls.append((a,k)))
        with self.assertRaisesRegex(pkg.PackageMetadataDenied,"OUTSIDE_ALLOWLIST"):
            ex(self.ctx(key,["/usr/lib/apt/apt-helper","cat-file","/etc/passwd"]))
        self.assertEqual(calls,[])

if __name__=="__main__":
    unittest.main(verbosity=2)
