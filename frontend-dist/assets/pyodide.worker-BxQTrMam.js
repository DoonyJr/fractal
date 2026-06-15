/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */const C=Symbol("Comlink.proxy"),z=Symbol("Comlink.endpoint"),L=Symbol("Comlink.releaseProxy"),k=Symbol("Comlink.finalizer"),w=Symbol("Comlink.thrown"),T=e=>typeof e=="object"&&e!==null||typeof e=="function",D={canHandle:e=>T(e)&&e[C],serialize(e){const{port1:t,port2:n}=new MessageChannel;return S(e,t),[n,[n]]},deserialize(e){return e.start(),W(e)}},V={canHandle:e=>T(e)&&w in e,serialize({value:e}){let t;return e instanceof Error?t={isError:!0,value:{message:e.message,name:e.name,stack:e.stack}}:t={isError:!1,value:e},[t,[]]},deserialize(e){throw e.isError?Object.assign(new Error(e.value.message),e.value):e.value}},M=new Map([["proxy",D],["throw",V]]);function H(e,t){for(const n of e)if(t===n||n==="*"||n instanceof RegExp&&n.test(t))return!0;return!1}function S(e,t=globalThis,n=["*"]){t.addEventListener("message",function f(r){if(!r||!r.data)return;if(!H(n,r.origin)){console.warn(`Invalid origin '${r.origin}' for comlink proxy`);return}const{id:o,type:_,path:c}=Object.assign({path:[]},r.data),l=(r.data.argumentList||[]).map(p);let a;try{const i=c.slice(0,-1).reduce((u,g)=>u[g],e),d=c.reduce((u,g)=>u[g],e);switch(_){case"GET":a=d;break;case"SET":i[c.slice(-1)[0]]=p(r.data.value),a=!0;break;case"APPLY":a=d.apply(i,l);break;case"CONSTRUCT":{const u=new d(...l);a=Y(u)}break;case"ENDPOINT":{const{port1:u,port2:g}=new MessageChannel;S(e,g),a=G(u,[u])}break;case"RELEASE":a=void 0;break;default:return}}catch(i){a={value:i,[w]:0}}Promise.resolve(a).catch(i=>({value:i,[w]:0})).then(i=>{const[d,u]=x(i);t.postMessage(Object.assign(Object.assign({},d),{id:o}),u),_==="RELEASE"&&(t.removeEventListener("message",f),O(t),k in e&&typeof e[k]=="function"&&e[k]())}).catch(i=>{const[d,u]=x({value:new TypeError("Unserializable return value"),[w]:0});t.postMessage(Object.assign(Object.assign({},d),{id:o}),u)})}),t.start&&t.start()}function I(e){return e.constructor.name==="MessagePort"}function O(e){I(e)&&e.close()}function W(e,t){const n=new Map;return e.addEventListener("message",function(r){const{data:o}=r;if(!o||!o.id)return;const _=n.get(o.id);if(_)try{_(o)}finally{n.delete(o.id)}}),j(e,n,[],t)}function h(e){if(e)throw new Error("Proxy has been released and is not useable")}function v(e){return y(e,new Map,{type:"RELEASE"}).then(()=>{O(e)})}const E=new WeakMap,P="FinalizationRegistry"in globalThis&&new FinalizationRegistry(e=>{const t=(E.get(e)||0)-1;E.set(e,t),t===0&&v(e)});function F(e,t){const n=(E.get(t)||0)+1;E.set(t,n),P&&P.register(e,t,e)}function U(e){P&&P.unregister(e)}function j(e,t,n=[],f=function(){}){let r=!1;const o=new Proxy(f,{get(_,c){if(h(r),c===L)return()=>{U(o),v(e),t.clear(),r=!0};if(c==="then"){if(n.length===0)return{then:()=>o};const l=y(e,t,{type:"GET",path:n.map(a=>a.toString())}).then(p);return l.then.bind(l)}return j(e,t,[...n,c])},set(_,c,l){h(r);const[a,i]=x(l);return y(e,t,{type:"SET",path:[...n,c].map(d=>d.toString()),value:a},i).then(p)},apply(_,c,l){h(r);const a=n[n.length-1];if(a===z)return y(e,t,{type:"ENDPOINT"}).then(p);if(a==="bind")return j(e,t,n.slice(0,-1));const[i,d]=R(l);return y(e,t,{type:"APPLY",path:n.map(u=>u.toString()),argumentList:i},d).then(p)},construct(_,c){h(r);const[l,a]=R(c);return y(e,t,{type:"CONSTRUCT",path:n.map(i=>i.toString()),argumentList:l},a).then(p)}});return F(o,e),o}function B(e){return Array.prototype.concat.apply([],e)}function R(e){const t=e.map(x);return[t.map(n=>n[0]),B(t.map(n=>n[1]))]}const N=new WeakMap;function G(e,t){return N.set(e,t),e}function Y(e){return Object.assign(e,{[C]:!0})}function x(e){for(const[t,n]of M)if(n.canHandle(e)){const[f,r]=n.serialize(e);return[{type:"HANDLER",name:t,value:f},r]}return[{type:"RAW",value:e},N.get(e)||[]]}function p(e){switch(e.type){case"HANDLER":return M.get(e.name).deserialize(e.value);case"RAW":return e.value}}function y(e,t,n,f){return new Promise(r=>{const o=$();t.set(o,r),e.start&&e.start(),e.postMessage(Object.assign({id:o},n),f)})}function $(){return new Array(4).fill(0).map(()=>Math.floor(Math.random()*Number.MAX_SAFE_INTEGER).toString(16)).join("-")}let s=null,m=null,b=null;const A=e=>(e&&!e.endsWith("/")?e+"/":e)||e;async function J(e){const n=await(await import(`${e}pyodide.mjs`)).loadPyodide({indexURL:e});return await n.loadPackage(["pandas","numpy"]),n}async function q(e={}){if(s)return{ok:!0};if(m)return m;const t=e.version||"0.25.0",n=`https://cdn.jsdelivr.net/pyodide/v${t}/full/`,f=`/assets/pyodide/v${t}/full/`,r=A(e.cdnBase||n),o=A(e.localBase||f),c=(e.preferCdn!==void 0?!!e.preferCdn:!0)?[r,o]:[o,r];return m=(async()=>{let l=null;for(const a of c)try{return s=await J(a),{ok:!0,baseUrl:a}}catch(i){l=i}throw b=l,m=null,l||new Error("Pyodide 初始化失败：所有候选源均不可用")})(),m}async function X(e=[]){if(!s)throw new Error("Pyodide 未初始化");e.length&&await s.loadPackage(e)}async function K(e,t={}){if(!s)throw new Error("Pyodide 未初始化");for(const[f,r]of Object.entries(t))s.globals.set(f,r);const n=await s.runPythonAsync(e);if(n&&typeof n=="object"&&typeof n.toJs=="function")try{return n.toJs()}finally{try{n.destroy()}catch{}}return n}const Q=`
import json
import pandas as pd
import numpy as np

def _clean_nan(obj):
    if isinstance(obj, dict):
        return {k: _clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_nan(item) for item in obj]
    if isinstance(obj, (pd.Series, np.ndarray)):
        return [None if (isinstance(x, float) and (np.isnan(x) or np.isinf(x))) else x for x in obj]
    if isinstance(obj, (float, np.floating)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    try:
        if pd.isna(obj):
            return None
    except (TypeError, ValueError):
        pass
    return obj


# raw_data / params / user_code 由 worker 通过 pyodide.globals.set 注入
_raw = raw_data.to_py() if hasattr(raw_data, 'to_py') else raw_data
_params = params.to_py() if hasattr(params, 'to_py') else params


def _get_param(key, default=None):
    if key in _params:
        return _params.get(key, default)
    camel = ''.join([key.split('_')[0]] + [p.capitalize() for p in key.split('_')[1:]])
    return _params.get(camel, default)


try:
    leverage = float(_get_param('leverage', 1) or 1)
except Exception:
    leverage = 1

trade_direction = _get_param('trade_direction', _get_param('tradeDirection', 'both')) or 'both'

def _safe_int(name, default=0):
    try:
        return int(_get_param(name, default) or default)
    except Exception:
        return default

def _safe_float(name, default=0.0):
    try:
        return float(_get_param(name, default) or default)
    except Exception:
        return default

initial_position = _safe_int('initial_position', 0)
initial_avg_entry_price = _safe_float('initial_avg_entry_price', 0.0)
initial_position_count = _safe_int('initial_position_count', 0)
initial_last_add_price = _safe_float('initial_last_add_price', 0.0)
initial_highest_price = _safe_float('initial_highest_price', 0.0)

df = pd.DataFrame(_raw)
for col in ('open', 'high', 'low', 'close', 'volume'):
    if col in df.columns:
        df[col] = df[col].astype(float)

_local_ns = {
    'df': df,
    'pd': pd,
    'np': np,
    'json': json,
    'leverage': leverage,
    'trade_direction': trade_direction,
    'initial_position': initial_position,
    'initial_avg_entry_price': initial_avg_entry_price,
    'initial_position_count': initial_position_count,
    'initial_last_add_price': initial_last_add_price,
    'initial_highest_price': initial_highest_price,
    'params': _params,
}

exec(user_code, _local_ns, _local_ns)

if 'output' not in _local_ns:
    if 'result_json' in _local_ns:
        output = json.loads(_local_ns['result_json'])
    else:
        output = {"plots": []}
else:
    output = _local_ns['output']
    if isinstance(output, str):
        output = json.loads(output)

output = _clean_nan(output)
json.dumps(output)
`;async function Z({userCode:e,rawData:t,params:n}){if(!s)throw new Error("Pyodide 未初始化");s.globals.set("user_code",e),s.globals.set("raw_data",t||[]),s.globals.set("params",n||{});try{return await s.runPythonAsync(Q)}finally{s.globals.set("user_code",""),s.globals.set("raw_data",null),s.globals.set("params",null)}}function ee(){return{ready:!!s,error:b?String(b.message||b):null}}S({init:q,runPython:K,runStrategy:Z,loadPackages:X,status:ee});
