import http from 'node:http';
import {performance} from 'node:perf_hooks';
const RID='00000000000000000000';
const sizes={hello:{count:0,target:0},medium:{count:800,target:320000},large:{count:1536,target:600000}};
const fixtures={};
for(const [size,{count,target}] of Object.entries(sizes)) {
 const items=Array.from({length:count},(_,i)=>({id:i,title:`Product ${String(i).padStart(5,'0')}`,description:'',price:((i%100)+.99).toFixed(2)}));
 let data={rid:RID,items};
 if(count){
  const remaining=target-Buffer.byteLength(JSON.stringify(data));
  const len=Math.floor(remaining/count),extra=remaining-len*count;
  for(let i=0;i<count;i++){
   const prefix=`sku-${String(i).padStart(6,'0')}-`;
   items[i].description=(prefix+'abcdefghijklmnopqrstuvwxyz0123456789'.repeat(40)).slice(0,len+(i<extra?1:0));
  }
 }
 const raw=JSON.stringify(data),bytes=Buffer.byteLength(raw);
 if(target&&bytes!==target)throw Error(`${size} ${bytes} != ${target}`);
 const pos=raw.indexOf(RID);
 fixtures[size]={prefix:Buffer.from(raw.slice(0,pos)),suffix:Buffer.from(raw.slice(pos+RID.length)),bytes,count};
}
let calls=0,completed=0,inflight=0,maxInflight=0,totalBytes=0,waitSum=0,waitMax=0,delays={};
http.createServer(async(req,res)=>{
 const p=new URL(req.url,'http://localhost');
 res.setHeader('content-type','application/json');res.setHeader('cache-control','no-store');
 if(p.pathname==='/stats'){res.end(JSON.stringify({calls,completed,inflight,maxInflight,totalBytes,waitMeanMs:calls?waitSum/calls:0,waitMaxMs:waitMax,delays}));return;}
 if(p.pathname==='/fixtures'){res.end(JSON.stringify(Object.fromEntries(Object.entries(fixtures).map(([k,v])=>[k,{bytes:v.bytes,count:v.count}]))));return;}
 if(p.pathname==='/reset'){if(inflight){res.statusCode=409;res.end('{}');return;}calls=completed=maxInflight=totalBytes=waitSum=waitMax=0;delays={};res.end('{}');return;}
 if(p.pathname!=='/data'){res.statusCode=404;res.end('{}');return;}
 const size=p.searchParams.get('size')||'hello',f=fixtures[size];
 if(!f){res.statusCode=400;res.end('{}');return;}
 const delay=Math.max(50,Math.min(500,Number(p.searchParams.get('delay')||50)));
 const rid=(p.searchParams.get('rid')||'probe').padEnd(20,'_').slice(0,20);
 calls++;inflight++;maxInflight=Math.max(maxInflight,inflight);delays[delay]=(delays[delay]||0)+1;
 const start=performance.now();await new Promise(r=>setTimeout(r,delay));const wait=performance.now()-start;waitSum+=wait;waitMax=Math.max(waitMax,wait);
 res.setHeader('content-length',f.bytes);
 // Pre-serialized immutable synthetic fixtures keep the mock backend from limiting SSR.
 // Every request transfers the entire JSON and a fresh request ID; the SSR app parses it.
 res.on('finish',()=>{completed++;inflight--;totalBytes+=f.bytes;});
 res.write(f.prefix);res.write(rid);res.end(f.suffix);
}).listen(4000,'0.0.0.0');
