# 六种 SSR 框架：公开评测与本机复测对照

检索日期：2026-09-22。本文是对公开作者报告的核对与比较，没有重新运行外部项目，也不使用外部 RPS 对本机数据做数值修正。

## 结论

本机综合判断仍限于本次构造业务：SolidStart 领先；TanStack Start 与 SvelteKit 接近；Nuxt 居中；React Router 与 Next.js 的位置取决于吞吐、延迟和 CPU 成本的权重。外部评测部分支持这种趋势，但不支持将它升级为通用排名。

需要特别收窄两项判断：React Router 在公开电商评测修正版中与 TanStack Start 接近，不能普遍排在 Nuxt 后面；Next.js 在简单动态 SSR 的公开测试中也可以接近或略高于 TanStack Start，不能普遍认定最慢。SolidStart 的外部端到端佐证较少，且下列来源属于其他框架项目自己的评测，证据强度有限。

## 本机基准及比较边界

本机采用 Node 24.21.0、M4 / Docker ARM64、单应用进程、应用 2 vCPU，后端经 HTTP 返回 50/200/500 ms 延迟及真实 JSON。关闭测试路径的压缩与 ETag，保留原生组件渲染和 hydration 序列化。SvelteKit 使用移除 HTML ETag 计算的明确补丁，不代表默认配置。

版本：Next.js 16.3.5；Nuxt 4.5.2；SvelteKit 2.70.3 / Svelte 5.57.1；TanStack React Start 1.168.56；React Router 8.4.0；SolidStart 2.0.5。

27 种页面/延迟/并发组合，每框架每组合两次 8 秒测量。下表逐场景相对 SolidStart 后等权取几何平均；延迟和 CPU 指数取倒数，均越高越好。这是三个独立指标，并没有预先定义一个综合加权分数。

| 框架 | 吞吐指数 | p95 效率指数 | CPU 效率指数 |
| --- | ---: | ---: | ---: |
| SolidStart | 100.0 | 100.0 | 100.0 |
| TanStack Start | 91.8 | 91.3 | 89.9 |
| SvelteKit | 90.5 | 86.0 | 86.2 |
| Nuxt | 88.6 | 81.1 | 73.2 |
| React Router | 83.9 | 83.8 | 68.7 |
| Next.js | 84.8 | 78.1 | 49.5 |

依据：[本机报告](REPORT.md)、[逐组合结果](rerun-20260922-noetag-json/RESULTS.md)、[汇总原始值](rerun-20260922-noetag-json/summary.json)。短测存在波动，相邻名次没有统计显著性证明；矩阵复用进程的 RSS 不用于页面独立内存排名。

## 外部来源与原始数字

### 1. Platformatic / Matteo Collina：采用 2026-04-10 修正版

AWS EKS 混合电商流量，目标到达率 1,000 req/s，3 分钟；统一关闭压缩。修正版报告 TanStack 和 React Router 的 Node/Watt 配置可承受目标负载；Node p99 分别为 121 / 298 ms。Next.js 在该负载下成功率约 55%。这是负载目标和过载结果，不是各框架最大成功 RPS。

旧版有 gzip 配置不一致，不能继续引用其差距作结论。该来源由 Watt 厂商发布，公开了代码，但场景、版本和多 Pod 部署与本机不同。它支持 TanStack/React Router 的电商 SSR 表现，反驳 React Router 必然属于倒数一档。

来源：[修正版评测](https://blog.platformatic.dev/ssr-framework-benchmarks-v2-corrected-results)；[复现代码](https://github.com/platformatic/k8s-watt-performance-demo/tree/ecommerce)。

### 2. eknkc/ssr-benchmark：1000 行表格的服务端渲染实验

作者公布：SvelteKit 589 ops/s、Remix 449、Nuxt 381、Next Pages 104、Next App 53。环境为 Node 20.6.1、M1 Pro；绕过真实 TCP，以模拟 HTTP 对象调用框架，渲染 1000 行双 UUID 表格。各框架输出体积不同。

它与本机中大页中 SvelteKit 相对 Next.js 的优势方向一致，但 ops/s 不能换算成本机 HTTP RPS。这里的 Remix 不是本机 React Router 8；纯 Solid renderer 也不能当作 SolidStart。README 没有把当前结果表绑定到清晰的运行版本快照，故仅作历史趋势参考。

来源：[原始结果、方法和代码](https://github.com/eknkc/ssr-benchmark)。

### 3. Pau Sanchez：2024-06-15 的 Hello World 与 HTTP 数据加载

Node 22.2.0、i7-8565U、100 连接、10 秒。Hello World：SvelteKit 4,063 RPS、Next.js 2,570、Nuxt 1,376；增加本地 HTTP 数据加载后：2,286、388、947 RPS。原文标注 Svelte 4.2、Next 14.2、Nuxt 3.11；Svelte 版本不等于 Kit 版本。

这是与本机 Hello World 排序不一致的证据，也显示仅增加数据加载就可能改变 Next/Nuxt 次序。版本、后端延迟和配置不同，不能用这些数字矫正本机。只摘录吞吐，不将原文 latency 列解释为 p50/p95。

来源：[作者评测](https://www.pausanchez.com/en/articles/frontend-ssr-frameworks-benchmarked-angular-nuxt-nextjs-and-sveltekit/)；[复现代码](https://github.com/pausan/toy-ssr-frontend-benchmark)。

### 4. rshono：2026-09-03 的同应用比较

Apple M1，100 行动态 SSR：Next.js 276 RPS、TanStack Start 253；三个客户端组件的 interactive 路由：Next.js 542、TanStack 933。作者建议把约 10% 内的差距当作接近，因此 276/253 不证明 Next.js 显著领先。

代码说明数据在模块加载时解析、无后端 I/O、应用压缩关闭；TanStack 使用 vite preview，与另两者生产服务器不对称。来源属于框架项目自测，只用来说明不同路由会改变相对表现，不赋予高权重。

来源：[公布数据](https://www.rshono.com/benchmarks)；[方法与限制](https://github.com/rshono/rshono/blob/main/packages/benchmarks/README.md)。

### 5. Niral：SolidStart 的补充佐证，低权重

项目文档称使用 1000 行动态 SSR、100 连接、10 秒、交替测试顺序：SolidStart 1 约 1,885 RPS，SvelteKit 2 约 599，Next 16 约 303。

方向与本机大页 SolidStart > SvelteKit > Next.js 一致。但该页面未提供清晰测试日期、完整硬件/运行时/依赖版本与压缩/ETag条件；且为另一个框架项目自测，本文未独立复现。只能作为补充，不能证明 SolidStart 的通用第一名。

来源：[项目发布的评测与方法概述](https://niral.site/docs/benchmarks)。

## 如何结合，而不是混算

1. 支持的趋势：部分较复杂、动态且不缓存的 SSR 负载，会拉大框架间计算成本和吞吐差异。
2. 修正的泛化：SvelteKit 不是所有场景都慢；Next.js 不是所有场景都最慢；React Router 不应被普遍归入性能落后一档。
3. 仍未证明：跨全部业务的六框架固定顺序、SvelteKit 与 TanStack 的普遍先后、HTML 字节数单独造成的性能比例。
4. 不能把外部 ops/s、目标到达率和成功 HTTP RPS 求平均。硬件、版本、并发、请求完成定义、缓存、序列化语义和错误率均不同。
5. 上述来源没有提供与本机等价的六框架 Event Loop、GC、CPU、内存完整矩阵，因此运行时排名仍只能依据本机实验，不能声称已被外部全面验证。

检索也发现 Lighthouse/客户端渲染、静态站点、Cloudflare Workers 和 SPA 对比。这些测量边界不同，未并入 Node 动态 SSR 性能排名。所有外部数字均为作者报告值；本机原始结果保持不变。
