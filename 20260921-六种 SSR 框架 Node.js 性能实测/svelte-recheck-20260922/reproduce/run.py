"""Run only resources labelled ssrbench.run=20260922. Requires prepared Docker volume.
Validation: python3 run.py validate
Benchmark: python3 run.py matrix
Cleanup: python3 run.py cleanup
"""
import subprocess, json, pathlib, sys, time, random, itertools, datetime
HERE=pathlib.Path(__file__).resolve().parent
OUT=HERE.parent/'evidence'
OUT.mkdir(exist_ok=True)
IMAGE='node:24-bookworm-slim'
LABEL='ssrbench.run=20260922'
COMMANDS={'next':['node','node_modules/next/dist/bin/next','start','-H','0.0.0.0'], 'nuxt':['node','.output/server/index.mjs'],'svelte':['node','build/index.js'],'tanstack':['node','.output/server/index.mjs'],'react-router':['node','node_modules/@react-router/serve/bin.cjs','build/server/index.js'],'solid':['node','.output/server/index.mjs']}
def docker(*args,check=True):
    r=subprocess.run(['docker',*args],capture_output=True,text=True)
    if check and r.returncode:raise RuntimeError(f'docker {args}: {r.stdout}\n{r.stderr}')
    return (r.stdout + (r.stderr if args[0]=='logs' else '')).strip()
def stop_app():
    if docker('ps','-aq','--filter','name=^ssrbench-app$'):
        label=docker('inspect','-f','{{index .Config.Labels "ssrbench.run"}}','ssrbench-app')
        assert label=='20260922'
        docker('rm','-f','ssrbench-app')
def start_app(name):
    stop_app()
    docker('run','-d','--name','ssrbench-app','--label',LABEL,'--network','ssrbench-20260922','--cpuset-cpus=0-1','--cpus=2','--memory=1536m','--memory-swap=1536m','-v','ssrbench-20260922:/bench','-w',f'/bench/apps/{name}','-e','NODE_ENV=production','-e','NODE_OPTIONS=--require=/bench/metrics.cjs --max-old-space-size=1024','-e','BENCH_METRICS_PORT=9100','-e','NEXT_TELEMETRY_DISABLED=1','-e','HOST=0.0.0.0','-e','HOSTNAME=0.0.0.0','-e','PORT=3000',IMAGE,*COMMANDS[name])
    for i in range(30):
        r=docker('exec','ssrbench-load','node','-e',"fetch('http://ssrbench-app:9100/').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))",check=False)
        ready=docker('inspect','-f','{{.State.Running}}','ssrbench-app')
        if ready!='true':raise RuntimeError(docker('logs','ssrbench-app',check=False))
        # Poll application itself so framework startup is excluded.
        p=subprocess.run(['docker','exec','ssrbench-load','node','-e',"fetch('http://ssrbench-app:3000/?rid=ready').then(async r=>{if(r.status!==200||!(await r.text()).includes('BENCH_END'))process.exit(1)}).catch(()=>process.exit(1))"],capture_output=True)
        if p.returncode==0:return
        time.sleep(.5)
    raise RuntimeError(f'{name} not ready: '+docker('logs','ssrbench-app',check=False))
def load(config):
    return docker('exec','ssrbench-load','node','/bench/load.mjs',json.dumps(config))
def validate(names):
    for name in names:
        start_app(name)
        print(name,docker('exec','ssrbench-load','node','/bench/__tests__/page.test.mjs',f'/bench/results/{name}-validation.json'),flush=True)
        docker('cp',f'ssrbench-load:/bench/results/{name}-validation.json',str(OUT/f'{name}-validation.json'))
        (OUT/f'{name}-startup.log').write_text(docker('logs','ssrbench-app',check=False))
    stop_app()
def matrix():
    frameworks=list(COMMANDS)
    # Reverse second-round order to reduce machine/order drift.
    for repeat in [1,2]:
        order=frameworks if repeat==1 else list(reversed(frameworks))
        for name in order:
            start_app(name)
            load(dict(size='large',delay=50,connections=16,seconds=8,measure=False))
            combos=list(itertools.product(['hello','medium','large'],[50,200,500]))
            random.Random(2109+repeat).shuffle(combos)
            for size,delay in combos:
                for connections in ([1,16,64] if repeat==1 else [64,16]):
                    stem=f'{name}-{size}-d{delay}-c{connections}-r{repeat}'
                    if (OUT/f'{stem}.json').exists():continue
                    bounds={'hello':(100,20000),'medium':(750*1024,850*1024),'large':(int(1.4*1024*1024),int(1.65*1024*1024))}[size]
                    conf=dict(framework=name,size=size,delay=delay,connections=connections,repeat=repeat,seconds=6 if connections==1 else 8,minBytes=bounds[0],maxBytes=bounds[1])
                    load({**conf,'seconds':1,'measure':False})
                    result=load({**conf,'out':f'/bench/results/{stem}.json'})
                    docker('cp',f'ssrbench-load:/bench/results/{stem}.json',str(OUT/f'{stem}.json'))
                    r=json.loads((OUT/f'{stem}.json').read_text())
                    assert r['complete']==r['good']==r['issued']==r['backendRequests']['calls']==r['backendRequests']['completed'],stem
                    assert not r['errors'] and not r['invalid'],stem
                    assert r['backendRequests']['inflight']==0,stem
                    print(datetime.datetime.now().isoformat(timespec='seconds'),stem,result,flush=True)
            (OUT/f'{name}-round{repeat}-runtime.log').write_text(docker('logs','ssrbench-app',check=False))
            stop_app()
    # Sustained check: fresh process, 10 s warmup + 30 s full-HTML completion load.
    for name in frameworks:
        stem=f'{name}-sustained-large-d50-c64'
        if (OUT/f'{stem}.json').exists():continue
        start_app(name)
        conf=dict(framework=name,size='large',delay=50,connections=64,minBytes=int(1.4*1024*1024),maxBytes=int(1.65*1024*1024))
        load({**conf,'seconds':10,'measure':False})
        result=load({**conf,'seconds':30,'out':f'/bench/results/{stem}.json','phase':'sustained'})
        docker('cp',f'ssrbench-load:/bench/results/{stem}.json',str(OUT/f'{stem}.json'))
        print(stem,result,flush=True)
        stop_app()
def cleanup():
    removed={}
    for kind,args in [('containers',['ps','-aq']),('networks',['network','ls','-q']),('volumes',['volume','ls','-q'])]:
        ids=docker(*args,'--filter','label='+LABEL).split()
        for resource in ids:
            if kind=='containers':docker('rm','-f',resource)
            elif kind=='networks':docker('network','rm',resource)
            else:docker('volume','rm',resource)
        removed[kind]=ids
    (OUT/'cleanup.json').write_text(json.dumps({'time':datetime.datetime.now(datetime.timezone.utc).isoformat(),'removed':removed,'remaining':{k:docker(*a,'--filter','label='+LABEL).split() for k,a in [('containers',['ps','-aq']),('networks',['network','ls','-q']),('volumes',['volume','ls','-q'])]}},indent=2))
if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='validate':validate(sys.argv[2:] or list(COMMANDS))
    elif mode=='matrix':matrix()
    elif mode=='cleanup':cleanup()
