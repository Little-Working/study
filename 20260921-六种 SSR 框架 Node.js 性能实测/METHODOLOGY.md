# SSR Node.js 基准测试口径

测试日期：2026-09-21（Asia/Shanghai）。报告是这台 ARM64 Docker 主机上的合成负载实测，不代表任意生产业务的框架排名。

## 比较对象

| 框架 | 版本 | production 路径 |
| --- | --- | --- |
| Next.js | 16.3.5，React 19.3.0 | `next build` → `next start`，App Router，动态 SSR |
| Nuxt | 4.5.2，Vue 3.5.41 | `nuxt build` → Nitro 2.13.4 node-server |
| SvelteKit | 2.70.3，Svelte 5.57.1 | `vite build` → adapter-node 5.5.7 |
| TanStack Start | 1.168.56，Router 1.170.38，React 19.3.0 | `vite build` → Nitro 3.0.260903-beta |
| React Router | 8.4.0，React 19.3.0 | `react-router build` → `react-router-serve` / Express 5.2.1 |
| SolidStart | 2.0.5，SolidJS 1.9.15，Router 1.0.0 | `vite build` → Nitro 3.0.260903-beta |

选择 npm 在测试时提供的版本，依赖实际版本和 integrity 由 `reproduce/locks/` 锁定。SolidJS 通过 SolidStart 测试全栈 SSR，而非只调用 Solid 的 renderToString。TanStack 与 SolidStart 使用的 Nitro 是 beta 版本，这属于结果适用边界。production 构建日志保存于 `evidence/*-build.log`。

## 运行环境与隔离

Node.js 24.21.0、Debian bookworm-slim、Linux ARM64，Docker Engine 29.4.0 / OrbStack。宿主机为 Apple M4（Mac16,12）、10 个逻辑 CPU、16 GiB 内存。Docker VM 有 10 个逻辑 CPU、约 8 GiB 内存。镜像 digest 和内核版本见 `evidence/environment.json`。

| 角色 | CPU 亲和性（VM 逻辑 CPU） | CPU 配额 | 内存限制 |
| --- | --- | --- | --- |
| 被测应用 | 0–1 | 2 CPU | 1536 MiB，无额外 swap；V8 old-space 1024 MiB |
| 压测器 | 2–5 | 4 CPU | 1024 MiB |
| 模拟后端 | 6–7 | 2 CPU | 512 MiB |

每次只运行一个被测应用，所有框架的资源约束、Node 版本、环境变量、监控 preload 相同。结果包含统一监控的开销，未另测关闭监控的基线。应用和依赖存放在 Docker 原生卷，不通过 macOS bind mount 读取运行时文件。构建完成后才开始正式计时。没有 CDN、反向代理、TLS、数据库或其他业务中间件。采用各框架的 Node production 启动器；React Router 的官方 serve 包含 Express 静态资源检查、compression 中间件（identity 请求不压缩）和 morgan tiny 访问日志，其他框架默认不逐请求打印访问日志。该差异保留在端到端服务成本中，因此不能将全部差异归因于 UI 渲染器本身。

这是宿主机上的虚拟化环境，CPU 亲和性不能保证宿主物理核心独占，也无法排除 macOS 其他进程、功耗和热调度影响。绝对吞吐量不应直接用于生产容量规划。

## 页面与后端数据

所有框架输出相同的 main / h1 / section / article / h2 / p / span / footer 结构。每条记录包括序号、标题、930 字节 ASCII 描述、价格，使用各自组件循环生成；没有通过 raw HTML / innerHTML 注入整页。

- Hello World：0 条列表记录，保留框架文档、hydration/bootstrap 输出、标题和结束标识。
- 中页面：800 条记录，目标约 800 KiB 的完整未压缩 HTML。
- 大页面：1536 条记录，目标约 1.5 MiB 的完整未压缩 HTML。

各框架接收相同的 `rid/count/textLength/delay` 紧凑数据描述，并在每次 SSR 时构造记录数组。后端通过独立容器的真实 HTTP 请求返回描述，执行 50、200、500 ms 的 setTimeout。延迟没有用忙循环消耗 CPU。实际定时耗时、并发数和请求数单独采集。

**因此这里测的是等待后端后的组件生成、SSR、框架序列化和完整 HTML 传输，未覆盖 800 KiB/1.5 MiB 后端 JSON 的网络传输、解析及对象保留成本。** 合成文本高度重复，且未压缩，不代表 gzip/brotli 的成本。Next.js 页面通过 App Router 的 server page 获取描述，再交给带 `'use client'` 的组件进行服务端 HTML 渲染与客户端 hydration；没有启用纯 RSC 大树或 client-only/关闭 SSR。这使其与其他框架的 hydration 模型更接近，但不能外推到所有 Next.js RSC 页面。

生产 HTTP 验收对每个框架执行 3 页面 × 3 延迟 × 同 URL 重复 2 次，要求每次 HTTP 200、无内容压缩、真实 article 数正确、请求 ID 和结束标识存在、体积在约定范围、完整响应时间不短于后端延迟。18 个页面请求必须对应 18 个后端请求。验证结果只保存大小、计数、摘要和 headers，不保存 HTML 测试数据。

正式请求携带不同 rid，并对每个完整响应校验 200、预期大小、rid、结束标识。Next.js 强制动态和 no-store；其他框架未启用 prerender、ISR 或页面缓存。每个正式窗口要求请求发出数 = 完整响应数 = 校验成功数 = 后端调用数 = 后端完成数。

## 负载与重复

HTTP/1.1 Keep-Alive，`Accept-Encoding: identity`，没有 pipelining。最多 4 个负载 worker，总并发为 1、16、64。一个连接完成全部响应后才发下一个请求，属于**闭环固定并发**，没有恒定到达率或 coordinated-omission 修正。没有独立测量 Docker 网络或内存带宽的极限，因此资源健康检查只证明未观察到 CPU 配额限流/OOM，不证明不存在其他共享资源影响。

- 共 6 框架 × 3 页面 × 3 延迟 × 3 并发 = 162 个独立场景。
- C=1：每场景 6 秒、1 次，作为低负载延迟参考。
- C=16 / C=64：每场景每次 8 秒、2 次，共 216 个主要测量窗口。
- 总计 270 个矩阵窗口；每个之前有 1 秒同配置预热。每个新应用进程先进行 8 秒大页面预热。
- 第二轮使用相反的框架顺序，并重新启动应用进程。每轮内页面/延迟组合采用固定种子的随机顺序，所有框架一致。
- 另对每个框架开启新进程，10 秒预热后测量 30 秒：大页面、50 ms、C=64，执行两轮且第二轮反转框架顺序，共 12 个持续窗口。增加第二轮的原因是短窗口出现较大波动，诊断记录见 `evidence/variability-check.json`。

发压到期限后停止新请求，但继续排空已发请求。RPS 分母是从开始到全部在途响应结束的实测时间，因此通常稍长于 6/8/30 秒。没有把尚未完成的请求计入成功吞吐量。应用 CPU/GC/ELU 监控从发压前 reset 到排空后读取，包含几毫秒至几十毫秒的控制请求开销，与客户端窗口存在小幅边界差异。

两次主要重复只用于呈现波动，不能据此宣称统计显著性；C=1、500 ms 的单窗口仅约 12 个响应，p95/p99 不适合当稳定尾延迟。短窗口也不能证明不存在长期内存泄漏。30 秒持续测同样仅用于短期核对，不是小时级稳定性测试。

## 指标定义

| 指标 | 采集 / 计算方式 | 解释边界 |
| --- | --- | --- |
| RPS / goodput | 完整响应数 / 实测排空时间；goodput 只计校验通过的 200 | 正式有效窗口两者相等。这里只请求 HTML，不包括静态资源 |
| 页面 QPS | 成功页面完成数 / 同一时间 | 每个请求对应一个页面，数值等于 goodput；不是数据库 query/s |
| 后端调用率 | 后端实际计数 / 同一客户端窗口 | 每页一次后端请求，通过计数对账验证 |
| 完整响应延迟 | 发起 http.get 到 response end | 包含后端等待、SSR、排队和 Docker 内网完整传输 |
| 首个 body 字节时间 | 发起 http.get 到第一段 response data | 报表简称 TTFB；并非浏览器 Navigation Timing，早到壳 HTML 不代表业务内容完成 |
| Node CPU % | `(user + system CPU 微秒) / wall 毫秒 / 10` | 100% = 1 个核心；包括进程内 V8 等线程，可超过 100%，应用配额 200% |
| CPU ms/成功请求 | Node CPU 时间 / 成功响应数 | 用来区分“吞吐高所以 CPU 高”与单位请求成本高 |
| Event loop utilization | `performance.eventLoopUtilization()` 区间差值 | 不是 CPU 使用率；1 表示事件循环没有空闲 |
| Event loop delay | `monitorEventLoopDelay({resolution:10})` 的 p50/p95/p99/max | 单位转换 ns→ms；10 ms 采样本身造成基线，不把约 10 ms 误解成额外卡顿 |
| GC | PerformanceObserver 的 gc 条目数、duration、kind | 记录 minor/major/incremental；GC duration 占比不等同严格 stop-the-world 比例或 CPU 占比 |
| RSS / heapUsed | `process.memoryUsage()` 每 200 ms 采样，另记起止值 | “峰值”为采样及起止观测值中的最大值，可能漏掉瞬时峰；RSS 包含共享驻留页，不等于 cgroup memory |
| 容器资源 | cgroup v2 cpu.stat、memory.current、memory.events | 检查 CPU throttling 和 OOM；内存与 RSS 保持独立口径 |
| 压测器 / 后端健康 | 同样记录 CPU、内存、event loop、实际延迟 | 用于判断结果是否被负载生成或后端挤占限制 |

矩阵汇总中吞吐量取同场景两轮 `Σ成功请求 / Σ实测时间`；p95/ELD p99/CPU 等取各窗口对应指标的中位数，并保留每轮原值与 RPS 范围。**窗口 p95 的中位数不是合并请求分布的 p95。** 内存展示窗口采样峰值的最大值；矩阵进程承接此前场景的堆/RSS，跨框架比较内存优先看新进程的持续测。

## 参考接口与 production 部署文档

- [Node.js performance hooks](https://nodejs.org/docs/latest-v24.x/api/perf_hooks.html)：event loop 和 GC 采集接口。
- [Node.js process](https://nodejs.org/docs/latest-v24.x/api/process.html)：CPU 和内存计数接口。
- [Next.js Route Segment Config](https://nextjs.org/docs/app/api-reference/file-conventions/route-segment-config)：动态渲染配置。
- [Nuxt deployment](https://nuxt.com/docs/4.x/getting-started/deployment)：Nitro Node 服务构建与启动。
- [SvelteKit adapter-node](https://svelte.dev/docs/kit/adapter-node)：Node production 构建与启动。
- [React Router production server](https://reactrouter.com/api/other-api/serve)：框架提供的 Node 服务。
- [TanStack Start hosting](https://tanstack.com/start/latest/docs/framework/react/guide/hosting)：Nitro/Node 部署路径。
- [SolidStart v2 getting started](https://docs.solidjs.com/solid-start/v2/getting-started)：v2 与 Node 24 要求。

这些文档用于确认运行方式和指标含义。性能结论只来自本次本地测量，不来自官方宣传或其他机器的榜单。
