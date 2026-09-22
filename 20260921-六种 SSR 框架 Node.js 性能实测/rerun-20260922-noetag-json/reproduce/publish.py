"""Publish a completed, verified report tree to the user-specified directory.
Run after plots, report review, and resource cleanup. No services are started here.
"""
from pathlib import Path
import hashlib,json,re,shutil,sys
RUN=Path(__file__).resolve().parent.parent
BASE=RUN.parent
DEST=Path(sys.argv[1]).resolve()
health=json.loads((RUN/'health.json').read_text())
assert health['windows']==402 and health['errors']==0 and health['exactHtmlBytesVerifiedWindows']==402
cleanup=json.loads((RUN/'evidence/cleanup.json').read_text())
assert all(not v for v in cleanup['remaining'].values())
for name in ['REPORT.md','RESULTS.md','METHODOLOGY.md','overview.png','matrix.png','runtime.png','overhead.png']:
 assert (RUN/name).is_file(),name
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
ignored={'__pycache__','.DS_Store'}
# Preserve independent edits to previously delivered historical artifacts.
conflicts=[]
for p in BASE.rglob('*'):
 if not p.is_file() or RUN.name in p.relative_to(BASE).parts or any(k in p.parts for k in ignored):continue
 q=DEST/p.relative_to(BASE)
 if q.is_file() and digest(p)!=digest(q):conflicts.append(str(p.relative_to(BASE)))
if conflicts:raise SystemExit('Destination contains independently changed historical files; reconcile without overwriting: '+repr(conflicts))
archive=BASE/'REPORT-20260922-before-noetag-json.md'
if not archive.exists():shutil.copy2(BASE/'REPORT.md',archive)
content=(RUN/'REPORT.md').read_text()
def prefix_link(match):
 url=match.group(2)
 return match.group(1)+(url if url.startswith(('https://','http://','#','/')) else RUN.name+'/'+url)+')'
content=re.sub(r'(!?\[[^\]]*\]\()([^\)]+)\)',prefix_link,content)
content+='\n## 历史实验\n\n本轮保留旧数据，不用新参数覆盖旧实验的数值：\n\n- [本轮独立目录及原始报告]('+RUN.name+'/REPORT.md)\n- [本轮之前的主报告](REPORT-20260922-before-noetag-json.md)\n- [2026-09-21 初测原始报告](REPORT-20260921-original.md)\n- [SvelteKit ETag 专项复核](svelte-recheck-20260922/REPORT.md)\n'
(BASE/'REPORT.md').write_text(content)
(BASE/'六种 SSR 框架 Node.js 性能实测.md').write_text(content)
for filename in ['METHODOLOGY.md','FINDINGS.md']:
 p=BASE/filename
 old=p.read_text()
 marker='> 最新无压缩 / 无 HTML ETag、600 KB 后端 JSON 复测：'
 if not old.startswith(marker):p.write_text(marker+'[查看本轮完整报告]('+RUN.name+'/REPORT.md) 和 [本轮方法]('+RUN.name+'/METHODOLOGY.md)。以下保留此前实验内容。\n\n'+old)
def manifest(root):
 paths=sorted(p for p in root.rglob('*') if p.is_file() and p.name!='SHA256SUMS' and not any(k in p.parts for k in ignored))
 (root/'SHA256SUMS').write_text(''.join(digest(p)+'  '+p.relative_to(root).as_posix()+'\n' for p in paths))
manifest(RUN);manifest(BASE)
shutil.copytree(BASE,DEST,dirs_exist_ok=True,ignore=shutil.ignore_patterns(*ignored))
copied=0
for p in BASE.rglob('*'):
 if p.is_file() and not any(k in p.parts for k in ignored):
  q=DEST/p.relative_to(BASE);assert q.is_file() and digest(p)==digest(q),str(q);copied+=1
print(json.dumps({'destination':str(DEST),'verifiedFiles':copied,'report':str(DEST/'REPORT.md')},ensure_ascii=False))
