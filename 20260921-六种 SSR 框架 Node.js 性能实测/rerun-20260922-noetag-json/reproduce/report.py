from pathlib import Path
import json,statistics
from analyze import analyze,NAMES
R=Path(__file__).resolve().parent.parent
s=analyze();h=s['health'];f=s['focus'];cal=json.loads((R/'evidence/calibration.json').read_text());build=json.loads((R/'evidence/build-audit.json').read_text());env=json.loads((R/'evidence/environment.json').read_text())
def table(headers,rows):return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(map(str,row))+' |' for row in rows)+'\n'
def fmt(x):return f'{x:,.1f}'
text=f'''# 六种 SSR 框架 Node.js 性能复测：关闭压缩与 HTML ETag

测试日期：2026-09-22。所有结果均为本机 Docker production 构建实测，模拟后端通过 HTTP 返回 320 KB / 600 KB 完整 JSON，使用统一轻量监控和低开销压测器。SvelteKit 使用明确记录的 ETag 计算补丁；此处不是六种框架默认配置的排名。

完成 **{h['windows']} 个测量窗口、{h['good']:,} 个有效完整响应、{h['errors']} 个请求错误/校验失败**，其中 {h['sampled']:,} 次开销对照请求附加了内容抽样；另完成 216 次压测前完整页面验收。正式矩阵和重点复核不在计时窗口内扫描内容；每个测量窗口后端调用数均与页面请求数一致。

## 主要结果

以下为大页（后端 JSON 600,000 字节、响应 HTML 约 1.6 MB）、后端 50 ms、并发 64 的 **3 个独立新进程 × 30 秒**结果，每个新进程先暖机 30 秒。吞吐和延迟列是窗口指标的中位数，括号为三次吞吐最小–最大值；p95 不是合并所有请求后重新计算的分位数。

'''
text+=table(['框架','有效 RPS：中位数（范围）','完整响应 p50 ms','p95 ms','p99 ms','CPU ms/请求','采样 RSS 最大 MiB'],[[x['name'],f"{x['rpsMedian']:.1f} ({x['rpsMin']:.1f}–{x['rpsMax']:.1f})",fmt(x['p50MedianMs']),fmt(x['p95MedianMs']),fmt(x['p99MedianMs']),fmt(x['cpuMsPerRequestMedian']),fmt(x['rssMaxMiB'])] for x in f])
best=f[0];sv=next(x for x in f if x['framework']=='svelte')
text+=f"\n在这个限定场景中，{best['name']} 的吞吐中位数最高，为 {best['rpsMedian']:.1f} RPS，进程 CPU 成本为 {best['cpuMsPerRequestMedian']:.2f} ms/请求。SvelteKit 为 {sv['rpsMedian']:.1f} RPS，完整响应 p95 的窗口中位数为 {sv['p95MedianMs']:.1f} ms；这里已经移除 HTML ETag 哈希，并实际传输与解析 600 KB 后端 JSON。\n"
text+=f"\n这里的 {sv['p95MedianMs']:.1f} ms 不是纯 render 时间。在接近满并发的闭环负载下，`并发 / RPS` 可近似检查平均响应时长的数量级：SvelteKit 的 `64 / {sv['rpsMedian']:.1f}` 约为 {64000/sv['rpsMedian']:.0f} ms。该关系不能用于推导 p95，也不能拆分 JSON 解析、渲染和序列化阶段。\n"
overlap=[a['name']+' / '+b['name'] for a,b in zip(f,f[1:]) if max(a['rpsMin'],b['rpsMin'])<=min(a['rpsMax'],b['rpsMax'])]
if overlap:text+='\n相邻框架中，'+'、'.join(overlap)+' 的三次吞吐范围有重叠，顺序不宜解读得过细；这些范围不是置信区间。\n'
text+='\n**跨进程波动仍未消除。** Nuxt 和 TanStack Start 各有一个明显较慢的重点窗口，均完整保留。较慢窗口同时出现每请求 CPU 成本上升；当时后端计时器平均等待仍约 53–56 ms，响应字节及请求计数无异常。缺少对应的 CPU profile 和宿主机调度/频率记录，尚不能分离 JIT、GC、应用内部路径与主机因素，不能把中间组的排序当作稳定承诺。详见 [异常窗口证据](evidence/variability.json)。\n'
text+='\n![大页重点场景结果](overview.png)\n\n框架顺序只对应这一合成场景。相同业务记录产生的框架原生 HTML/hydration 格式略有不同；响应字节不是人为补齐到完全相等。更大的数据对象、字段结构、组件复杂度、缓存策略与部署环境均可能改变顺序。\n'
text+='\n## Node.js 运行时\n\n'
text+=table(['框架','进程 CPU%','ELU%','event-loop delay p99 ms','GC ms/请求','GC 次数 / 最长事件 ms（三窗）','heap 最大 MiB','external 最大 MiB','首 body p50 ms'],[[x['name'],fmt(x['cpuPctMedian']),fmt(x['eluPctMedian']),fmt(x['eventLoopP99MedianMs']),f"{x['gcMsPerRequestMedian']:.3f}",f"{x['gcCountTotal']} / {x['gcEventMaxMs']:.1f}",fmt(x['heapMaxMiB']),fmt(x['externalMaxMiB']),fmt(x['firstBodyP50MedianMs'])] for x in f])
text+='\nCPU 以单个逻辑核的 100% 为基准。event-loop delay 是 20 ms 分辨率下的原始值；GC 时长不是精确的暂停比例或 GC CPU 占比。内存为每秒采样，可能遗漏瞬时峰值。首 body 可能只是流式外壳，不等于页面渲染完成。\n\n![Node 运行时指标](runtime.png)\n'
text+='\n## 覆盖全部页面、后端延迟和并发\n\n3 种页面 × 50/200/500 ms 后端延迟 × 1/16/64 并发 × 6 框架，完整矩阵跑两轮，每个单元每轮 8 秒，暖机不计入。第二轮反转框架顺序，单元采用固定种子打乱。\n\n![完整矩阵](matrix.png)\n\n[查看 162 个组合的详细表](RESULTS.md)。矩阵 RPS 使用两窗总成功数除以总实际时间；延迟列是两个窗口分位数的中位数，绝不是总体分位数。低并发、高后端延迟单元样本较少，不能用其 p99 做精细排名。\n'
text+='\n## 监控与压测器开销对照\n\n下表是对应两次窗口 RPS 中位数之间的差值。正值表示左侧条件在本次对照中更快，不是理论优化收益，更不是用于修改原始分数的系数。监控为 lean/off/off/lean 的四个新进程；客户端对照在同一个暖机进程按正序/反序进行。\n\n'
text+=table(['框架','lean 相对 off','8 worker 相对 4','取消 1/128 抽样相对默认'],[[x['name'],f"{x['leanVsOffPct']:+.1f}%",f"{x['workers8VsDefaultPct']:+.1f}%",f"{x['noSamplingVsDefaultPct']:+.1f}%"] for x in s['controls']])
text+='\n![监控和客户端开销对照](overhead.png)\n\n客户端对照完成后，在第一个正式矩阵窗口开始前，六框架统一采用 **最多 4 worker、关闭内容抽样扫描**（并发 1 时为 1 worker）；保留每个响应的状态、字节、响应头及后端调用数检查。这样进一步降低压测器计算开销。决定和当时的数据见 [protocol-amendment.json](evidence/protocol-amendment.json)。上表 1/128 抽样仅是客户端对照的参考条件，也用于两种监控模式的对照，不是正式矩阵配置。\n\n'
text+=f"全体测量窗口中，压测器 CPU 最大 {h['loadCpuPctMax']:.1f}%（配额 400%），单 worker ELU 最大 {h['loadWorkerEluPctMax']:.1f}%；后端 CPU 最大 {h['backendCpuPctMax']:.1f}%（配额 200%），后端平均计时器等待相对设定值的最大超出为 {h['backendTimerOvershootMeanMsMax']:.2f} ms。单窗口内存采样调用的累计墙钟耗时最大 {h['memorySampleCostMsMax']:.2f} ms，不能直接当作纯 CPU 开销。这些数据和对照用于检查瓶颈，不能证明所有系统开销已消失。\n\n"
text+=table(['容器角色','cgroup 周期总数','发生限流的周期数','累计 throttled ms'],[[role,v['nr_periods'],v['nr_throttled'],fmt(v['throttled_usec']/1000)] for role,v in h['throttling'].items()])
text+='\n所有窗口均检查 OOM 事件。cgroup 统计跨越窗口边界辅助采样，进程 CPU 主指标来自应用自身。少量吞吐差异也可能来自 JIT、GC、进程初始状态和宿主机调度；仅两次对照不足以为每个框架确定精确监控损耗率，报告保留原始观测，不做人工数值矫正。\n'
text+='\n## 实际数据量与版本\n\n'
text+=table(['框架','Hello HTML bytes','中页 HTML bytes','大页 HTML bytes'],[[name,*[f"{cal[key][size]['observedMin']:,}–{cal[key][size]['observedMax']:,}" for size in ['hello','medium','large']]] for key,name in NAMES.items()])
text+='\n后端分别为 41、320,000、600,000 字节，中页 800 条商品、大页 1,536 条商品。所有框架从后端接收同一结构；预生成的 mock JSON 降低后端序列化瓶颈，应用 JSON 解析、SSR 和 hydration 序列化仍逐请求发生。\n\n'
text+=table(['框架','实际安装的主要依赖'],[[name,'；'.join(f'{k} {v}' for k,v in build[key]['versions'].items())] for key,name in NAMES.items()])
text+=f"\n运行环境：Node.js {env['node']}、Docker {env['ServerVersion']}、{env['OperatingSystem']} / {env['Architecture']}（{env['NCPU']} vCPU，{env['MemTotal']/2**30:.1f} GiB）。应用 2 CPU/1,536 MiB，压测器 4 CPU/1 GiB，后端 2 CPU/512 MiB，三者使用不重叠的虚拟 CPU 集。每次仅运行一个被测框架。镜像摘要、系统信息与依赖 lockfile 均保留。\n"
text+='\n## 解释边界\n\n- 本轮测量包含模拟后端拉取、完整 JSON 解析、原生 HTML 渲染与数据序列化；未对六框架内部阶段进行等价插桩，不能拆出可信的“纯序列化毫秒数”。总 p95 减去后端延迟也不能得到 render p95。\n- 动态 HTML/API 请求路径不做 gzip/br 或 ETag 计算；未请求的静态资源、构建指纹不在压测范围。压测前的主动 Accept-Encoding 测试与探针无触发记录，正式压测移除重型探针。\n- SvelteKit 改的是生产产物中的 HTML ETag 计算点。该结果用于比较禁用附加计算后的 SSR 链路，不能替代默认 SvelteKit 的生产表现。\n- 所有结果是闭环固定并发下的观测，不是开放到达率负载下的容量 SLA；达到饱和时，请求队列会显著抬高 p95。\n- 新旧实验同时改变了后端 JSON、页面组成、监控和压测器，不能把两者差值全部归因于关闭 ETag 或 gzip。公开 benchmark 也不构成对本次数据的校正依据。\n- 8 秒矩阵窗和 30 秒重点窗不证明长时间稳定性、内存泄漏情况、浏览器 hydration 性能或真实业务页面体验。\n'
text+='\n## 资料与复现\n\n- [测量协议、指标定义和关闭方式](METHODOLOGY.md)\n- [全部组合结果](RESULTS.md) / [机器可读汇总](summary.json) / [健康检查](health.json)\n- [逐窗口原始结果](runs/) / [构建、验收和清理证据](evidence/)\n- [复现说明](reproduce/README.md) / [完整脚本](reproduce/)\n- [图片：概览](overview.png)、[矩阵](matrix.png)、[运行时](runtime.png)、[开销对照](overhead.png)，均附同名 SVG\n\n本轮生成的应用、依赖、JSON 测试数据、容器和网络在结束后清理；指标证据和可复现代码保留。实际销毁回执见 [cleanup.json](evidence/cleanup.json)。\n'
(R/'REPORT.md').write_text(text)
out='# 全部场景结果\n\n每行两次 8 秒窗口。RPS 为成功请求数/实际总时间；p50/p95/p99、CPU% 和 EL p99 为窗口指标的中位数，不是合并请求后的分位数。RSS 为两窗采样最大值；GC/请求和 CPU/请求按请求数加权。矩阵单元复用每轮的应用进程，RSS 可能保留此前大页的内存高水位，不能当作该页面独立启动时的内存占用。\n\n'
for size in ['hello','medium','large']:
 for delay in [50,200,500]:
  out+=f'## {size} / 后端 {delay} ms\n\n'
  rows=[]
  for c in [1,16,64]:
   for x in sorted([x for x in s['matrix'] if x['size']==size and x['delay']==delay and x['connections']==c],key=lambda x:-x['rps']):
    rows.append([x['name'],c,x['requests'],fmt(x['rps']),'/'.join(f'{v:.1f}' for v in x['rpsRuns']),fmt(x['p50WindowMedianMs']),fmt(x['p95WindowMedianMs']),fmt(x['p99WindowMedianMs']),fmt(x['cpuPctMedian']),f"{x['cpuMsPerRequest']:.3f}",fmt(x['rssMaxMiB']),fmt(x['eventLoopP99WindowMedianMs']),f"{x['gcMsPerRequest']:.3f}"])
  out+=table(['框架','并发','成功数','RPS','两次 RPS','p50 ms','p95 ms','p99 ms','CPU%','CPU ms/请求','RSS MiB','EL p99 ms','GC ms/请求'],rows)+'\n'
out+='## 开销对照原始 RPS\n\n'
out+=table(['框架','lean 两次','off 两次','4 worker 抽样两次','8 worker 抽样两次','4 worker 不抽样两次'],[[x['name'],*[' / '.join(f'{v:.1f}' for v in a) for a in [x['monitorRps']['lean'],x['monitorRps']['off'],x['clientRps']['default'],x['clientRps']['workers8'],x['clientRps']['noSampling']]]] for x in s['controls']])
(R/'RESULTS.md').write_text(out)
print(R/'REPORT.md')
