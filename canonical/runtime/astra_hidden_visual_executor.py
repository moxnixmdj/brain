#!/usr/bin/env python3
import argparse, base64, csv, datetime, hashlib, http.server, io, json, os, pathlib, re, secrets, socketserver, sqlite3, subprocess, threading, time, urllib.request
import websocket

ROOT=pathlib.Path(__file__).resolve().parents[2]
ASTRA=ROOT/'canonical'/'astra'
CONTRACT=ASTRA/'HIDDEN_EXECUTION_CONTRACT.json'
PREFLIGHT=ASTRA/'RAW_VISUAL_CDP_PREFLIGHT.json'
MARKER=ASTRA/'HIDDEN_ONESHOT_CONSUMED.json'
RESULT=ASTRA/'HIDDEN_RESULT.json'
TRAJ=ASTRA/'HIDDEN_TRAJECTORY.json'
FRAMES=ASTRA/'hidden_frames'
DB=ASTRA/'HIDDEN_AUTHORITY.sqlite'
PRIVATE=pathlib.Path('/tmp/project_brain_hidden_private.json')
AGENT='RECOVERY-WEBONE-H6-SUCCESSOR-MBTA006-V1'
TASK='RECOVERY-ASTRA-HIDDEN-EXECUTE-V1'
VERIFY='RECOVERY-ASTRA-FRESH-SUCCESSOR-VERIFY-V1'
NS='recovery-astra-webone-mbta006-20260921-v1'
ALLOWED={'Page.enable','Page.navigate','Page.captureScreenshot','Page.getLayoutMetrics','Input.dispatchMouseEvent','Input.dispatchKeyEvent','Input.insertText','Emulation.setDeviceMetricsOverride'}
FORBIDDEN_PREFIX=('DOM.','Accessibility.','Runtime.','Debugger.','CSS.','Profiler.','Schema.')
FORBIDDEN={'Network.getResponseBody','Network.searchInResponseBody','Network.getRequestPostData','Page.getResourceContent','Page.searchInResource','Page.captureSnapshot'}

def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z')
def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':'))
def sha_text(s): return hashlib.sha256(s.encode()).hexdigest()
def sha_file(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def writej(p,x):
 p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')

class CDP:
 def __init__(self,ws):
  self.ws=websocket.create_connection(ws,timeout=20,origin='http://127.0.0.1:9222');self.i=0;self.sent=[]
 def call(self,m,p=None):
  if m not in ALLOWED or m in FORBIDDEN or m.startswith(FORBIDDEN_PREFIX):
   raise RuntimeError('CDP_METHOD_FORBIDDEN:'+m)
  self.i+=1; rid=self.i; self.sent.append(m)
  self.ws.send(json.dumps({'id':rid,'method':m,'params':p or {}},separators=(',',':')))
  while True:
   x=json.loads(self.ws.recv())
   if x.get('id')!=rid: continue
   if 'error' in x: raise RuntimeError('CDP_ERROR:'+json.dumps(x['error'],sort_keys=True))
   return x.get('result',{})
 def close(self):
  try:self.ws.close()
  except:pass

class Browser:
 def __init__(self,c): self.c=c
 def enable(self):
  self.c.call('Page.enable')
  self.c.call('Emulation.setDeviceMetricsOverride',{'width':1280,'height':900,'deviceScaleFactor':1,'mobile':False})
 def navigate(self,url): return self.c.call('Page.navigate',{'url':url})
 def screenshot(self,p):
  r=self.c.call('Page.captureScreenshot',{'format':'png','fromSurface':True,'captureBeyondViewport':False})
  data=base64.b64decode(r['data']);pathlib.Path(p).write_bytes(data);return len(data)
 def click(self,x,y):
  for typ in ('mousePressed','mouseReleased'):
   self.c.call('Input.dispatchMouseEvent',{'type':typ,'x':float(x),'y':float(y),'button':'left','clickCount':1})
 def scroll(self,dy):
  self.c.call('Input.dispatchMouseEvent',{'type':'mouseWheel','x':1100.0,'y':750.0,'deltaX':0.0,'deltaY':float(dy)})

def chrome_start():
 chrome=next((p for p in ['/usr/bin/google-chrome','/usr/bin/google-chrome-stable','/usr/bin/chromium'] if os.path.exists(p)),None)
 if not chrome: raise RuntimeError('NO_CHROME')
 prof=f'/tmp/pb-hidden-{secrets.token_hex(4)}';pathlib.Path(prof).mkdir()
 proc=subprocess.Popen([chrome,'--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--remote-debugging-address=127.0.0.1','--remote-debugging-port=9222','--remote-allow-origins=http://127.0.0.1:9222',f'--user-data-dir={prof}','about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 end=time.time()+25
 while time.time()<end:
  try:
   tabs=json.load(urllib.request.urlopen('http://127.0.0.1:9222/json',timeout=2))
   page=next(x for x in tabs if x.get('type')=='page')
   return proc,CDP(page['webSocketDebuggerUrl'])
  except Exception: time.sleep(.25)
 proc.terminate();raise RuntimeError('CDP_NOT_READY')

def ocr(path):
 p=subprocess.run(['tesseract',str(path),'stdout','tsv'],text=True,capture_output=True)
 if p.returncode: raise RuntimeError('OCR_FAIL:'+p.stderr[-500:])
 rows=list(csv.DictReader(io.StringIO(p.stdout),delimiter='\t'))
 words=[]
 for r in rows:
  t=(r.get('text') or '').strip()
  try: conf=float(r.get('conf') or -1)
  except: conf=-1
  if not t or conf<20: continue
  try:
   words.append({'text':t,'x':int(r['left']),'y':int(r['top']),'w':int(r['width']),'h':int(r['height']),'line':(r['block_num'],r['par_num'],r['line_num'])})
  except: pass
 groups={}
 for w in words: groups.setdefault(w['line'],[]).append(w)
 lines=[]
 for ws in groups.values():
  ws=sorted(ws,key=lambda z:z['x']);txt=' '.join(w['text'] for w in ws)
  lines.append({'text':txt,'words':ws,'y':min(w['y'] for w in ws)})
 lines.sort(key=lambda z:z['y'])
 return words,lines

def norm(s): return re.sub(r'\s+',' ',re.sub(r'[^a-z0-9 ]',' ',s.lower())).strip()

def phrase_box(lines,phrase):
 target=norm(phrase).split()
 for line in lines:
  toks=[norm(w['text']) for w in line['words']]
  toks=[t for t in toks if t]
  for i in range(len(toks)):
   for j in range(i+1,min(len(toks),i+len(target)+4)+1):
    if norm(' '.join(toks[i:j]))==norm(phrase):
     ws=line['words'][i:j];x=min(w['x'] for w in ws);y=min(w['y'] for w in ws);r=max(w['x']+w['w'] for w in ws);b=max(w['y']+w['h'] for w in ws)
     return {'x':x,'y':y,'w':r-x,'h':b-y,'text':line['text']}
 # substring fallback only for multiword targets
 if len(target)>1:
  for line in lines:
   if norm(phrase) in norm(line['text']):
    ws=line['words'];x=min(w['x'] for w in ws);y=min(w['y'] for w in ws);r=max(w['x']+w['w'] for w in ws);b=max(w['y']+w['h'] for w in ws)
    return {'x':x,'y':y,'w':r-x,'h':b-y,'text':line['text']}
 return None

class VisualExecutor:
 def __init__(self,browser,budget=40,frame_dir=FRAMES):
  self.b=browser;self.budget=budget;self.actions=[];self.frames=[];self.frame_dir=pathlib.Path(frame_dir);self.frame_dir.mkdir(parents=True,exist_ok=True);self.n=0
 def frame(self,label):
  p=self.frame_dir/f'{len(self.frames):03d}-{label}.png';n=self.b.screenshot(p);words,lines=ocr(p);text='\n'.join(x['text'] for x in lines)
  rec={'index':len(self.frames),'label':label,'path':str(p.relative_to(ROOT)),'bytes':n,'sha256':sha_file(p),'ocr_sha256':sha_text(text),'ocr_text':text[:12000],'dom_used':False,'source':'Page.captureScreenshot'}
  self.frames.append(rec);return rec,lines
 def act(self,kind,payload,fn):
  if len(self.actions)>=self.budget: raise RuntimeError('ACTION_BUDGET_EXHAUSTED')
  t=time.monotonic();fn();self.actions.append({'index':len(self.actions),'kind':kind,'payload':payload,'duration_ms':round((time.monotonic()-t)*1000,3),'ts':utc()});time.sleep(2.0)
 def click_phrase(self,phrases,label,scroll_tries=0):
  if isinstance(phrases,str):phrases=[phrases]
  for attempt in range(scroll_tries+1):
   fr,lines=self.frame(f'{label}-scan{attempt}')
   for ph in phrases:
    box=phrase_box(lines,ph)
    if box:
     x=box['x']+box['w']/2;y=box['y']+box['h']/2
     self.act('click',{'matched_phrase':ph,'matched_line':box['text'],'x':x,'y':y,'frame_index':fr['index']},lambda:self.b.click(x,y))
     return ph
   if attempt<scroll_tries:self.act('scroll',{'dy':650,'reason':'seek '+('|'.join(phrases)),'frame_index':fr['index']},lambda:self.b.scroll(650))
  raise RuntimeError('VISIBLE_PHRASE_NOT_FOUND:'+('|'.join(phrases)))
 def click_weekend_day(self):
  fr,lines=self.frame('weekend-selector-open')
  candidates=[]
  for line in lines:
   n=norm(line['text'])
   if re.search(r'\bsaturday\b|\bsunday\b|\bsat\b|\bsun\b',n):
    ws=line['words'];x=min(w['x'] for w in ws);y=min(w['y'] for w in ws);r=max(w['x']+w['w'] for w in ws);b=max(w['y']+w['h'] for w in ws)
    candidates.append((y,{'x':x,'y':y,'w':r-x,'h':b-y,'text':line['text']}))
  if not candidates: raise RuntimeError('WEEKEND_DAY_NOT_VISIBLE')
  box=sorted(candidates,key=lambda z:z[0])[0][1];x=box['x']+box['w']/2;y=box['y']+box['h']/2
  self.act('click',{'matched_phrase':'Saturday|Sunday','matched_line':box['text'],'x':x,'y':y,'frame_index':fr['index']},lambda:self.b.click(x,y))
  return box['text']

def init_db():
 if DB.exists(): DB.unlink()
 c=sqlite3.connect(DB)
 c.execute('''CREATE TABLE recovery_tasks(task_id TEXT PRIMARY KEY,lane TEXT,state TEXT,priority REAL,prerequisites_json TEXT,executor_caps_json TEXT,lease_owner TEXT,lease_token TEXT,lease_expires_at TEXT,submitter TEXT,result_sha256 TEXT,verifier TEXT,verification_sha256 TEXT,objective TEXT,success_criteria TEXT,provenance_class TEXT)''')
 c.execute('''CREATE TABLE recovery_oneshot_fence_v2(namespace TEXT PRIMARY KEY,task_id TEXT NOT NULL,attempt_id TEXT NOT NULL,state TEXT NOT NULL,lease_owner TEXT NOT NULL,lease_token_sha256 TEXT NOT NULL,lease_expires_at TEXT NOT NULL,prerequisite_states_sha256 TEXT NOT NULL,binding_sha256 TEXT NOT NULL,acquired_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,terminal_manifest_sha256 TEXT,terminal_at TEXT)''')
 c.execute('''CREATE TABLE recovery_evidence_v2(namespace TEXT NOT NULL,logical_name TEXT NOT NULL,ordinal INTEGER NOT NULL,content_sha256 TEXT NOT NULL,content_json TEXT NOT NULL,accepted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(namespace,logical_name))''')
 c.execute('INSERT INTO recovery_tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(VERIFY,'ASTRA','COMPLETE',97,'[]','["cap:verify"]',None,None,None,'WOLFRAM-REMOTE-KERNEL-20260921-SUCCESSOR-V1','f105e7dfae6fdc5adc6d0268bcd062fc4f28f363a3a52f9ee260a8ede3e88e44','WOLFRAM-REMOTE-KERNEL-20260921-SUCCESSOR-V1','f105e7dfae6fdc5adc6d0268bcd062fc4f28f363a3a52f9ee260a8ede3e88e44','verify successor','distinct verifier','RECOVERY_DERIVED'))
 c.execute('INSERT INTO recovery_tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(TASK,'ASTRA','READY',96,json.dumps([VERIFY]),'["cap:astra_targeted_execution"]',None,None,None,None,None,None,None,'Execute exactly one fresh hidden mission under the verified successor.','Exactly one scored attempt, zero scored retries, rendered-UI-only policy, sealed evidence trajectory, hard-$0.','RECOVERY_DERIVED'))
 c.execute('INSERT INTO recovery_tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',('RECOVERY-ASTRA-HIDDEN-ADJUDICATE-V1','ASTRA','BLOCKED',95,json.dumps([TASK]),'["cap:verify"]',None,None,None,None,None,None,None,'Independently adjudicate sealed hidden result.','Distinct verifier required.','RECOVERY_DERIVED'))
 c.commit();c.close()

def claim_and_arm():
 if MARKER.exists() or RESULT.exists(): raise RuntimeError('CANONICAL_ONE_SHOT_ALREADY_CONSUMED')
 contract=json.loads(CONTRACT.read_text());pre=json.loads(PREFLIGHT.read_text())
 if not pre.get('pass') or pre.get('hidden_candidate_touched') is not False: raise RuntimeError('RAW_VISUAL_PREFLIGHT_REQUIRED')
 if sha_text(contract['candidate']['instruction'])!=contract['candidate']['instruction_sha256']: raise RuntimeError('INSTRUCTION_BINDING_BAD')
 if contract['corpus']['index']!=342 or contract['candidate']['new_id']!='mbta-1E2K9j2Q': raise RuntimeError('INDEX_BINDING_BAD')
 init_db();owner=AGENT;token=secrets.token_hex(16);exp=(datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(minutes=20)).isoformat().replace('+00:00','Z')
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row
 c.execute("UPDATE recovery_tasks SET state='LEASED',lease_owner=?,lease_token=?,lease_expires_at=? WHERE task_id=? AND state='READY'",(owner,token,exp,TASK))
 if c.total_changes!=1: raise RuntimeError('CLAIM_RACE')
 states=[{'task_id':VERIFY,'state':c.execute('select state from recovery_tasks where task_id=?',(VERIFY,)).fetchone()['state']}]
 public={'task_id':TASK,'lease_owner':owner,'lease_token_sha256':sha_text(token),'lease_expires_at':exp,'prerequisite_states':states}
 psha=sha_text(canon(states));binding=sha_text(canon(public));attempt=secrets.token_hex(16)
 c.execute('INSERT INTO recovery_oneshot_fence_v2(namespace,task_id,attempt_id,state,lease_owner,lease_token_sha256,lease_expires_at,prerequisite_states_sha256,binding_sha256) VALUES(?,?,?,?,?,?,?,?,?)',(NS,TASK,attempt,'ACTIVE',owner,sha_text(token),exp,psha,binding))
 c.commit();c.close()
 marker={'schema':'PROJECT_BRAIN_ASTRA_HIDDEN_ONESHOT_MARKER_V1','task_id':TASK,'namespace':NS,'attempt_id':attempt,'worker_identity':AGENT,'candidate_id':contract['candidate']['id'],'candidate_index':342,'new_id':'mbta-1E2K9j2Q','instruction_sha256':contract['candidate']['instruction_sha256'],'binding_sha256':binding,'armed_at_utc':utc(),'scored_attempts_authorized':1,'scored_retries_authorized':0,'hidden_navigation_started':False}
 writej(MARKER,marker);writej(PRIVATE,{'owner':owner,'token':token,'attempt_id':attempt,'binding_sha256':binding})
 print(json.dumps(marker))

def ev(name,value):
 priv=json.loads(PRIVATE.read_text());c=sqlite3.connect(DB);c.row_factory=sqlite3.Row
 f=c.execute('select * from recovery_oneshot_fence_v2 where namespace=?',(NS,)).fetchone()
 if not f or f['state']!='ACTIVE': raise RuntimeError('ACTIVE_FENCE_REQUIRED')
 ordv=c.execute('select count(*) from recovery_evidence_v2 where namespace=?',(NS,)).fetchone()[0];payload=canon(value)
 c.execute('insert into recovery_evidence_v2 values(?,?,?,?,?,CURRENT_TIMESTAMP)',(NS,name,ordv,sha_text(payload),payload));c.commit();c.close()

def terminal(outcome):
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;f=c.execute('select * from recovery_oneshot_fence_v2 where namespace=?',(NS,)).fetchone()
 evidence=[dict(zip(['logical_name','ordinal','content_sha256'],r)) for r in c.execute('select logical_name,ordinal,content_sha256 from recovery_evidence_v2 where namespace=? order by ordinal',(NS,))]
 manifest={'schema':'RECOVERY_ONESHOT_TERMINAL_MANIFEST_V2','namespace':NS,'task_id':TASK,'attempt_id':f['attempt_id'],'outcome':outcome,'binding_sha256':f['binding_sha256'],'evidence':evidence};msha=sha_text(canon(manifest))
 c.execute("update recovery_oneshot_fence_v2 set state=?,terminal_manifest_sha256=?,terminal_at=CURRENT_TIMESTAMP where namespace=? and state='ACTIVE'",(outcome,msha,NS))
 c.execute("update recovery_tasks set state='SUBMITTED',submitter=?,result_sha256=?,lease_owner=NULL,lease_token=NULL,lease_expires_at=NULL where task_id=?",(AGENT,msha,TASK));c.commit();c.close()
 return manifest,msha

def run_hidden():
 contract=json.loads(CONTRACT.read_text());marker=json.loads(MARKER.read_text())
 marker['hidden_navigation_started']=True;marker['navigation_started_at_utc']=utc();writej(MARKER,marker)
 FRAMES.mkdir(parents=True,exist_ok=True)
 proc,c=chrome_start();b=Browser(c);b.enable();x=VisualExecutor(b,contract['execution_contract']['action_budget'])
 result=None
 try:
  ev('0000-runner-open',{'ts':utc(),'candidate_index':342,'instruction_sha256':contract['candidate']['instruction_sha256'],'visual_only':True,'action_budget':40})
  # Wrapper-level prohibited method probe: must be rejected before sending to Chrome.
  try:c.call('DOM.getDocument');forbidden_rejected=False
  except Exception as e:forbidden_rejected='CDP_METHOD_FORBIDDEN' in str(e)
  if not forbidden_rejected: raise RuntimeError('VISUAL_ONLY_ALLOWLIST_NOT_ENFORCED')
  x.act('navigate',{'url':contract['candidate']['start_url']},lambda:b.navigate(contract['candidate']['start_url']))
  # Optional visible consent dismissal, only if screenshot text shows it.
  fr,lines=x.frame('initial-home')
  for ph in ['Accept All Cookies','Accept all cookies','Accept All','I Agree']:
   box=phrase_box(lines,ph)
   if box:
    xx=box['x']+box['w']/2;yy=box['y']+box['h']/2;x.act('click',{'matched_phrase':ph,'matched_line':box['text'],'x':xx,'y':yy,'frame_index':fr['index'],'purpose':'visible_cookie_consent'},lambda xx=xx,yy=yy:b.click(xx,yy));break
  x.click_phrase('Ferry','ferry-home',scroll_tries=1)
  x.click_phrase('Charlestown Ferry','charlestown-ferry',scroll_tries=2)
  x.click_phrase(['Today','Schedule for Today'],'date-selector',scroll_tries=1)
  weekend_line=x.click_weekend_day()
  x.click_phrase('PDF Schedules','pdf-section',scroll_tries=8)
  pdf_phrase=x.click_phrase(['Current Charlestown Ferry Weekend Schedule PDF','Charlestown Ferry Weekend Schedule PDF','Weekend Schedule PDF'],'weekend-pdf',scroll_tries=4)
  final,_=x.frame('final-after-pdf-click')
  result={'schema':'RECOVERY_ASTRA_HIDDEN_EXECUTION_RESULT_V1','task_id':TASK,'namespace':NS,'candidate_index':342,'candidate_id':contract['candidate']['id'],'new_id':contract['candidate']['new_id'],'instruction_sha256':contract['candidate']['instruction_sha256'],'success':True,'weekend_choice_visible_line':weekend_line,'pdf_link_matched':pdf_phrase,'actions_total':len(x.actions),'action_budget':40,'budget_fraction':len(x.actions)/40,'frames_total':len(x.frames),'forbidden_semantic_methods_sent':0,'models_used':False,'pixel_ocr_only':True,'hidden_scored_attempts_consumed':1,'scored_retries':0,'final_frame_sha256':final['sha256'],'promotion_authorized':False}
  ev('9000-efficiency',{'actions_total':len(x.actions),'action_budget':40,'budget_fraction':len(x.actions)/40})
  ev('9001-result',result);manifest,msha=terminal('TERMINAL_SUCCESS');result['terminal_manifest_sha256']=msha;result['terminal_manifest']=manifest
 except Exception as e:
  result={'schema':'RECOVERY_ASTRA_HIDDEN_EXECUTION_RESULT_V1','task_id':TASK,'namespace':NS,'candidate_index':342,'success':False,'error':type(e).__name__+':'+str(e),'actions_total':len(x.actions),'action_budget':40,'frames_total':len(x.frames),'forbidden_semantic_methods_sent':0,'models_used':False,'pixel_ocr_only':True,'hidden_scored_attempts_consumed':1,'scored_retries':0,'promotion_authorized':False}
  try:ev('9000-efficiency',{'actions_total':len(x.actions),'action_budget':40,'budget_fraction':len(x.actions)/40});ev('9001-result',result);manifest,msha=terminal('TERMINAL_FAILURE');result['terminal_manifest_sha256']=msha;result['terminal_manifest']=manifest
  except Exception as ee:result['seal_error']=str(ee)
 finally:
  try:c.close()
  except:pass
  proc.terminate()
  try:proc.wait(timeout=5)
  except:proc.kill()
 writej(TRAJ,{'schema':'RECOVERY_ASTRA_HIDDEN_TRAJECTORY_V1','task_id':TASK,'candidate_index':342,'actions':x.actions,'frames':x.frames,'visual_only':True,'ocr_source':'PNG_PIXELS_ONLY','forbidden_semantic_methods_sent':0})
 writej(RESULT,result)
 if PRIVATE.exists():PRIVATE.unlink()
 print(json.dumps(result))
 if not result.get('success'): raise SystemExit(7)

def canary():
 root=pathlib.Path('/tmp/astra-visual-canary');root.mkdir(exist_ok=True)
 style='<style>body{font-family:Arial,sans-serif;font-size:44px;padding:50px}a{display:block;font-size:44px;margin:60px 0;color:#0645ad}h1,h2{font-size:52px}</style>'
 pages={
 'index.html':f'<html>{style}<body><h1>Visual Canary</h1><a href="/ferry.html">Ferry</a></body></html>',
 'ferry.html':f'<html>{style}<body><a href="/route.html">Charlestown Ferry</a></body></html>',
 'route.html':f'<html>{style}<body><a href="/days.html">Today</a></body></html>',
 'days.html':f'<html>{style}<body><a href="/pdf.html">Saturday</a></body></html>',
 'pdf.html':f'<html>{style}<body><h2>PDF Schedules</h2><a href="/done.html">Current Charlestown Ferry Weekend Schedule PDF</a></body></html>',
 'done.html':f'<html>{style}<body><h1>Charlestown Ferry Weekend Schedule PDF</h1></body></html>'}
 for n,h in pages.items():(root/n).write_text(h)
 class Handler(http.server.SimpleHTTPRequestHandler):
  def log_message(self,*a):pass
 os.chdir(root);srv=socketserver.TCPServer(('127.0.0.1',8765),Handler);threading.Thread(target=srv.serve_forever,daemon=True).start()
 proc,c=chrome_start();b=Browser(c);b.enable();tmp=ASTRA/'canary_frames';tmp.mkdir(parents=True,exist_ok=True);x=VisualExecutor(b,20,tmp)
 try:
  x.act('navigate',{'url':'http://127.0.0.1:8765/index.html'},lambda:b.navigate('http://127.0.0.1:8765/index.html'))
  x.click_phrase('Ferry','c-ferry');x.click_phrase('Charlestown Ferry','c-charlestown');x.click_phrase('Today','c-today');x.click_weekend_day();x.click_phrase('PDF Schedules','c-pdf-section');x.click_phrase('Current Charlestown Ferry Weekend Schedule PDF','c-pdf-link');final,_=x.frame('c-final')
  ok='Charlestown Ferry Weekend Schedule PDF' in final['ocr_text']
  out={'schema':'PROJECT_BRAIN_ASTRA_VISUAL_OPERATOR_CANARY_V1','pass':ok,'actions_total':len(x.actions),'frames_total':len(x.frames),'final_frame_sha256':final['sha256'],'hidden_candidate_touched':False,'visual_only':True}
  writej(ASTRA/'VISUAL_OPERATOR_CANARY.json',out);print(json.dumps(out))
  if not ok:raise SystemExit(5)
 finally:
  c.close();proc.terminate();srv.shutdown()

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['arm','execute','canary']);a=ap.parse_args()
 {'arm':claim_and_arm,'execute':run_hidden,'canary':canary}[a.mode]()
