import json, pathlib
R=pathlib.Path(__file__).resolve().parent.parent
d=json.loads((R/'summary.json').read_text())
p=json.loads((R/'evidence/profile-summary.json').read_text())
rows=d['recheck'];focus=[r for r in rows if r['phase']=='focus'];controls=[r for r in rows if r['phase'].startswith('control-')]
def table(data):
    out=['| 测量窗口 | RPS | p50 ms | p95 ms | CPU ms/请求 | ELU % | ELD p99 ms | GC 观测占比 % | RSS 峰值 MiB |','| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for label,r in data:out.append(f"| {label} | {r['rps']:.1f} | {r['p50']:.1f} | {r['p95']:.1f} | {r['cpuMsPerRequest']:.2f} | {r['eluPct']:.1f} | {r['eldP99']:.1f} | {r['gcPct']:.2f} | {r['rssMiB']:.1f} |")
    return '\n'.join(out)
baseline=table([(f'原始 30 秒 #{i+1}',r) for i,r in enumerate(d['original'])]+[(f'复测 60 秒 #{i+1}',r) for i,r in enumerate(focus)])
ct=table([(r['phase'].removeprefix('control-'),r) for r in controls])
mt=['| 页面 | 后端 ms | 并发 | RPS | p50 ms | p95 ms | CPU ms/请求 | ELD p99 ms |','| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
for r in sorted([r for r in rows if r['phase']=='matrix'],key=lambda r:({'hello':0,'medium':1,'large':2}[r['page']],r['delay'],r['concurrency'])):
    mt.append(f"| {r['page']} | {r['delay']} | {r['concurrency']} | {r['rps']:.1f} | {r['p50']:.1f} | {r['p95']:.1f} | {r['cpuMsPerRequest']:.2f} | {r['eldP99']:.1f} |")
top=p['functions'][0]
control_by={r['phase']:r for r in controls}
if controls:
    a=control_by['control-default-before'];b=control_by['control-no-etag'];c=control_by['control-default-restored']
    control_text=f"默认实现 {a['rps']:.1f} RPS → 仅跳过 ETag 计算 {b['rps']:.1f} RPS → 恢复默认实现 {c['rps']:.1f} RPS。对应每请求 CPU {a['cpuMsPerRequest']:.2f} → {b['cpuMsPerRequest']:.2f} → {c['cpuMsPerRequest']:.2f} ms。"
else:control_text='尚未完成，不能使用此稿作为最终报告。'
v=d['verification']
text=f'''# SvelteKit 独立复测与原报告修订

日期：2026-09-22。原实验：[六框架报告](../REPORT.md)。本次只重测 SvelteKit，其他五个框架没有在本次重新测量。

## 需要修正的结论

1. **原始约 95 RPS 的慢结果可以复现，但不能当作稳定容量或固定排名。** 三轮新进程、每轮 60 秒的默认实现测得 {focus[0]['rps']:.1f}、{focus[1]['rps']:.1f}、{focus[2]['rps']:.1f} RPS。原报告只观察两轮 30 秒，低估了进程间波动。较快和较慢样本全部保留；没有用网上的数字替换本地结果。
2. **不能把这个结果解释为 Svelte 组件渲染本身最慢。** 单独 CPU profile 中，完整 HTML 的 ETag `hash()` 占采样 self time 的 {top['pct']:.1f}%。调用栈为 `render_response → hash`。这是 SvelteKit 响应生成阶段的一部分，属于原本端到端口径，但不是大型后端数据序列化，也不能等同于组件 renderer 的耗时。
3. **ETag 对照仅用于定位，不能作为“矫正后的框架默认成绩”。** {control_text} 跳过 ETag 改变了 HTTP 条件缓存验证行为，不是本实验验证过的官方配置或生产优化方案。
4. **公开基准不具备直接校准条件。** 有旧版 Svelte 4 的小页面数据、绕过 HTTP 的 renderer/框架数据，也有 1000 行生产 SSR 数据；均没有同时匹配本次版本、HTML 体积、后端延迟、CPU 与并发。[逐项核对与原始链接](SOURCES.md)。

## 默认实现：原始与本次逐轮结果

约 1.482 MiB HTML、50 ms 模拟后端、64 个 HTTP Keep-Alive 连接。原始每轮预热 10 秒、测 30 秒；本次每轮预热 15 秒、测 60 秒。每一行均为独立新进程，不开 CPU profiler。表内 p50/p95 是该行全部请求的分位数，不能将它们的平均值当成合并分布分位数。

{baseline}

![默认实现复测对比](comparison.png)

仅供描述：本次三轮按总请求/总实测时间合并为 {d['focus']['rps']:.1f} RPS，窗口 RPS 中位数为 {d['focus']['rpsMedian']:.1f}。跨度明显，三次重复不足以估计可靠置信区间或宣布稳定容量；不应把合并数填回原六框架表制造新的精确排名。

## CPU profile 与因果对照

CPU profile 在第四个独立进程上采集：先预热 10 秒，再单独记录 20 秒负载。它有诊断开销，未纳入上表正式成绩。采样 self time 包含 idle/GC，因此 {top['pct']:.1f}% 不是单个请求的墙钟阶段占比，也不是 p95 的占比。

![CPU 热点](profile.png)

安装的 SvelteKit 2.70.3 生产产物中，`render_response` 在非延迟数据流分支对完整 `transformed` HTML 计算 ETag；hash 使用逐字符循环。已保存 [源码定位与 SHA256](evidence/compiled-source-evidence.json)、[profile 摘要](evidence/profile-summary.json) 和 [原始 CPU profile](evidence/profile.cpuprofile)。官方源码的对应实现见 [render_response](https://github.com/sveltejs/kit/blob/main/packages/kit/src/runtime/server/page/render.js)、[hash](https://github.com/sveltejs/kit/blob/main/packages/kit/src/utils/hash.js)；本次证据以锁定版本产物为准，不能用可变的 main 分支替代。

对照实验保持同一构建、页面和后端，只在诊断变体中删除生成 ETag 的一行，再还原。每个变体均为新进程，15 秒预热、45 秒测量；额外对三种页面、三种延迟执行同 URL 两次验收，比较 HTML 摘要及 ETag 是否存在。

{ct}

![ETag 诊断对照，不能替代默认成绩](etag-control.png)

这组对照与 profile 一起用于判断 ETag 的实际成本。单独测试未改变组件循环、没有用预渲染或 raw HTML 替代 SSR。三种页面 × 三种后端延迟 × 两次访问共 18 组验收，三个变体的完整 HTML SHA256 全部一致，恢复后的 ETag 也与原值一致，见 [对照验收](evidence/control/verification.json)。移除 ETag 发生在计算位置；在响应完成后仅删除 ETag header 并不能省去前面的计算。

**仍未证明的部分：** 为什么相同默认实现的新进程在约 93–203 RPS 之间大幅波动，对照恢复后的进程又约为 135 RPS。未采集 V8 优化/反优化轨迹，也没有固定宿主物理核心或频率，不能据此断言 JIT、ARM64 或调度是根因。profile 证明当前诊断运行的热点，对照证明该阶段影响；两者都不能完整解释所有进程间波动。

## 27 个补充场景

每种页面单独启动新进程，先预热 10 秒。页面内按固定随机顺序依次测试 50/200/500ms × 1/16/64 并发，每窗口预热 2 秒、测量 15 秒，共 27 窗口，每场景只有一次。它们用于检查负载响应趋势；尤其 C1/500ms 样本少，不能当作稳定尾延迟估计。

{chr(10).join(mt)}

## 环境、计时与验证

- 固定原镜像：Node 24.21.0、ARM64；SvelteKit 2.70.3、Svelte 5.57.1、adapter-node 5.5.7、Vite 8.3.0。使用原 npm lockfile 的 `npm ci` 和 `vite build`，`NODE_ENV=production node build/index.js`。
- 应用单进程、CPU 0–1 / 2 CPU 配额、1536MiB、V8 old-space 1024MiB；负载器 CPU 2–5 / 4 CPU；后端 CPU 6–7 / 2 CPU。每次只启动一个应用，所有场景串行。宿主仍是 macOS/OrbStack 共享机器，不保证物理资源独占。
- [页面生成器、后端、监控、压测器及锁文件](evidence/source-consistency.json) 与原实验逐字节一致。压测器读取完整 HTML 并验证状态、大小、请求 ID、结束标识。使用 identity，不测压缩。
- 默认大页面后端仍返回小描述 JSON，由应用生成 1536 条记录。包含实际 HTTP 后端等待、生成记录、SSR、必要框架处理与完整 HTML 传输；**没有增加大型后端 JSON 解析、浏览器 hydration 或逐阶段墙钟计时**。CPU profile 是本轮新增诊断。
- 总计 {v['windows']} 个测量窗口（包括单独标记的 profile 与 ETag 对照），{v['requests']:,} 个成功完整响应；0 错误、0 内容校验失败、0 新增 OOM kill；每个窗口的页面请求数与后端完成数一致。正式默认复测、profile 和变体结果分开保存，不混排。
- 首次搭建在发压前因误将监控端口环境变量传给负载 worker 而中止，已修正为只在应用/后端开启监控服务；原压测器代码未改。对照搭建还曾误选 sourcemap 文件，亦在正式发压前中止并修正。这两次尝试均没有正式性能窗口，日志分别保存在 `setup-retry.log` 与 `control-setup-retry.log`，临时资源已自动清理。

## 材料与清理

- [逐窗口数据](runs.csv)、[汇总 JSON](summary.json)、[执行记录](execution.log)、[对照执行记录](control-execution.log)。
- [默认复测资源清理](evidence/cleanup.json)、[对照资源清理](evidence/control/cleanup.json)。本地生成应用、node_modules、构建目录、测试数据随临时目录/专用 Docker 卷销毁；保留报告、指标、源码定位摘要、profile 和复现脚本。
- [复现入口](reproduce/README.md)。诊断修改只存在于一次性 Docker 卷，未修改仓库业务应用或已安装框架。
'''
(R/'REPORT.md').write_text(text)
print(R/'REPORT.md')
