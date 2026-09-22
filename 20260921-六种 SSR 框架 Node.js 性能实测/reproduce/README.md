# 复现说明

此目录是生成器、压测器和监控代码，不包含运行中的服务、已生成页面、node_modules 或构建产物。

在新的空目录中仅复制 `reproduce/` 后运行，不复制历史 `evidence/`，避免混合不同机器/时间的结果。需要 Docker（至少 8 个逻辑 CPU、约 8 GiB 内存）、Python 3 和依赖下载网络。

```sh
docker pull public.ecr.aws/docker/library/node@sha256:2fe369e969550cde8e867afc3fe370b260140cab4a23d467074295b42163d553
python3 reproduce/all.py
```

`all.py` 会生成独立最小应用，使用保存的 package-lock.json 执行 `npm ci`，production 构建，执行 HTTP 验收与性能矩阵，并在 `finally` 中删除专用容器、网络、卷和本地临时应用。测试耗时约 45–60 分钟，依赖下载/构建另计。未使用 Docker image build；production 产物位于一次性 Docker 卷内，由同一固定 Node 镜像运行。不会修改仓库已有 playground 应用。

运行中断后可执行 `python3 reproduce/run.py cleanup`，它只按 `ssrbench.run=20260921` 标签清理本基准资源，不执行全局 prune，不删除基础镜像。强制结束 Python 或宿主机关机不能保证 finally 已运行，需要显式清理。

- `prepare.py`：六框架应用生成器。Next.js 使用 App Router + Client Component 的服务端 HTML 渲染；其余使用常规可 hydration 的框架页面。
- `backend.mjs`：独立 HTTP 后端，50/200/500 ms 非阻塞定时延迟，每次请求返回相同结构的紧凑数据描述及请求 ID。
- `metrics.cjs`：Node preload，200 ms 内存采样、10 ms event loop histogram、GC PerformanceObserver、process CPU 与 cgroup 计数。
- `load.mjs`：4 个 worker 上限的闭环 HTTP/1.1 Keep-Alive 压测器，每连接一次只发一个请求，消费完整响应并校验结束标识、请求 ID 和体积。
- `__tests__/page.test.mjs`：生产服务验收，同 URL 重复访问确认每次回源，校验状态、压缩、HTML 记录数、体积和延迟。
- `run.py`：运行顺序、预热、时长、并发、指标对账和资源清理。
- `locks/`：实际安装的 package.json 和 npm 锁文件。复现以此为准。

后端只有生成规则和非敏感合成数据，没有外部数据库。报告保留 JSON 指标证据、构建日志、验收摘要、访问日志的状态码汇总和锁文件；这些是报告材料，生成的测试页面及服务数据随 Docker 卷销毁。

测量完成后，可执行 `python3 reproduce/analyze.py --complete` 进行完整性检查并生成 CSV/JSON 汇总；安装 matplotlib 后执行 `python3 reproduce/plot.py` 生成 PNG/SVG，最后执行 `python3 reproduce/report.py` 生成表格报告。解释性结论仍需根据新机器的新结果审阅，不能沿用旧排名。
