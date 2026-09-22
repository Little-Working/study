"""Generate disposable, minimal SSR applications; no repository apps are modified."""
import json, pathlib, sys
root = pathlib.Path(sys.argv[1]).resolve()
root.mkdir(parents=True, exist_ok=True)
def write(path, text):
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.strip() + '\n')
def app(name, deps, build, files):
    write(f'apps/{name}/package.json', json.dumps({'name':'ssrbench-'+name,'private':True,'type':'module','scripts':{'build':build},'dependencies':deps},indent=2))
    for path, text in files.items(): write(f'apps/{name}/{path}',text)
    write(f'apps/{name}/shared.js', SHARED)
SHARED = '''
export function rows(data) {
  const text = 'abcdefghijklmnopqrstuvwxyz0123456789'.repeat(30).slice(0, data.textLength);
  return Array.from({length:data.count}, (_,i)=>({id:i,title:`Product ${String(i).padStart(5,'0')}`,description:text,price:((i%100)+0.99).toFixed(2)}));
}
export async function backend(size,delay,rid) {
  const url = new URL('http://ssrbench-backend:4000/data');
  url.search = new URLSearchParams({size,delay:String(delay),rid:String(rid)}).toString();
  const r = await fetch(url, {cache:'no-store'});
  if (!r.ok) throw new Error(`backend ${r.status}`);
  return r.json();
}
'''
REACT_PAGE = '''
import {rows} from '../shared.js';
export default function Bench({data}) {
  const items=rows(data);
  return <main data-request={data.rid}><h1>Hello World</h1><section>{items.map(row=><article key={row.id} data-row={row.id}><h2>{row.title}</h2><p>{row.description}</p><span>{row.price}</span></article>)}</section><footer>BENCH_END</footer></main>;
}
'''
react={'react':'19.3.0','react-dom':'19.3.0'}
app('next',dict(react,next='16.3.5'), 'next build', {
'next.config.mjs':"export default {compress:false,poweredByHeader:false,experimental:{cpus:2}};",
'app/layout.jsx':'export default function Layout({children}) {return <html lang="en"><body>{children}</body></html>}',
'app/Bench.jsx':"'use client';\n"+REACT_PAGE,
'app/page.jsx':'''import Bench from './Bench';
import {backend} from '../shared.js';
export const dynamic='force-dynamic';
export const revalidate=0;
export default async function Page({searchParams}) {const p=await searchParams; const data=await backend(p.size||'hello',p.delay||50,p.rid||'probe');return <Bench data={data}/>;}'''
})
app('nuxt',{'nuxt':'4.5.2','vue':'3.5.41'},'nuxt build',{
'nuxt.config.ts':"export default defineNuxtConfig({devtools:{enabled:false},telemetry:false,nitro:{preset:'node-server'},routeRules:{'/**':{cache:false}}});",
'app/app.vue':'''<script setup>
import {rows,backend} from '../shared.js';
const route=useRoute();
const {data}=await useAsyncData('bench',()=>backend(route.query.size||'hello',route.query.delay||50,route.query.rid||'probe'));
const items=computed(()=>rows(data.value));
</script>
<template><main :data-request="data.rid"><h1>Hello World</h1><section><article v-for="row in items" :key="row.id" :data-row="row.id"><h2>{{row.title}}</h2><p>{{row.description}}</p><span>{{row.price}}</span></article></section><footer>BENCH_END</footer></main></template>'''
})
app('svelte',{'@sveltejs/kit':'2.70.3','@sveltejs/adapter-node':'5.5.7','@sveltejs/vite-plugin-svelte':'7.3.0','svelte':'5.57.1','vite':'8.3.0'},'vite build',{
'svelte.config.js':"import adapter from '@sveltejs/adapter-node';export default {kit:{adapter:adapter({precompress:false})}};",
'vite.config.js':"import {sveltekit} from '@sveltejs/kit/vite';import {defineConfig} from 'vite';export default defineConfig({plugins:[sveltekit()]});",
'src/app.html':'<!doctype html><html lang="en"><head>%sveltekit.head%</head><body><div>%sveltekit.body%</div></body></html>',
'src/routes/+page.server.js':"import {backend} from '../../shared.js';export const prerender=false;export async function load({url}) {return {bench:await backend(url.searchParams.get('size')||'hello',url.searchParams.get('delay')||50,url.searchParams.get('rid')||'probe')}};",
'src/routes/+page.svelte':'''<script>
import {rows} from '../../shared.js';
let {data}=$props();
let items=$derived(rows(data.bench));
</script>
<main data-request={data.bench.rid}><h1>Hello World</h1><section>{#each items as row (row.id)}<article data-row={row.id}><h2>{row.title}</h2><p>{row.description}</p><span>{row.price}</span></article>{/each}</section><footer>BENCH_END</footer></main>'''
})
app('react-router',dict(react,**{'react-router':'8.4.0','@react-router/dev':'8.4.0','@react-router/node':'8.4.0','@react-router/serve':'8.4.0','isbot':'5.2.2','vite':'8.3.0'}),'react-router build',{
'vite.config.js':"import {reactRouter} from '@react-router/dev/vite';import {defineConfig} from 'vite';export default defineConfig({plugins:[reactRouter()]});",
'react-router.config.js':'export default {ssr:true};',
'app/routes.js':"import {index} from '@react-router/dev/routes';export default [index('page.jsx')];",
'app/root.jsx':"import {Outlet,Scripts,Meta,Links} from 'react-router';export default function Root(){return <html lang='en'><head><Meta/><Links/></head><body><Outlet/><Scripts/></body></html>}",
'app/Bench.jsx':REACT_PAGE,
'app/page.jsx':"import {useLoaderData} from 'react-router';import Bench from './Bench';import {backend} from '../shared.js';export async function loader({request}){const p=new URL(request.url).searchParams;return backend(p.get('size')||'hello',p.get('delay')||50,p.get('rid')||'probe')}export default function Page(){return <Bench data={useLoaderData()}/>;}"
})
app('tanstack',dict(react,**{'@tanstack/react-start':'1.168.56','@tanstack/react-router':'1.170.38','@vitejs/plugin-react':'6.1.1','vite':'8.3.0','nitro':'3.0.260903-beta'}),'vite build',{
'vite.config.ts':"import {defineConfig} from 'vite';import {tanstackStart} from '@tanstack/react-start/plugin/vite';import react from '@vitejs/plugin-react';import {nitro} from 'nitro/vite';export default defineConfig({plugins:[nitro(),tanstackStart(),react()]});",
'src/router.tsx':"import {createRouter} from '@tanstack/react-router';import {routeTree} from './routeTree.gen';export function getRouter(){return createRouter({routeTree})}",
'src/routes/__root.tsx':"import {createRootRoute,HeadContent,Scripts} from '@tanstack/react-router';export const Route=createRootRoute({shellComponent:({children})=><html lang='en'><head><HeadContent/></head><body>{children}<Scripts/></body></html>});",
'src/Bench.jsx':REACT_PAGE,
'src/routes/index.tsx':'''import {createFileRoute} from '@tanstack/react-router';
import {createServerFn} from '@tanstack/react-start';
import {backend} from '../../shared.js';
import Bench from '../Bench';
const getData=createServerFn({method:'GET'}).inputValidator((d:any)=>d).handler(({data})=>backend(data.size||'hello',data.delay||50,data.rid||'probe'));
export const Route=createFileRoute('/')({validateSearch:(s:any)=>s,loaderDeps:({search})=>search,loader:({deps})=>getData({data:deps}),component:Page});
function Page(){const data=Route.useLoaderData();return <Bench data={data}/>;}'''
})
app('solid',{'@solidjs/start':'2.0.5','@solidjs/router':'1.0.0','solid-js':'1.9.15','nitro':'3.0.260903-beta','vite':'8.3.0'},'vite build',{
'vite.config.ts':"import {defineConfig} from 'vite';import {solidStart} from '@solidjs/start/config';import {nitro} from 'nitro/vite';export default defineConfig({plugins:[solidStart(),nitro()]});",
'src/app.tsx':"import {Router} from '@solidjs/router';import {FileRoutes} from '@solidjs/start/router';import {Suspense} from 'solid-js';export default function App(){return <Router root={props=><Suspense>{props.children}</Suspense>}><FileRoutes/></Router>;}",
'src/entry-server.tsx':"import {createHandler,StartServer} from '@solidjs/start/server';export default createHandler(()=><StartServer document={props=><html lang='en'><head>{props.assets}</head><body><div id='app'>{props.children}</div>{props.scripts}</body></html>}/>);",
'src/entry-client.tsx':"import {mount,StartClient} from '@solidjs/start/client';mount(()=><StartClient/>,document.getElementById('app')!);",
'src/routes/index.tsx':'''import {query,createAsync,useSearchParams} from '@solidjs/router';
import {For,Show} from 'solid-js';
import {backend,rows} from '../../shared.js';
const getData=query(async(size,delay,rid)=>{'use server';return backend(size,delay,rid)},'bench');
export default function Page(){const [p]=useSearchParams();const data=createAsync(()=>getData(p.size||'hello',p.delay||50,p.rid||'probe'));
return <Show when={data()}>{d=><main data-request={d().rid}><h1>Hello World</h1><section><For each={rows(d())}>{row=><article data-row={row.id}><h2>{row.title}</h2><p>{row.description}</p><span>{row.price}</span></article>}</For></section><footer>BENCH_END</footer></main>}</Show>;}'''
})
print(root)
