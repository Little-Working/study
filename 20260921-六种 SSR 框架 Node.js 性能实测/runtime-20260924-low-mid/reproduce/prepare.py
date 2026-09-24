"""Generate identical real-data page workloads from the original scaffold."""
from pathlib import Path
import subprocess,sys,shutil
HERE=Path(__file__).resolve().parent
root=Path(sys.argv[1]).resolve()
subprocess.run([sys.executable,str(HERE/'base_prepare.py'),str(root)],check=True)
shared='''export function rows(data) { return data.items; }
export async function backend(size,delay,rid) {
 const url=new URL('http://ssrbench3-backend:4000/data');
 url.search=new URLSearchParams({size,delay:String(delay),rid:String(rid)}).toString();
 const response=await fetch(url,{cache:'no-store'});
 if(!response.ok) throw new Error(`backend ${response.status}`);
 return response.json();
}
'''
for app in (root/'apps').iterdir():
    for f in app.rglob('shared.js'):f.write_text(shared)
    for f in app.rglob('*'):
        if f.suffix not in ['.jsx','.tsx','.vue','.svelte']:continue
        s=f.read_text()
        klass='className' if f.suffix in ['.jsx','.tsx'] and app.name!='solid' else 'class'
        # Same static HTML attributes, record count and component structure in all six.
        s=s.replace('<article ',f'<article {klass}="product-card border rounded shadow-sm bg-white overflow-hidden flex flex-col" ')
        s=s.replace('<h2>',f'<h2 {klass}="product-title text-base font-semibold leading-tight">')
        s=s.replace('<p>',f'<p {klass}="product-description text-sm leading-relaxed">')
        s=s.replace('<span>',f'<span {klass}="product-price font-bold text-lg">')
        f.write_text(s)
    for f in ['package.json','package-lock.json']:shutil.copy2(HERE/'locks'/app.name/f,app/f)
p=root/'apps/next/next.config.mjs'
p.write_text(p.read_text().replace('compress:false,','compress:false,generateEtags:false,'))
p=root/'apps/nuxt/nuxt.config.ts'
p.write_text(p.read_text().replace("preset:'node-server'","preset:'node-server',compressPublicAssets:false"))
