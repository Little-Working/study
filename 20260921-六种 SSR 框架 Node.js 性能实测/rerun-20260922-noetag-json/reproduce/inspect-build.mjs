import fs from 'node:fs';
import path from 'node:path';
const frameworks=['next','nuxt','svelte','tanstack','react-router','solid'];
const packages=['next','react','react-dom','nuxt','vue','nitropack','nitro','svelte','@sveltejs/kit','@sveltejs/adapter-node','@tanstack/react-start','@tanstack/react-router','react-router','@react-router/express','express','@solidjs/start','solid-js','@solidjs/router','vite'];
const report={};
for(const framework of frameworks){
 const root='/bench/apps/'+framework;
 const versions={};for(const pkg of packages){try{versions[pkg]=JSON.parse(fs.readFileSync(root+'/node_modules/'+pkg+'/package.json')).version}catch{}}
 const sourceEvidence=[];
 const sub=framework==='svelte'?'build/server':framework==='next'?'.next/server':framework==='react-router'?'build/server':'.output/server';
 function scan(dir){for(const e of fs.readdirSync(dir,{withFileTypes:true})){const file=path.join(dir,e.name);if(e.isDirectory()){if(e.name!=='node_modules')scan(file);continue;}if(!/\.(mjs|js)$/.test(file))continue;
  const lines=fs.readFileSync(file,'utf8').split('\n');
  lines.forEach((line,i)=>{if(/\betag\b|hash\(transformed\)|createGzip|compression\(/i.test(line))sourceEvidence.push({file:file.replace(root+'/',''),line:i+1,text:line.slice(0,1000)});});
 }}
 scan(root+'/'+sub);
 report[framework]={versions,sourceEvidence};
}
report.next.effectiveConfig=JSON.parse(fs.readFileSync('/bench/apps/next/.next/required-server-files.json')).config;
fs.writeFileSync('/bench/results/build-audit.json',JSON.stringify(report,null,2));
