"""SvelteKit-only reproduction. All Docker mutations scoped to this benchmark.
Run `python3 recheck.py`; dependencies and services removed in finally.
"""
import pathlib, tempfile, shutil, subprocess, json, random, itertools, time
import run
from run import docker, HERE, OUT, LABEL, load, start_app, stop_app, cleanup
BASE='public.ecr.aws/docker/library/node@sha256:2fe369e969550cde8e867afc3fe370b260140cab4a23d467074295b42163d553'
run.IMAGE=BASE
run.COMMANDS={'svelte':['node','build/index.js']}
BOUNDS={'hello':(100,20000),'medium':(750*1024,850*1024),'large':(int(1.4*1024*1024),int(1.65*1024*1024))}
def window(stem,size,delay,connections,seconds,phase):
    lo,hi=BOUNDS[size]
    conf=dict(framework='svelte',size=size,delay=delay,connections=connections,seconds=seconds,minBytes=lo,maxBytes=hi,phase=phase)
    result=load({**conf,'out':f'/bench/results/{stem}.json'})
    docker('cp',f'ssrbench-load:/bench/results/{stem}.json',str(OUT/f'{stem}.json'))
    d=json.loads((OUT/f'{stem}.json').read_text())
    assert d['issued']==d['good']==d['complete']==d['backendRequests']['calls']==d['backendRequests']['completed'],stem
    assert not d['errors'] and not d['invalid'] and d['backendRequests']['inflight']==0,stem
    assert d['app']['cgroup']['memoryEventsEnd']['oom_kill']==d['app']['cgroup']['memoryEventsStart']['oom_kill'],stem
    print(stem,result,flush=True)
for args in [('ps','-aq'),('volume','ls','-q'),('network','ls','-q')]:
    if docker(*args,'--filter','label='+LABEL):raise SystemExit('Existing recheck resources: inspect first')
for name in ['ssrbench-app','ssrbench-builder','ssrbench-load','ssrbench-backend']:
    if docker('ps','-aq','--filter',f'name=^{name}$'):raise SystemExit('Container name in use: '+name)
if list(OUT.glob('focus*.json')):raise SystemExit('Use a fresh evidence directory')
tmp=pathlib.Path(tempfile.mkdtemp(prefix='svelte-recheck-'))
try:
    subprocess.run(['python3',str(HERE/'prepare.py'),str(tmp)],check=True)
    for f in ['package.json','package-lock.json']:shutil.copyfile(HERE/'locks/svelte'/f,tmp/'apps/svelte'/f)
    docker('volume','create','--label',LABEL,'ssrbench-20260922')
    docker('network','create','--label',LABEL,'ssrbench-20260922')
    docker('run','-d','--name','ssrbench-builder','--label',LABEL,'--cpus=4','--memory=4g','-v','ssrbench-20260922:/bench','-e','npm_config_cache=/bench/npm-cache',BASE,'sleep','infinity')
    docker('cp',str(tmp/'apps'),'ssrbench-builder:/bench/apps')
    print('Installing locked dependencies and production build',flush=True)
    try:
        docker('exec','ssrbench-builder','sh','-c','cd /bench/apps/svelte && npm ci --no-audit --no-fund > /bench/install.log 2>&1 && npm run build > /bench/build.log 2>&1')
    finally:
        for f in ['install.log','build.log']:docker('cp','ssrbench-builder:/bench/'+f,str(OUT/f),check=False)
    for f in ['metrics.cjs','backend.mjs','load.mjs','profile.cjs','__tests__']:docker('cp',str(HERE/f),'ssrbench-builder:/bench/'+f)
    docker('exec','ssrbench-builder','mkdir','-p','/bench/results')
    for name,cpus,quota,mem,command in [('backend','6-7','2','512m',['node','--require','/bench/metrics.cjs','/bench/backend.mjs']),('load','2-5','4','1g',['sleep','infinity'])]:
        docker('run','-d','--name','ssrbench-'+name,'--label',LABEL,'--network','ssrbench-20260922','--cpuset-cpus='+cpus,'--cpus='+quota,'--memory='+mem,'-v','ssrbench-20260922:/bench','-e','NODE_ENV=production',*(['-e','BENCH_METRICS_PORT=9100'] if name=='backend' else []),BASE,*command)
    info=json.loads(docker('info','--format','{{json .}}'))
    env={k:info.get(k) for k in ['NCPU','MemTotal','Architecture','OperatingSystem','KernelVersion','ServerVersion']}
    env['image']=json.loads(docker('image','inspect',BASE))[0]['Id']
    env['versions']=json.loads(docker('exec','ssrbench-builder','node','-e',"const p='/bench/apps/svelte/node_modules/';console.log(JSON.stringify(Object.fromEntries(['@sveltejs/kit','@sveltejs/adapter-node','svelte','vite'].map(n=>[n,require(p+n+'/package.json').version]))))"))
    (OUT/'environment.json').write_text(json.dumps(env,indent=2))
    run.validate(['svelte'])
    # Fresh process each repetition; no profiling in headline measurements.
    for repeat in range(1,4):
        start_app('svelte')
        load(dict(size='large',delay=50,connections=64,seconds=15,measure=False))
        window(f'focus-r{repeat}','large',50,64,60,'focus')
        stop_app()
    # Separate diagnostic capture, with identical production bundle.
    run.COMMANDS['svelte']=['node','--require','/bench/profile.cjs','build/index.js']
    start_app('svelte')
    load(dict(size='large',delay=50,connections=64,seconds=10,measure=False))
    docker('kill','--signal=USR2','ssrbench-app')
    for _ in range(100):
        if docker('exec','ssrbench-builder','test','-f','/bench/profile-started',check=False)=='':
            if subprocess.run(['docker','exec','ssrbench-builder','test','-f','/bench/profile-started']).returncode==0:break
        time.sleep(.1)
    window('diagnostic-profile','large',50,64,20,'profile')
    docker('kill','--signal=USR2','ssrbench-app')
    for _ in range(100):
        if subprocess.run(['docker','exec','ssrbench-builder','test','-f','/bench/profile.cpuprofile'],capture_output=True).returncode==0:break
        time.sleep(.1)
    docker('cp','ssrbench-builder:/bench/profile.cpuprofile',str(OUT/'profile.cpuprofile'))
    # Retain only executable compiled server source for diagnosis, not generated HTML.
    docker('cp','ssrbench-builder:/bench/apps/svelte/build/server',str(OUT/'compiled-server'))
    stop_app();run.COMMANDS['svelte']=['node','build/index.js']
    # Broader sanity matrix; each page starts with a new process.
    for size in ['hello','medium','large']:
        start_app('svelte');load(dict(size=size,delay=50,connections=16,seconds=10,measure=False))
        combos=list(itertools.product([50,200,500],[1,16,64]));random.Random(2209).shuffle(combos)
        for delay,c in combos:
            load(dict(size=size,delay=delay,connections=c,seconds=2,measure=False))
            window(f'matrix-{size}-d{delay}-c{c}',size,delay,c,15,'matrix')
        stop_app()
finally:
    try:cleanup()
    finally:
        shutil.rmtree(tmp)
        (OUT/'local-cleanup.json').write_text(json.dumps({'removed':str(tmp),'exists':tmp.exists()}))
