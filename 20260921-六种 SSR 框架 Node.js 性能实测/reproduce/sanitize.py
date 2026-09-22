"""Keep runtime evidence without retaining synthetic per-request access-log rows."""
import pathlib,re,collections,json
ROOT=pathlib.Path(__file__).resolve().parent.parent/'evidence'
summary={}
for p in [*ROOT.glob('*runtime.log'),*ROOT.glob('*startup.log')]:
 lines=p.read_text().splitlines();kept=[];statuses=collections.Counter()
 for line in lines:
  m=re.match(r'GET /\S* (\d{3}) ',line)
  if m:statuses[m.group(1)]+=1
  else:kept.append(line)
 if statuses:
  kept.append('[ssrbench] Synthetic per-request access rows removed; status counts: '+json.dumps(dict(statuses),sort_keys=True))
  p.write_text('\n'.join(kept)+'\n');summary[p.name]=dict(statuses)
if summary:
 p=ROOT/'access-log-summary.json'
 existing=json.loads(p.read_text())if p.exists()else{}
 existing.update(summary);p.write_text(json.dumps(existing,indent=2))
print('Access logs retained as status-count summaries:',len(summary))
