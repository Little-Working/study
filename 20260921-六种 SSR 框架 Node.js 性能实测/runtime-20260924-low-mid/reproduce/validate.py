from common import *
for f in ['metrics.cjs','gc-stats.cjs','audit.cjs','load.mjs','__tests__']:docker('cp',str(HERE/f)+('/.' if (HERE/f).is_dir() else ''),'ssrbench3-builder:/bench/'+f)
(OUT/'sentinel-selftest.json').write_text(docker('exec','ssrbench3-builder','node','/bench/__tests__/audit.test.cjs'))
calibration={}
try:
 for name in FRAMEWORKS:
  start_app(name,audit=True)
  result=docker('exec','ssrbench3-load','node','/bench/__tests__/page.test.mjs',f'/bench/results/{name}-validation.json')
  print(name,result,flush=True);copy_result(name+'-validation.json')
  (OUT/(name+'-validation-runtime.log')).write_text(docker('logs','ssrbench3-app'))
  d=json.loads((OUT/(name+'-validation.json')).read_text())
  calibration[name]={size:{'minBytes':int(min(r['bytes'] for r in d['results'] if r['size']==size)*.985),'maxBytes':int(max(r['bytes'] for r in d['results'] if r['size']==size)*1.015),'observedMin':min(r['bytes'] for r in d['results'] if r['size']==size),'observedMax':max(r['bytes'] for r in d['results'] if r['size']==size)} for size in ['hello','medium','large']}
  stop_app()
 (OUT/'calibration.json').write_text(json.dumps(calibration,indent=2))
finally:stop_app()
