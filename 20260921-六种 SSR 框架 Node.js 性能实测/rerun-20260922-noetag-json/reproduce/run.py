"""Sequential benchmark. Each completed window is persisted before proceeding.
Pilot must pass before the full matrix. Always destroys only this run's resources.
"""
from common import *
import random,sys,traceback

CAL=json.loads((OUT/'calibration.json').read_text())
RUNS=ROOT/'runs';RUNS.mkdir(exist_ok=True)
def cgroup(container):
 script="const fs=require('fs');const r={};for(const p of ['cpu.stat','memory.current','memory.peak','memory.events'])r[p]=fs.readFileSync('/sys/fs/cgroup/'+p,'utf8');console.log(JSON.stringify(r));"
 return json.loads(docker('exec','-e','NODE_OPTIONS=',container,'node','-e',script))
def window(name,phase,ident,size='large',delay=50,connections=64,seconds=15,workers=4,sample=128,measure=True):
 if phase in ['matrix','focus']:sample=0
 cfg=dict(framework=name,phase=phase,size=size,delay=delay,connections=connections,seconds=seconds,workers=workers,sampleEvery=sample,measure=measure,**{k:v for k,v in CAL[name][size].items() if k in ['minBytes','maxBytes']})
 if measure:
  cfg['out']='/bench/results/'+ident+'.json'
  before={c:cgroup('ssrbench2-'+c) for c in ['app','load','backend']}
 print(docker('exec','ssrbench2-load','node','/bench/load.mjs',json.dumps(cfg)),flush=True)
 if not measure:return
 after={c:cgroup('ssrbench2-'+c) for c in ['app','load','backend']}
 docker('cp','ssrbench2-load:'+cfg['out'],str(RUNS/(ident+'.json')))
 p=RUNS/(ident+'.json');r=json.loads(p.read_text());r['id']=ident;r['cgroup']={'before':before,'after':after}
 r['containerState']=json.loads(docker('inspect','-f','{{json .State}}','ssrbench2-app'))
 p.write_text(json.dumps(r))
 assert r['good']==r['issued']==r['complete'] and not r['errors'] and not r['invalid'],ident+' invalid responses'
 assert r['backendRequests']['calls']==r['issued'] and r['backendRequests']['completed']==r['issued'],ident+' backend count mismatch'
 assert not r['containerState']['OOMKilled'],ident+' OOM'
 return r
def warm(name,size='large',delay=50,connections=64,seconds=8):
 window(name,'warmup','unused',size,delay,connections,seconds,measure=False)
def start(name,mode='lean',warm_seconds=8):
 start_app(name,mode);warm(name,seconds=warm_seconds)
def save_log(ident):
 (OUT/(ident+'-runtime.log')).write_text(docker('logs','ssrbench2-app'))

if __name__=='__main__':
 if list(RUNS.glob('*.json')):raise SystemExit('Existing measurements: inspect instead of silently overwriting/restarting.')
 try:
  # Pilot/loader controls use a single warm process per framework, balanced order.
  # Initial reference: 4 workers + 1/128 samples. Formal windows disable scans
  # after the client-control calibration (see protocol-amendment.json).
  for name in FRAMEWORKS:
   start(name)
   for j,(workers,sample) in enumerate([(4,128),(8,128),(4,0),(4,0),(8,128),(4,128)]):
    window(name,'client-control',f'client-{name}-{j}',seconds=12,workers=workers,sample=sample)
   save_log('client-'+name)
  # Two independent processes per mode in reversed order: lean/off/off/lean.
  for name in FRAMEWORKS:
   for j,mode in enumerate(['lean','off','off','lean']):
    start(name,mode)
    window(name,'monitor-control',f'monitor-{name}-{j}-{mode}',seconds=15)
    save_log(f'monitor-{name}-{j}')
  # Full 3 sizes x 3 delays x 3 concurrency matrix, two passes.
  # Reverse framework order on pass two; predeclared randomized cell order.
  cells=[(s,d,c) for s in ['hello','medium','large'] for d in [50,200,500] for c in [1,16,64]]
  for repeat in range(2):
   order=FRAMEWORKS if repeat==0 else list(reversed(FRAMEWORKS))
   sequence=cells.copy();random.Random(20260922+repeat).shuffle(sequence)
   for name in order:
    start(name)
    for size,delay,connections in sequence:
     warm(name,size,delay,connections,seconds=2)
     window(name,'matrix',f'matrix-{repeat}-{name}-{size}-{delay}-c{connections}',size,delay,connections,seconds=8)
    save_log(f'matrix-{repeat}-{name}')
  # Longer headline windows: three fresh processes, rotated framework order.
  for repeat in range(3):
   order=FRAMEWORKS[repeat*2:]+FRAMEWORKS[:repeat*2]
   for name in order:
    start(name,warm_seconds=30)
    window(name,'focus',f'focus-{repeat}-{name}',seconds=30)
    save_log(f'focus-{repeat}-{name}')
  (OUT/'run-complete.json').write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'windows':len(list(RUNS.glob('*.json'))),'expected':402},indent=2))
 except BaseException:
  (OUT/'run-failure.txt').write_text(traceback.format_exc())
  raise
 finally:cleanup()
