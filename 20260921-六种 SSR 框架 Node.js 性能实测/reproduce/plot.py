"""Generate standalone publication/shareable charts with matplotlib."""
import json,pathlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
ROOT=pathlib.Path(__file__).resolve().parent.parent
DATA=json.loads((ROOT/'summary.json').read_text())
NAMES={'next':'Next.js','nuxt':'Nuxt','svelte':'SvelteKit','tanstack':'TanStack Start','react-router':'React Router','solid':'SolidStart'}
COLORS=dict(zip(NAMES,['#5173D7','#25A785','#DB7241','#9B60C4','#D64A68','#2C98AD']))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','figure.facecolor':'#FAFBFE','axes.facecolor':'#FAFBFE','axes.labelcolor':'#303749','text.color':'#182137','xtick.color':'#596174','ytick.color':'#596174','savefig.facecolor':'#FAFBFE'})
sust=sorted(DATA['sustained'],key=lambda x:x['rps'])
if len(sust)==6 and all(r['windows']==2 for r in sust):
 fig,axes=plt.subplots(2,3,figsize=(15,8.4))
 metrics=[('rps','Complete HTML throughput','responses / s'),('latency_p95_ms','Full response latency, p95','ms'),('cpu_ms_per_req','Node CPU per successful response','CPU ms / response'),('eld_p99_ms','Event-loop delay, p99','ms (10 ms sampling baseline)'),('gc_observed_pct','Observed GC duration / wall time','% (not an exact pause ratio)'),('rss_peak_mib','Sampled peak RSS','MiB (200 ms samples)')]
 for ax,(key,title,label) in zip(axes.flat,metrics):
  vals=[r[key]for r in sust]; bars=ax.barh([NAMES[r['framework']]for r in sust],vals,color=[COLORS[r['framework']]for r in sust],height=.63)
  ax.set_title(title,loc='left',fontsize=12,pad=12);ax.set_xlabel(label);ax.grid(axis='x',alpha=.14);ax.set_axisbelow(True);ax.set_xlim(0,max(vals)*1.22)
  for bar,val in zip(bars,vals):ax.text(val+max(vals)*.018,bar.get_y()+bar.get_height()/2,f'{val:.1f}',va='center',fontsize=10)
 fig.suptitle('Production SSR on Node.js 24.21.0 / ARM64 Docker',x=.03,y=.985,ha='left',fontsize=20,fontweight='bold')
 fig.text(.03,.93,'~1.5 MiB HTML | 50 ms backend | 64 concurrent requests | 2 fresh-process runs: 10 s warmup + 30 s measurement each',fontsize=11,color='#596174')
 fig.text(.03,.016,'2 runs; weighted RPS, median window metrics, maximum sampled memory. 1,536 records; actual HTML differs by framework markers. 2 CPU / 1,536 MiB app limit. No compression.',fontsize=9,color='#596174')
 fig.tight_layout(rect=[0,.04,1,.90],w_pad=3,h_pad=2.7)
 for ext in ['png','svg']:fig.savefig(ROOT/f'overview.{ext}',dpi=170)
 plt.close(fig)
 fig,axes=plt.subplots(2,2,figsize=(14,9))
 for repeat in [1,2]:
  for r in sust:
   part='sustained' if repeat==1 else 'sustained2'
   raw=json.loads((ROOT/'evidence'/f"{r['framework']}-{part}-large-d50-c64.json").read_text())
   for ax,key,title in zip(axes[repeat-1],['rss','heapUsed'],['RSS','V8 heap used']):
    ss=raw['app']['samples'];ax.plot([v['t']/1000 for v in ss],[v[key]/2**20 for v in ss],color=COLORS[r['framework']],label=NAMES[r['framework']],linewidth=1.4)
    ax.set_title(f'{title} — sustained run {repeat}',loc='left');ax.set_xlabel('Seconds since metrics reset');ax.set_ylabel('MiB');ax.grid(alpha=.15);ax.set_ylim(bottom=0)
 for col in [0,1]:
  maximum=max(max(line.get_ydata()) for row in [0,1] for line in axes[row,col].lines)*1.05;axes[0,col].set_ylim(0,maximum);axes[1,col].set_ylim(0,maximum)
 axes[0,1].legend(loc='upper right',fontsize=9,ncol=2)
 fig.suptitle('Memory under ~1.5 MiB HTML / 50 ms backend / concurrency 64',fontsize=16,fontweight='bold')
 fig.text(.02,.012,'200 ms sampling; fresh process per run, natural GC, no forced collection. These traces do not establish long-term memory stability.',fontsize=9,color='#596174')
 fig.tight_layout(rect=[0,.04,1,.94]);fig.savefig(ROOT/'memory.png',dpi=170);plt.close(fig)
scenarios=DATA['scenarios']
if len(scenarios)==162:
 fig,axes=plt.subplots(3,3,figsize=(14,11))
 for row,page in enumerate(['hello','medium','large']):
  for col,delay in enumerate([50,200,500]):
   ax=axes[row,col];rr=sorted([r for r in scenarios if r['page']==page and r['delay_ms']==delay and r['concurrency']==64],key=lambda r:r['rps'])
   bars=ax.barh([NAMES[r['framework']]for r in rr],[r['rps']for r in rr],color=[COLORS[r['framework']]for r in rr],height=.62)
   ax.errorbar([r['rps']for r in rr],range(len(rr)),xerr=[[r['rps']-r['rps_min']for r in rr],[r['rps_max']-r['rps']for r in rr]],fmt='none',color='#303749',capsize=3,linewidth=1)
   ax.set_title(f'{page.title()} | backend {delay} ms',loc='left');ax.set_xlabel('Complete successful responses / s');ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
 fig.suptitle('Throughput matrix at concurrency 64',fontsize=20,fontweight='bold',x=.03,ha='left')
 fig.text(.03,.025,'Bars = total successful responses / total elapsed time over 2 runs. Whiskers = run min/max, NOT confidence intervals. 8 s launch windows + drain.',fontsize=9,color='#596174')
 fig.tight_layout(rect=[0,.06,1,.95],h_pad=2.4,w_pad=2.6);fig.savefig(ROOT/'matrix.png',dpi=170);plt.close(fig)
print('Charts generated for completed datasets.')
