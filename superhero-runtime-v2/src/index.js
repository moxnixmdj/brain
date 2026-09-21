import { DurableObject, WorkflowEntrypoint } from 'cloudflare:workers';
import { chromium } from '@cloudflare/playwright';
import {
  createMission, selectProvider, beginDispatch, applyProviderResult, rollGeneration, appendKernelEvent
} from './kernel.js';

const AGENT_ID = 'SUPERHERO-RUNTIME-2';
const STATE_OBJECT = 'project-brain-superhero-v2-global';
const enc = new TextEncoder();
const now = () => Date.now();
const j = (x, status=200) => Response.json(x,{status,headers:{'cache-control':'no-store'}});
const safe = (x,n=12000) => String(x??'').slice(0,n);
const sha256hex = async s => [...new Uint8Array(await crypto.subtle.digest('SHA-256',typeof s==='string'?enc.encode(s):s))].map(b=>b.toString(16).padStart(2,'0')).join('');

function auth(req, env){ return !env.CONTROL_TOKEN || req.headers.get('authorization')===`Bearer ${env.CONTROL_TOKEN}`; }
function stub(env){ return env.STATE.getByName(STATE_OBJECT); }

export class SuperheroState extends DurableObject {
  constructor(ctx, env){
    super(ctx,env);
    ctx.storage.sql.exec(`
      CREATE TABLE IF NOT EXISTS missions(mission_id TEXT PRIMARY KEY, mission_json TEXT NOT NULL, updated_at INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS runtime_events(seq INTEGER PRIMARY KEY AUTOINCREMENT, mission_id TEXT NOT NULL, ts INTEGER NOT NULL, event_type TEXT NOT NULL, payload_json TEXT NOT NULL);
    `);
  }
  create(id, goal, frontier=[]){
    const m=createMission({missionId:id,goal,frontier}); this.put(m); this.event(id,'MISSION_CREATED',{goal,frontierCount:frontier.length}); return m;
  }
  put(m){ this.ctx.storage.sql.exec('INSERT OR REPLACE INTO missions(mission_id,mission_json,updated_at) VALUES(?,?,?)',m.missionId,JSON.stringify(m),now()); return m; }
  get(id){ const r=this.ctx.storage.sql.exec('SELECT mission_json FROM missions WHERE mission_id=?',id).toArray(); return r.length?JSON.parse(String(r[0].mission_json)):null; }
  event(id,t,p){ this.ctx.storage.sql.exec('INSERT INTO runtime_events(mission_id,ts,event_type,payload_json) VALUES(?,?,?,?)',id,now(),t,JSON.stringify(p)); }
  events(id,limit=200){ return this.ctx.storage.sql.exec('SELECT seq,ts,event_type,payload_json FROM runtime_events WHERE mission_id=? ORDER BY seq DESC LIMIT ?',id,Math.min(500,Math.max(1,limit))).toArray().reverse(); }
}

function providers(env){
  return [
    {id:'tool-router',class:'api',kinds:['*'],enabled:!!env.TOOL_ROUTER_URL,incrementalCost:0,reliability:.95,latencyMs:250,evidenceQuality:.9,independence:.9,retryable:true},
    {id:'web-search',class:'search',kinds:['goal','search_web','knowledge'],enabled:!!env.WEB_SEARCH_ENDPOINT,incrementalCost:0,reliability:.9,latencyMs:600,evidenceQuality:.85,independence:.9,retryable:true},
    {id:'github-search',class:'repository',kinds:['goal','repository_search','code_search'],enabled:!!env.GITHUB_TOKEN,incrementalCost:0,reliability:.98,latencyMs:350,evidenceQuality:.95,independence:.9,retryable:true},
    {id:'http-fetch',class:'api',kinds:['retrieve_url'],enabled:true,incrementalCost:0,reliability:.98,latencyMs:300,evidenceQuality:.9,independence:.8,retryable:true},
    {id:'browser-visual',class:'browser',kinds:['browser_visual'],enabled:!!env.BROWSER,incrementalCost:0,reliability:.85,latencyMs:800,evidenceQuality:1,independence:.8,retryable:true},
    {id:'workers-ai-optional',class:'model',kinds:['goal','synthesis','vision_interpretation'],enabled:env.ENABLE_MODEL_PROVIDER==='true' && !!env.AI,incrementalCost:0,reliability:.8,latencyMs:1200,evidenceQuality:.6,independence:.3,retryable:true},
  ];
}

async function dispatch(env, p, need, mission){
  if(p.id==='tool-router'){
    const r=await fetch(env.TOOL_ROUTER_URL,{method:'POST',headers:{'content-type':'application/json',...(env.TOOL_ROUTER_TOKEN?{authorization:`Bearer ${env.TOOL_ROUTER_TOKEN}`}:{})},body:JSON.stringify({agentId:AGENT_ID,missionId:mission.missionId,need,evidence:mission.evidence.slice(-20)})});
    if(!r.ok) return {status:'retry',reason:`TOOL_ROUTER_HTTP_${r.status}`,evidence:{status:r.status}};
    return await r.json();
  }
  if(p.id==='web-search'){
    const u=new URL(env.WEB_SEARCH_ENDPOINT); u.searchParams.set('q',need.query);
    const r=await fetch(u,{headers:env.WEB_SEARCH_TOKEN?{authorization:`Bearer ${env.WEB_SEARCH_TOKEN}`}:{}});
    const text=safe(await r.text(),50000);
    if(!r.ok) return {status:'retry',reason:`SEARCH_HTTP_${r.status}`,evidence:{status:r.status}};
    return {status:'ok',summary:'Web search evidence acquired.',evidence:{url:r.url,status:r.status,body:text},newNeeds:[{id:`synthesis-${mission.cycle}`,kind:'synthesis',query:`Synthesize evidence for goal: ${mission.goal}`,priority:80}]};
  }
  if(p.id==='github-search'){
    const q=encodeURIComponent(need.query);
    const r=await fetch(`https://api.github.com/search/code?q=${q}`,{headers:{authorization:`Bearer ${env.GITHUB_TOKEN}`,accept:'application/vnd.github+json','user-agent':'ProjectBrain-Superhero/2.0'}});
    const text=safe(await r.text(),50000);
    if(!r.ok) return {status:'retry',reason:`GITHUB_SEARCH_HTTP_${r.status}`,evidence:{status:r.status,body:text}};
    return {status:'ok',summary:'GitHub repository evidence acquired.',evidence:{status:r.status,body:text},newNeeds:[{id:`synthesis-${mission.cycle}`,kind:'synthesis',query:`Synthesize repository evidence for goal: ${mission.goal}`,priority:80}]};
  }
  if(p.id==='http-fetch'){
    const u=new URL(need.metadata?.url || need.query); if(!/^https?:$/.test(u.protocol)) return {status:'blocked',reason:'UNSUPPORTED_URL_SCHEME'};
    const r=await fetch(u,{headers:{'user-agent':'ProjectBrain-Superhero/2.0'}}); const body=safe(await r.text(),60000);
    return r.ok?{status:'ok',summary:`Fetched ${r.url}`,evidence:{url:r.url,status:r.status,contentType:r.headers.get('content-type'),body}}:{status:'retry',reason:`HTTP_${r.status}`,evidence:{url:r.url,status:r.status}};
  }
  if(p.id==='browser-visual'){
    const url=need.metadata?.url || need.query; if(!/^https?:/.test(url)) return {status:'blocked',reason:'BROWSER_URL_REQUIRED'};
    const browser=await chromium.launch(env.BROWSER); const page=await browser.newPage({viewport:{width:1280,height:900}});
    await page.goto(url,{waitUntil:'domcontentloaded',timeout:45000});
    const bytes=await page.screenshot({type:'png',fullPage:false}); await browser.close();
    const hash=await sha256hex(bytes);
    return {status:'ok',summary:'Visual browser screenshot captured; interpretation remains a separate provider need.',evidence:{url,screenshotSha256:hash,screenshotBytes:bytes.byteLength},newNeeds:[{id:`vision-${mission.cycle}`,kind:'vision_interpretation',query:`Interpret screenshot ${hash} for mission goal`,priority:95,metadata:{screenshotSha256:hash,url}}]};
  }
  if(p.id==='workers-ai-optional'){
    const model=need.kind==='vision_interpretation'?(env.VISION_MODEL||'@cf/google/gemma-4-26b-a4b-it'):(env.TEXT_MODEL||'@cf/nvidia/nemotron-3-120b-a12b');
    const prompt=`Mission: ${mission.goal}\nNeed: ${need.kind}: ${need.query}\nRecent evidence: ${JSON.stringify(mission.evidence.slice(-8)).slice(-24000)}\nReturn JSON {status:'ok', summary:'...', finalAnswer?:'...', newNeeds?:[...]}. Do not claim unsupported evidence.`;
    const r=await env.AI.run(model,{messages:[{role:'user',content:prompt}],max_completion_tokens:1200,temperature:.1});
    let text=typeof r==='string'?r:(r?.response||r?.choices?.[0]?.message?.content||JSON.stringify(r)); const m=String(text).match(/\{[\s\S]*\}/);
    try { const x=JSON.parse(m?.[0]||'{}'); return {status:x.status||'ok',summary:x.summary||'Optional model source returned evidence.',finalAnswer:x.finalAnswer,newNeeds:x.newNeeds,evidence:{model,raw:safe(text,8000)}}; }
    catch { return {status:'ok',summary:'Optional model source returned unstructured evidence.',evidence:{model,raw:safe(text,8000)}}; }
  }
  return {status:'blocked',reason:`UNKNOWN_PROVIDER:${p.id}`};
}

async function githubCheckpoint(env, mission, evt){
  if(!env.GITHUB_TOKEN||!env.BRAIN_REPO) return {skipped:true};
  const path=`canonical/runtime-events-v2/${mission.missionId}/${String(mission.generation).padStart(4,'0')}-${String(mission.cycle).padStart(6,'0')}.json`;
  const body=JSON.stringify({schema:'PROJECT_BRAIN_SUPERHERO_RUNTIME_EVENT_V2',agent_id:AGENT_ID,mission,event:evt},null,2)+'\n';
  const r=await fetch(`https://api.github.com/repos/${env.BRAIN_REPO}/contents/${path}`,{method:'PUT',headers:{authorization:`Bearer ${env.GITHUB_TOKEN}`,accept:'application/vnd.github+json','content-type':'application/json','user-agent':'ProjectBrain-Superhero/2.0'},body:JSON.stringify({message:`superhero v2 checkpoint ${mission.missionId} g${mission.generation} c${mission.cycle}`,content:btoa(unescape(encodeURIComponent(body))),branch:'main'})});
  return {status:r.status,ok:r.ok};
}

export class SuperheroWorkflow extends WorkflowEntrypoint {
  async run(event, step){
    const id=event.payload.missionId; const state=stub(this.env); const max=Math.min(Number(this.env.MAX_CYCLES_PER_GENERATION||'400'),400);
    for(let i=0;i<max;i++){
      const snapshot=await step.do(`load-${i}`,async()=>{const m=await state.get(id); if(!m) throw new Error('MISSION_NOT_FOUND'); return m;});
      if(['COMPLETE','FAILED','BLOCKED'].includes(snapshot.status)) return snapshot;
      const decision=selectProvider(snapshot,providers(this.env));
      if(decision.type==='blocked'){
        const m=appendKernelEvent(snapshot,'MISSION_BLOCKED',{reason:decision.reason}); m.status='BLOCKED'; m.summary=decision.reason; await state.put(m); await state.event(id,'MISSION_BLOCKED',{reason:decision.reason}); return m;
      }
      if(decision.type==='idle') return snapshot;
      const started=beginDispatch(snapshot,decision); await state.put(started); await state.event(id,'PROVIDER_SELECTED',{needId:decision.need.id,providerId:decision.provider.id,score:decision.score});
      const result=await step.do(`dispatch-${i}`,{retries:{limit:2,delay:'10 seconds',backoff:'exponential'}},async()=>dispatch(this.env,decision.provider,decision.need,started));
      const next=applyProviderResult(started,decision.need.id,decision.provider,result); await state.put(next); await state.event(id,'PROVIDER_RESULT',{needId:decision.need.id,providerId:decision.provider.id,status:result.status||'ok'});
      if(next.cycle%10===0 || ['COMPLETE','BLOCKED','FAILED'].includes(next.status)) await step.do(`checkpoint-${i}`,async()=>githubCheckpoint(this.env,next,{type:'STATE_CHECKPOINT'}));
      if(['COMPLETE','BLOCKED','FAILED'].includes(next.status)) return next;
    }
    const current=await state.get(id); if(!current||['COMPLETE','BLOCKED','FAILED'].includes(current.status)) return current;
    const next=rollGeneration(current); await state.put(next); await state.event(id,'GENERATION_ROLLOVER',{generation:next.generation});
    const instance=await this.env.SUPERHERO_LOOP.create({id:`${id}-g${next.generation}`,params:{missionId:id,generation:next.generation}});
    return {rollover:true,missionId:id,generation:next.generation,nextInstanceId:instance.id};
  }
}

export default { async fetch(req,env){
  if(!auth(req,env)) return j({error:'UNAUTHORIZED'},401); const u=new URL(req.url); const state=stub(env);
  if(req.method==='POST'&&u.pathname==='/missions'){
    const b=await req.json(); const goal=safe(b?.goal,20000).trim(); if(!goal)return j({error:'GOAL_REQUIRED'},400); const id=safe(b?.missionId||crypto.randomUUID(),120);
    const m=await state.create(id,goal,Array.isArray(b?.frontier)?b.frontier:[]); const instance=await env.SUPERHERO_LOOP.create({id:`${id}-g0`,params:{missionId:id,generation:0}}); return j({agentId:AGENT_ID,mission:m,workflowInstanceId:instance.id},202);
  }
  const mm=u.pathname.match(/^\/missions\/([^/]+)$/); if(req.method==='GET'&&mm){const m=await state.get(mm[1]); return m?j({agentId:AGENT_ID,mission:m,events:await state.events(mm[1])}):j({error:'NOT_FOUND'},404);}
  if(req.method==='GET'&&u.pathname==='/health')return j({ok:true,agentId:AGENT_ID,kernel:'MODEL_INDEPENDENT',modelsRole:'OPTIONAL_PROVIDER_ONLY',fullAstraClaim:false,superworkerRealClaim:false});
  return j({agentId:AGENT_ID,endpoints:{createMission:'POST /missions',mission:'GET /missions/:id',health:'GET /health'}});
}};
