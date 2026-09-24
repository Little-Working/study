"""Run only after all measurements and Docker cleanup."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
ROOT=Path(__file__).resolve().parent.parent
assert (ROOT/'evidence/run-complete.json').exists()
assert not any(json.loads((ROOT/'evidence/cleanup.json').read_text())['remaining'].values())
X=json.loads((ROOT/'summary.json').read_text())
ORDER=['next','nuxt','svelte','tanstack','react-router','solid']
NAMES={'solid':'SolidStart','svelte':'SvelteKit','tanstack':'TanStack Start','nuxt':'Nuxt','react-router':'React Router','next':'Next.js'}
SIZES=['hello','medium','large'];TITLES={'hello':'Hello World','medium':'~800 KB HTML','large':'~1.5 MB HTML'}
Q=['p50Ms','p75Ms','p90Ms','p95Ms','p99Ms','maxMs']
R={(r['framework'],r['size'],r['delay'],r['connections']):r for r in X['matrix']}
plt.rcParams.update({'font.size':11,'axes.titlesize':13,'figure.facecolor':'#f8fafc','axes.facecolor':'white','axes.spines.top':False,'axes.spines.right':False,'savefig.facecolor':'#f8fafc'})
COLORS=['#64748b','#10a465','#e76f51','#7c3aed','#2563eb','#0d9488']
def save(fig,name):
 fig.savefig(ROOT/(name+'.png'),dpi=170,bbox_inches='tight');fig.savefig(ROOT/(name+'.svg'),bbox_inches='tight');plt.close(fig)

fig,axes=plt.subplots(3,2,figsize=(13,12))
for i,size in enumerate(SIZES):
 for j,metric in enumerate(['eventLoop','gc']):
  ax=axes[i,j];vals=[R[f,size,200,8][metric]['p99Ms'] for f in ORDER]
  bars=ax.barh([NAMES[f] for f in ORDER],[v or 0 for v in vals],color=COLORS);ax.invert_yaxis();ax.set_title(TITLES[size]+' | '+('Event Loop p99' if j==0 else 'GC event p99'));ax.set_xlabel('milliseconds (10 ms timer included)' if metric=='eventLoop' else 'observed event duration (ms)');ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
  if metric=='gc' and all(0<R[f,size,200,8]['gc']['count']<100 for f in ORDER):ax.set_title(TITLES[size]+' | GC event p99\nSparse: p99 equals the sample maximum',fontsize=12)
  for k,(bar,v) in enumerate(zip(bars,vals)):
   label='not observed' if v is None else f'{v:.2f}'
   if metric=='gc':label+=f"  (n={R[ORDER[k],size,200,8]['gc']['count']})"
   ax.text(bar.get_width()+max([a or 0 for a in vals])*.02,bar.get_y()+bar.get_height()/2,label,va='center',fontsize=9)
  ax.set_xlim(0,max([v or 0 for v in vals])*1.5+0.01)
fig.suptitle('Node.js runtime under moderate concurrency\nC=8 | backend 200 ms | production | no compression / HTML ETag',fontsize=17,y=.99)
fig.text(.5,.015,'Event Loop: median of two window p99 values, 10 ms sampling baseline included.\nGC: pooled event-duration p99; n<100 is sparse. Different metrics have different denominators.',ha='center',fontsize=10)
fig.tight_layout(rect=[0,.065,1,.94],h_pad=2);save(fig,'overview')

for metric,name,title in [('eventLoop','eventloop-quantiles','Event Loop delay'),('gc','gc-quantiles','GC event duration')]:
 values=[R[f,s,200,c][metric][q] for f in ORDER for s in SIZES for c in [1,8] for q in Q];positive=[v for v in values if v and v>0]
 norm=LogNorm(vmin=max(min(positive),.0001),vmax=max(positive));cmap=plt.get_cmap('YlOrRd').copy();cmap.set_bad('#e2e8f0')
 fig,axes=plt.subplots(3,2,figsize=(14,12));fig.subplots_adjust(left=.15,right=.89,bottom=.1,top=.89,wspace=.60,hspace=.56)
 for i,size in enumerate(SIZES):
  for j,c in enumerate([1,8]):
   ax=axes[i,j];a=np.array([[R[f,size,200,c][metric][q] if R[f,size,200,c][metric][q] is not None else np.nan for q in Q] for f in ORDER]);im=ax.imshow(a,cmap=cmap,norm=norm,aspect='auto')
   labels=[NAMES[f] if metric=='eventLoop' else NAMES[f]+f" (n={R[f,size,200,c]['gc']['count']})" for f in ORDER]
   ax.set_yticks(range(6),labels);ax.set_xticks(range(6),['p50','p75','p90','p95','p99','max']);ax.set_title(TITLES[size]+f' | C={c}');ax.tick_params(axis='both',length=0,labelsize=9)
   for r in range(6):
    for k in range(6):
     v=a[r,k];ax.text(k,r,'—' if np.isnan(v) else f'{v:.2f}',ha='center',va='center',fontsize=9,color='white' if not np.isnan(v) and norm(v)>.67 else '#0f172a')
 cax=fig.add_axes([.92,.20,.016,.58]);fig.colorbar(im,cax=cax,label='milliseconds (log color scale)')
 fig.suptitle(title+' | all requested percentiles\nBackend 200 ms | two 20-second windows per cell',fontsize=17,y=.97)
 note='EL percentiles: median of window values; max: maximum across windows. Raw values include the 10 ms timer interval.' if metric=='eventLoop' else 'GC: nearest-rank quantiles of pooled events; max is observed maximum. n<100: sparse p99; gray: not observed.'
 fig.text(.5,.035,note,ha='center',fontsize=10);save(fig,name)

fig,axes=plt.subplots(2,3,figsize=(15,8));vals=[r['eventLoop']['p99Ms'] for r in X['matrix']];norm=LogNorm(vmin=min(vals),vmax=max(vals))
for i,c in enumerate([1,8]):
 for j,size in enumerate(SIZES):
  ax=axes[i,j];a=np.array([[R[f,size,d,c]['eventLoop']['p99Ms'] for d in [50,200,500]] for f in ORDER]);im=ax.imshow(a,cmap='YlOrRd',norm=norm,aspect='auto');ax.set_xticks(range(3),['50 ms','200 ms','500 ms']);ax.set_yticks(range(6),[NAMES[f] for f in ORDER]);ax.set_title(TITLES[size]+f' | C={c}');ax.tick_params(length=0,labelsize=9)
  for r in range(6):
   for k in range(3):ax.text(k,r,f'{a[r,k]:.1f}',ha='center',va='center',fontsize=10,color='white' if norm(a[r,k])>.67 else '#0f172a')
fig.suptitle('Event Loop p99 across every page, backend delay and concurrency',fontsize=17)
fig.tight_layout(rect=[0,.05,.95,.93]);cax=fig.add_axes([.96,.17,.012,.61]);fig.colorbar(im,cax=cax,label='ms');fig.text(.5,.015,'Two-window percentile median | 10 ms native sampling interval | no cross-scenario averaging',ha='center',fontsize=10);save(fig,'eventloop-matrix')
print('Generated overview, eventloop-quantiles, gc-quantiles, eventloop-matrix PNG + SVG')
