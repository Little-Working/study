import json,pathlib,subprocess
from run import docker,OUT,COMMANDS,HERE,IMAGE
for name in COMMANDS:
    dest=HERE/'locks'/name;dest.mkdir(parents=True,exist_ok=True)
    for filename in ['package.json','package-lock.json']:
        docker('cp',f'ssrbench-builder:/bench/apps/{name}/{filename}',str(dest/filename))
    for stage in ['install','build']:
        docker('cp',f'ssrbench-builder:/bench/{name}-{stage}.log',str(OUT/f'{name}-{stage}.log'))
env={'dockerVersion':json.loads(docker('version','--format','{{json .}}')),'dockerInfo':json.loads(docker('info','--format','{{json .}}')),'image':json.loads(docker('image','inspect',IMAGE))[0],'containers':json.loads(docker('inspect','ssrbench-backend','ssrbench-load','ssrbench-builder')),'kernel':docker('exec','ssrbench-builder','cat','/proc/version')}
# Retain machine characteristics, not daemon paths or networking internals.
env['dockerInfo']={k:env['dockerInfo'].get(k) for k in ['NCPU','MemTotal','Architecture','OperatingSystem','KernelVersion','ServerVersion','CgroupVersion','CgroupDriver']}
env['image']={k:env['image'].get(k) for k in ['Id','RepoDigests','Architecture','Created','Size']}
env['containers']=[{'name':c['Name'],'id':c['Id'],'image':c['Config']['Image'],'limits':{k:c['HostConfig'][k] for k in ['NanoCpus','CpusetCpus','Memory','MemorySwap']}} for c in env['containers']]
(OUT/'environment.json').write_text(json.dumps(env,indent=2))
print('Captured production build logs, lockfiles and environment.')
