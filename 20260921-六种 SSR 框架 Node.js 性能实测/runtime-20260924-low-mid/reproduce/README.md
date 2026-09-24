# 复现：低中并发 Event Loop / GC 分位数

请将本 reproduce 文件夹及上一级 PROTOCOL.md 复制到新的空目录，保持 新目录/reproduce 和 新目录/PROTOCOL.md 层级。不要把旧 runs/evidence 一起复制，以免覆盖证据。使用 Docker（至少8个vCPU、约8GiB）、Python3，沿用镜像摘要和六个 lockfile。

```sh
python3 reproduce/setup.py
python3 reproduce/validate.py
python3 reproduce/bootstrap.py
python3 reproduce/run.py
python3 reproduce/summarize.py
python3 reproduce/runtime_report.py
python3 reproduce/runtime_plot.py
```

图表步骤依赖 matplotlib 和 numpy，只在测量完成、Docker资源清理后执行。参考绘图库版本见 plot-requirements.txt。结果输出到 reproduce 的上一级。host.json 是本次另行记录的宿主硬件信息；复现未提供该文件时报告显示宿主硬件未记录，Docker VM 信息仍自动采集。

setup 在专属 Docker 数据卷内顺序 npm ci/build 六个应用。源码由 base_prepare.py / prepare.py 生成；动态路由真实读取后端 JSON 并保留 hydration 数据。patch.mjs 关闭 SvelteKit 的 HTML ETag 实际哈希计算。

validate 独立进行全页完整内容校验、gzip/br主动协商及压缩/ETag哨兵自检，不纳入正式性能统计。bootstrap 自检 GC 数学、事件边界、已知阻塞、实际GC事件和禁用模式，并停止构建容器。

run 先做24个监控开销窗口，再串行执行108组合×2轮=216个正式窗口和36个空闲基线。并发1/8，不寻求极限容量。监控使用10ms Event Loop直方图，预分配GC事件数组，内存1Hz采样，无逐请求埋点。GC全类型及各类型分位数由原始事件独立重算；未观测到用null，不填0。

**资源范围**：标签 ssrbench.run=20260924-runtime；容器前缀 ssrbench3-；同一 Docker daemon 不要同时运行两个本实验。run 在正常结束或Python异常时清理本轮容器、网络、数据卷，不执行全局prune。若只运行setup/validate或遇到强制断电/SIGKILL，恢复后执行：

```sh
python3 reproduce/common.py
```

GC统计中的 kind=2 在该Node镜像对应 minor_mark_sweep。在线采集器将未知名称类型标为unknown但始终保留原始kind；离线脚本按镜像实际常量重分组，所有事件仍包含在all中。

PROTOCOL.md 是本轮预先确定的测量协议。跨硬件/版本的绝对数值不可直接比较。原始JSON和构建/验收/清理证据应与报告一起保留。

本轮 CONCLUSIONS.md 是核对原始数据后撰写的解释，报告生成器存在该文件时会嵌入。重新测量时请重新分析后撰写，不要复制旧结论。
