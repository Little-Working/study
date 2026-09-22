"""Summarize Inspector CPU profile by sampled self time; not wall phase timing."""
import json, collections, pathlib
p=pathlib.Path(__file__).resolve().parent.parent/'evidence'
d=json.loads((p/'profile.cpuprofile').read_text())
nodes={n['id']:n for n in d['nodes']}
weights=collections.Counter()
for sample,delta in zip(d['samples'],d['timeDeltas']):weights[sample]+=delta
by_function=collections.Counter()
for i,us in weights.items():
    frame=nodes[i]['callFrame']
    by_function[(frame['functionName'],frame['url'],frame['lineNumber']+1)]+=us
total=sum(weights.values())
rows=[dict(function=f,url=url,line=line,selfMs=us/1000,pct=100*us/total) for (f,url,line),us in by_function.most_common()]
summary={'method':'Inspector CPU sampled self-time, 1ms default sampling; includes idle/GC; separate diagnostic run, not phase wall duration','sampledMs':total/1000,'functions':rows}
(p/'profile-summary.json').write_text(json.dumps(summary,indent=2))
for row in rows[:20]:print(json.dumps(row))
