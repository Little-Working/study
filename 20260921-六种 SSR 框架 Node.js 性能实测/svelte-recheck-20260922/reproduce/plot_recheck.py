import json,pathlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=pathlib.Path(__file__).resolve().parent.parent
d=json.loads((R/'summary.json').read_text())
rows=d['original']+[r for r in d['recheck'] if r['phase']=='focus']
names=['Original 30s #1','Original 30s #2']+[f'Recheck 60s #{i+1}' for i in range(len(rows)-2)]
colors=['#8898ad']*2+['#e66b37']*(len(rows)-2)
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(1,3,figsize=(15,5.8),layout='constrained')
for ax,key,title in zip(axes,['rps','p95','cpuMsPerRequest'],['Complete HTML responses / second','Full-response p95 (ms)','Process CPU time / request (ms)']):
    values=[r[key] for r in rows]
    ax.barh(names,values,color=colors);ax.invert_yaxis();ax.set_title(title,pad=14)
    ax.set_xlim(0,max(values)*1.24);ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
    for i,v in enumerate(values):ax.text(v+max(values)*.025,i,f'{v:.1f}',va='center')
fig.suptitle('SvelteKit isolated recheck | 1.482 MiB HTML | 50 ms backend | 64 connections\nSame locked versions, Node image and CPU limits; each bar is an independent process',fontsize=14)
fig.savefig(R/'comparison.png',dpi=180);fig.savefig(R/'comparison.svg');plt.close(fig)
p=json.loads((R/'evidence/profile-summary.json').read_text())
rows=p['functions'][:8];fig,ax=plt.subplots(figsize=(11,5.6),layout='constrained')
labels=[r['function'] or '(anonymous)' for r in rows]
ax.barh([f'{i+1}. {s}' for i,s in enumerate(labels)],[r['pct'] for r in rows],color='#376791');ax.invert_yaxis()
ax.set_xlabel('Share of sampled self time (%) — includes idle/GC');ax.set_title('Separate diagnostic CPU profile: top frames')
ax.set_xlim(0,max(r['pct'] for r in rows)*1.2)
for i,r in enumerate(rows):ax.text(r['pct']+.5,i,f"{r['pct']:.1f}%",va='center')
fig.savefig(R/'profile.png',dpi=180);fig.savefig(R/'profile.svg')
plt.close(fig)
controls=[r for r in d['recheck'] if r['phase'].startswith('control-')]
if controls:
    labels=['Default before','Diagnostic: no ETag','Default restored']
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    for ax,key,title in zip(axes,['rps','p95'],['Complete HTML responses / second','Full-response p95 (ms)']):
        values=[r[key] for r in controls];ax.barh(labels,values,color=['#8898ad','#3a917f','#8898ad']);ax.invert_yaxis()
        ax.set_xlim(0,max(values)*1.25);ax.set_title(title,pad=15)
        for i,v in enumerate(values):ax.text(v+max(values)*.025,i,f'{v:.1f}',va='center')
    fig.suptitle('ETag diagnostic control | 1.482 MiB / 50 ms / 64 connections\nModified HTTP semantics: diagnostic only, excluded from framework ranking',fontsize=13)
    fig.savefig(R/'etag-control.png',dpi=180);fig.savefig(R/'etag-control.svg')
