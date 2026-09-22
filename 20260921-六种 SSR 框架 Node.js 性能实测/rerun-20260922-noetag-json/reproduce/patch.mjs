import fs from 'node:fs';
import crypto from 'node:crypto';
const patches=[];
const sha=s=>crypto.createHash('sha256').update(s).digest('hex');
const dir='/bench/apps/svelte/build/server/chunks';
let found=0;
for(const f of fs.readdirSync(dir)) {
 if(!f.endsWith('.js'))continue;
 const p=dir+'/'+f,s=fs.readFileSync(p,'utf8');
 if(!s.includes('hash(transformed)'))continue;
 const lines=s.split('\n').filter(l=>l.includes('hash(transformed)'));
 if(lines.length!==1||!lines[0].includes('headers.set("etag"'))throw Error('Unexpected SvelteKit ETag source');
 const changed=s.replace(lines[0],'// Benchmark configuration: HTML ETag computation disabled at source.');
 fs.writeFileSync(p,changed);patches.push({framework:'svelte',path:p,beforeSha256:sha(s),afterSha256:sha(changed),removed:lines[0]});found++;
}
if(found!==1)throw Error('Expected one SvelteKit HTML ETag calculation');
patches.push({framework:'next',configuration:{compress:false,generateEtags:false}});
patches.push({framework:'react-router',configuration:'Express production adapter; app.disable(etag); no compression middleware; no access logger; no static middleware in HTML-only benchmark'});
fs.writeFileSync('/bench/results/patches.json',JSON.stringify(patches,null,2));
console.log(JSON.stringify(patches));
