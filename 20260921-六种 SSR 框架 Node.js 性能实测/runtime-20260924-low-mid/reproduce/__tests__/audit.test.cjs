// Positive controls: verify that a zero sentinel count in page acceptance is meaningful.
const assert=require('node:assert/strict');
const zlib=require('node:zlib');
assert.ok(zlib.gzipSync('probe').length>0);
require('../audit.cjs');
const names=['gzip','gzipSync','deflate','deflateSync','deflateRaw','deflateRawSync','brotliCompress','brotliCompressSync','createGzip','createDeflate','createDeflateRaw','createBrotliCompress','Gzip','Deflate','DeflateRaw','BrotliCompress'];
for(const name of names)assert.throws(()=>zlib[name]('probe'),/Unexpected compression calculation/);
assert.throws(()=>require('/bench/apps/react-router/node_modules/etag')('probe'),/Unexpected ETag calculation/);
assert.throws(()=>require('/bench/apps/next/node_modules/next/dist/server/lib/etag').generateETag('probe'),/Unexpected Next ETag calculation/);
assert.throws(()=>require('node:http').ServerResponse.prototype.setHeader.call({},'etag','probe'),/ETag response header unexpectedly set/);
(async()=>{
 const esm=await import('node:zlib');
 assert.throws(()=>esm.gzipSync('probe'),/Unexpected compression calculation/);
 assert.deepEqual(globalThis.__benchAudit,{compressionCalls:17,etagModuleCalls:2,etagHeaders:1});
 console.log(JSON.stringify({passed:true,positiveControlCounters:globalThis.__benchAudit,compressionEntrypoints:names,esmBindingVerified:true}));
})().catch(e=>{console.error(e);process.exitCode=1;});
