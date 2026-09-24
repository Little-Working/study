"""Offline only: exact pooled GC event quantiles, explicitly non-pooled ELD summaries."""
from pathlib import Path
import json,math,statistics,collections
ROOT=Path(__file__).resolve().parent.parent
PCTS=[50,75,90,95,99]
KINDS={1:'minor',2:'minor_mark_sweep',4:'major',8:'incremental',16:'weakcb'}
NAMES={'next':'Next.js','nuxt':'Nuxt','svelte':'SvelteKit','tanstack':'TanStack Start','react-router':'React Router','solid':'SolidStart'}
def quantiles(values):
 a=sorted(values)
 return {'count':len(a),'totalMs':sum(a),'maxMs':max(a) if a else None,'meanMs':statistics.mean(a) if a else None,'p99Sparse':len(a)<100,**{f'p{p}Ms':a[math.ceil(p/100*len(a))-1] if a else None for p in PCTS}}
def combine_metrics(items,key):
 # No attempt to recover a pooled ELD histogram from its percentile outputs.
 vals=[r[key] for r in items]
 return {'sampleCount':sum(v.get('count',0) for v in vals),'aggregation':'median_of_window_quantiles; maximum_of_window_maxima',**{f'p{p}Ms':statistics.median(v[f'p{p}Ms'] for v in vals) for p in PCTS},'maxMs':max(v['maxMs'] for v in vals),'p99RangeMs':[min(v['p99Ms'] for v in vals),max(v['p99Ms'] for v in vals)]}
def cpu_stat(s):return {k:int(v) for k,v in (l.split() for l in s.splitlines())}
def main():
 runs=[json.loads(p.read_text()) for p in sorted((ROOT/'runs').glob('*.json'))]
 if not (ROOT/'evidence/run-complete.json').exists():raise SystemExit('Measurement not complete; do not publish partial rankings')
 assert len(runs)==240
 matrix=[r for r in runs if r['phase']=='matrix'];assert len(matrix)==216
 groups=collections.defaultdict(list)
 for r in matrix:groups[(r['framework'],r['size'],r['delay'],r['connections'])].append(r)
 assert len(groups)==108 and all(len(v)==2 for v in groups.values())
 health={'windows':len(runs),'matrixWindows':len(matrix),'good':sum(r['good'] for r in runs),'errors':sum(sum(r['errors'].values()) for r in runs),'invalid':sum(len(r['invalid']) for r in runs),'gcDropped':sum((r['app'].get('gc') or {}).get('dropped',0) for r in runs),'maxAppCpuPct':max(r['app']['cpuPct'] for r in matrix),'maxLoadCpuPct':max(r['load']['cpuPct'] for r in runs),'maxBackendCpuPct':max(r['backend']['cpuPct'] for r in runs),'maxWorkerEluPct':max(max(r['load']['workerEluPct']) for r in runs),'minRequestsPerMatrixWindow':min(r['good'] for r in matrix),'gcTypes':{},'throttle':{},'maxBackendTimerOvershootMeanMs':max(r['backendRequests']['waitMeanMs']-r['delay'] for r in matrix),'maxMemorySampleCostMs':max(r['app']['memory']['memorySampleCostMs'] for r in matrix),'minEventLoopSamplesPerWindow':min(r['app']['eventLoop']['count'] for r in matrix)}
 assert health['errors']==health['invalid']==health['gcDropped']==0
 for r in runs:
  assert r['good']==r['issued']==r['complete']==r['backendRequests']['calls']==r['backendRequests']['completed']
  assert r['backendRequests']['totalBytes']==r['issued']*{'hello':41,'medium':320000,'large':600000}[r['size']]
  assert not r['containerState']['OOMKilled']
  for role in ['app','load','backend']:
   before=cpu_stat(r['cgroup']['before'][role]['memory.events']);after=cpu_stat(r['cgroup']['after'][role]['memory.events'])
   assert after.get('oom_kill',0)==before.get('oom_kill',0), 'OOM occurred in measurement window'
  assert r['responseBytes']['min']>=r['minBytes'] and r['responseBytes']['max']<=r['maxBytes']
  if r['app']['gc']:
   g=r['app']['gc'];assert g['count']==len(g['events']);assert abs(g['totalMs']-sum(e['durationMs'] for e in g['events']))<1e-6
   for p in PCTS:assert abs(g[f'p{p}Ms']-quantiles([e['durationMs'] for e in g['events']])[f'p{p}Ms'])<1e-6 if g['count'] else g[f'p{p}Ms'] is None
 for role in ['app','load','backend']:
  pairs=[(cpu_stat(r['cgroup']['before'][role]['cpu.stat']),cpu_stat(r['cgroup']['after'][role]['cpu.stat'])) for r in runs]
  health['throttle'][role]={k:sum(b.get(k,0)-a.get(k,0) for a,b in pairs) for k in ['nr_periods','nr_throttled','throttled_usec']}
 for code,name in KINDS.items():health['gcTypes'][name]=sum(sum(e['kind']==code for e in r['app']['gc']['events']) for r in matrix)
 summary=[]
 for (framework,size,delay,c),rs in groups.items():
  apps=[r['app'] for r in rs];events=[e for a in apps for e in a['gc']['events']]
  gc=quantiles([e['durationMs'] for e in events]);gc['aggregation']='pooled_event_nearest_rank'
  gc['kinds']={name:quantiles([e['durationMs'] for e in events if e['kind']==code]) for code,name in KINDS.items()}
  assert sum(v['count'] for v in gc['kinds'].values())==gc['count'], 'Unexpected GC kind; inspect raw data before publishing'
  gc['msPerRequest']=gc['totalMs']/sum(r['good'] for r in rs)
  gc['eventsPerSecond']=gc['count']/sum(a['wallMs']/1000 for a in apps)
  gc['observedPct']=100*gc['totalMs']/sum(a['wallMs'] for a in apps)
  summary.append({'framework':framework,'name':NAMES[framework],'size':size,'delay':delay,'connections':c,'windows':[r['id'] for r in rs],'requests':sum(r['good'] for r in rs),'eventLoop':combine_metrics(apps,'eventLoop'),'gc':gc,'cpuPct':statistics.median(a['cpuPct'] for a in apps),'cpuMsPerRequest':sum(a['cpuMs'] for a in apps)/sum(r['good'] for r in rs),'eluPct':statistics.median(a['eluPct'] for a in apps),'rssMaxMiB':max(a['memory']['rssPeak'] for a in apps)/2**20,'heapMaxMiB':max(a['memory']['heapPeak'] for a in apps)/2**20,'externalMaxMiB':max(a['memory']['externalPeak'] for a in apps)/2**20,'rps':sum(r['good'] for r in rs)/sum(r['elapsedSeconds'] for r in rs),'httpMs':{**{f'p{p}':statistics.median(r['latencyMs'][f'p{p}'] for r in rs) for p in PCTS},'max':max(r['latencyMs']['max'] for r in rs)},'rpsRuns':[r['rps'] for r in rs]})
 idle=[json.loads(p.read_text()) for p in sorted((ROOT/'evidence').glob('idle-*.json'))];assert len(idle)==36
 controls=[]
 for f in NAMES:
  rs=[r for r in runs if r['phase']=='monitor-control' and r['framework']==f]
  modes={m:[r for r in rs if r['app']['mode']==m] for m in ['lean','off']}
  controls.append({'framework':f,'name':NAMES[f],'rps':{m:[r['rps'] for r in v] for m,v in modes.items()},'leanVsOffRpsPct':100*(statistics.median(r['rps'] for r in modes['lean'])/statistics.median(r['rps'] for r in modes['off'])-1),'cpuMsPerRequest':{m:sum(r['app']['cpuMs'] for r in v)/sum(r['good'] for r in v) for m,v in modes.items()}})
 health['zeroGcCells']=sum(r['gc']['count']==0 for r in summary)
 health['sparseGcCells']=sum(r['gc']['count']<100 for r in summary)
 health['sparseMajorGcCells']=sum(r['gc']['kinds']['major']['count']<100 for r in summary)
 output={'health':health,'matrix':summary,'idle':idle,'controls':controls}
 (ROOT/'summary.json').write_text(json.dumps(output,indent=2))
 (ROOT/'health.json').write_text(json.dumps(health,indent=2))
 print(json.dumps(health,indent=2))
if __name__=='__main__':main()
