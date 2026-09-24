const assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const path=require('node:path');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const url='http://127.0.0.1:9100';
async function exercise(mode){
 const child=spawn(process.execPath,['--expose-gc','--require',path.join(__dirname,'../metrics.cjs'),'-e',`process.on('message',()=>{setTimeout(()=>{const end=performance.now()+80;while(performance.now()<end){};let a=Array.from({length:100000},(_,i)=>({i}));global.gc();a=null;global.gc();setTimeout(()=>process.send('done'),30);},30);});`],{env:{...process.env,NODE_OPTIONS:'',BENCH_METRICS_MODE:mode},stdio:['ignore','ignore','inherit','ipc']});
 try{
  for(let i=0;i<100;i++){try{await fetch(url);break;}catch{await sleep(20);}}
  await fetch(url+'/reset');const done=new Promise(r=>child.once('message',r));child.send('go');await done;
  const r=await (await fetch(url+'/stop')).json();
  assert.equal(r.mode,mode);assert.ok(r.wallMs>100);assert.ok(r.memory.sampleCount>=1);
  if(mode==='lean'){assert.ok(r.eventLoop.count>0);assert.ok(r.eventLoop.maxMs>=60);assert.ok(r.gc.count>=2);assert.ok(r.gc.kinds.major.count>=2);assert.equal(r.gc.dropped,0);for(const p of [50,75,90,95,99])assert.ok(Number.isFinite(r.gc[`p${p}Ms`]));}
  else {assert.equal(r.gc,null);assert.equal(r.eventLoop,null);}
  await sleep(25);assert.deepEqual(await (await fetch(url+'/stop')).json(),r);
  console.log(JSON.stringify({mode,eventLoop:r.eventLoop,gcCount:r.gc?.count,majorCount:r.gc?.kinds.major.count}));
 }finally{const exit=new Promise(r=>child.once('exit',r));child.kill();await exit;}
}
(async()=>{await exercise('lean');await exercise('off');console.log('Live monitor GC, blocked loop, off mode and frozen boundary PASS');})().catch(e=>{console.error(e);process.exitCode=1;});
