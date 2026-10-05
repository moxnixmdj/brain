from __future__ import annotations
# PREPARED ONLY. Do not execute until structural candidate hash/size receipt exists.
import hashlib, json, pathlib, urllib.parse, urllib.request
ROOT=pathlib.Path('/tmp/h100pack')
CHARTQA_COMMIT='044eabfc306abfe9340c5741f0093aefc5973d06'
BASE=f'https://raw.githubusercontent.com/vis-nlp/ChartQA/{CHARTQA_COMMIT}/'
DEV_IMAGES={'3887.png','4576.png','5734.png','11756.png','13153.png','multi_col_20933.png','multi_col_972.png','multi_col_60377.png','multi_col_60563.png','multi_col_101153.png','multi_col_80582.png'}
FILES=[
 ('human','ChartQA Dataset/val/val_human.json','983dacfcb6aabc8598031c07eeba7747f9884c4a'),
 ('augmented','ChartQA Dataset/val/val_augmented.json','131068b504407d9cdd8413fe5c574772bb241613'),
]
def git_blob_sha(blob:bytes)->str:
    return hashlib.sha1(b'blob '+str(len(blob)).encode()+bytes([0])+blob).hexdigest()
out=[]
imgdir=ROOT/'chartqa_holdout_images'; imgdir.mkdir(exist_ok=True)
for kind,path,expected_blob_sha in FILES:
    url=BASE+urllib.parse.quote(path,safe='/')
    raw=urllib.request.urlopen(url).read()
    observed_blob_sha=git_blob_sha(raw)
    if observed_blob_sha!=expected_blob_sha:
        raise RuntimeError(f'ANNOTATION_BLOB_SHA_MISMATCH:{kind}:{observed_blob_sha}!={expected_blob_sha}')
    data=json.loads(raw.decode('utf-8'))
    indices=[]
    for i in range(10,len(data)):
        if data[i]['imgname'] in DEV_IMAGES:
            continue
        indices.append(i)
        if len(indices)==10:
            break
    if len(indices)!=10:
        raise RuntimeError(f'INSUFFICIENT_NONOVERLAP_CASES:{kind}:{len(indices)}')
    for i in indices:
        row=data[i]
        img=row['imgname']
        case={'id':('H2_' if kind=='human' else 'A2_')+f'{i:02d}',
              'kind':kind,'annotation_index':i,'imgname':img,'query':row['query'],'label':row['label']}
        imgurl=BASE+urllib.parse.quote('ChartQA Dataset/val/png/'+img,safe='/')
        blob=urllib.request.urlopen(imgurl).read()
        (imgdir/img).write_bytes(blob)
        case['image_sha256']=hashlib.sha256(blob).hexdigest()
        case['image_bytes']=len(blob)
        out.append(case)
receipt={'schema':'PROJECT_BRAIN_H100_UNICHART_STRUCTURAL_HOLDOUT_MATERIALIZATION_V1',
         'chartqa_commit':CHARTQA_COMMIT,
         'selection':'FIRST_10_POST_INDEX9_NONDEV_IMAGES_PER_SPLIT','case_count':20,
         'annotation_blob_sha_verified':True,'cases':out}
(ROOT/'chartqa_structural_holdout.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps({'case_count':len(out),'receipt':str(ROOT/'chartqa_structural_holdout.json')},indent=2))
