import assert from 'node:assert/strict';
import {writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const out=process.argv[2],results=[];
const get=async url=>(await fetch(url)).json();
const fixtures=await get('http://ssrbench2-backend:4000/fixtures');
for(const size of ['hello','medium','large']){
 const r=await fetch(`http://ssrbench2-backend:4000/data?size=${size}&delay=50&rid=backend-validation`);
 const raw=await r.text(),data=JSON.parse(raw);
 assert.equal(Buffer.byteLength(raw),fixtures[size].bytes);
 assert.equal(data.items.length,{hello:0,medium:800,large:1536}[size]);
 assert.equal(new Set(data.items.map(r=>r.description)).size,data.items.length);
 assert.ok(!r.headers.get('etag')&&!r.headers.get('content-encoding'));
}
assert.equal(fixtures.medium.bytes,320000);assert.equal(fixtures.large.bytes,600000);
await get('http://ssrbench2-backend:4000/reset');
for(const size of ['hello','medium','large'])for(const delay of [50,200,500])for(const encoding of ['identity','gzip, deflate, br'])for(let repeat=0;repeat<2;repeat++){
 const rid='validation-request__',start=performance.now();
 const r=await fetch(`http://ssrbench2-app:3000/?size=${size}&delay=${delay}&rid=${rid}`,{headers:{'accept-encoding':encoding,'accept':'text/html','if-none-match':'"nonmatching-test-value"'}});
 const body=await r.text(),bytes=Buffer.byteLength(body),elapsedMs=performance.now()-start;
 assert.equal(r.status,200);assert.ok(r.headers.get('content-type')?.includes('text/html'));
 assert.ok(!r.headers.get('etag'));assert.ok(!r.headers.get('content-encoding'));
 assert.ok(body.includes(rid));assert.ok(body.includes('BENCH_END'));
 assert.equal((body.match(/<article\b/g)||[]).length,fixtures[size].count);
 if(size!=='hello')assert.ok(body.includes('sku-000000-')&&body.includes(`sku-${String(fixtures[size].count-1).padStart(6,'0')}-`));
 assert.ok(elapsedMs>=delay-5);
 results.push({size,delay,encoding,repeat,bytes,elapsedMs,sha256:createHash('sha256').update(body).digest('hex'),headers:Object.fromEntries(r.headers)});
}
const stats=await get('http://ssrbench2-backend:4000/stats'),metrics=await get('http://ssrbench2-app:9100/');
assert.equal(stats.calls,36);assert.equal(stats.completed,36);assert.equal(stats.inflight,0);
assert.deepEqual(metrics.audit,{compressionCalls:0,etagModuleCalls:0,etagHeaders:0});
writeFileSync(out,JSON.stringify({fixtures,results,backend:stats,audit:metrics.audit}));
console.log(JSON.stringify({sizes:results.filter(r=>r.delay===50&&r.repeat===0&&r.encoding==='identity').map(r=>({size:r.size,bytes:r.bytes})),audit:metrics.audit}));
