import sys, os, json, threading, time, urllib.request, urllib.parse, shutil
sys.path.insert(0,'canonical/runtime')
import htmlform_read_v1 as H, discover_v1 as D, compose_v1 as C

E='/home/user/brain/canonical/astra_runtime/state/env_gui'
shutil.rmtree(E, ignore_errors=True); os.makedirs(E+'/out')
TOKEN="tok_live_9931"

FORM=f'''<html><body>
<form action="/submit" method="post">
<input type=hidden name=csrf value={TOKEN}>
<input name=fullname required placeholder="your name">
<select name=role required><option value=admin><option value=viewer></select>
<input type=checkbox name=terms required>
<button type=submit>Send</button>
<button name=reset>Delete everything</button>
</form></body></html>'''

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
class Hnd(BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def do_GET(self):
        b=FORM.encode(); self.send_response(200)
        self.send_header("Content-Type","text/html"); self.send_header("Content-Length",str(len(b)))
        self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        n=int(self.headers.get("Content-Length") or 0)
        body=self.rfile.read(n).decode()
        q=urllib.parse.parse_qs(body)
        errs=[]
        if q.get("csrf",[""])[0]!=TOKEN: errs.append("missing or wrong field 'csrf'")
        if not q.get("fullname",[""])[0].strip(): errs.append("field 'fullname' is required")
        if q.get("role",[""])[0] not in ("admin","viewer"):
            errs.append("field 'role' must be one of: admin, viewer")
        if not q.get("terms"): errs.append("field 'terms' must be accepted")
        if errs:
            out=("REJECTED: "+ "; ".join(errs)).encode()
        else:
            open(E+"/out/submitted.txt","w").write("name=%s role=%s"%(q["fullname"][0],q["role"][0]))
            out=b"ACCEPTED: form submitted"
        self.send_response(200); self.send_header("Content-Length",str(len(out)))
        self.end_headers(); self.wfile.write(out)

srv=ThreadingHTTPServer(("127.0.0.1",8055),Hnd)
threading.Thread(target=srv.serve_forever,daemon=True).start(); time.sleep(0.7)

print("STEP 1  discover the service")
ports=D.services(ports=[8055]); print("   listening:", ports)

print("STEP 2  fetch the page and read its fields")
html=urllib.request.urlopen("http://127.0.0.1:8055/form",timeout=5).read().decode()
desc=H.describe(H.read_forms(html))["forms"][0]
print("   required :", desc["required_input"])
print("   choices  :", desc["choices"])
print("   hidden   :", desc["hidden_replay"])
print("   buttons  :", [(b["label"],b["risk"]) for b in desc["buttons"]])

def submit(vals):
    data=urllib.parse.urlencode(vals).encode()
    r=urllib.request.urlopen(urllib.request.Request(
        "http://127.0.0.1:8055/submit",data=data),timeout=5)
    return r.read().decode()

print("\nSTEP 3  submit EMPTY -- then learn from what it complains about")
payload=dict(desc["hidden_replay"])
reply=submit(payload)
print("   reply:", reply[:150])
needs=C.missing_from_error(reply)
print("   learned it needs:", needs)

print("\nSTEP 4  fill what it named, retry, repeat")
for step in range(6):
    if "ACCEPTED" in reply: break
    needs=C.missing_from_error(reply)
    if not needs: break
    filled=False
    for n in needs:
        if "fullname" in n: payload["fullname"]="Ada"; filled=True
        elif "role" in n:   payload["role"]="admin"; filled=True
        elif "terms" in n:  payload["terms"]="on"; filled=True
        elif "csrf" in n:   payload.update(desc["hidden_replay"]); filled=True
    if not filled: break
    reply=submit(payload)
    print("   step %d: %s"%(step+1, reply[:110]))

print("\nRESULT")
print("   accepted  :", "ACCEPTED" in reply)
print("   file wrote:", os.path.isfile(E+"/out/submitted.txt"))
if os.path.isfile(E+"/out/submitted.txt"):
    print("   contents  :", open(E+"/out/submitted.txt").read())
srv.shutdown()
