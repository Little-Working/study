import http from 'node:http';
import {Worker,isMainThread,parentPort,workerData} from 'node:worker_threads';
import {performance} from 'node:perf_hooks';
import {writeFileSync,readdirSync} from 'node:fs';
const stamp=()=>Number(process.hrtime.bigint())/1e6;
const stats=a=>{if(!a.length)return {count:0};a.sort((a,b)=>a-b);const q=p=>a[Math.min(a.length-1,Math.ceil(p*a.length)-1)];return {count:a.length,mean:a.reduce((s,v)=>s+v,0)/a.length,min:a[0],max:a.at(-1),p50:q(.5),p75:q(.75),p90:q(.90),p95:q(.95),p99:q(.99)};};
if(!isMainThread){
 const {id,connections,size,delay,minBytes,maxBytes,sampleEvery}=workerData;
 const agent=new http.Agent({keepAlive:true,maxSockets:connections});
 let issued=0,complete=0,good=0,bytesTotal=0,byteMin=Infinity,byteMax=0,firstStart=Infinity,lastEnd=0,deadline;
 const latency=[],ttfb=[],errors={},invalid=[],statuses={};let sampled=0,sampleInvalid=0;
 async function request(){
  const n=issued++,rid=`w${id}${String(n).padStart(18,'0')}`,sample=sampleEvery>0&&n%sampleEvery===0;
  const start=stamp();firstStart=Math.min(firstStart,start);
  return new Promise(resolve=>{
   let done=false;
   const fail=e=>{if(done)return;done=true;lastEnd=Math.max(lastEnd,stamp());errors[e]=(errors[e]||0)+1;resolve();};
   const req=http.get(`http://ssrbench3-app:3000/?size=${size}&delay=${delay}&rid=${rid}`,{agent,headers:{'accept':'text/html','accept-encoding':'identity','user-agent':'ssrbench-runtime/1.0'}},res=>{
    let bytes=0,first=true;const chunks=sample?[]:null;
    res.on('data',chunk=>{if(first){ttfb.push(stamp()-start);first=false;}bytes+=chunk.length;if(sample)chunks.push(chunk);});
    res.on('end',()=>{
     if(done)return;done=true;const end=stamp();lastEnd=Math.max(lastEnd,end);latency.push(end-start);complete++;
     bytesTotal+=bytes;byteMin=Math.min(byteMin,bytes);byteMax=Math.max(byteMax,bytes);statuses[res.statusCode]=(statuses[res.statusCode]||0)+1;
     let valid=res.statusCode===200&&bytes>=minBytes&&bytes<=maxBytes&&!res.headers.etag&&!res.headers['content-encoding'];
     if(sample){sampled++;const body=Buffer.concat(chunks);if(!body.includes(Buffer.from(rid))||!body.includes(Buffer.from('BENCH_END'))){valid=false;sampleInvalid++;}}
     if(valid)good++;else if(invalid.length<8)invalid.push({status:res.statusCode,bytes,etag:res.headers.etag,encoding:res.headers['content-encoding'],sample});
     resolve();
    });res.on('error',e=>fail(e.code||e.message));res.on('aborted',()=>fail('aborted'));
   });req.setTimeout(30000,()=>req.destroy(Error('timeout')));req.on('error',e=>fail(e.code||e.message));
  });
 }
 parentPort.on('message',async m=>{
  if(!m.start)return;deadline=m.deadline;const cpu=process.cpuUsage(),elu=performance.eventLoopUtilization();
  await Promise.all(Array.from({length:connections},async()=>{while(Date.now()<deadline)await request();}));
  const u=performance.eventLoopUtilization(elu);agent.destroy();
  parentPort.postMessage({issued,complete,good,bytesTotal,byteMin,byteMax,firstStart,lastEnd,latency,ttfb,errors,invalid,statuses,sampled,sampleInvalid,eluPct:u.utilization*100});
 });parentPort.postMessage({ready:true});
}else{
 const config=JSON.parse(process.argv[2]);
 // Adopted after client controls, before the first formal matrix window.
 // Content checks live in independent acceptance tests, not formal timing.
 if(config.phase==='matrix'||config.phase==='focus')config.sampleEvery=0;
 // The focus phase follows all 324 matrix files. Extend every fresh-process
 // focus warmup consistently, including with the already-running controller.
 const {connections=64,size='large',delay=50,seconds=10,minBytes=1,maxBytes=2000000,workers:requestedWorkers=4,sampleEvery=128,measure=true,out}=config;
 const count=Math.min(connections,requestedWorkers),workers=[];
 for(let i=0;i<count;i++)workers.push(new Worker(new URL(import.meta.url),{workerData:{id:i,connections:Math.floor(connections/count)+(i<connections%count?1:0),size,delay,minBytes,maxBytes,sampleEvery}}));
 await Promise.all(workers.map(w=>new Promise((r,j)=>{w.once('message',r);w.once('error',j)})));
 const get=async url=>{const response=await fetch(url);if(!response.ok)throw Error(`${url} ${response.status}`);return response.json();};
 if(measure){await get('http://ssrbench3-app:9100/reset');await get('http://ssrbench3-backend:9100/reset');await get('http://ssrbench3-backend:4000/reset');}
 const start=stamp(),cpuStart=process.cpuUsage();
 const promises=workers.map(w=>new Promise((r,j)=>{w.once('message',r);w.once('error',j)}));
 const deadline=Date.now()+seconds*1000;for(const w of workers)w.postMessage({start:true,deadline});
 const results=await Promise.all(promises),cpu=process.cpuUsage(cpuStart);
 // Snapshot application before quantile sorting/report serialization.
 let app,backend,backendRequests;
 if(measure){app=await get('http://ssrbench3-app:9100/stop');backend=await get('http://ssrbench3-backend:9100/stop');backendRequests=await get('http://ssrbench3-backend:4000/stats');}
 const first=Math.min(...results.map(r=>r.firstStart)),last=Math.max(...results.map(r=>r.lastEnd)),elapsedSeconds=(last-first)/1000;
 const sum=k=>results.reduce((s,r)=>s+r[k],0),merge=k=>results.reduce((a,r)=>{for(const [key,v]of Object.entries(r[k]))a[key]=(a[key]||0)+v;return a;},{});
 const result={...config,workers:count,sampleEvery,dateEnd:new Date().toISOString(),elapsedSeconds,dispatchMs:first-start,issued:sum('issued'),complete:sum('complete'),good:sum('good'),rps:sum('good')/elapsedSeconds,bytes:sum('bytesTotal'),responseBytes:{min:Math.min(...results.map(r=>r.byteMin)),max:Math.max(...results.map(r=>r.byteMax)),mean:sum('bytesTotal')/sum('complete')},latencyMs:stats(results.flatMap(r=>r.latency)),firstBodyMs:stats(results.flatMap(r=>r.ttfb)),statuses:merge('statuses'),errors:merge('errors'),invalid:results.flatMap(r=>r.invalid),sampled:sum('sampled'),sampleInvalid:sum('sampleInvalid'),load:{cpuMs:(cpu.user+cpu.system)/1000,cpuPct:(cpu.user+cpu.system)/(elapsedSeconds*1e4),workerEluPct:results.map(r=>r.eluPct)},app,backend,backendRequests};
 if(out)writeFileSync(out,JSON.stringify(result));
 console.log(JSON.stringify({framework:config.framework,phase:config.phase,size,delay,connections,seconds,good:result.good,rps:result.rps,p50:result.latencyMs.p50,p95:result.latencyMs.p95,errors:result.errors,invalid:result.invalid,sampled:result.sampled}));
 await Promise.all(workers.map(w=>w.terminate()));
}
