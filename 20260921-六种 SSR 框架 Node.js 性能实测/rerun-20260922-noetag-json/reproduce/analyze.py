"""Validate coverage and derive tables; no fabricated missing values."""
from pathlib import Path
import json,statistics,collections
ROOT=Path(__file__).resolve().parent.parent
NAMES={'next':'Next.js','nuxt':'Nuxt','svelte':'SvelteKit','tanstack':'TanStack Start','react-router':'React Router','solid':'SolidStart'}
def median(x):return statistics.median(x)
def cpu_stat(s):return {k:int(v) for k,v in (line.split() for line in s.strip().splitlines())}
def analyze():
 runs=[json.loads(p.read_text()) for p in sorted((ROOT/'runs').glob('*.json'))]
 counts=dict(collections.Counter(r['phase'] for r in runs))
 assert counts=={'client-control':36,'monitor-control':24,'matrix':324,'focus':18},counts
 assert len({r['id'] for r in runs})==402
 validation={f:json.loads((ROOT/'evidence'/f'{f}-validation.json').read_text()) for f in NAMES}
 for r in runs:
  if r['phase'] in ['matrix','focus']:assert r['workers']==min(4,r['connections']) and r['sampleEvery']==0 and r['sampled']==0,r['id']
  assert r['good']==r['complete']==r['issued'] and not r['errors'] and not r['invalid'],r['id']
  assert r['sampleInvalid']==0
  exact={x['bytes'] for x in validation[r['framework']]['results'] if x['size']==r['size'] and x['delay']==r['delay'] and x['encoding']=='identity'}
  assert len(exact)==1,(r['id'],exact)
  expected_html=next(iter(exact))
  assert r['responseBytes']['min']==r['responseBytes']['max']==expected_html,(r['id'],r['responseBytes'],expected_html)
  assert r['backendRequests']['calls']==r['backendRequests']['completed']==r['issued'],r['id']
  assert r['backendRequests']['inflight']==0
  expected={'hello':41,'medium':320000,'large':600000}[r['size']]
  assert r['backendRequests']['totalBytes']==expected*r['issued'],(r['id'],r['backendRequests'])
  assert not r['containerState']['OOMKilled']
  for role in ['app','load','backend']:
   for stage in ['before','after']:
    m=cpu_stat(r['cgroup'][stage][role]['memory.events']);assert m['oom']==m['oom_kill']==0,(r['id'],role,m)
  r['appCpuMsPerRequest']=r['app']['cpuMs']/r['good']
  r['gcMsPerRequest']=r['app']['gc']['totalMs']/r['good'] if r['app']['gc'] else None
  r['throttling']={}
  for role in ['app','load','backend']:
   a=cpu_stat(r['cgroup']['before'][role]['cpu.stat']);b=cpu_stat(r['cgroup']['after'][role]['cpu.stat'])
   r['throttling'][role]={k:b[k]-a[k] for k in ['nr_periods','nr_throttled','throttled_usec']}
 focus=[];matrix=[];controls=[]
 for f,name in NAMES.items():
  group=[r for r in runs if r['framework']==f and r['phase']=='focus'];assert len(group)==3
  focus.append({'framework':f,'name':name,'rpsMedian':median([r['rps'] for r in group]),'rpsMin':min(r['rps'] for r in group),'rpsMax':max(r['rps'] for r in group),
   **{k:median([r['latencyMs'][q] for r in group]) for k,q in [('p50MedianMs','p50'),('p95MedianMs','p95'),('p99MedianMs','p99')]},
   'p95MinMs':min(r['latencyMs']['p95'] for r in group),'p95MaxMs':max(r['latencyMs']['p95'] for r in group),
   'cpuPctMedian':median([r['app']['cpuPct'] for r in group]),'cpuMsPerRequestMedian':median([r['appCpuMsPerRequest'] for r in group]),
   'rssMaxMiB':max(r['app']['memory']['rssPeak'] for r in group)/2**20,'heapMaxMiB':max(r['app']['memory']['heapPeak'] for r in group)/2**20,
   'externalMaxMiB':max(r['app']['memory']['externalPeak'] for r in group)/2**20,'eluPctMedian':median([r['app']['eluPct'] for r in group]),
   'eventLoopP99MedianMs':median([r['app']['eventLoop']['p99Ms'] for r in group]),'gcMsPerRequestMedian':median([r['gcMsPerRequest'] for r in group]),
   'gcCountTotal':sum(r['app']['gc']['count'] for r in group),'gcEventMaxMs':max(r['app']['gc']['maxMs'] for r in group),'requests':sum(r['good'] for r in group),'rpsRuns':[r['rps'] for r in group],
   'firstBodyP50MedianMs':median([r['firstBodyMs']['p50'] for r in group])})
  for size in ['hello','medium','large']:
   for delay in [50,200,500]:
    for c in [1,16,64]:
     group=[r for r in runs if (r['phase'],r['framework'],r['size'],r['delay'],r['connections'])==('matrix',f,size,delay,c)];assert len(group)==2
     matrix.append({'framework':f,'name':name,'size':size,'delay':delay,'connections':c,'rps':sum(r['good'] for r in group)/sum(r['elapsedSeconds'] for r in group),'rpsRuns':[r['rps'] for r in group],
      'p50WindowMedianMs':median([r['latencyMs']['p50'] for r in group]),'p95WindowMedianMs':median([r['latencyMs']['p95'] for r in group]),'p99WindowMedianMs':median([r['latencyMs']['p99'] for r in group]),
      'cpuPctMedian':median([r['app']['cpuPct'] for r in group]),'cpuMsPerRequest':sum(r['app']['cpuMs'] for r in group)/sum(r['good'] for r in group),
      'rssMaxMiB':max(r['app']['memory']['rssPeak'] for r in group)/2**20,'eventLoopP99WindowMedianMs':median([r['app']['eventLoop']['p99Ms'] for r in group]),'gcMsPerRequest':sum(r['app']['gc']['totalMs'] for r in group)/sum(r['good'] for r in group),'requests':sum(r['good'] for r in group)})
  monitor={mode:[r['rps'] for r in runs if r['framework']==f and r['phase']=='monitor-control' and r['app']['mode']==mode] for mode in ['lean','off']}
  client={label:[r['rps'] for r in runs if r['framework']==f and r['phase']=='client-control' and (r['workers'],r['sampleEvery'])==v] for label,v in [('default',(4,128)),('workers8',(8,128)),('noSampling',(4,0))]}
  assert all(len(v)==2 for v in [*monitor.values(),*client.values()])
  controls.append({'framework':f,'name':name,'monitorRps':monitor,'clientRps':client,'leanVsOffPct':100*(median(monitor['lean'])/median(monitor['off'])-1),'workers8VsDefaultPct':100*(median(client['workers8'])/median(client['default'])-1),'noSamplingVsDefaultPct':100*(median(client['noSampling'])/median(client['default'])-1)})
 health={'windows':len(runs),'counts':counts,'exactHtmlBytesVerifiedWindows':len(runs),'good':sum(r['good'] for r in runs),'errors':sum(r['issued']-r['good'] for r in runs),'sampled':sum(r['sampled'] for r in runs),
  'minWindowRequests':min(r['good'] for r in runs),'loadCpuPctMax':max(r['load']['cpuPct'] for r in runs),'loadWorkerEluPctMax':max(max(r['load']['workerEluPct']) for r in runs),
  'backendCpuPctMax':max(r['backend']['cpuPct'] for r in runs),'backendTimerOvershootMeanMsMax':max(r['backendRequests']['waitMeanMs']-r['delay'] for r in runs),
  'memorySampleCostMsMax':max(r['app']['memory']['memorySampleCostMs'] for r in runs),
  'throttling':{role:{key:sum(r['throttling'][role][key] for r in runs) for key in ['nr_periods','nr_throttled','throttled_usec']} for role in ['app','load','backend']},
  'firstWindowEnd':min(r['dateEnd'] for r in runs),'lastWindowEnd':max(r['dateEnd'] for r in runs)}
 summary={'health':health,'focus':sorted(focus,key=lambda x:-x['rpsMedian']),'matrix':matrix,'controls':controls}
 variability=[]
 for r in runs:
  if r['phase']=='focus' and r['framework'] in ['nuxt','tanstack']:
   variability.append({'id':r['id'],'rps':r['rps'],'p95Ms':r['latencyMs']['p95'],'cpuMsPerRequest':r['appCpuMsPerRequest'],'appCpuPct':r['app']['cpuPct'],'backendTimerMeanMs':r['backendRequests']['waitMeanMs'],'loadCpuPct':r['load']['cpuPct'],'gcTotalMs':r['app']['gc']['totalMs'],'good':r['good'],'exactBytes':r['responseBytes'],'backendCalls':r['backendRequests']['calls']})
 (ROOT/'evidence/variability.json').write_text(json.dumps({'interpretation':'Observed cross-process variation; no outlier removed or corrected. Root cause unproven without synchronized profiles and host scheduling/frequency measurements.','records':variability},indent=2))
 (ROOT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
 (ROOT/'health.json').write_text(json.dumps(health,ensure_ascii=False,indent=2))
 return summary
if __name__=='__main__':print(json.dumps(analyze()['health'],indent=2))
