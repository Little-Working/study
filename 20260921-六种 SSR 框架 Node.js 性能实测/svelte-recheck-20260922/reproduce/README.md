# SvelteKit 独立复核复现

使用原报告中的固定 Node 镜像及本目录的锁文件。需要 Docker、Python 3、依赖下载网络。脚本要求没有同名基准容器和同标签资源；不修改业务项目，不清理其他 Docker 服务。

在新目录中复制本目录，确保相邻 `evidence/` 不包含既有结果。先运行默认复测，结束并清理后才能启动对照：

```sh
python3 reproduce/recheck.py
python3 reproduce/control.py
python3 reproduce/profile_summary.py
```

- `recheck.py`：三个新进程的 60 秒正式大页面窗口、一个独立 20 秒 CPU profile、27 个 15 秒矩阵窗口。`finally` 清理专用 Docker 容器、网络、卷和本地临时生成应用。
- `control.py`：复用同一搭建过程，执行默认 → 仅删除完整 HTML ETag 计算 → 恢复默认，三次独立进程，每次预热 15 秒、测 45 秒。变体会改变条件 HTTP 缓存验证行为，只用于定位，不可代替默认框架成绩。
- `profile.cjs`：Inspector 在预热后收到信号才开始采样，测量后停止并保存；没有监听调试网络端口。
- `profile_summary.py`：统计采样 self time，含 idle/GC，不是逐请求墙钟阶段耗时。
- 原页面生成器、后端、监控、压测器、页面验收及 npm 锁文件沿用原实验。

本次保留了原报告目录，因此 `summarize.py` 可以读取 `../../evidence/` 中原来的两轮持续测作比较。若只复制本次复核目录，可直接读取新 `evidence/`，或调整该脚本的原报告路径。

```sh
python3 reproduce/summarize.py
python3 reproduce/plot_recheck.py  # 需 matplotlib
python3 reproduce/write_report.py
```

报告解释部分针对已观察数据编写，新机器结果必须重新审阅。原始 CPU profile 的 `file:///bench/` 路径是一次性 Docker 卷中的构建位置，不是当前可访问的本地文件。

本次诊断曾临时提取 `evidence/compiled-server/` 用于核对 profile 与代码；交付前删除该构建目录，仅保留定位、SHA256 和必要的窄代码片段。重现后也应删除生成的构建目录、`__pycache__/` 等临时产物。中断时使用 `python3 reproduce/run.py cleanup` 清理 `ssrbench.run=20260922` 标签的资源；对照清理证据需保存到相应输出目录。
