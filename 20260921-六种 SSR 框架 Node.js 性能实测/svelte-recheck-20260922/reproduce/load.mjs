import http from 'node:http';
import {Worker,isMainThread,parentPort,workerData} from 'node:worker_threads';
import {performance,monitorEventLoopDelay} from 'node:perf_hooks';
import {writeFileSync} from 'node:fs';
import metrics from './metrics.cjs';
const stats=a=>{if(!a.length)return {count:0};a.sort((a,b)=>a-b);const q=p=>a[Math.min(a.length-1,Math.ceil(a.length*p)-1)];return {count:a.length,mean:a.reduce((a,b)=>a+b,0)/a.length,p50:q(.5),p95:q(.95),p99:q(.99),max:a.at(-1),min:a[0]}};
if(!isMainThread){
  const {target,connections,size,delay,id,minBytes,maxBytes}=workerData;
  const agent=new http.Agent({keepAlive:true,maxSockets:connections});
  const lat=[],ttfb=[],sizes=[],status={},errors={},invalid=[];let issued=0,complete=0,good=0,totalBytes=0,deadline;
  const h=monitorEventLoopDelay({resolution:10});h.enable();
  async function request(){const rid=`r${id}-${String(issued++).padStart(9,'0')}`;const start=performance.now();return new Promise(resolve=>{
    let done=false;const fail=e=>{if(done)return;done=true;errors[e]=(errors[e]||0)+1;resolve()};
    const req=http.get(`${target}/?size=${size}&delay=${delay}&rid=${rid}`,{agent,headers:{'accept-encoding':'identity','user-agent':'ssrbench/1.0','accept':'text/html'}},res=>{
      let bytes=0,first=true,tail='',hasEnd=false,hasRid=false;
      res.on('data',b=>{if(first){ttfb.push(performance.now()-start);first=false}bytes+=b.length;const s=tail+b.toString();if(s.includes('BENCH_END'))hasEnd=true;if(s.includes(rid))hasRid=true;tail=s.slice(-100)});
      res.on('end',()=>{if(done)return;done=true;complete++;status[res.statusCode]=(status[res.statusCode]||0)+1;lat.push(performance.now()-start);sizes.push(bytes);totalBytes+=bytes;
        if(res.statusCode===200&&hasEnd&&hasRid&&bytes>=minBytes&&bytes<=maxBytes)good++;else if(invalid.length<5)invalid.push({status:res.statusCode,bytes,hasEnd,hasRid});resolve()});
      res.on('error',e=>fail(e.code||e.message));res.on('aborted',()=>fail('aborted'));
    });req.setTimeout(30000,()=>req.destroy(new Error('timeout')));req.on('error',e=>fail(e.code||e.message));
  })}
  parentPort.on('message',async m=>{if(m.start){deadline=m.deadline;h.reset();await Promise.all(Array.from({length:connections},async()=>{while(Date.now()<deadline)await request()}));agent.destroy();parentPort.postMessage({issued,complete,good,totalBytes,lat,ttfb,sizes,status,errors,invalid,eventLoopP99Ms:h.percentile(99)/1e6});}});
  parentPort.postMessage({ready:true});
}else{
  const config=JSON.parse(process.argv[2]);
  const {target='http://ssrbench-app:3000',connections=16,size='hello',delay=50,seconds=10,out,minBytes=1,maxBytes=2000000,measure=true}=config;
  const count=Math.min(4,connections),workers=[];
  for(let i=0;i<count;i++)workers.push(new Worker(new URL(import.meta.url),{workerData:{target,connections:Math.floor(connections/count)+(i<connections%count?1:0),size,delay,id:i,minBytes,maxBytes}}));
  await Promise.all(workers.map(w=>new Promise((r,j)=>{w.once('message',r);w.once('error',j)})));
  const get=async(url)=>{const r=await fetch(url);if(!r.ok)throw new Error(`${url}: ${r.status}`);return r.json()};
  if(measure){await get('http://ssrbench-app:9100/reset');await get('http://ssrbench-backend:9100/reset');await get('http://ssrbench-backend:4000/reset');}
  metrics.reset();const t=performance.now(),dateStart=new Date().toISOString();
  const promises=workers.map(w=>new Promise((r,j)=>{w.once('message',r);w.once('error',j)}));
  for(const w of workers)w.postMessage({start:true,deadline:Date.now()+seconds*1000});
  const results=await Promise.all(promises);const elapsed=(performance.now()-t)/1000,load=metrics.summary();
  const sum=k=>results.reduce((n,r)=>n+r[k],0),merge=k=>results.reduce((a,r)=>{for(const [key,v]of Object.entries(r[k]))a[key]=(a[key]||0)+v;return a},{});
  const result={...config,dateStart,elapsedSeconds:elapsed,issued:sum('issued'),complete:sum('complete'),good:sum('good'),rps:sum('complete')/elapsed,goodput:sum('good')/elapsed,totalBytes:sum('totalBytes'),bytesPerSecond:sum('totalBytes')/elapsed,latencyMs:stats(results.flatMap(r=>r.lat)),ttfbMs:stats(results.flatMap(r=>r.ttfb)),responseBytes:stats(results.flatMap(r=>r.sizes)),statuses:merge('status'),errors:merge('errors'),invalid:results.flatMap(r=>r.invalid),load:{...load,workerEventLoopP99Ms:results.map(r=>r.eventLoopP99Ms)}};
  if(measure){result.app=await get('http://ssrbench-app:9100/');result.backend=await get('http://ssrbench-backend:9100/');const b=await get('http://ssrbench-backend:4000/stats');result.backendRequests={...b,durations:stats(b.durations)};}
  if(out)writeFileSync(out,JSON.stringify(result));
  console.log(JSON.stringify({size,delay,connections,seconds,elapsed,good:result.good,rps:result.rps,p95:result.latencyMs.p95,errors:result.errors,invalid:result.invalid,backendCalls:result.backendRequests?.calls}));
  await Promise.all(workers.map(w=>w.terminate()));
}
