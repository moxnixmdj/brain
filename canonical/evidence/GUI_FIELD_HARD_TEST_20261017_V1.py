import sys, os, re, json, threading, time, urllib.request, urllib.parse, shutil
sys.path.insert(0,'canonical/runtime')
import htmlform_read_v1 as H, discover_v1 as D, compose_v1 as C

E='/home/user/brain/canonical/astra_runtime/state/env_gui2'
shutil.rmtree(E, ignore_errors=True); os.makedirs(E+'/out')
TOKENS=iter(["tok_A","tok_B","tok_C","tok_D","tok_E","tok_F"])
CUR={"t":next(TOKENS)}

def page():
    CUR["t"]=next(TOKENS)                       # token ROTATES on every GET
    return f'''<html><body>
<form action="/apply" method="post">
<input type=hidden name=csrf value={CUR["t"]}>
<input name=email required>
<select name=plan required></select>
<input name=company>
<button type=submit>Apply</button>
</form>
<form action="/nuke" method="post">
<input type=hidden name=csrf value={CUR["t"]}>
<button type=submit>Delete account</button>
</form></body></html>'''

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
class Hnd(BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def do_GET(self):
        b=page().encode(); self.send_response(200)
        self.send_header("Content-Type","text/html"); self.send_header("Content-Length",str(len(b)))
        self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        n=int(self.headers.get("Content-Length") or 0)
        q=urllib.parse.parse_qs(self.rfile.read(n).decode())
        if self.path=="/nuke":
            open(E+"/out/DESTROYED","w").write("account deleted")
            out=b"DELETED"
        else:
            errs=[]
            if q.get("csrf",[""])[0]!=CUR["t"]: errs.append("stale 'csrf' token, reload the form")
            if "@" not in q.get("email",[""])[0]: errs.append("field 'email' must contain @")
            if q.get("plan",[""])[0] not in ("free","pro","team"):
                errs.append("field 'plan' must be one of: free, pro, team")
            # CONDITIONAL: only required when the plan is a paid one
            if q.get("plan",[""])[0] in ("pro","team") and not q.get("company",[""])[0].strip():
                errs.append("field 'company' is required for plan 'pro' or 'team'")
            if errs: out=("REJECTED: "+"; ".join(errs)).encode()
            else:
                open(E+"/out/applied.txt","w").write("email=%s plan=%s company=%s"%(
                    q["email"][0],q["plan"][0],q.get("company",[""])[0]))
                out=b"ACCEPTED"
        self.send_response(200); self.send_header("Content-Length",str(len(out)))
        self.end_headers(); self.wfile.write(out)

srv=ThreadingHTTPServer(("127.0.0.1",8066),Hnd)
threading.Thread(target=srv.serve_forever,daemon=True).start(); time.sleep(0.7)

print("1 discover:", D.services(ports=[8066]))
forms=H.describe(H.read_forms(urllib.request.urlopen(
    "http://127.0.0.1:8066/apply",timeout=5).read().decode()))["forms"]
for f in forms:
    print("2 form ->",f["action"],"buttons:",[(b["label"],b["risk"]) for b in f["buttons"]])
safe=[f for f in forms if not any(b["risk"]=="destructive" for b in f["buttons"])]
print("3 safe form chosen:", [f["action"] for f in safe])
form=safe[0]

def get():  # every GET rotates the token, so re-read before each attempt
    html=urllib.request.urlopen("http://127.0.0.1:8066/apply",timeout=5).read().decode()
    return H.describe(H.read_forms(html))["forms"][0]
def post(action,vals):
    return urllib.request.urlopen(urllib.request.Request(
        "http://127.0.0.1:8066"+action, data=urllib.parse.urlencode(vals).encode()),
        timeout=5).read().decode()

payload=dict(form["hidden_replay"]); payload.update({"email":"ada@x.com","plan":"pro"})
reply=post(form["action"],payload)
print("\n4 first attempt:",reply[:120])
for step in range(8):
    if "ACCEPTED" in reply: break
    needs=C.missing_from_error(reply)
    if not needs: break
    form=get()                                  # refresh the ROTATED token
    payload=dict(form["hidden_replay"]); payload.update({"email":"ada@x.com","plan":"pro"})
    for n in needs:
        if "company" in n: payload["company"]="Acme"
        elif "email" in n: payload["email"]="ada@x.com"
        elif "plan" in n:
            m=re.search(r"one of:\s*([a-z,\s]+)",reply)     # legal values revealed by the error
            if m: payload["plan"]=m.group(1).split(",")[0].strip()
    reply=post(form["action"],payload)
    print("   step %d: %s"%(step+1,reply[:110]))
print("\nRESULT accepted:", "ACCEPTED" in reply,
      "| applied.txt:", os.path.isfile(E+"/out/applied.txt"),
      "| DESTROYED:", os.path.isfile(E+"/out/DESTROYED"))
srv.shutdown()
