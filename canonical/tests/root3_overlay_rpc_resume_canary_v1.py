#!/usr/bin/env python3
import hashlib,json,os,pathlib,subprocess,sys,tempfile

def worker(repo):
    repo=pathlib.Path(repo); bridge=repo/'bridge'; bridge.mkdir(parents=True,exist_ok=True)
    payload={'kind':'http_get','payload':{'url':'https://example.invalid/data','max_bytes':32}}
    canon=json.dumps(payload,sort_keys=True,separators=(',',':')).encode()
    rid=hashlib.sha256(canon).hexdigest()
    req=bridge/(rid+'.request.json'); resp=bridge/(rid+'.response.json')
    if not req.exists():
        req.write_text(json.dumps({**payload,'request_sha256':rid},sort_keys=True))
    if not resp.exists():
        print(json.dumps({'status':'REQUEST_PENDING','request_sha256':rid}))
        return 7
    obj=json.loads(resp.read_text())
    if obj.get('request_sha256')!=rid or obj.get('status')!='ok':
        return 8
    print(json.dumps({
        'status':'COMPLETE',
        'request_sha256':rid,
        'result':obj['result'],
    },sort_keys=True))
    return 0

def supervisor(lower):
    td=tempfile.mkdtemp(prefix='brain-rpc-')
    ram=td+'/ram'; merged=td+'/merged'
    os.mkdir(ram); os.mkdir(merged)
    subprocess.run(['mount','-t','tmpfs','-o','size=32m,nosuid,nodev','tmpfs',ram],check=True)
    os.mkdir(ram+'/upper'); os.mkdir(ram+'/work')
    subprocess.run([
        'mount','-t','overlay','overlay','-o',
        f'lowerdir={lower},upperdir={ram}/upper,workdir={ram}/work',
        merged,
    ],check=True)
    first=subprocess.run([sys.executable,__file__,'--worker',merged],capture_output=True,text=True)
    a=json.loads(first.stdout)
    assert first.returncode==7 and a['status']=='REQUEST_PENDING'
    rid=a['request_sha256']
    req=json.loads((pathlib.Path(merged)/'bridge'/(rid+'.request.json')).read_text())
    assert req['request_sha256']==rid
    response={
        'request_sha256':rid,
        'status':'ok',
        'result':{
            'body':'trusted-parent-result',
            'body_sha256':hashlib.sha256(b'trusted-parent-result').hexdigest(),
        },
    }
    (pathlib.Path(merged)/'bridge'/(rid+'.response.json')).write_text(
        json.dumps(response,sort_keys=True)
    )
    second=subprocess.run([sys.executable,__file__,'--worker',merged],capture_output=True,text=True)
    b=json.loads(second.stdout)
    out={
        'first_rc':first.returncode,
        'second_rc':second.returncode,
        'pending':a['status']=='REQUEST_PENDING',
        'resumed_complete':b['status']=='COMPLETE',
        'same_request':b['request_sha256']==rid,
        'result_bound':b['result']['body_sha256']==response['result']['body_sha256'],
        'host_lower_unchanged':not (pathlib.Path(lower)/'bridge').exists(),
    }
    out['status']='PASS' if all(out[k] for k in [
        'pending','resumed_complete','same_request','result_bound','host_lower_unchanged'
    ]) and second.returncode==0 else 'FAIL'
    print(json.dumps(out,sort_keys=True))
    return 0 if out['status']=='PASS' else 1

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--worker':
        raise SystemExit(worker(sys.argv[2]))
    td=tempfile.mkdtemp(prefix='brain-rpc-lower-')
    lower=pathlib.Path(td); (lower/'seed').write_text('x')
    raise SystemExit(supervisor(str(lower)))
