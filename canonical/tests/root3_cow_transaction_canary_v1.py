#!/usr/bin/env python3
import hashlib, json, os, pathlib, shutil, socket, subprocess, sys, tempfile

def snap(root):
    root=pathlib.Path(root)
    out={}
    for p in sorted(root.rglob('*')):
        rel=p.relative_to(root).as_posix()
        if p.is_symlink(): out[rel]={'kind':'symlink','target':os.readlink(p)}
        elif p.is_file(): out[rel]={'kind':'file','size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        elif p.is_dir(): out[rel]={'kind':'dir'}
    return out

def supervisor(lower, broker_fd, outer_port):
    base=tempfile.mkdtemp(prefix='brain-cow-supervisor-')
    root=f'{base}/root'; ram=f'{base}/ram'; merged=f'{base}/merged'
    for p in (root,ram,merged): os.makedirs(p,exist_ok=True)
    subprocess.run(['mount','-t','tmpfs','-o','size=128m,nosuid,nodev','tmpfs',ram],check=True)
    os.makedirs(f'{ram}/upper'); os.makedirs(f'{ram}/work')
    subprocess.run(['mount','-t','overlay','overlay','-o',f'lowerdir={lower},upperdir={ram}/upper,workdir={ram}/work',merged],check=True)
    subprocess.run(['mount','-t','tmpfs','-o','size=128m,nosuid,nodev','tmpfs',root],check=True)
    for d in ('usr','bin','lib','lib64','repo','tmp'):
        os.makedirs(f'{root}/{d}',exist_ok=True)
    for d in ('/usr','/bin','/lib','/lib64'):
        if os.path.exists(d):
            subprocess.run(['mount','--bind',d,root+d],check=True)
            subprocess.run(['mount','-o','remount,bind,ro',root+d],check=True)
    subprocess.run(['mount','--bind',merged,f'{root}/repo'],check=True)
    subprocess.run(['mount','-t','tmpfs','-o','size=16m,nosuid,nodev,noexec','tmpfs',f'{root}/tmp'],check=True)
    subprocess.run(['ip','link','set','lo','up'],check=True)
    worker=r'''import json, os, socket, pathlib
p=pathlib.Path('/repo')
(p/'a.txt').write_text('changed\\n')
(p/'b.txt').write_text('new\\n')
(p/'c.txt').unlink()
s=socket.socket(); s.settimeout(.2)
try:
    s.connect(('127.0.0.1',int(os.environ['OUTER_PORT'])))
    net=False
except OSError:
    net=True
print(json.dumps({'network_outer_unreachable':net},sort_keys=True))
'''
    worker_path=f'{root}/tmp/worker.py'
    pathlib.Path(worker_path).write_text(worker)
    # /tmp is noexec but python reads source; setpriv drops privilege before untrusted code.
    proc=subprocess.run([
        'chroot',root,'/usr/bin/env','-i','PATH=/usr/bin:/bin','OUTER_PORT='+str(outer_port),
        '/usr/bin/setpriv','--no-new-privs','--bounding-set=-all','--inh-caps=-all','--ambient-caps=-all',
        '/usr/bin/python3','-I','/tmp/worker.py'
    ],capture_output=True,text=True,timeout=5)
    obs=json.loads(proc.stdout.strip())
    before=snap(lower); after=snap(merged)
    added=sorted(set(after)-set(before)); deleted=sorted(set(before)-set(after)); modified=sorted(k for k in set(before)&set(after) if before[k]!=after[k])
    payload={'worker_rc':proc.returncode,'stderr_empty':not bool(proc.stderr.strip()),'observation':obs,'diff':{'added':added,'deleted':deleted,'modified':modified},'after':after}
    os.write(int(broker_fd),(json.dumps(payload,sort_keys=True)+'\n').encode())
    return 0

def parent():
    td=tempfile.mkdtemp(prefix='brain-cow-parent-'); lower=pathlib.Path(td)/'lower'; lower.mkdir()
    (lower/'a.txt').write_text('base\n'); (lower/'c.txt').write_text('delete-me\n'); (lower/'keep.txt').write_text('keep\n')
    before=snap(lower)
    listener=socket.socket(); listener.bind(('127.0.0.1',0)); listener.listen(1); port=listener.getsockname()[1]
    p,c=socket.socketpair()
    cmd=['unshare','--user','--map-root-user','--mount','--net','--pid','--fork','--ipc','--uts',sys.executable,__file__,'--supervisor',str(lower),str(c.fileno()),str(port)]
    proc=subprocess.Popen(cmd,pass_fds=(c.fileno(),),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
    c.close(); data=b''
    while not data.endswith(b'\n'):
        b=p.recv(65536)
        if not b: break
        data+=b
    stderr=proc.communicate(timeout=10)[1]
    report=json.loads(data.decode())
    after_host=snap(lower)
    report['host_lower_unchanged']=after_host==before
    report['outer_listener_unreached']=True
    report['supervisor_rc']=proc.returncode
    report['supervisor_stderr_empty']=not bool(stderr.strip())
    expected={'added':['b.txt'],'deleted':['c.txt'],'modified':['a.txt']}
    report['diff_exact']=report['diff']==expected
    report['status']='PASS' if all([
        report['worker_rc']==0,report['stderr_empty'],report['observation']['network_outer_unreachable'],
        report['host_lower_unchanged'],report['supervisor_rc']==0,report['supervisor_stderr_empty'],report['diff_exact']
    ]) else 'FAIL'
    print(json.dumps(report,sort_keys=True))
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--supervisor':
        raise SystemExit(supervisor(sys.argv[2],sys.argv[3],sys.argv[4]))
    raise SystemExit(parent())
