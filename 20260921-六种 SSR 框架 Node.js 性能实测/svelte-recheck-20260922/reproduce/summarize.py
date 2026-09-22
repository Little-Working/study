import json, pathlib, statistics, csv
ROOT=pathlib.Path(__file__).resolve().parent.parent
E=ROOT/'evidence'
def row(file):
    d=json.loads(file.read_text());a=d['app'];m=a['memory']
    return dict(file=file.name,phase=d.get('phase',''),page=d['size'],delay=d['delay'],concurrency=d['connections'],requests=d['good'],seconds=d['elapsedSeconds'],rps=d['rps'],p50=d['latencyMs']['p50'],p95=d['latencyMs']['p95'],p99=d['latencyMs']['p99'],mean=d['latencyMs']['mean'],cpuPct=a['cpuPct'],cpuMsPerRequest=a['cpuMs']/d['good'],eluPct=a['eventLoop']['utilization']*100,eldP99=a['eventLoop']['p99Ms'],gcPct=a['gc']['observedDurationPct'],rssMiB=max(m['rssPeak'],m['rssEnd'])/2**20,heapMiB=max(m['heapUsedPeak'],m['heapUsedEnd'])/2**20,backendP95=d['backendRequests']['durations']['p95'],bodyBytes=d['responseBytes']['mean'],loadCpuPct=d['load']['cpuPct'],throttledUsec=a['cgroup']['throttledUsec'])
files=sorted([*E.glob('focus-r*.json'),*E.glob('matrix-*.json'),*E.glob('diagnostic*.json')])
files += [E/'control'/f'{v}.json' for v in ['default-before','no-etag','default-restored'] if (E/'control'/f'{v}.json').exists()]
rows=[row(f) for f in files]
for f in files:
    d=json.loads(f.read_text())
    assert d['issued']==d['complete']==d['good']==d['backendRequests']['calls']==d['backendRequests']['completed']
    assert not d['errors'] and not d['invalid'] and d['backendRequests']['inflight']==0
    assert d['responseBytes']['min']==d['responseBytes']['max']
    assert d['app']['cgroup']['memoryEventsStart']['oom_kill']==d['app']['cgroup']['memoryEventsEnd']['oom_kill']
focus=[r for r in rows if r['phase']=='focus']
agg={'windows':len(focus),'rps':sum(r['requests'] for r in focus)/sum(r['seconds'] for r in focus),'requests':sum(r['requests'] for r in focus)}
for k in ['rps','p50','p95','p99','cpuPct','cpuMsPerRequest','eluPct','eldP99','gcPct','rssMiB','heapMiB']:
    agg[k+'Median']=statistics.median(r[k] for r in focus)
    agg[k+'Range']=[min(r[k] for r in focus),max(r[k] for r in focus)]
original=[row(ROOT.parent/'evidence'/f'svelte-{stem}-large-d50-c64.json') for stem in ['sustained','sustained2']]
result={'original':original,'recheck':rows,'focus':agg,'verification':{'windows':len(rows),'requests':sum(r['requests'] for r in rows),'errors':0,'invalid':0,'backendReconciled':True,'oomKills':0}}
(ROOT/'summary.json').write_text(json.dumps(result,indent=2))
with (ROOT/'runs.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(json.dumps({'focus':agg,'verification':result['verification']},indent=2))
