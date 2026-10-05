from __future__ import annotations
import hashlib, json, pathlib, urllib.parse, urllib.request
from canonical.runtime.h100_unichart_chartqa_preservation_runner_v1 import (
    make_model_and_processor, load_fp32_donor, answer_case, relaxed_correct
)

ROOT=pathlib.Path('/tmp/h100pack')
CHARTQA_COMMIT='044eabfc306abfe9340c5741f0093aefc5973d06'
BASE=f'https://raw.githubusercontent.com/vis-nlp/ChartQA/{CHARTQA_COMMIT}/'
FILES=[
 ('human','ChartQA Dataset/val/val_human.json','983dacfcb6aabc8598031c07eeba7747f9884c4a','DQH'),
 ('augmented','ChartQA Dataset/val/val_augmented.json','131068b504407d9cdd8413fe5c574772bb241613','DQA'),
]
DEV_IMAGES={'3887.png','4576.png','5734.png','11756.png','13153.png',
'multi_col_20933.png','multi_col_972.png','multi_col_60377.png','multi_col_60563.png','multi_col_101153.png','multi_col_80582.png'}
SOURCE=ROOT/'chartqa_pytorch_model.bin'
IMAGE_DIR=ROOT/'chartqa_donorqual_images'; IMAGE_DIR.mkdir(exist_ok=True)
START_INDEX=20
TARGET_PER_SPLIT=10

def git_blob_sha(blob:bytes)->str:
    return hashlib.sha1(b'blob '+str(len(blob)).encode()+bytes([0])+blob).hexdigest()

def sha256(blob:bytes)->str:
    return hashlib.sha256(blob).hexdigest()

model,processor=make_model_and_processor()
load=load_fp32_donor(model,SOURCE)
selected=[]; scan_trace=[]; split_summaries={}
for kind,path,expected_blob,prefix in FILES:
    raw=urllib.request.urlopen(BASE+urllib.parse.quote(path,safe='/')).read()
    observed=git_blob_sha(raw)
    if observed!=expected_blob:
        raise RuntimeError(f'ANNOTATION_BLOB_SHA_MISMATCH:{kind}:{observed}!={expected_blob}')
    data=json.loads(raw.decode('utf-8'))
    got=0; scanned=0
    for i in range(START_INDEX,len(data)):
        row=data[i]; img=row['imgname']
        if img in DEV_IMAGES:
            scan_trace.append({'split':kind,'annotation_index':i,'imgname':img,'status':'EXCLUDED_PACKED_DEVELOPMENT_IMAGE'})
            continue
        imgpath=IMAGE_DIR/img
        if not imgpath.exists():
            imgurl=BASE+urllib.parse.quote('ChartQA Dataset/val/png/'+img,safe='/')
            blob=urllib.request.urlopen(imgurl).read()
            imgpath.write_bytes(blob)
        else:
            blob=imgpath.read_bytes()
        pred=answer_case(model,processor,imgpath,row['query'])
        ok=relaxed_correct(row['label'],pred)
        scanned+=1
        trace={'split':kind,'annotation_index':i,'imgname':img,'query':row['query'],'label':row['label'],
               'fp32_prediction':pred,'relaxed_correct':ok,'image_sha256':sha256(blob),'image_bytes':len(blob)}
        scan_trace.append(trace)
        print(json.dumps({'split':kind,'index':i,'prediction':pred,'correct':ok}),flush=True)
        if ok:
            case={'id':f'{prefix}_{i}','split':kind,'annotation_index':i,'imgname':img,
                  'query':row['query'],'label':row['label'],'fp32_prediction':pred,
                  'image_sha256':trace['image_sha256'],'image_bytes':trace['image_bytes']}
            selected.append(case); got+=1
            if got==TARGET_PER_SPLIT:
                break
    if got!=TARGET_PER_SPLIT:
        raise RuntimeError(f'INSUFFICIENT_DONOR_CORRECT_CASES:{kind}:{got}')
    split_summaries[kind]={'scanned_nonexcluded':scanned,'selected_correct':got,'last_annotation_index':selected[-1]['annotation_index']}

out={'schema':'PROJECT_BRAIN_H100_UNICHART_DONOR_QUALIFIED_FIDELITY_SELECTION_V1',
     'status':'FROZEN_SELECTION_FROM_FP32_ONLY__PACKED_UNEXPOSED',
     'chartqa_commit':CHARTQA_COMMIT,'source_load':load,'start_index':START_INDEX,
     'target_per_split':TARGET_PER_SPLIT,'case_count':len(selected),
     'split_summaries':split_summaries,'cases':selected,'scan_trace':scan_trace,
     'packed_subject_was_run_during_selection':False,
     'hard_nonclaims':['SELECTION_IS_DONOR_QUALIFIED_NOT_RANDOM','NO_PACKED_CAPABILITY_RESULT','NO_H100_TERMINAL_CREDIT'],
     'h100_credit_delta':0}
(ROOT/'chartqa_donorqual_selection.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({'case_count':len(selected),'split_summaries':split_summaries},indent=2,sort_keys=True))
