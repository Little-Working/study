// No filesystem reads or per-request hooks. Identical lean instrumentation for each app.
const http=require('node:http');
const {performance,monitorEventLoopDelay,PerformanceObserver}=require('node:perf_hooks');
const enabled=process.env.BENCH_METRICS_MODE!=='off';
const delay=enabled?monitorEventLoopDelay({resolution:20}):null;
delay?.enable();
let start,cpu,elu,gc,samples,memorySampleCostMs;
function memorySample(){const t=performance.now();const m=process.memoryUsage();samples.push({t:performance.now()-start,rss:m.rss,heapUsed:m.heapUsed,external:m.external});memorySampleCostMs+=performance.now()-t;}
function reset(){start=performance.now();cpu=process.cpuUsage();elu=performance.eventLoopUtilization();gc={count:0,totalMs:0,maxMs:0,kinds:{}};samples=[];memorySampleCostMs=0;delay?.reset();memorySample();}
reset();
if(enabled){
 new PerformanceObserver(list=>{for(const e of list.getEntries())if(e.startTime>=start){const k=e.detail.kind;gc.count++;gc.totalMs+=e.duration;gc.maxMs=Math.max(gc.maxMs,e.duration);gc.kinds[k]??={count:0,totalMs:0};gc.kinds[k].count++;gc.kinds[k].totalMs+=e.duration;}}).observe({entryTypes:['gc']});
 setInterval(memorySample,1000).unref();
}
function summary(){
 const end=performance.now(),c=process.cpuUsage(cpu),u=performance.eventLoopUtilization(elu),m=process.memoryUsage();
 return {mode:enabled?'lean':'off',node:process.version,pid:process.pid,wallMs:end-start,cpuMs:(c.user+c.system)/1000,cpuPct:(c.user+c.system)/(end-start)/10,eluPct:u.utilization*100,eventLoop:delay?{p50Ms:delay.percentile(50)/1e6,p95Ms:delay.percentile(95)/1e6,p99Ms:delay.percentile(99)/1e6,maxMs:delay.max/1e6}:null,gc:enabled?{...gc,observedPct:100*gc.totalMs/(end-start)}:null,memory:{rssStart:samples[0].rss,rssEnd:m.rss,rssPeak:Math.max(m.rss,...samples.map(s=>s.rss)),heapPeak:Math.max(m.heapUsed,...samples.map(s=>s.heapUsed)),externalPeak:Math.max(m.external,...samples.map(s=>s.external)),sampleCount:samples.length,memorySampleCostMs},samples:enabled?samples:undefined,audit:globalThis.__benchAudit||null};
}
http.createServer((req,res)=>{res.setHeader('content-type','application/json');if(req.url==='/reset'){reset();res.end('{"ok":true}')}else res.end(JSON.stringify(summary()));}).listen(9100,'0.0.0.0');
