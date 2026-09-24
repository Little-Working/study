// Validation-only sentinels. Never preload this module during timed measurements.
const Module=require('node:module');
const zlib=require('node:zlib');
globalThis.__benchAudit={compressionCalls:0,etagModuleCalls:0,etagHeaders:0};
for(const name of ['gzip','gzipSync','deflate','deflateSync','deflateRaw','deflateRawSync','brotliCompress','brotliCompressSync','createGzip','createDeflate','createDeflateRaw','createBrotliCompress','Gzip','Deflate','DeflateRaw','BrotliCompress']){
 const desc=Object.getOwnPropertyDescriptor(zlib,name);
 if(desc?.configurable)Object.defineProperty(zlib,name,{...desc,value:function(){globalThis.__benchAudit.compressionCalls++;throw Error('Unexpected compression calculation: '+name)}});
}
require('node:module').syncBuiltinESMExports();
const original=Module._load;
Module._load=function(request,parent,isMain){
 const result=original.apply(this,arguments);
 if(request==='etag'||request.endsWith('/etag')){
  if(typeof result==='function')return function(){globalThis.__benchAudit.etagModuleCalls++;throw Error('Unexpected ETag calculation');};
  if(result&&typeof result.generateETag==='function')return new Proxy(result,{get(target,key){if(key==='generateETag')return function(){globalThis.__benchAudit.etagModuleCalls++;throw Error('Unexpected Next ETag calculation');};return target[key];}});
 }
 return result;
};
const setHeader=require('node:http').ServerResponse.prototype.setHeader;
require('node:http').ServerResponse.prototype.setHeader=function(name,value){if(String(name).toLowerCase()==='etag'){globalThis.__benchAudit.etagHeaders++;throw Error('ETag response header unexpectedly set');}return setHeader.apply(this,arguments);};
