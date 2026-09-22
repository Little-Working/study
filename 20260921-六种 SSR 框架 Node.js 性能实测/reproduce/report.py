"""Render the measured tables; explanatory conclusions are reviewed separately."""
import pathlib,json,statistics,collections
ROOT=pathlib.Path(__file__).resolve().parent.parent
D=json.loads((ROOT/'summary.json').read_text());H=json.loads((ROOT/'health.json').read_text())
N={'next':'Next.js','nuxt':'Nuxt','svelte':'SvelteKit','tanstack':'TanStack Start','react-router':'React Router','solid':'SolidStart'}
P={'hello':'Hello World','medium':'约 800 KiB','large':'约 1.5 MiB'}
S=D['sustained'];A=D['scenarios'];R=D['runs']
assert len(R)==282 and len(S)==6 and all(x['windows']==2 for x in S)
out=['# 六种 SSR 框架 Node.js 性能实测','', '测试日期：2026-09-21。Node.js 24.21.0 / ARM64 Docker，全部使用 production 构建。完整方法、适用边界和版本见 [测试口径](METHODOLOGY.md)。','', '> 本报告比较这六个最小应用的具体部署组合。相同的合成记录数、后端等待和资源配置，不等于覆盖所有业务架构；不能据此直接决定迁移框架。','']
if (ROOT/'FINDINGS.md').exists():out.extend([(ROOT/'FINDINGS.md').read_text().strip(),''])
def table(headers,rows):
 out.append('| '+' | '.join(headers)+' |');out.append('| '+' | '.join(['---']*len(headers))+' |')
 out.extend('| '+' | '.join(map(str,row))+' |'for row in rows);out.append('')
out+=['统一环境：应用单进程、2 CPU 配额、1536 MiB 内存限制；V8 old-space 1024 MiB。后端延迟 50/200/500 ms，并发 1/16/64，HTTP Keep-Alive，无压缩。框架版本：Next.js 16.3.5、Nuxt 4.5.2、SvelteKit 2.70.3、TanStack Start 1.168.56、React Router 8.4.0、SolidStart 2.0.5。', '', '## 持续负载结果','', '大页面、50 ms 后端延迟、64 并发；各框架独立新进程，预热 10 秒，发压 30 秒并等待在途响应全部结束，执行两轮且第二轮反转框架顺序。下表按两轮累计成功请求 / 累计实测时间排序；延迟分位数、CPU、GC 和 ELU 为窗口指标中位数，内存为两轮观测峰值的较大值。两次重复不能提供可靠的统计置信区间。','', '此处每个页面只有一次 HTML 请求且每次请求调用后端一次，因此页面 QPS、成功 RPS 和按相同时间窗计算的后端调用率数值相同。没有测试数据库 QPS。','']
S.sort(key=lambda r:-r['rps'])
table(['框架','RPS / 页面 QPS','两轮 RPS 范围','完整响应 p50 / p95 (ms)','首 body 字节 p50 (ms)','CPU %','CPU ms/请求'],[[N[r['framework']],f"{r['rps']:.1f}",f"{r['rps_min']:.1f}–{r['rps_max']:.1f}",f"{r['latency_p50_ms']:.1f} / {r['latency_p95_ms']:.1f}",f"{r['ttfb_p50_ms']:.1f}",f"{r['cpu_pct']:.1f}",f"{r['cpu_ms_per_req']:.2f}"]for r in S])
table(['框架','ELU %','Event loop p99 (ms)','GC 次/秒','GC ms/千请求','GC 时长占窗口 %','RSS 峰值 (MiB)','heap 峰值 (MiB)'],[[N[r['framework']],f"{r['elu_pct']:.1f}",f"{r['eld_p99_ms']:.1f}",f"{r['gc_count_per_s']:.1f}",f"{r['gc_ms_per_1000_req']:.1f}",f"{r['gc_observed_pct']:.1f}",f"{r['rss_peak_mib']:.1f}",f"{r['heap_peak_mib']:.1f}"]for r in S])
out+=['CPU 100% 表示一个核心，应用上限 200%。Event loop 以 10 ms 分辨率采样，约 10 ms 是测量基线；GC 时长占比不是精确的暂停时间占比。RSS/heap 峰值为观测峰值，不是操作系统记录的瞬时历史最高值。','', '![持续负载指标](overview.png)','']
out+=['## 全部页面与后端延迟的吞吐量','', '下表统一为 64 并发。每格按两次 8 秒发压窗口及排空时间计算 `Σ成功请求 / Σ实测时间`，单位 RPS。不要跨不同后端延迟的格子直接排名；等待占比高时，上限主要由并发与后端延迟决定。64 并发下，只考虑 50/200/500 ms 等待的理想上限分别是 1280/320/128 RPS，实际还需支付渲染与传输成本。','']
lookup={(r['framework'],r['page'],r['delay_ms'],r['concurrency']):r for r in A}
table(['页面','后端延迟 (ms)',*N.values()],[[P[p],d,*[f"{lookup[(n,p,d,64)]['rps']:.1f}" for n in N]]for p in P for d in [50,200,500]])
out+=['![64 并发吞吐矩阵与两轮范围](matrix.png)','', '图中误差线表示两轮的最小/最大值，不是置信区间。16 并发和低并发数据保存在 [全部场景汇总 CSV](summary.csv) 与 [逐窗口 CSV](runs.csv)。','', '### 大页面、50 ms：并发与波动','']
table(['框架','C=1 RPS','C=16 RPS','C=64 RPS','C=64 两轮范围','C=64 窗口 p95 中位数 (ms)'],[[N[n],f"{lookup[(n,'large',50,1)]['rps']:.1f}",f"{lookup[(n,'large',50,16)]['rps']:.1f}",f"{lookup[(n,'large',50,64)]['rps']:.1f}",f"{lookup[(n,'large',50,64)]['rps_min']:.1f}–{lookup[(n,'large',50,64)]['rps_max']:.1f}",f"{lookup[(n,'large',50,64)]['latency_p95_ms']:.1f}"]for n in N])
out+=['窗口 p95 的中位数不是全部请求合并后的 p95。C=1 只运行一次 6 秒；尤其 500 ms 场景请求数少，仅用作低负载延迟参考。矩阵使用经过前序负载的同一进程，内存比较优先参考上面的新进程持续测。','', '## 实际 HTML 体积和页面内容','']
sizeRows=[]
for n in N:
 v=json.loads((ROOT/'evidence'/f'{n}-validation.json').read_text())['results']
 vv={r['size']:r for r in v if r['delay']==50 and r['repeat']==1}
 sizeRows.append([N[n],f"{vv['hello']['bytes']:,} B",f"{vv['medium']['bytes']/1024:.1f} KiB",f"{vv['large']['bytes']/2**20:.3f} MiB"])
table(['框架','Hello World','中页面：800 条记录','大页面：1536 条记录'],sizeRows)
out+=['记录字段、文本长度和组件层级相同。SolidStart 等框架添加的 hydration 标识造成一定体积差异；保留这些实际部署成本，没有靠减少记录数对齐字节数。','', '**后端返回的是紧凑的记录生成描述，列表在每次 SSR 时生成。没有测试大型后端 JSON 的解析，也没有测浏览器 hydration、LCP、CDN、TLS 或压缩。** Next.js 使用 App Router + Client Component 的 SSR HTML 路径，不能将结果等同于纯 RSC 页面。React Router 使用带默认访问日志的官方 serve；TanStack/SolidStart 使用 Nitro 3 beta。','', '## 内存、GC 与观测边界','', '![持续负载的内存曲线](memory.png)','', '这些曲线来自两轮 30 秒窗口和自然 GC，没有手动强制回收。RSS 保留/增长可能来自 V8 堆扩容、native buffer、分配器及共享页，单凭 RSS 不能判断泄漏。GC 原始计数、major/minor/incremental 分类、每千请求 GC 时长、heap 起止值、cgroup 内存均保存在原始 JSON 和逐窗口 CSV 中。','', '## 测量有效性','']
table(['检查项','实测结果'],[
 ['覆盖',f"{H['scenarios']} 个独立矩阵场景；270 个矩阵窗口 + 12 个持续窗口"],
 ['正式窗口内完整且校验成功的响应',f"{H['requests']:,} 次"],
 ['HTTP / 内容校验 / 网络错误',str(H['errors'])],
 ['后端对账','所有窗口：发出 = 完整响应 = 成功校验 = 后端请求 = 后端完成；无遗留在途请求'],
 ['OOM kill','应用、后端、压测器所有窗口均无新增 OOM kill'],
 ['应用 CPU throttling 累计',f"{H['app_throttle_ms_sum']:.1f} ms"],
 ['压测器最高窗口平均 CPU',f"{H['load_cpu_pct_max']:.1f}% / 400% 配额"],
 ['压测器 CPU throttling 累计',f"{H['load_throttle_ms_sum']:.1f} ms"],
 ['后端最高窗口平均 CPU',f"{H['backend_cpu_pct_max']:.1f}% / 200% 配额"],
 ['后端实际平均等待的最大超出量',f"{H['backend_delay_excess_mean_ms_max']:.2f} ms（相对于配置的 50/200/500 ms）"],
 ['后端实际 p95 等待的最大超出量',f"{H['backend_delay_excess_p95_ms_max']:.2f} ms"],
 ['主要重复中吞吐范围超过加权均值 10% 的场景',f"{len(H['rps_spread_over_10pct'])} / 108；详见 health.json"]])
out+=['闭环固定并发不会展示恒定到达率下无限增长的排队，因此“本次最高 RPS”不是满足某个线上 SLA 的极限容量。没有长期压力、突发流量、跨进程扩容或 x86 验证。','', '## 复现与清理','', '执行步骤、生成器、负载器、验收脚本及确切依赖锁文件见 [复现说明](reproduce/README.md)。[原始证据目录](evidence/) 保留每个窗口的监控摘要和 200 ms 内存采样，以及构建与运行日志。','', '清理状态由 [cleanup.json](evidence/cleanup.json) 和 [local-cleanup.json](evidence/local-cleanup.json) 记录。生成的应用、production 产物、依赖、npm 缓存、HTML 测试数据和本次 Docker 容器/卷/网络均属于一次性资源；只保留报告、指标证据和复现代码。已有基础镜像保留。','']
(ROOT/'REPORT.md').write_text('\n'.join(out))
print(ROOT/'REPORT.md')
