// Same monitor for every app. No per-request hooks, filesystem reads or GC forcing.
const http=require('node:http');
const {performance,monitorEventLoopDelay,PerformanceObserver}=require('node:perf_hooks');
const {createRecorder,PERCENTILES}=require('./gc-stats.cjs');
const enabled=process.env.BENCH_METRICS_MODE!=='off',resolutionMs=10;
const delay=enabled?monitorEventLoopDelay({resolution:resolutionMs}):null;
const recorder=createRecorder();
const observer=enabled?new PerformanceObserver(list=>recorder.ingest(list.getEntries())):null;
observer?.observe({entryTypes:['gc']});
let start=0,cpu,elu,samples=[],memorySampleCostMs=0,active=false,frozen=null;
function memorySample(){if(!active)return;const t=performance.now(),m=process.memoryUsage();samples.push({t:t-start,...m});memorySampleCostMs+=performance.now()-t;}
function reset(){active=false;delay?.disable();observer?.takeRecords();samples=[];memorySampleCostMs=0;frozen=null;start=performance.now();recorder.reset(start);cpu=process.cpuUsage();elu=performance.eventLoopUtilization();delay?.reset();delay?.enable();active=true;memorySample();}
if(enabled)setInterval(memorySample,1000).unref();
async function stop(){
 if(frozen)return frozen;
 if(!active)return {mode:enabled?'lean':'off',audit:globalThis.__benchAudit||null,active:false};
 const end=performance.now(),c=process.cpuUsage(cpu),u=performance.eventLoopUtilization(elu),m=process.memoryUsage();
 active=false;recorder.stop(end);delay?.disable();
 const eventLoop=delay?{count:Number(delay.count),resolutionMs,minMs:delay.count?delay.min/1e6:null,maxMs:delay.count?delay.max/1e6:null,meanMs:delay.count?delay.mean/1e6:null}:null;
 if(delay)for(const p of PERCENTILES)eventLoop[`p${p}Ms`]=delay.count?delay.percentile(p)/1e6:null;
 // Drain queued GC entries after fixing the time boundary; exclude stop/report GC.
 if(observer){recorder.ingest(observer.takeRecords());await new Promise(setImmediate);await new Promise(setImmediate);recorder.ingest(observer.takeRecords());}
 const gc=enabled?recorder.summary():null;
 if(gc)gc.observedPct=100*gc.totalMs/(end-start);
 frozen={mode:enabled?'lean':'off',node:process.version,pid:process.pid,wallMs:end-start,cpuMs:(c.user+c.system)/1000,cpuPct:(c.user+c.system)/(end-start)/10,eluPct:u.utilization*100,eventLoop,gc,memory:{rssStart:samples[0]?.rss??m.rss,rssEnd:m.rss,rssPeak:Math.max(m.rss,...samples.map(s=>s.rss)),heapPeak:Math.max(m.heapUsed,...samples.map(s=>s.heapUsed)),externalPeak:Math.max(m.external,...samples.map(s=>s.external)),arrayBuffersPeak:Math.max(m.arrayBuffers,...samples.map(s=>s.arrayBuffers)),sampleCount:samples.length,memorySampleCostMs},samples:enabled?samples:undefined,audit:globalThis.__benchAudit||null};
 return frozen;
}
http.createServer(async(req,res)=>{res.setHeader('content-type','application/json');try{if(req.url==='/reset'){reset();res.end('{"ok":true}');}else if(req.url==='/stop'){res.end(JSON.stringify(await stop()));}else{res.end(JSON.stringify({active,mode:enabled?'lean':'off',audit:globalThis.__benchAudit||null}));}}catch(e){res.statusCode=500;res.end(JSON.stringify({error:e.message}));}}).listen(9100,'0.0.0.0');
