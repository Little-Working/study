"""Render measured results with matplotlib; run only after load testing ends."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parent.parent
S=json.loads((ROOT/'summary.json').read_text())
COLORS={'next':'#2878b5','nuxt':'#009c75','svelte':'#df5d38','tanstack':'#b98a16','react-router':'#9153a5','solid':'#36778b'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','figure.facecolor':'#fbfcfe','axes.facecolor':'#fbfcfe','grid.alpha':.18,'savefig.facecolor':'#fbfcfe'})
def save(fig,name):
 for ext in ['png','svg']:fig.savefig(ROOT/(name+'.'+ext),dpi=170,bbox_inches='tight')
 plt.close(fig)
F=S['focus'];names=[x['name'].replace(' Start','\nStart').replace(' Router','\nRouter') for x in F];colors=[COLORS[x['framework']] for x in F];xx=np.arange(6)
def bars(ax,key,title,unit,lo=None,hi=None,digits=1):
 values=np.array([x[key] for x in F]);err=None
 if lo:err=np.array([values-[x[lo] for x in F],[x[hi] for x in F]-values])
 ax.bar(xx,values,color=colors,width=.66,yerr=err,capsize=4,error_kw={'lw':1.3,'ecolor':'#263448'})
 ax.set_xticks(xx,names);ax.set_ylabel(unit);ax.set_title(title,loc='left',pad=13);ax.grid(axis='y');ax.set_axisbelow(True)
 for i,v in enumerate(values):ax.text(i,(F[i][hi] if hi else v)+max(values)*.03,f'{v:.{digits}f}',ha='center',va='bottom',fontsize=9)
 ax.set_ylim(0,max([x[hi] for x in F] if hi else values)*1.2)
fig,axs=plt.subplots(2,2,figsize=(14,9),layout='constrained')
fig.suptitle('Six SSR frameworks | full response, gzip & HTML ETag disabled',fontsize=18,fontweight='bold')
bars(axs[0,0],'rpsMedian','Successful throughput — higher is better','responses / second','rpsMin','rpsMax')
bars(axs[0,1],'p95MedianMs','Full-response p95 — lower is better','milliseconds','p95MinMs','p95MaxMs')
bars(axs[1,0],'cpuMsPerRequestMedian','Application CPU per completed request','CPU milliseconds / request')
bars(axs[1,1],'rssMaxMiB','Largest sampled RSS across three windows','MiB')
fig.supxlabel('600,000-byte backend JSON • ~1.6 MB HTML • 50 ms backend • concurrency 64\n3 fresh processes × 30 s; bars are medians except RSS; whiskers show min–max, not confidence intervals.',fontsize=10)
save(fig,'overview')

fig,axs=plt.subplots(3,3,figsize=(15,12))
fig.subplots_adjust(left=.065,right=.985,top=.91,bottom=.105,hspace=.42,wspace=.24)
fig.suptitle('Full matrix | successful complete responses per second',fontsize=18,fontweight='bold',y=.985)
fig.text(.5,.95,'Two 8-second measured windows per cell, after warmup. RPS = total successes / total actual elapsed time.',ha='center',fontsize=10)
for row,size in enumerate(['hello','medium','large']):
 for col,delay in enumerate([50,200,500]):
  ax=axs[row,col]
  for f,color in COLORS.items():
   cells=sorted([x for x in S['matrix'] if x['framework']==f and x['size']==size and x['delay']==delay],key=lambda x:x['connections'])
   ax.plot([1,16,64],[x['rps'] for x in cells],'-o',color=color,label=cells[0]['name'],lw=1.7,ms=4)
  ax.set_title(f'{size.capitalize()} | backend {delay} ms',loc='left');ax.set_xscale('log',base=2);ax.set_xticks([1,16,64],['1','16','64']);ax.set_xlabel('Concurrent requests');ax.set_ylabel('Successful RPS');ax.set_ylim(bottom=0);ax.grid()
handles,labels=axs[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.025),ncol=6,frameon=False)
save(fig,'matrix')

fig,axs=plt.subplots(2,2,figsize=(14,9),layout='constrained')
fig.suptitle('Node.js runtime | large page, 50 ms backend, concurrency 64',fontsize=18,fontweight='bold')
bars(axs[0,0],'cpuPctMedian','Application process CPU','% of one logical CPU')
bars(axs[0,1],'eventLoopP99MedianMs','Raw event-loop delay p99','milliseconds (20 ms resolution)')
bars(axs[1,0],'gcMsPerRequestMedian','Observed GC duration per request','GC milliseconds / request',digits=3)
bars(axs[1,1],'heapMaxMiB','Largest sampled V8 heap used','MiB')
fig.supxlabel('Median of three 30-second windows except heap peak. Raw event-loop delay includes its sampling interval.\nGC event duration is not an exact stop-the-world percentage or GC CPU measurement.',fontsize=10)
save(fig,'runtime')

C=S['controls'];labels=[x['name'].replace(' Start','\nStart').replace(' Router','\nRouter') for x in C]
fig,axs=plt.subplots(1,3,figsize=(16,5.8),layout='constrained')
fig.suptitle('Overhead controls | measured RPS change, not a correction multiplier',fontsize=17,fontweight='bold')
for ax,key,title in zip(axs,['leanVsOffPct','workers8VsDefaultPct','noSamplingVsDefaultPct'],['Lean monitoring vs off','8 load workers vs 4','No content sampling vs 1/128']):
 vals=[x[key] for x in C];ax.barh(np.arange(6),vals,color=[COLORS[x['framework']] for x in C]);ax.set_yticks(np.arange(6),labels);ax.invert_yaxis();ax.axvline(0,color='#394555',lw=1);ax.set_title(title,loc='left');ax.set_xlabel('RPS difference (%)');ax.grid(axis='x');ax.set_axisbelow(True)
 bound=max(abs(v) for v in vals)+8;ax.set_xlim(-bound,bound)
 for i,v in enumerate(vals):ax.text(v+(1 if v>=0 else -1),i,f'{v:+.1f}%',va='center',ha='left' if v>=0 else 'right',fontsize=9)
fig.supxlabel('Two windows per condition; balanced order. Same load CPU quota (4). Positive = faster measured throughput.\nFresh-process/JIT/GC variation remains; small or negative differences do not prove zero or negative overhead.',fontsize=10)
save(fig,'overhead')
