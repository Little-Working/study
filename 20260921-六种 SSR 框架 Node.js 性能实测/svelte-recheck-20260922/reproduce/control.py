"""Run after recheck.py completes. Default / remove only ETag calculation / restore.
The no-ETag case changes conditional HTTP cache validation and is diagnostic only.
It must never replace an unmodified framework result in a ranking.
"""
import pathlib
source=(pathlib.Path(__file__).parent/'recheck.py').read_text()
source=source.replace("from run import docker, HERE, OUT, LABEL, load, start_app, stop_app, cleanup", "from run import docker, HERE, LABEL, load, start_app, stop_app, cleanup\nrun.OUT=run.OUT/'control'\nrun.OUT.mkdir(exist_ok=True)\nOUT=run.OUT")
source=source.replace("if list(OUT.glob('focus*.json')):", "if any((OUT/(v+'.json')).exists() for v in ['default-before','no-etag','default-restored']):")
start=source.index("    run.validate(['svelte'])")
end=source.index('\nfinally:',start)
control=r'''    original=docker('exec','ssrbench-builder','node','-e',"const fs=require('fs');const dir='/bench/apps/svelte/build/server/chunks';for(const f of fs.readdirSync(dir)){if(f.startsWith('index.js-')&&f.endsWith('.js')){const p=dir+'/'+f; const s=fs.readFileSync(p,'utf8');if(s.includes('hash(transformed)'))console.log(p)}}")
    assert original.startswith('/bench/apps/svelte/build/server/chunks/') and len(original.splitlines())==1
    docker('exec','ssrbench-builder','cp',original,'/bench/default-index.js')
    mutation="const fs=require('fs');const p=process.argv[1];const s=fs.readFileSync(p,'utf8');const line=s.split('\\n').find(l=>l.includes('hash(transformed)'));if(!line||!line.includes('headers.set'))throw Error('Unexpected compiled source');fs.writeFileSync(p,s.replace(line,'// Diagnostic only: omit HTML ETag calculation'));console.log(JSON.stringify({path:p,removed:line}));"
    for variant in ['default-before','no-etag','default-restored']:
        if variant=='no-etag':
            change=docker('exec','ssrbench-builder','node','-e',mutation,original)
            (OUT/'diagnostic-patch.json').write_text(change)
        else:docker('exec','ssrbench-builder','cp','/bench/default-index.js',original)
        run.validate(['svelte'])
        (OUT/'svelte-validation.json').rename(OUT/(variant+'-validation.json'))
        start_app('svelte')
        load(dict(size='large',delay=50,connections=64,seconds=15,measure=False))
        window(variant,'large',50,64,45,'control-'+variant)
        stop_app()
'''
source=source[:start]+control+source[end:]
exec(compile(source,__file__,'exec'))
