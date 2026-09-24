"""Sequential low/mid concurrency runtime benchmark. Fresh process per page and pass.
All results are persisted before next window. Cleanup is restricted to this run label.
"""
from common import *
import random,sys,traceback
CAL=json.loads((OUT/'calibration.json').read_text())
RUNS=ROOT/'runs';RUNS.mkdir(exist_ok=True)

def cgroup(container):
 script="const fs=require('fs');const r={};for(const p of ['cpu.stat','memory.current','memory.peak','memory.events'])r[p]=fs.readFileSync('/sys/fs/cgroup/'+p,'utf8');console.log(JSON.stringify(r));"
 return json.loads(docker('exec','-e','NODE_OPTIONS=',container,'node','-e',script))

def window(name,phase,ident,size='large',delay=50,connections=8,seconds=20,workers=2,measure=True):
 cfg=dict(framework=name,phase=phase,size=size,delay=delay,connections=connections,seconds=seconds,workers=workers,sampleEvery=0,measure=measure,**{k:v for k,v in CAL[name][size].items() if k in ['minBytes','maxBytes']})
 if measure:
  cfg['out']='/bench/results/'+ident+'.json'
  before={c:cgroup('ssrbench3-'+c) for c in ['app','load','backend']}
 print(docker('exec','ssrbench3-load','node','/bench/load.mjs',json.dumps(cfg)),flush=True)
 if not measure:return
 after={c:cgroup('ssrbench3-'+c) for c in ['app','load','backend']}
 docker('cp','ssrbench3-load:'+cfg['out'],str(RUNS/(ident+'.json')))
 p=RUNS/(ident+'.json');r=json.loads(p.read_text());r['id']=ident;r['cgroup']={'before':before,'after':after}
 r['containerState']=json.loads(docker('inspect','-f','{{json .State}}','ssrbench3-app'))
 p.write_text(json.dumps(r))
 assert r['good']==r['issued']==r['complete'] and not r['errors'] and not r['invalid'],ident+' invalid responses'
 assert r['backendRequests']['calls']==r['issued'] and r['backendRequests']['completed']==r['issued'],ident+' backend count mismatch'
 assert not r['containerState']['OOMKilled'],ident+' OOM'
 for part in ['app','backend']:
  if r[part]['mode']=='lean':
   assert r[part]['eventLoop']['count']>0,ident+' empty event loop samples'
   assert r[part]['gc']['dropped']==0,ident+' GC overflow'
 return r

def warm(name,size,delay=200,connections=8,seconds=10):
 window(name,'warmup','unused',size,delay,connections,seconds,measure=False)

def idle(name,size,repeat):
 ident=f'idle-{repeat}-{name}-{size}'
 js="const get=async p=>(await fetch('http://ssrbench3-app:9100/'+p)).json();await get('reset');await new Promise(r=>setTimeout(r,10000));const r=await get('stop');console.log(JSON.stringify(r));"
 r=json.loads(docker('exec','ssrbench3-load','node','--input-type=module','-e',js));r.update(framework=name,size=size,repeat=repeat,phase='idle')
 (OUT/(ident+'.json')).write_text(json.dumps(r))

def save_log(ident):
 (OUT/(ident+'-runtime.log')).write_text(docker('logs','ssrbench3-app'))

if __name__=='__main__':
 if list(RUNS.glob('*.json')):raise SystemExit('Existing measurements: inspect instead of silently restarting.')
 try:
  # ABBA fresh-process monitor control, same client, page, backend and load.
  for name in FRAMEWORKS:
   for j,mode in enumerate(['lean','off','off','lean']):
    start_app(name,mode);warm(name,'large',50,8,10)
    window(name,'monitor-control',f'monitor-{name}-{j}-{mode}',seconds=15)
    save_log(f'monitor-{name}-{j}')
  # 108 combinations, two independent page processes per framework.
  # Only one SSR target is active; no builds or profiling during formal windows.
  for repeat in range(2):
   order=FRAMEWORKS if repeat==0 else list(reversed(FRAMEWORKS))
   pages=['hello','medium','large'] if repeat==0 else ['large','medium','hello']
   cells=[(d,c) for d in [50,200,500] for c in [1,8]]
   random.Random(20260924+repeat).shuffle(cells)
   for name in order:
    for size in pages:
     start_app(name);warm(name,size);idle(name,size,repeat)
     for delay,connections in cells:
      warm(name,size,delay,connections,3)
      window(name,'matrix',f'matrix-{repeat}-{name}-{size}-{delay}-c{connections}',size,delay,connections,20)
     save_log(f'matrix-{repeat}-{name}-{size}')
  (OUT/'run-complete.json').write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'windows':len(list(RUNS.glob('*.json'))),'expected':240,'matrix':216,'controls':24,'idle':36},indent=2))
 except BaseException:
  (OUT/'run-failure.txt').write_text(traceback.format_exc());raise
 finally:cleanup()
