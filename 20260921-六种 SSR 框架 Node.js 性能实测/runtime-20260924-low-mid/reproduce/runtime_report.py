from pathlib import Path
import json,statistics
from summarize import NAMES,PCTS
ROOT=Path(__file__).resolve().parent.parent
SIZES={'hello':'Hello World','medium':'中型页面（约 800 KB HTML）','large':'大型页面（约 1.5 MB HTML）'}
ORDER=['next','nuxt','svelte','tanstack','react-router','solid']
def fmt(v,d=2):return '—' if v is None else f'{v:,.{d}f}'
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])+'\n'
def main():
 x=json.loads((ROOT/'summary.json').read_text());rows=x['matrix'];h=x['health']
 lookup={(r['framework'],r['size'],r['delay'],r['connections']):r for r in rows}
 el=['# Event Loop 全场景分位数\n\n单位 ms。p50–p99 为两窗分位数的中位数，max 为两窗最大；N 为两窗采样数之和。10 ms 原生采样间隔包含在数值内。p99 范围列暴露两窗差异。\n']
 gc=['# GC 全场景分位数\n\n单位 ms。合并同一场景两窗的原始 GC 事件，以最近秩法计算。N 是事件数；— 表示未观测到，不是 0 ms。N<100 标注稀疏，p99 接近极端次序统计量，不能作为稳定尾延迟；≥100 也不代表置信区间充分。全类型混合分位数不能替代 major 分位数。\n']
 res=['# 辅助运行时与 HTTP 指标\n\nCPU 100% 约等于一逻辑核；ELU 是事件循环利用率；RSS/heap 为采样最大。HTTP 分位数是两窗指标中位数；RPS 只是固定并发下成功完成率，不是容量上限。\n']
 for size,title in SIZES.items():
  for delay in [50,200,500]:
   for c in [1,8]:
    title2=f'\n## {title} / 后端 {delay} ms / 并发 {c}\n\n'
    rs=[lookup[f,size,delay,c] for f in ORDER]
    el.append(title2+table(['框架','N','p50','p75','p90','p95','p99','max','两窗 p99'],[[r['name'],r['eventLoop']['sampleCount'],*[fmt(r['eventLoop'][f'p{p}Ms']) for p in PCTS],fmt(r['eventLoop']['maxMs']),' / '.join(fmt(v) for v in r['eventLoop']['p99RangeMs'])] for r in rs]))
    gc.append(title2+table(['框架','类型','N','p50','p75','p90','p95','p99','max','样本'],[[r['name'],kind,g['count'],*[fmt(g[f'p{p}Ms'],3) for p in PCTS],fmt(g['maxMs'],3),'未观测到' if not g['count'] else ('稀疏' if g['p99Sparse'] else '≥100')] for r in rs for kind,g in [('all',r['gc']),*r['gc']['kinds'].items()]]))
    res.append(title2+table(['框架','CPU %','ELU %','CPU ms/请求','RSS MiB','heap MiB','GC 次/s','GC ms/请求','RPS','HTTP p50','HTTP p95','HTTP p99'],[[r['name'],fmt(r['cpuPct'],1),fmt(r['eluPct'],1),fmt(r['cpuMsPerRequest'],3),fmt(r['rssMaxMiB'],1),fmt(r['heapMaxMiB'],1),fmt(r['gc']['eventsPerSecond']),fmt(r['gc']['msPerRequest'],3),fmt(r['rps'],1),fmt(r['httpMs']['p50']),fmt(r['httpMs']['p95']),fmt(r['httpMs']['p99'])] for r in rs]))
 for name,text in [('RESULTS-eventloop.md',el),('RESULTS-gc.md',gc),('RESULTS-resources.md',res)]: (ROOT/name).write_text('\n'.join(text))
 doc=['# 六种 SSR 框架：低中并发 Event Loop 与 GC 分位数实测\n',
 '测试日期：2026-09-24。Docker production 构建，关闭动态 HTML/API 路径的 ETag 和压缩；并发 1/8，后端 50/200/500 ms。全部结果为新一轮实测，不复用旧测试数字。\n',
 f"完成 **216 个正式窗口、24 个监控开销对照、36 个空闲基线**，合计 {h['good']:,} 次有效完整响应（含监控对照），请求错误 {h['errors']}，校验失败 {h['invalid']}，GC 记录溢出 {h['gcDropped']}。\n",
 '## 如何读结论\n\n这次测的是自然运行中的事件循环延迟与 GC 事件时长，不追求极限 QPS。请求实际经过后端 HTTP 等待、JSON 解析、原生 SSR 渲染和框架响应序列化；本轮没有逐阶段计时埋点，不能把 GC 或 Event Loop 数字直接解释成纯 HTML 渲染或序列化耗时。不测浏览器执行或客户端 hydration。不同框架以相同并发运行，实际完成请求量仍不同，因此既列 GC 单次时长，也列次数/秒与毫秒/请求。不要把 HTTP p99、Event Loop p99 和 GC p99 当作同一个指标。\n',
 '以下重点表固定后端 200 ms、并发 8，三个页面分别展示。它是便于阅读的切片，全部 108 个组合见末尾明细。Event Loop p50–p99 是两窗指标中位数（仅两窗，数值等于两窗均值，并非合并直方图分位数），GC 是同场景原始事件合并分位数；max 均为观测到的最高值，绝非未来上界。\n',
 '![三种页面重点场景](overview.png)\n']
 if (ROOT/'CONCLUSIONS.md').exists():doc.insert(3,(ROOT/'CONCLUSIONS.md').read_text())
 for size,title in SIZES.items():
  rs=[lookup[f,size,200,8] for f in ORDER]
  doc.append('## '+title+'\n\n**Event Loop：单位 ms，包含 10 ms 采样间隔**\n\n'+table(['框架','p50','p75','p90','p95','p99','max'],[[r['name'],*[fmt(r['eventLoop'][f'p{p}Ms']) for p in PCTS],fmt(r['eventLoop']['maxMs'])] for r in rs]))
  doc.append('**GC：单位 ms，全类型合并；N 是事件数**\n\n'+table(['框架','N','p50','p75','p90','p95','p99','max','major N'],[[r['name'],str(r['gc']['count'])+('*' if r['gc']['p99Sparse'] else ''),*[fmt(r['gc'][f'p{p}Ms']) for p in PCTS],fmt(r['gc']['maxMs']),r['gc']['kinds']['major']['count']] for r in rs]))
 doc.append('\n* 表示 N<100。— 表示未观测到。major 单独分位数见 GC 明细。\n\n![Event Loop 六档分位数](eventloop-quantiles.png)\n\n![GC 六档分位数](gc-quantiles.png)\n\n![全部延迟与并发场景的 Event Loop p99](eventloop-matrix.png)\n')
 doc.append('## GC 类型和有限观测\n\n'+table(['类型','正式窗口事件总数'],[[k,v] for k,v in h['gcTypes'].items()]))
 doc.append('原始记录保留 kind、flags、窗口内开始时间和时长。minor/minor_mark_sweep/major/incremental/weakcb 按 Node perf_hooks 分类；这些 duration 是 Node 报告的事件时长，不等于 GC 总 CPU 时间，也不代表整个并发 GC 生命周期或精确 stop-the-world 占比。未观测到某类型只能说明本次窗口没有样本。没有用强制 GC 制造“漂亮”的分位数。\n')
 doc.append('## 空闲基线与监测开销\n\n'+table(['框架','空闲 EL p50 ms 中位数','空闲 EL p99 ms 中位数','空闲 EL max ms'],[[NAMES[f],fmt(statistics.median(r['eventLoop']['p50Ms'] for r in x['idle'] if r['framework']==f)),fmt(statistics.median(r['eventLoop']['p99Ms'] for r in x['idle'] if r['framework']==f)),fmt(max(r['eventLoop']['maxMs'] for r in x['idle'] if r['framework']==f))] for f in ORDER]))
 doc.append(table(['框架','lean RPS 两窗','off RPS 两窗','lean/off RPS 变化','lean CPU ms/请求','off CPU ms/请求'],[[r['name'],' / '.join(fmt(v,1) for v in r['rps']['lean']),' / '.join(fmt(v,1) for v in r['rps']['off']),fmt(r['leanVsOffRpsPct'],1)+'%',fmt(r['cpuMsPerRequest']['lean'],3),fmt(r['cpuMsPerRequest']['off'],3)] for r in x['controls']]))
 doc.append('对照采用大页/50 ms/C8、四个独立进程的 lean/off/off/lean 顺序。off 仍保留边界 CPU/内存查询及控制 HTTP 服务；仅禁用周期性采样、EL 直方图和 GC observer。该开销对照仅覆盖这一场景，包含进程/JIT/宿主机波动，不把差值当作精确监控税，也不对正式数据做倍率修正。\n')
 doc.append('## 质量与资源检查\n\n'+table(['检查','结果'],[['最少正式请求数/窗',h['minRequestsPerMatrixWindow']],['最少 Event Loop 采样数/窗',h['minEventLoopSamplesPerWindow']],['应用最高进程 CPU %',fmt(h['maxAppCpuPct'],1)],['客户端最高进程 CPU %',fmt(h['maxLoadCpuPct'],1)],['客户端 worker 最高 ELU %',fmt(h['maxWorkerEluPct'],1)],['后端最高进程 CPU %',fmt(h['maxBackendCpuPct'],1)],['后端平均定时等待超出设定值的最大值 ms',fmt(h['maxBackendTimerOvershootMeanMs'])],['单窗累计 memoryUsage 调用墙钟耗时最大值 ms',fmt(h['maxMemorySampleCostMs'])]]))
 doc.append(table(['角色','cgroup periods','throttled periods','throttled ms'],[[k,v['nr_periods'],v['nr_throttled'],fmt(v['throttled_usec']/1000)] for k,v in h['throttle'].items()]))
 doc.append('cgroup 计数覆盖窗口前后边界采集，可能含辅助采集进程；应用进程 CPU 来自冻结边界的 process.cpuUsage。压测器与后端使用不重叠的 VM CPU 集，仍共享宿主机与虚拟化层。进程 CPU 100% 约等于一逻辑核；应用配额2核，CPU>100%可能包含V8后台线程。固定并发8对不同框架不保证相同CPU利用率。RSS按1Hz采样，可能遗漏短峰值，不能据此判定泄漏。\n')
 cal=json.loads((ROOT/'evidence/calibration.json').read_text())
 doc.append('## 实际响应体积\n\nUTF-8 HTML正文（不含HTTP头），包含框架内联hydration数据；不包含外部JS/CSS/图片。后端JSON分别为41、320000、600000字节；商品记录数为0、800、1536。\n\n'+table(['框架','Hello字节','中页字节','大页字节'],[[NAMES[f],*[str(cal[f][size]['observedMin'])+'–'+str(cal[f][size]['observedMax']) for size in SIZES]] for f in ORDER]))
 audit=json.loads((ROOT/'evidence/build-audit.json').read_text())
 env=json.loads((ROOT/'evidence/environment.json').read_text())
 host=json.loads((ROOT/'evidence/host.json').read_text()) if (ROOT/'evidence/host.json').exists() else {}
 doc.append('## 环境\n\n'+table(['项目','配置'],[['宿主CPU',host.get('machdep.cpu.brand_string','未记录')],['宿主核心数',host.get('hw.ncpu','未记录')],['宿主内存GiB',fmt(int(host['hw.memsize'])/2**30,1) if host.get('hw.memsize') else '未记录'],['Docker VM CPU',env['NCPU']],['Docker VM内存GiB',fmt(env['MemTotal']/2**30,2)],['架构',env['Architecture']],['Node',env['node']],['应用CPU/内存','2 vCPU / 1536 MiB'],['V8 old space','1024 MiB']]))
 doc.append('## 页面实现与比较边界\n\n'+table(['框架','本轮实现'],[
 ['Next.js','App Router；动态 Server Page 拉数据，商品列表为 use client 组件并参与服务端 HTML 预渲染；保留 RSC/水合数据'],
 ['Nuxt','useAsyncData + Vue 原生 v-for；Nitro node-server'],
 ['SvelteKit','+page.server load + Svelte each；adapter-node'],
 ['TanStack Start','React Start；路由 loader 调用 createServerFn；Nitro Node 服务'],
 ['React Router','Framework SSR 模式，loader + React 列表；Express 生产适配器'],
 ['SolidStart','SolidJS 通过 SolidStart 测试；query/createAsync + For；Nitro Node 服务']]))
 doc.append('六者均遍历真实后端商品数组生成同结构商品列表，保留框架自己的数据序列化和水合协议，没有把列表替换成预制 HTML 字符串。Next.js 数据不代表 Pages Router 或纯 Server Component 列表；SolidJS 数字也不等于脱离路由/服务层的纯 renderToString 微基准。\n')
 doc.append('## 构建、协议与局限\n\n依赖锁文件沿用上一轮：Next 16.3.5、Nuxt 4.5.2、SvelteKit 2.70.3 / Svelte 5.57.1、TanStack React Start 1.168.56、React Router 8.4.0、SolidStart 2.0.5 / Solid 1.9.15。镜像和实际安装证据见 [构建审计](evidence/build-audit.json)、[环境](evidence/environment.json)。\n\n完整内容验收覆盖三种页面、三档延迟、identity/gzip-br 协商，并断言每页恰好一次后端调用。正式窗口不拼接/扫描完整HTML，只统计字节、状态和响应头。SvelteKit移除实际HTML ETag哈希调用，补丁见 [记录](evidence/patches.json)。本结果不代表默认配置。\n\n每组合两次20秒，低并发慢后端的请求及GC样本有限。短窗最大值和p99会受偶发事件影响；不把两轮结果描述为长期稳定保证。各页分组重启进程，同一页的不同延迟/并发组合仍共享该页进程历史。生成的是扁平商品数组，不代表任意组件树或业务对象。HTML、后端JSON和渲染量一起变化，因此不能把差异全部归因于HTML字节数。\n\n- [预先确定的协议](PROTOCOL.md)\n- [Event Loop 全场景分位数](RESULTS-eventloop.md)\n- [GC 全场景及分类型分位数](RESULTS-gc.md)\n- [CPU、内存及 HTTP 辅助指标](RESULTS-resources.md)\n- SVG 图表：[重点场景](overview.svg) / [Event Loop 分位数](eventloop-quantiles.svg) / [GC 分位数](gc-quantiles.svg) / [完整 EL p99 矩阵](eventloop-matrix.svg)\n- [汇总 JSON](summary.json) / [原始窗口](runs/)\n- [复现步骤](reproduce/README.md) / [清理证据](evidence/cleanup.json)\n\n指标依据：[Node 24 perf_hooks](https://nodejs.org/docs/latest-v24.x/api/perf_hooks.html)。\n')
 cleanup=json.loads((ROOT/'evidence/cleanup.json').read_text());assert not any(cleanup['remaining'].values())
 doc.append('本轮 Docker 容器、网络和测试数据卷已按专属标签销毁。保留报告、指标、脚本与锁文件，不保留运行中的服务或生成的业务数据。\n')
 (ROOT/'REPORT.md').write_text('\n'.join(doc))
if __name__=='__main__':main()
