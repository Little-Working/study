# 复现说明

依赖：Docker（至少分配 8 个 vCPU；本次为 10 vCPU/约 8 GiB、ARM64）、Python 3。使用同一镜像摘要和保留的 lockfile；跨硬件或架构所得数值不可直接比较。

请仅复制 `reproduce` 文件夹到一个新的空报告目录，保留 `新目录/reproduce/` 层级，不复制旧的 runs/evidence，然后进入该新目录执行下列命令，以免覆盖已有证据。脚本只操作固定 `ssrbench.run=20260922-v2` 标签的实验资源；同一 Docker daemon 同时只能运行一个本实验。

```sh
python3 reproduce/setup.py
python3 reproduce/validate.py
python3 reproduce/run.py
python3 reproduce/analyze.py
python3 reproduce/report.py
python3 reproduce/plot.py
```

最后一步需要 matplotlib，仅在压测完成后运行，以免制图占用测量期间的宿主机资源。生产构建在临时 Docker 数据卷内，不修改业务仓库应用；所有应用源码由 `base_prepare.py` 与 `prepare.py` 生成。

绘图库版本见 `plot-requirements.txt`，可在独立 Python 虚拟环境中安装。METHODOLOGY.md、历史协议调整及基础设施修复记录属于本次实验文档；复制复现脚本会重新产生测量证据，不会重新制造这些历史记录。

`setup.py` 构建后会留下本轮服务资源供后续使用；若仅运行构建/验收，需要执行 `python3 reproduce/common.py` 清理。`run.py` 在成功或 Python 异常退出后清理本轮容器、网络和卷。若宿主机强制断电或进程被 SIGKILL，finally 无法运行，恢复后需手工执行相同清理脚本。脚本不做全局 prune。

构建阶段运行 `inspect-build.mjs` 生成 `build-audit.json`，保留实际安装版本与 ETag 相关产物线索。正式验收还会保留配置、ETag 补丁和主动协商证据。

`runs/*.json` 保存每个测量窗口；`evidence/*-validation.json` 保存所有页面验收；`evidence/patches.json` 保存 SvelteKit ETag 计算点前后散列；`evidence/cleanup.json` 为实际销毁记录。`run.log` 的 warmup 行只供诊断，不参与统计。

完整指标定义、样本时长、资源配额和局限见上级目录的 METHODOLOGY.md。
