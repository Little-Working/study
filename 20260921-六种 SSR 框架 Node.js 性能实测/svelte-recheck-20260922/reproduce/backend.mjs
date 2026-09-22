import http from 'node:http';
import {performance} from 'node:perf_hooks';
let calls=0,completed=0,inflight=0,maxInflight=0,durations=[],requested={};
http.createServer(async(req,res)=>{
  const p=new URL(req.url,'http://localhost');res.setHeader('content-type','application/json');res.setHeader('cache-control','no-store');
  if(p.pathname==='/stats'){res.end(JSON.stringify({calls,completed,inflight,maxInflight,durations,requested}));return;}
  if(p.pathname==='/reset'){if(inflight){res.statusCode=409;res.end('{}');return;}calls=completed=maxInflight=0;durations=[];requested={};res.end('{}');return;}
  if(p.pathname!=='/data'){res.statusCode=404;res.end('{}');return;}
  const delay=Math.max(50,Math.min(500,Number(p.searchParams.get('delay')||50)));
  const size=p.searchParams.get('size')||'hello';const count={hello:0,medium:800,large:1536}[size];
  if(count===undefined){res.statusCode=400;res.end('{}');return;}
  calls++;inflight++;maxInflight=Math.max(maxInflight,inflight);requested[delay]=(requested[delay]||0)+1;
  const t=performance.now();await new Promise(r=>setTimeout(r,delay));durations.push(performance.now()-t);
  res.end(JSON.stringify({rid:p.searchParams.get('rid')||'probe',count,textLength:930,delay}));completed++;inflight--;
}).listen(4000,'0.0.0.0');
