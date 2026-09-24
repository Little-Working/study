"""Build phase only; leaves owned resources for validation/calibration and measurement.
On any failure clean all owned resources. Final runner also cleans in finally.
"""
from common import *
import tempfile,shutil,sys
for args in [('ps','-aq'),('network','ls','-q'),('volume','ls','-q')]:
 if docker(*args,'--filter','label='+LABEL):raise SystemExit('Existing owned resources; inspect before restarting.')
tmp=pathlib.Path(tempfile.mkdtemp(prefix='ssr-runtime-build-'))
try:
 subprocess.run([sys.executable,str(HERE/'prepare.py'),str(tmp)],check=True)
 rr=tmp/'apps/react-router/server.mjs'
 rr.write_text("import express from 'express';import {createRequestHandler} from '@react-router/express';import * as build from './build/server/index.js';const app=express();app.disable('etag');app.disable('x-powered-by');app.use(createRequestHandler({build,mode:'production'}));app.listen(3000,'0.0.0.0');\n")
 docker('volume','create','--label',LABEL,RESOURCE)
 docker('network','create','--label',LABEL,RESOURCE)
 docker('run','-d','--name','ssrbench3-builder','--label',LABEL,'--cpus=4','--memory=4g','-v',RESOURCE+':/bench','-e','npm_config_cache=/bench/npm-cache','-e','NEXT_TELEMETRY_DISABLED=1','-e','NUXT_TELEMETRY_DISABLED=1',IMAGE,'sleep','infinity')
 docker('cp',str(tmp/'apps'),'ssrbench3-builder:/bench/apps')
 for name in FRAMEWORKS:
  print('Installing/building',name,flush=True)
  try:docker('exec','ssrbench3-builder','sh','-c',f'cd /bench/apps/{name} && npm ci --no-audit --no-fund > /bench/{name}-install.log 2>&1 && npm run build > /bench/{name}-build.log 2>&1')
  finally:
   for stage in ['install','build']:docker('cp',f'ssrbench3-builder:/bench/{name}-{stage}.log',str(OUT/f'{name}-{stage}.log'),check=False)
 for filename in ['backend.mjs','metrics.cjs','gc-stats.cjs','audit.cjs','patch.mjs','inspect-build.mjs','load.mjs','__tests__']:
  if (HERE/filename).exists():docker('cp',str(HERE/filename),'ssrbench3-builder:/bench/'+filename)
 docker('exec','ssrbench3-builder','mkdir','-p','/bench/results')
 print(docker('exec','ssrbench3-builder','node','/bench/patch.mjs'),flush=True)
 docker('cp','ssrbench3-builder:/bench/results/patches.json',str(OUT/'patches.json'))
 docker('exec','ssrbench3-builder','node','/bench/inspect-build.mjs')
 docker('cp','ssrbench3-builder:/bench/results/build-audit.json',str(OUT/'build-audit.json'))
 docker('run','-d','--name','ssrbench3-backend','--label',LABEL,'--network',RESOURCE,'--cpuset-cpus=6-7','--cpus=2','--memory=512m','-v',RESOURCE+':/bench','-e','NODE_ENV=production',IMAGE,'node','--require','/bench/metrics.cjs','/bench/backend.mjs')
 docker('run','-d','--name','ssrbench3-load','--label',LABEL,'--network',RESOURCE,'--cpuset-cpus=2-5','--cpus=4','--memory=1g','-v',RESOURCE+':/bench',IMAGE,'sleep','infinity')
 info=json.loads(docker('info','--format','{{json .}}'));env={k:info.get(k) for k in ['NCPU','MemTotal','Architecture','OperatingSystem','KernelVersion','ServerVersion']}
 env['imageId']=json.loads(docker('image','inspect',IMAGE))[0]['Id']
 env['node']=docker('exec','ssrbench3-builder','node','--version')
 (OUT/'environment.json').write_text(json.dumps(env,indent=2));print('Build phase complete',flush=True)
except BaseException:
 cleanup();raise
finally:
 shutil.rmtree(tmp)
 (OUT/'build-local-cleanup.json').write_text(json.dumps({'removed':str(tmp),'exists':tmp.exists()}))
