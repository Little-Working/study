"""Reproduce in disposable Docker resources, always cleaning them in finally.
Usage: python3 all.py
Requires >=8 Docker logical CPUs, 8 GiB VM RAM, Docker and Python 3.
"""
import pathlib, tempfile, shutil, subprocess, os, json, datetime
from run import docker, cleanup, validate, matrix, HERE, OUT, COMMANDS, LABEL
BASE='public.ecr.aws/docker/library/node@sha256:2fe369e969550cde8e867afc3fe370b260140cab4a23d467074295b42163d553'
for args in [('ps','-aq'),('volume','ls','-q'),('network','ls','-q')]:
    if docker(*args,'--filter','label='+LABEL):raise SystemExit('Existing benchmark resources found. Inspect and clean them first.')
if list(OUT.glob('*-d*-c*-r*.json')) or list(OUT.glob('*-sustained*-*.json')):raise SystemExit('Use a fresh copy/output directory to avoid mixing independent runs.')
tmp=pathlib.Path(tempfile.mkdtemp(prefix='ssrbench-'))
try:
    subprocess.run(['python3',str(HERE/'prepare.py'),str(tmp)],check=True)
    for name in COMMANDS:
        for filename in ['package.json','package-lock.json']:
            shutil.copyfile(HERE/'locks'/name/filename,tmp/'apps'/name/filename)
    docker('image','inspect',BASE)
    # Tag points to the immutable digest used in this report, within this script's process.
    import run
    run.IMAGE=BASE
    docker('volume','create','--label',LABEL,'ssrbench-20260921')
    docker('network','create','--label',LABEL,'ssrbench-20260921')
    docker('run','-d','--name','ssrbench-builder','--label',LABEL,'--cpus=4','--memory=4g','-v','ssrbench-20260921:/bench','-e','npm_config_cache=/bench/npm-cache','-e','NEXT_TELEMETRY_DISABLED=1','-e','NUXT_TELEMETRY_DISABLED=1',BASE,'sleep','infinity')
    docker('cp',str(tmp/'apps'),'ssrbench-builder:/bench/apps')
    for name in COMMANDS:
        print('Building',name,flush=True)
        docker('exec','ssrbench-builder','sh','-c',f'cd /bench/apps/{name} && npm ci --no-audit --no-fund > /bench/{name}-install.log 2>&1 && npm run build > /bench/{name}-build.log 2>&1')
    for filename in ['metrics.cjs','backend.mjs','load.mjs','__tests__']:
        docker('cp',str(HERE/filename),f'ssrbench-builder:/bench/{filename}')
    docker('exec','ssrbench-builder','mkdir','-p','/bench/results')
    docker('run','-d','--name','ssrbench-backend','--label',LABEL,'--network','ssrbench-20260921','--cpuset-cpus=6-7','--cpus=2','--memory=512m','-v','ssrbench-20260921:/bench','-e','NODE_ENV=production','-e','BENCH_METRICS_PORT=9100',BASE,'node','--require','/bench/metrics.cjs','/bench/backend.mjs')
    docker('run','-d','--name','ssrbench-load','--label',LABEL,'--network','ssrbench-20260921','--cpuset-cpus=2-5','--cpus=4','--memory=1g','-v','ssrbench-20260921:/bench',BASE,'sleep','infinity')
    import capture  # Saves build logs, lockfiles and current Docker environment.
    validate(list(COMMANDS))
    matrix()
    import confirm  # Reverse-order second sustained pass, also with fresh processes.
finally:
    try:
        cleanup()
    finally:
        shutil.rmtree(tmp)
        (OUT/'local-cleanup.json').write_text(json.dumps({'time':datetime.datetime.now(datetime.timezone.utc).isoformat(),'removed':[str(tmp)],'remaining':[] if not tmp.exists() else [str(tmp)]},indent=2))
    subprocess.run(['python3',str(HERE/'sanitize.py')],check=True)
