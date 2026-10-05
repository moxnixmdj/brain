#!/usr/bin/env python3
import json,os,pathlib,socket,subprocess,sys,tempfile

def grandchild(port):
    out={}
    out['host_etc_hidden']=not pathlib.Path('/etc/passwd').exists()
    try:
        pathlib.Path('/input/data').write_text('evil')
        out['input_readonly']=False
    except OSError:
        out['input_readonly']=True
    s=socket.socket(); s.settimeout(.2)
    try:
        s.connect(('127.0.0.1',int(port)))
        out['outer_tcp_unreachable']=False
    except OSError:
        out['outer_tcp_unreachable']=True
    s.close()
    pathlib.Path('/tmp/grandchild').write_text('ok')
    out['private_scratch']=pathlib.Path('/tmp/grandchild').read_text()=='ok'
    print(json.dumps(out,sort_keys=True))
    return 0

def child(port):
    p=subprocess.run(
        [sys.executable,__file__,'--grandchild',port],
        capture_output=True,text=True,
    )
    g=json.loads(p.stdout)
    print(json.dumps({'grandchild_rc':p.returncode,'grandchild':g},sort_keys=True))
    return 0

def parent():
    listener=socket.socket()
    listener.bind(('127.0.0.1',0))
    listener.listen(1)
    port=listener.getsockname()[1]
    td=tempfile.mkdtemp(prefix='tree-')
    root=td+'/root'
    os.mkdir(root)
    inp=tempfile.NamedTemporaryFile(delete=False)
    inp.write(b'bound'); inp.close()
    setup='''set -euo pipefail
ROOT="$1"; INPUT="$2"; SCRIPT="$3"; PORT="$4"
mount --make-rprivate /
mount -t tmpfs -o size=96m,nosuid,nodev tmpfs "$ROOT"
mkdir -p "$ROOT"/{usr,bin,lib,lib64,tmp,input,work}
for d in /usr /bin /lib /lib64; do
  [ -e "$d" ] || continue
  mount --bind "$d" "$ROOT$d"
  mount -o remount,bind,ro "$ROOT$d"
done
mount -t tmpfs -o size=16m,nosuid,nodev,noexec tmpfs "$ROOT/tmp"
: > "$ROOT/input/data"
mount --bind "$INPUT" "$ROOT/input/data"
mount -o remount,bind,ro "$ROOT/input/data"
: > "$ROOT/work/canary.py"
mount --bind "$SCRIPT" "$ROOT/work/canary.py"
mount -o remount,bind,ro "$ROOT/work/canary.py"
ip link set lo up
exec chroot "$ROOT" /usr/bin/env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1  /usr/bin/setpriv --no-new-privs --bounding-set=-all --inh-caps=-all --ambient-caps=-all  /usr/bin/python3 -I /work/canary.py --child "$PORT"
'''
    proc=subprocess.run([
        'unshare','--user','--map-root-user','--mount','--net','--pid','--fork',
        '--ipc','--uts','bash','-c',setup,'_',root,inp.name,__file__,str(port)
    ],capture_output=True,text=True,timeout=10)
    c=json.loads(proc.stdout)
    g=c['grandchild']
    out={
        'child_rc':proc.returncode,
        'grandchild_rc':c['grandchild_rc'],
        **g,
        'stderr_empty':not bool(proc.stderr.strip()),
    }
    out['status']='PASS' if all([
        out['child_rc']==0,
        out['grandchild_rc']==0,
        out['host_etc_hidden'],
        out['input_readonly'],
        out['outer_tcp_unreachable'],
        out['private_scratch'],
    ]) else 'FAIL'
    print(json.dumps(out,sort_keys=True))
    return 0 if out['status']=='PASS' else 1

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--grandchild':
        raise SystemExit(grandchild(sys.argv[2]))
    if len(sys.argv)>1 and sys.argv[1]=='--child':
        raise SystemExit(child(sys.argv[2]))
    raise SystemExit(parent())
