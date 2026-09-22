// Same instrumentation preload for every production Node process.
const {monitorEventLoopDelay,performance,PerformanceObserver,constants}=require('node:perf_hooks');
const http=require('node:http');
const fs=require('node:fs');
const h=monitorEventLoopDelay({resolution:10});h.enable();
const read=(path)=>{try{return fs.readFileSync(path,'utf8')}catch{return null}};
const kv=(path)=>Object.fromEntries((read(path)||'').trim().split('\n').filter(Boolean).map(x=>{const [k,v]=x.split(/\s+/);return [k,Number(v)]}));
const cg=()=>({cpu:kv('/sys/fs/cgroup/cpu.stat'),memory:Number(read('/sys/fs/cgroup/memory.current'))||null,events:kv('/sys/fs/cgroup/memory.events')});
let start,cpu,elu,base,gc,samples;
function reset(){h.reset();start=performance.now();cpu=process.cpuUsage();elu=performance.eventLoopUtilization();base=cg();gc=[];samples=[{t:0,...process.memoryUsage(),cgroup:base.memory}];}
const observer=new PerformanceObserver(list=>{for(const e of list.getEntries()) if(e.startTime>=start)gc.push({kind:e.detail.kind,ms:e.duration})});observer.observe({entryTypes:['gc']});
function quantile(a,p){if(!a.length)return null;const s=[...a].sort((a,b)=>a-b);return s[Math.min(s.length-1,Math.ceil(s.length*p)-1)]}
reset();setInterval(()=>samples.push({t:performance.now()-start,...process.memoryUsage(),cgroup:cg().memory}),200).unref();
function summary(){const wall=performance.now()-start,c=process.cpuUsage(cpu),end=cg(),u=performance.eventLoopUtilization(elu);const total=gc.reduce((n,g)=>n+g.ms,0);const kinds={};for(const g of gc){const k=Object.entries(constants).find(([k,v])=>k.startsWith('NODE_PERFORMANCE_GC_')&&!k.includes('FLAGS')&&v===g.kind)?.[0]||g.kind;kinds[k]??={count:0,durationMs:0};kinds[k].count++;kinds[k].durationMs+=g.ms;}return {pid:process.pid,node:process.version,wallMs:wall,cpuMs:(c.user+c.system)/1000,cpuPct:(c.user+c.system)/wall/10,eventLoop:{utilization:u.utilization,p50Ms:h.percentile(50)/1e6,p95Ms:h.percentile(95)/1e6,p99Ms:h.percentile(99)/1e6,maxMs:h.max/1e6,meanMs:Number.isFinite(h.mean)?h.mean/1e6:null},gc:{count:gc.length,totalMs:total,maxMs:gc.length?Math.max(...gc.map(g=>g.ms)):0,p95Ms:quantile(gc.map(g=>g.ms),.95),observedDurationPct:total/wall*100,kinds},memory:{rssStart:samples[0].rss,rssEnd:process.memoryUsage().rss,rssPeak:Math.max(...samples.map(s=>s.rss)),heapUsedStart:samples[0].heapUsed,heapUsedEnd:process.memoryUsage().heapUsed,heapUsedPeak:Math.max(...samples.map(s=>s.heapUsed)),cgroupPeak:Math.max(...samples.map(s=>s.cgroup||0))},cgroup:{cpuUsec:(end.cpu.usage_usec||0)-(base.cpu.usage_usec||0),throttledUsec:(end.cpu.throttled_usec||0)-(base.cpu.throttled_usec||0),nrThrottled:(end.cpu.nr_throttled||0)-(base.cpu.nr_throttled||0),memoryEventsStart:base.events,memoryEventsEnd:end.events},samples};}
if(process.env.BENCH_METRICS_PORT)http.createServer((req,res)=>{res.setHeader('content-type','application/json');if(req.url==='/reset'){reset();res.end('{"ok":true}')}else res.end(JSON.stringify(summary()))}).listen(Number(process.env.BENCH_METRICS_PORT),'0.0.0.0');
module.exports={reset,summary};
