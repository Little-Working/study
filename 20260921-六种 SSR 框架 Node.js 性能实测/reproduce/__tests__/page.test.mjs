// Production HTTP acceptance checks; run against one isolated framework at a time.
import assert from 'node:assert/strict';
import {writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const out=process.argv[2];
await fetch('http://ssrbench-backend:4000/reset');
const results=[];
for(const size of ['hello','medium','large'])for(const delay of [50,200,500])for(let repeat=0;repeat<2;repeat++){
  const start=performance.now();
  const r=await fetch(`http://ssrbench-app:3000/?size=${size}&delay=${delay}&rid=validation`,{headers:{'accept-encoding':'identity','user-agent':'ssrbench/1.0'}});
  const s=await r.text();const bytes=Buffer.byteLength(s),count={hello:0,medium:800,large:1536}[size];
  assert.equal(r.status,200);assert.match(r.headers.get('content-type'),/text\/html/);assert.ok(!r.headers.get('content-encoding'));assert.ok(s.includes('BENCH_END'));assert.ok(s.includes('data-request="validation"'));assert.equal((s.match(/<article\b/g)||[]).length,count);
  if(size==='medium')assert.ok(bytes>750*1024&&bytes<850*1024,`medium: ${bytes}`);
  if(size==='large')assert.ok(bytes>1.4*1024*1024&&bytes<1.65*1024*1024,`large: ${bytes}`);
  const elapsedMs=performance.now()-start;assert.ok(elapsedMs>=delay-5);
  results.push({size,delay,repeat,bytes,articles:count,elapsedMs,sha256:createHash('sha256').update(s).digest('hex'),headers:Object.fromEntries(r.headers)});
}
const backend=await(await fetch('http://ssrbench-backend:4000/stats')).json();
assert.equal(backend.calls,18);assert.equal(backend.completed,18);assert.equal(backend.inflight,0);
writeFileSync(out,JSON.stringify({results,backend}));console.log(JSON.stringify(results.filter(r=>r.delay===50&&r.repeat===1).map(({size,bytes,articles})=>({size,bytes,articles}))));
