# SvelteKit 公开资料交叉核对

检索日期：2026-09-22。只采用官方文档、官方源码和基准作者直接发布的结果；未用搜索摘要、论坛印象或客户端 DOM/Lighthouse 排名替代服务端 SSR 数据。

| 来源 | 公开数据 / 做法 | 与本次实验的关键差异 | 用途 |
| --- | --- | --- | --- |
| [eknkc/ssr-benchmark](https://github.com/eknkc/ssr-benchmark) | SvelteKit 589 ops/s，平均 1.696ms，响应约 184.46KB；1000 行两列 UUID | Node 20.6.1、M1 Pro；模拟 Request/Response，绕过真实 HTTP；并非本次 1.5MiB、后端 50ms、64 并发 | 证明公开排名依赖负载，无法按比例换算本次 RPS/p95 |
| [Pau Sanchez 原作者实测](https://pausanchez.com/en/articles/frontend-ssr-frameworks-benchmarked-angular-nuxt-nextjs-and-sveltekit/) | 2024-06-15；Svelte 4.2；Hello World 4063 RPS，拉取本地 HTTP 字符串 2286 RPS | Node 22.2.0、Intel i7、100 连接、10 秒；小页面、旧主版本，没有相同后端延迟 | 仅作历史交叉参考，不能校准 Svelte 5 大页面数据；不引用其口径不明确的 latency 列 |
| [Niral 官方项目的基准](https://niral.site/docs/benchmarks) | 宣称 1000 行、生产服务、100 连接、10 秒：SvelteKit 2 约 599 req/s，p50 137ms、p99 约 1.1s；单独 Svelte 5 renderer 约 0.18ms/render | 本页未完整给出可匹配的硬件、准确依赖版本、HTML 字节数和后端等待；由参与比较的框架项目发布 | 说明纯 renderer 与完整框架请求应区分；不作为独立权威排名或本次更正值 |
| [SvelteKit adapter-node 官方文档](https://svelte.dev/docs/kit/adapter-node) | 生产构建后运行 Node adapter 产物 | 本次使用 `vite build`、`node build/index.js`、`NODE_ENV=production`；没有使用 dev server | 验证生产运行方式 |
| [SvelteKit 性能文档](https://svelte.dev/docs/kit/performance) | 建议在构建后的环境中分析性能，使用 instrumentation 辨识耗时 | 没有承诺任意页面的 RPS/p50/p95 | 支持以实际版本的 profile 和测量为准 |
| [官方 render_response 源码](https://github.com/sveltejs/kit/blob/main/packages/kit/src/runtime/server/page/render.js)、[hash 源码](https://github.com/sveltejs/kit/blob/main/packages/kit/src/utils/hash.js) | 无延迟数据流分支中，对完整响应字符串计算 ETag；hash 遍历字符串字符 | `main` 可变化，不能代替已安装版本证据 | 提供待验证热点线索；最终判断必须以本地锁定版本的源码和 profile 为准 |

没有找到同时匹配 Node 24.21.0、SvelteKit 2.70.3 / Svelte 5.57.1、ARM64 Docker、2 CPU、1.5MiB、50ms 后端、64 并发的公开基准。因此不能直接“用网上正常值替换异常值”，需要保留原始测量并独立复测。
