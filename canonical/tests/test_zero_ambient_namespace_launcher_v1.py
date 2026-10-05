import json, os, pathlib, pwd, socket, tempfile, textwrap, unittest
from canonical.runtime import zero_ambient_namespace_launcher_v1 as m

def nonroot_identity():
    if os.geteuid()!=0:
        return os.geteuid(), os.getegid()
    for name in ('oai','ubuntu','nobody'):
        try: ent=pwd.getpwnam(name)
        except KeyError: continue
        if ent.pw_uid>0 and ent.pw_gid>0: return ent.pw_uid, ent.pw_gid
    for ent in pwd.getpwall():
        if ent.pw_uid>=1000 and ent.pw_gid>0: return ent.pw_uid, ent.pw_gid
    raise RuntimeError('NO_NONROOT_TEST_IDENTITY')

UID,GID=nonroot_identity()

def write_input(files):
    td=tempfile.TemporaryDirectory(prefix='ns-launch-test-')
    root=pathlib.Path(td.name); os.chown(root,UID,GID); os.chmod(root,0o755)
    for name,src in files.items():
        p=root/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(textwrap.dedent(src)); os.chown(p,UID,GID); os.chmod(p,0o644)
    return td,root

def policy(root,script,*args,**limits):
    base={'pids':16,'memory_mb':128,'cpu_seconds':3,'wallclock_s':5,'scratch_mb':16,'max_file_mb':2,'nofile':32,'broker_max_bytes':65536}
    base.update(limits)
    return {'argv':['/usr/bin/python3','-I','/input/'+script,*map(str,args)],'input_dir':str(root),'host_uid':UID,'host_gid':GID,'limits':base}

class NamespaceLauncherTests(unittest.TestCase):
    def test_basic_one_channel_and_network(self):
        tcp=socket.socket(); tcp.bind(('127.0.0.1',0)); tcp.listen(1); port=tcp.getsockname()[1]
        token='outer-'+str(os.getpid()); ux=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); ux.bind('\0'+token); ux.listen(1)
        td,root=write_input({'c.py':f'''\
            import os,json,pathlib,socket
            fd=int(os.environ['PROJECT_BRAIN_BROKER_FD']); rep={{}}
            rep['hidden']=all(not pathlib.Path(x).exists() for x in ['/etc','/dev','/proc','/sys','/home'])
            try: pathlib.Path('/ROOT_WRITE').write_text('x'); rep['root_ro']=False
            except OSError: rep['root_ro']=True
            try: pathlib.Path('/usr/X').write_text('x'); rep['usr_ro']=False
            except OSError: rep['usr_ro']=True
            pathlib.Path('/work/x').write_text('ok'); rep['scratch']=True
            s=socket.socket(); s.bind(('127.0.0.1',0)); rep['inner_loopback']=True; s.close()
            s=socket.socket(); s.settimeout(.1)
            try: s.connect(('127.0.0.1',{port})); rep['outer_tcp_unreachable']=False
            except OSError: rep['outer_tcp_unreachable']=True
            u=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); u.settimeout(.1)
            try: u.connect('\\0{token}'); rep['outer_abstract_unreachable']=False
            except OSError: rep['outer_abstract_unreachable']=True
            os.write(fd,(json.dumps(rep)+'\\n').encode())
        '''})
        try:
            r=m.run_confined(policy(root,'c.py')); self.assertEqual(r['status'],'CHILD_EXITED'); self.assertEqual(r['returncode'],0)
            self.assertTrue(all(json.loads(r['broker_payload']).values()))
        finally:
            tcp.close(); ux.close(); td.cleanup()

    def test_caps_nproc_memory_enforced(self):
        td,root=write_input({'c.py':'''\
            import os,json,pathlib,subprocess
            fd=int(os.environ['PROJECT_BRAIN_BROKER_FD']); rep={}
            pathlib.Path('/work/p').mkdir()
            rep['mount_denied']=subprocess.run(['/usr/bin/mount','-t','proc','proc','/work/p']).returncode!=0
            kids=[]; failed=False
            for _ in range(40):
                try: pid=os.fork()
                except OSError: failed=True; break
                if pid==0:
                    import time; time.sleep(2); os._exit(0)
                kids.append(pid)
            for pid in kids:
                try: os.kill(pid,9)
                except OSError: pass
            for pid in kids:
                try: os.waitpid(pid,0)
                except OSError: pass
            rep['nproc']=failed and len(kids)<40
            try: bytearray(220*1024*1024); rep['memory']=False
            except (MemoryError,OSError): rep['memory']=True
            os.write(fd,(json.dumps(rep)+'\\n').encode())
        '''})
        try:
            r=m.run_confined(policy(root,'c.py')); self.assertEqual(r['returncode'],0)
            j=json.loads(r['broker_payload']); self.assertTrue(j['mount_denied']); self.assertTrue(j['nproc']); self.assertTrue(j['memory'])
        finally: td.cleanup()

    def test_undeclared_fd_closed_and_stdio_not_returned(self):
        leak_r,leak_w=os.pipe()
        td,root=write_input({'c.py':'''\
            import os,json,sys
            fd=int(os.environ['PROJECT_BRAIN_BROKER_FD']); leak=int(sys.argv[1])
            try: os.fstat(leak); leak_closed=False
            except OSError: leak_closed=True
            print('DO_NOT_RETURN_STDOUT'); os.write(2,b'DO_NOT_RETURN_STDERR\\n')
            os.write(fd,(json.dumps({'broker_only':True,'undeclared_fd_closed':leak_closed})+'\\n').encode())
        '''})
        try:
            r=m.run_confined(policy(root,'c.py',leak_r))
            self.assertEqual(json.loads(r['broker_payload']),{'broker_only':True,'undeclared_fd_closed':True})
            self.assertNotIn('stdout',r); self.assertNotIn('stderr',r)
        finally:
            os.close(leak_r); os.close(leak_w); td.cleanup()

    def test_broker_overflow_fails_closed(self):
        td,root=write_input({'c.py':'''\
            import os
            fd=int(os.environ['PROJECT_BRAIN_BROKER_FD'])
            try: os.write(fd,b'x'*10000)
            except OSError: pass
        '''})
        try:
            r=m.run_confined(policy(root,'c.py',broker_max_bytes=128))
            self.assertEqual(r['status'],'BROKER_OUTPUT_LIMIT_EXCEEDED')
        finally: td.cleanup()

    def test_root_parent_requires_nonroot_identity(self):
        td,root=write_input({'c.py':'pass\n'})
        try:
            with self.assertRaisesRegex(m.NamespaceConfinementError,'ROOT_PARENT_REQUIRES'):
                m.canonical_policy({'argv':['/usr/bin/python3','/input/c.py'],'input_dir':str(root)})
        finally: td.cleanup()

if __name__=='__main__': unittest.main(verbosity=2)
