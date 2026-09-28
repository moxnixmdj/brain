#!/usr/bin/env node
"use strict";
const fs=require("fs");
const path=require("path");
const {pathToFileURL}=require("url");

async function loadPackage(root){
  try { return {module:require(root), loader:"require"}; }
  catch(first){
    const pkg=JSON.parse(fs.readFileSync(path.join(root,"package.json"),"utf8"));
    const entries=[];
    const add=(x)=>{ if(typeof x==="string" && x) entries.push(x); };
    const exp=pkg.exports;
    if(typeof exp==="string") add(exp);
    else if(exp && typeof exp==="object"){
      const dot=exp["."] || exp;
      if(typeof dot==="string") add(dot);
      else if(dot && typeof dot==="object"){
        add(dot.import); add(dot.require); add(dot.default); add(dot.node);
      }
    }
    add(pkg.module); add(pkg.main); add("index.js");
    for(const rel of [...new Set(entries)]){
      try{
        const full=path.resolve(root,rel);
        return {module:await import(pathToFileURL(full).href),loader:"import:"+rel};
      }catch(_){}
    }
    throw first;
  }
}
function rootObject(mod,selector){
  if(selector==="default") return mod && mod.default;
  return mod;
}
function resolveExport(obj,name){
  let cur=obj;
  for(const part of String(name||"").split(".").filter(Boolean)){
    if(cur==null || !(part in Object(cur))) throw new Error("EXPORT_NOT_FOUND:"+name);
    cur=cur[part];
  }
  if(typeof cur!=="function") throw new Error("EXPORT_NOT_CALLABLE:"+name);
  return cur;
}
function toBuffer(value){
  if(Buffer.isBuffer(value)) return value;
  if(value instanceof ArrayBuffer) return Buffer.from(value);
  if(ArrayBuffer.isView(value)) return Buffer.from(value.buffer,value.byteOffset,value.byteLength);
  throw new Error("ENCODER_DID_NOT_RETURN_BYTES");
}
function normalizeSemantic(value){
  if(value instanceof Map){
    const out={};
    for(const [k,v] of value.entries()) out[String(k)]=normalizeSemantic(v);
    return out;
  }
  if(Array.isArray(value)) return value.map(normalizeSemantic);
  if(value && typeof value==="object"){
    if(Buffer.isBuffer(value) || value instanceof ArrayBuffer || ArrayBuffer.isView(value)) return value;
    const out={};
    for(const [k,v] of Object.entries(value)) out[k]=normalizeSemantic(v);
    return out;
  }
  return value;
}
function semanticallyEqual(a,b){
  return JSON.stringify(normalizeSemantic(a))===JSON.stringify(normalizeSemantic(b));
}
function semanticDecodeProjection(observed,expected,byteLength){
  if(semanticallyEqual(observed,expected)) return "direct";
  if(
    Array.isArray(observed) &&
    observed.length===2 &&
    Number.isInteger(observed[1]) &&
    observed[1]===byteLength &&
    semanticallyEqual(observed[0],expected)
  ) return "tuple_value_full_consumption";
  return null;
}

async function main(){
  const cfg=JSON.parse(fs.readFileSync(0,"utf8"));
  const loaded=await loadPackage(cfg.package_root);
  const roots=[["module",loaded.module]];
  if(loaded.module && loaded.module.default) roots.push(["default",loaded.module.default]);
  if(cfg.mode==="probe"){
    const fixture=JSON.parse(fs.readFileSync(cfg.json_path,"utf8"));
    const pairs=[["encode","decode"],["pack","unpack"],["serialize","deserialize"]];
    for(const [selector,obj] of roots){
      for(const [encName,decName] of pairs){
        try{
          const enc=resolveExport(obj,encName), dec=resolveExport(obj,decName);
          const bytes=toBuffer(await enc(fixture));
          if(!bytes.length) continue;
          const observed=await dec(bytes);
          const decodeProjection=semanticDecodeProjection(observed,fixture,bytes.length);
          if(decodeProjection){
            process.stdout.write(JSON.stringify({
              ok:true,root_selector:selector,encode_export:encName,decode_export:decName,
              loader:loaded.loader,probe_output_bytes:bytes.length,
              decode_projection:decodeProjection
            }));
            return;
          }
        }catch(_){}
      }
    }
    throw new Error("NO_COMPATIBLE_NODE_CODEC_CONTRACT");
  }
  const obj=rootObject(loaded.module,cfg.root_selector||"module");
  if(cfg.mode==="probe_decode"){
    const expected=JSON.parse(fs.readFileSync(cfg.json_path,"utf8"));
    const bytes=fs.readFileSync(cfg.binary_path);
    const decodeNames=["decode","unpack","deserialize","loads","unpackb"];
    for(const [selector,obj] of roots){
      for(const decName of decodeNames){
        try{
          const dec=resolveExport(obj,decName);
          const observed=await dec(bytes);
          const decodeProjection=semanticDecodeProjection(observed,expected,bytes.length);
          if(decodeProjection){
            process.stdout.write(JSON.stringify({
              ok:true,root_selector:selector,decode_export:decName,
              loader:loaded.loader,decode_projection:decodeProjection
            }));
            return;
          }
        }catch(_){}
      }
    }
    throw new Error("NO_COMPATIBLE_NODE_DECODE_CONTRACT");
  }
  if(cfg.mode==="encode"){
    const fixture=JSON.parse(fs.readFileSync(cfg.json_path,"utf8"));
    const enc=resolveExport(obj,cfg.encode_export);
    const bytes=toBuffer(await enc(fixture));
    if(!bytes.length) throw new Error("NODE_CODEC_OUTPUT_EMPTY");
    fs.writeFileSync(cfg.output_path,bytes);
    process.stdout.write(JSON.stringify({ok:true,output_bytes:bytes.length,loader:loaded.loader}));
    return;
  }
  if(cfg.mode==="decode"){
    const dec=resolveExport(obj,cfg.decode_export);
    const bytes=fs.readFileSync(cfg.binary_path);
    const observed=await dec(bytes);
    process.stdout.write(JSON.stringify({ok:true,observed,loader:loaded.loader}));
    return;
  }
  throw new Error("NODE_CODEC_MODE_UNSUPPORTED:"+cfg.mode);
}
main().catch(err=>{ console.error(String(err && err.stack || err)); process.exit(1); });
