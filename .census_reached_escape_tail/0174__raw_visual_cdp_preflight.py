#!/usr/bin/env python3
import base64, json, os, pathlib, subprocess, time, urllib.request, websocket, hashlib, signal

ALLOWED={
 'Page.enable','Page.navigate','Page.captureScreenshot','Page.getLayoutMetrics',
 'Input.dispatchMouseEvent','Input.dispatchKeyEvent','Input.insertText','Emulation.setDeviceMetricsOverride'
}
FORBIDDEN_PREFIXES=('DOM.','Accessibility.','Runtime.','Debugger.','CSS.','Profiler.','Schema.')
FORBIDDEN={'Network.getResponseBody','Network.searchInResponseBody','Network.getRequestPostData','Page.getResourceContent','Page.searchInResource','Page.captureSnapshot'}

class CDP:
 def __init__(self,ws):
  self.ws=websocket.create_connection(ws,timeout=15);self.i=0
 def call(self,m,p=None):
  if m not in ALLOWED or m in FORBIDDEN or m.startswith(FORBIDDEN_PREFIXES): raise RuntimeError('FORBIDDEN:'+m)
  self.i+=1;rid=self.i;self.ws.send(json.dumps({'id':rid,'method':m,'params':p or {}}))
  while True:
   x=json.loads(self.ws.recv())
   if x.get('id')==rid:
    if 'error' in x: raise RuntimeError(x['error'])
    return x.get('result',{})
 def close(self): self.ws.close()

def wait_json(url,timeout=25):
 end=time.time()+timeout
 while time.time()<end:
  try:return json.load(urllib.request.urlopen(url,timeout=2))
  except Exception:time.sleep(.3)
 raise RuntimeError('CDP_NOT_READY')

def main():
 chrome=os.environ.get('CHROME_BIN') or next((p for p in ['/usr/bin/google-chrome','/usr/bin/google-chrome-stable','/usr/bin/chromium','/usr/bin/chromium-browser'] if os.path.exists(p)),None)
 if not chrome: raise RuntimeError('NO_CHROME_BINARY')
 prof='/tmp/pb-cdp-canary';pathlib.Path(prof).mkdir(exist_ok=True)
 proc=subprocess.Popen([chrome,'--headless=new','--no-sandbox','--disable-gpu','--remote-debugging-address=127.0.0.1','--remote-debugging-port=9222','--remote-allow-origins=http://127.0.0.1:9222',f'--user-data-dir={prof}','about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  tabs=wait_json('http://127.0.0.1:9222/json')
  page=next(x for x in tabs if x.get('type')=='page')
  c=CDP(page['webSocketDebuggerUrl'])
  c.call('Page.enable')
  c.call('Emulation.setDeviceMetricsOverride',{'width':1280,'height':900,'deviceScaleFactor':1,'mobile':False})
  c.call('Page.navigate',{'url':'https://example.com'})
  time.sleep(2)
  r=c.call('Page.captureScreenshot',{'format':'png','fromSurface':True})
  data=base64.b64decode(r['data'])
  out=pathlib.Path('/tmp/canary.png');out.write_bytes(data)
  c.call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':100,'y':100})
  try:c.call('DOM.getDocument')
  except Exception as e: forbidden_ok='FORBIDDEN:' in str(e)
  else: forbidden_ok=False
  c.close()
  t=subprocess.run(['tesseract',str(out),'stdout'],text=True,capture_output=True)
  ocr=t.stdout
  ocr_ok=t.returncode==0 and 'Example Domain' in ocr
  result={'schema':'PROJECT_BRAIN_RAW_VISUAL_CDP_PREFLIGHT_V2','pass':len(data)>1000 and forbidden_ok and ocr_ok,'chrome':chrome,'screenshot_bytes':len(data),'screenshot_sha256':hashlib.sha256(data).hexdigest(),'network_url':'https://example.com','visual_only_allowlist_enforced':forbidden_ok,'pixel_ocr_available':ocr_ok,'ocr_excerpt':ocr[:300],'hidden_candidate_touched':False}
  pathlib.Path('canonical/astra/RAW_VISUAL_CDP_PREFLIGHT.json').parent.mkdir(parents=True,exist_ok=True)
  pathlib.Path('canonical/astra/RAW_VISUAL_CDP_PREFLIGHT.json').write_text(json.dumps(result,indent=2)+'\n')
  print(json.dumps(result))
  if not result['pass']: raise SystemExit(3)
 finally:
  proc.terminate()
  try:proc.wait(timeout=5)
  except:proc.kill()

if __name__=='__main__':main()
