"""Archive only a completed, verified run; preserve earlier reports and clean this staging directory."""
from pathlib import Path
import json,hashlib,shutil,subprocess,datetime,re
ROOT=Path(__file__).resolve().parent.parent
BASE=Path('/Users/liuhao/repo/github/study/20260921-六种 SSR 框架 Node.js 性能实测')
NAME='runtime-20260924-low-mid'
DEST=BASE/NAME
LABEL='ssrbench.run=20260924-runtime'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 assert ROOT==Path('/private/tmp/ssr-runtime-20260924'), 'Only clean the known staging directory'
 assert not DEST.exists(), 'Destination exists; inspect instead of overwriting'
 for name in ['REPORT.md','六种 SSR 框架 Node.js 性能实测.md']:
  target=BASE/name
  if target.exists():assert not (BASE/(target.stem+'-before-runtime-20260924'+target.suffix)).exists(), 'Backup already exists; inspect before publishing'
 h=json.loads((ROOT/'health.json').read_text());assert h['matrixWindows']==216 and h['errors']==h['invalid']==h['gcDropped']==0
 assert not any(json.loads((ROOT/'evidence/cleanup.json').read_text())['remaining'].values())
 remaining={}
 for kind,cmd in [('containers',['ps','-aq']),('networks',['network','ls','-q']),('volumes',['volume','ls','-q'])]:
  r=subprocess.run(['docker',*cmd,'--filter','label='+LABEL],capture_output=True,text=True,check=True);remaining[kind]=r.stdout.split()
 assert not any(remaining.values()),remaining
 (ROOT/'evidence/live-cleanup-check.json').write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'label':LABEL,'remaining':remaining},indent=2))
 for n in ['overview.png','overview.svg','eventloop-quantiles.png','gc-quantiles.png','eventloop-matrix.png','REPORT.md','RESULTS-eventloop.md','RESULTS-gc.md','RESULTS-resources.md']:
  assert (ROOT/n).is_file() and (ROOT/n).stat().st_size>100,n
 # Preserve all measured evidence. Generated app fixtures lived in the deleted Docker volume.
 shutil.copytree(ROOT,DEST,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 files=[p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
 for p in files:assert digest(p)==digest(DEST/p.relative_to(ROOT)),p
 report=(DEST/'REPORT.md').read_text()
 def prefix(m):
  target=m.group(1)
  return ']('+target+')' if '://' in target or target.startswith('#') else ']('+NAME+'/'+target+')'
 report=re.sub(r'\]\(([^)]+)\)',prefix,report)
 for name in ['REPORT.md','六种 SSR 框架 Node.js 性能实测.md']:
  target=BASE/name
  if target.exists():
   backup=BASE/(target.stem+'-before-runtime-20260924'+target.suffix)
   assert not backup.exists(),backup
   shutil.copy2(target,backup)
  target.write_text(report)
 for match in re.finditer(r'\]\(([^)]+)\)',report):
  target=match.group(1)
  if '://' not in target and not target.startswith('#'):assert (BASE/target).exists(),target
 removed=str(ROOT);shutil.rmtree(ROOT)
 (DEST/'evidence/local-cleanup.json').write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'removedStaging':removed,'exists':ROOT.exists(),'generatedAppData':'Docker volume removed; see cleanup.json','retained':'metrics, logs, source generators, lockfiles, reports and charts'},indent=2))
 manifest=[(digest(p),p.relative_to(DEST).as_posix()) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='SHA256SUMS']
 (DEST/'SHA256SUMS').write_text(''.join(f'{sha}  {name}\n' for sha,name in manifest))
 for sha,name in manifest:assert digest(DEST/name)==sha
 print(json.dumps({'published':str(DEST),'verifiedFiles':len(manifest),'stagingRemoved':not ROOT.exists(),'dockerRemaining':remaining},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
