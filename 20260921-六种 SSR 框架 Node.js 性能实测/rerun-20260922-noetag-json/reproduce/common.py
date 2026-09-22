import pathlib,subprocess,json,time,datetime
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parent
OUT=ROOT/'evidence';OUT.mkdir(exist_ok=True)
IMAGE='public.ecr.aws/docker/library/node@sha256:2fe369e969550cde8e867afc3fe370b260140cab4a23d467074295b42163d553'
LABEL='ssrbench.run=20260922-v2';RESOURCE='ssrbench2-20260922'
FRAMEWORKS=['next','nuxt','svelte','tanstack','react-router','solid']
COMMANDS={'next':['node','node_modules/next/dist/bin/next','start','-H','0.0.0.0'],'nuxt':['node','.output/server/index.mjs'],'svelte':['node','build/index.js'],'tanstack':['node','.output/server/index.mjs'],'react-router':['node','server.mjs'],'solid':['node','.output/server/index.mjs']}
def docker(*args,check=True):
 r=subprocess.run(['docker',*args],capture_output=True,text=True)
 if check and r.returncode:raise RuntimeError(f'docker {args}: {r.stdout}\n{r.stderr}')
 return (r.stdout+(r.stderr if args[0]=='logs' else '')).strip()
def stop_app():
 if docker('ps','-aq','--filter','name=^ssrbench2-app$'):
  assert docker('inspect','-f','{{index .Config.Labels "ssrbench.run"}}','ssrbench2-app')=='20260922-v2'
  docker('rm','-f','ssrbench2-app')
def start_app(name,mode='lean',audit=False):
 stop_app()
 opts='--require=/bench/metrics.cjs --max-old-space-size=1024'+(' --require=/bench/audit.cjs' if audit else '')
 docker('run','-d','--name','ssrbench2-app','--label',LABEL,'--network',RESOURCE,'--cpuset-cpus=0-1','--cpus=2','--memory=1536m','--memory-swap=1536m','-v',RESOURCE+':/bench','-w',f'/bench/apps/{name}','-e','NODE_ENV=production','-e','NODE_OPTIONS='+opts,'-e','BENCH_METRICS_MODE='+mode,'-e','NEXT_TELEMETRY_DISABLED=1','-e','HOST=0.0.0.0','-e','HOSTNAME=0.0.0.0','-e','PORT=3000',IMAGE,*COMMANDS[name])
 for _ in range(60):
  if docker('inspect','-f','{{.State.Running}}','ssrbench2-app')!='true':raise RuntimeError(docker('logs','ssrbench2-app'))
  p=subprocess.run(['docker','exec','ssrbench2-load','node','-e',"fetch('http://ssrbench2-app:3000/?rid=ready').then(async r=>{if(r.status!==200||!(await r.text()).includes('BENCH_END'))process.exit(1)}).catch(()=>process.exit(1))"],capture_output=True)
  if p.returncode==0:return
  time.sleep(.5)
 raise RuntimeError('Startup timeout: '+name)
def copy_result(name):
 docker('cp','ssrbench2-load:/bench/results/'+name,str(OUT/name))
def cleanup():
 removed={}
 for kind,args in [('containers',['ps','-aq']),('networks',['network','ls','-q']),('volumes',['volume','ls','-q'])]:
  ids=docker(*args,'--filter','label='+LABEL).split()
  for i in ids:docker(*({'containers':['rm','-f'],'networks':['network','rm'],'volumes':['volume','rm']}[kind]),i)
  removed[kind]=ids
 remaining={k:docker(*args,'--filter','label='+LABEL).split() for k,args in [('containers',['ps','-aq']),('networks',['network','ls','-q']),('volumes',['volume','ls','-q'])]}
 (OUT/'cleanup.json').write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'removed':removed,'remaining':remaining},indent=2))
if __name__=='__main__':cleanup()
