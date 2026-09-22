"""Second independent sustained run, in reverse framework order."""
import json
from run import COMMANDS,OUT,start_app,stop_app,load,docker
for name in reversed(list(COMMANDS)):
 stem=f'{name}-sustained2-large-d50-c64'
 if (OUT/f'{stem}.json').exists():continue
 start_app(name)
 conf=dict(framework=name,size='large',delay=50,connections=64,minBytes=int(1.4*1024*1024),maxBytes=int(1.65*1024*1024))
 load({**conf,'seconds':10,'measure':False})
 result=load({**conf,'seconds':30,'out':f'/bench/results/{stem}.json','phase':'sustained','repeat':2})
 docker('cp',f'ssrbench-load:/bench/results/{stem}.json',str(OUT/f'{stem}.json'))
 print(stem,result,flush=True)
 stop_app()
