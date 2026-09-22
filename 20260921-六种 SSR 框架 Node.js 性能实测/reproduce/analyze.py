"""Validate raw measurements and export comparable, explicitly defined aggregates."""
import csv,json,statistics,pathlib,collections,math,sys
ROOT=pathlib.Path(__file__).resolve().parent.parent
E=ROOT/'evidence'
NAMES={'next':'Next.js','nuxt':'Nuxt','svelte':'SvelteKit','tanstack':'TanStack Start','react-router':'React Router','solid':'SolidStart'}
def flat(r):
 a=r['app'];g=a['gc'];m=a['memory'];e=a['eventLoop'];b=r['backendRequests'];l=r['load']
 return {'framework':r['framework'],'phase':r.get('phase','matrix'),'page':r['size'],'delay_ms':r['delay'],'concurrency':r['connections'],'repeat':r.get('repeat',1),'seconds':r['elapsedSeconds'],'requests':r['good'],'rps':r['goodput'],'qps':r['goodput'],'body_bytes':r['responseBytes']['mean'],'throughput_mib_s':r['bytesPerSecond']/2**20,'latency_mean_ms':r['latencyMs']['mean'],'latency_p50_ms':r['latencyMs']['p50'],'latency_p95_ms':r['latencyMs']['p95'],'latency_p99_ms':r['latencyMs']['p99'],'ttfb_p50_ms':r['ttfbMs']['p50'],'ttfb_p95_ms':r['ttfbMs']['p95'],'cpu_pct':a['cpuPct'],'cpu_ms_per_req':a['cpuMs']/r['good'],'elu_pct':e['utilization']*100,'eld_p99_ms':e['p99Ms'],'eld_max_ms':e['maxMs'],'gc_count':g['count'],'gc_count_per_s':g['count']/(a['wallMs']/1000),'gc_total_ms':g['totalMs'],'gc_ms_per_1000_req':g['totalMs']/r['good']*1000,'gc_observed_pct':g['observedDurationPct'],'gc_max_ms':g['maxMs'],'gc_major_count':g['kinds'].get('NODE_PERFORMANCE_GC_MAJOR',{}).get('count',0),'rss_start_mib':m['rssStart']/2**20,'rss_peak_mib':max(m['rssPeak'],m['rssStart'],m['rssEnd'])/2**20,'rss_end_mib':m['rssEnd']/2**20,'heap_start_mib':m['heapUsedStart']/2**20,'heap_peak_mib':max(m['heapUsedPeak'],m['heapUsedStart'],m['heapUsedEnd'])/2**20,'heap_end_mib':m['heapUsedEnd']/2**20,'cgroup_peak_mib':m['cgroupPeak']/2**20,'app_throttle_ms':a['cgroup']['throttledUsec']/1000,'load_cpu_pct':l['cpuPct'],'load_worker_eld_p99_max_ms':max(l['workerEventLoopP99Ms']),'load_throttle_ms':l['cgroup']['throttledUsec']/1000,'backend_calls':b['calls'],'backend_cpu_pct':r['backend']['cpuPct'],'backend_delay_mean_ms':b['durations']['mean'],'backend_delay_p95_ms':b['durations']['p95'],'backend_delay_max_ms':b['durations']['max'],'errors':sum(r['errors'].values())+r['complete']-r['good']}
def read_all():
 rows=[];raw=[]
 for p in sorted(E.glob('*.json')):
  r=json.loads(p.read_text())
  if not isinstance(r,dict) or 'framework' not in r or 'app' not in r:continue
  assert r['good']==r['complete']==r['issued']==r['backendRequests']['calls']==r['backendRequests']['completed'],p
  assert not r['errors'] and not r['invalid'] and r['backendRequests']['inflight']==0,p
  assert r['latencyMs']['mean']*r['rps']/1000<=r['connections']*1.01,p
  assert r['rps']<=r['connections']/(r['delay']/1000)*1.05,p
  assert r['responseBytes']['max']-r['responseBytes']['min']<100,p
  assert sum(r['backendRequests']['requested'].values())==r['good'],p
  for k in ['app','backend','load']:
   c=r[k]['cgroup'];assert c['memoryEventsEnd']['oom_kill']==c['memoryEventsStart']['oom_kill'],p
   assert c['cpuUsec']>0 and r[k]['memory']['cgroupPeak']>0,p
   assert r[k]['eventLoop']['meanMs'] is not None,p
  rows.append(flat(r));raw.append(r)
 return rows,raw
def write_csv(path,rows):
 with path.open('w',newline='')as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def aggregate(rows):
 groups=collections.defaultdict(list)
 for r in rows:
  if r['phase']=='sustained':continue
  groups[(r['framework'],r['page'],r['delay_ms'],r['concurrency'])].append(r)
 result=[]
 for (framework,page,delay,c),rr in groups.items():
  out={'framework':framework,'page':page,'delay_ms':delay,'concurrency':c,'windows':len(rr),'requests':sum(x['requests']for x in rr),'seconds':sum(x['seconds']for x in rr)}
  out['rps']=out['requests']/out['seconds'];out['rps_min']=min(x['rps']for x in rr);out['rps_max']=max(x['rps']for x in rr);out['rps_spread_pct']=(out['rps_max']-out['rps_min'])/out['rps']*100
  for key in ['body_bytes','throughput_mib_s','latency_mean_ms','latency_p50_ms','latency_p95_ms','latency_p99_ms','ttfb_p50_ms','ttfb_p95_ms','cpu_pct','cpu_ms_per_req','elu_pct','eld_p99_ms','gc_count_per_s','gc_ms_per_1000_req','gc_observed_pct','gc_max_ms','load_cpu_pct','backend_cpu_pct','backend_delay_mean_ms']:
   out[key]=statistics.median(x[key]for x in rr)
  for key in ['rss_peak_mib','heap_peak_mib','cgroup_peak_mib']:out[key]=max(x[key]for x in rr)
  result.append(out)
 return result
if __name__=='__main__':
 rows,raw=read_all();agg=aggregate(rows)
 if not rows:raise SystemExit('No completed measurements')
 if '--complete' in sys.argv:
  assert len(rows)==282, len(rows)
  assert len(agg)==162, len(agg)
  assert len([r for r in rows if r['phase']=='sustained'])==12
  for r in agg:assert r['windows']==(1 if r['concurrency']==1 else 2),r
  assert len({(r['framework'],r['phase'],r['page'],r['delay_ms'],r['concurrency'],r['repeat'])for r in rows})==len(rows)
 write_csv(ROOT/'runs.csv',rows);write_csv(ROOT/'summary.csv',agg)
 sustained=[]
 for framework in NAMES:
  rr=[r for r in rows if r['phase']=='sustained' and r['framework']==framework]
  if not rr:continue
  item={'framework':framework,'windows':len(rr)}
  for key in rr[0]:
   if key!='repeat' and isinstance(rr[0][key],(int,float)):item[key]=statistics.median(x[key]for x in rr)
  item['requests']=sum(x['requests']for x in rr);item['seconds']=sum(x['seconds']for x in rr)
  item['rps']=item['requests']/item['seconds'];item['qps']=item['rps']
  for key in ['backend_calls','errors','gc_count','gc_total_ms']:item[key]=sum(x[key]for x in rr)
  item['rps_min']=min(x['rps']for x in rr);item['rps_max']=max(x['rps']for x in rr)
  for key in ['rss_peak_mib','heap_peak_mib','cgroup_peak_mib']:item[key]=max(x[key]for x in rr)
  sustained.append(item)
 (ROOT/'summary.json').write_text(json.dumps({'runs':rows,'scenarios':agg,'sustained':sustained},indent=2))
 health={'windows':len(rows),'scenarios':len(agg),'requests':sum(r['requests']for r in rows),'errors':sum(r['errors']for r in rows),'app_cpu_pct_max':max(r['cpu_pct']for r in rows),'app_throttle_ms_sum':sum(r['app_throttle_ms']for r in rows),'load_cpu_pct_max':max(r['load_cpu_pct']for r in rows),'load_throttle_ms_sum':sum(r['load_throttle_ms']for r in rows),'load_worker_eld_p99_max_ms':max(r['load_worker_eld_p99_max_ms']for r in rows),'backend_cpu_pct_max':max(r['backend_cpu_pct']for r in rows),'backend_delay_excess_mean_ms_max':max(r['backend_delay_mean_ms']-r['delay_ms']for r in rows),'backend_delay_excess_p95_ms_max':max(r['backend_delay_p95_ms']-r['delay_ms']for r in rows),'rps_spread_over_10pct':[r for r in agg if r['windows']==2 and r['rps_spread_pct']>10]}
 (ROOT/'health.json').write_text(json.dumps(health,indent=2));print(json.dumps({k:v for k,v in health.items() if k!='rps_spread_over_10pct'},indent=2))
 print('large / 50 ms / c64:')
 for r in sorted([r for r in agg if r['page']=='large' and r['delay_ms']==50 and r['concurrency']==64],key=lambda r:-r['rps']):
  print(r['framework'],round(r['rps'],1),round(r['latency_p95_ms'],1),round(r['cpu_ms_per_req'],2),round(r['eld_p99_ms'],1))
