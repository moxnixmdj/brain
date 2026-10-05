from __future__ import annotations
# PREPARED ONLY. Do not execute until structural candidate hash/size receipt exists.
import hashlib, json, pathlib, urllib.parse, urllib.request
ROOT=pathlib.Path('/tmp/h100pack')
BASE='https://raw.githubusercontent.com/vis-nlp/ChartQA/main/'
FILES=[
 ('human','ChartQA Dataset/val/val_human.json',range(10,20)),
 ('augmented','ChartQA Dataset/val/val_augmented.json',range(10,20)),
]
out=[]
imgdir=ROOT/'chartqa_holdout_images'; imgdir.mkdir(exist_ok=True)
for kind,path,indices in FILES:
    url=BASE+urllib.parse.quote(path,safe='/')
    data=json.load(urllib.request.urlopen(url))
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
         'selection':'HUMAN_10_19_PLUS_AUGMENTED_10_19','case_count':20,'cases':out}
(ROOT/'chartqa_structural_holdout.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps({'case_count':len(out),'receipt':str(ROOT/'chartqa_structural_holdout.json')},indent=2))
