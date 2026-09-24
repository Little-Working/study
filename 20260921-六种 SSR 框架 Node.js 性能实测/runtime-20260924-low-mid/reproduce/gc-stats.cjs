const PERCENTILES=[50,75,90,95,99];
const KINDS={1:'minor',4:'major',8:'incremental',16:'weakcb'};
function stats(values){
 if(!values.length)return {count:0,meanMs:null,totalMs:0,p50Ms:null,p75Ms:null,p90Ms:null,p95Ms:null,p99Ms:null,maxMs:null,p99Sparse:true};
 const a=Array.from(values).sort((x,y)=>x-y),total=a.reduce((s,v)=>s+v,0);
 const r={count:a.length,meanMs:total/a.length,totalMs:total,maxMs:a.at(-1),p99Sparse:a.length<100};
 for(const p of PERCENTILES)r[`p${p}Ms`]=a[Math.ceil(a.length*p/100)-1];
 return r;
}
function createRecorder(capacity=65536){
 const duration=new Float64Array(capacity),offset=new Float64Array(capacity),kind=new Uint8Array(capacity),flags=new Uint8Array(capacity);
 let count=0,dropped=0,start=Infinity,end=Infinity;
 return {
  reset(at){count=0;dropped=0;start=at;end=Infinity;},
  stop(at){end=at;},
  ingest(entries){for(const e of entries){if(e.startTime<start||e.startTime>=end)continue;if(count===capacity){dropped++;continue;}duration[count]=e.duration;offset[count]=e.startTime-start;kind[count]=e.detail.kind;flags[count]=e.detail.flags;count++;}},
  summary(){const groups={};for(const [id,name] of Object.entries(KINDS))groups[name]=stats(Array.from(duration.subarray(0,count)).filter((_,i)=>kind[i]===Number(id)));
   const unknown=[];for(let i=0;i<count;i++)if(!KINDS[kind[i]])unknown.push(duration[i]);if(unknown.length)groups.unknown=stats(unknown);
   return {...stats(duration.subarray(0,count)),dropped,kinds:groups,events:Array.from({length:count},(_,i)=>({offsetMs:offset[i],durationMs:duration[i],kind:kind[i],flags:flags[i]}))};}
 };
}
module.exports={PERCENTILES,KINDS,stats,createRecorder};
