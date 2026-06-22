# Goal 1 Tasks

## Task 1: 定位未来规划和相关展示入口

验证标准：列出所有包含“未来计划/未来规划/roadmap”内容的权威文件，并确认哪些需要修改。

完成记录：

- 已完成。
- 权威未来规划文件：`docs/deliverables/未来规划.md`。
- 相关展示实现：`web_agent_demo/server.py` 的 `render_index()`，负责 Web demo 的 HTML、CSS、页面文案、Agent 阶段轨道、实时事件流、检查器、Self-Evolving Code Loop 和候选表。
- 相关测试：`tests/test_web_agent_demo.py`，当前对页面标题、阶段名、Evolution 区域和若干样式片段有断言，后续修改页面文案/样式时需要同步测试。
- 搜索结论：除本 goal 记录外，未发现其他独立的 `future`、`roadmap`、`未来规划` 文件；`docs/deliverables/项目总结.md`、`产品说明文档.md`、`项目文档.md` 中有 Agent 阶段说明，但不是未来规划的权威来源。
- 后续修改范围建议：Task 2 优先完善 `docs/deliverables/未来规划.md`；Task 4-5 再调整 `web_agent_demo/server.py` 和对应测试，使页面从当前偏展示化/炫酷的 workbench 风格收敛为更专业的开发者工具风格。

## Task 2: 完善未来规划内容

验证标准：未来规划文档中的条目从泛泛描述变为具体、开发者可执行的路线图，并保留项目语境。

完成记录：

- 已完成。
- 重写 `docs/deliverables/未来规划.md`，将原先偏产品演示和“指挥舱”方向的规划，改成面向开发人员和技术评审的“调度分析工作台”路线图。
- 补齐了后续需要实现的具体内容：场景元数据层、风险画像、Baseline vs AutoSolver 对比、决策解释面板、抽象调度结果视图、ROI 参数化估算。
- 明确了实现位置建议，覆盖 `web_agent_demo/sample_cases.py`、`web_agent_demo/server.py::list_cases()`、前端 report 展示和 `tests/test_web_agent_demo.py`。
- 增加了页面风格准则，明确避免花哨示例图风格，改用中性、克制、高信息密度的工程控制台风格。
- 增加了三阶段实施路线图：开发者工作台整理版、调度分析增强版、落地接口预留版。
- 增加了开发验证清单，包括 `python -m unittest tests.test_web_agent_demo`、`python -m py_compile web_agent_demo/server.py` 和误导性文案检查。
- 验证：`rg -n "场景元数据|Baseline vs AutoSolver|决策解释|调度结果视图|ROI|页面风格准则|开发验证清单|验收标准|实现位置建议|开发人员" docs/deliverables/未来规划.md` 能命中关键章节。
- 验证：`rg -n "官方成绩|本地分数|黑科技" web_agent_demo || true` 无输出，当前页面未新增这些误导性表达。
- 验证：`git diff --check -- docs/deliverables/未来规划.md` 通过。

## Task 3: 第一轮全面检查-debug循环

验证标准：检查前 2 个任务的内容一致性、遗漏项、术语一致性和潜在副作用；发现问题立即修复。

完成记录：

- 已完成。
- 全量复读 `goal/goal-1/input.md`、`goal/goal-1/plan.md`、`goal/goal-1/tasks.md` 后执行检查，确认前两项仍对齐原始目标：参考未来规划、完善内容、风格转向专业开发者工具。
- 内容覆盖检查：`docs/deliverables/未来规划.md` 已覆盖原规划中的业务场景、Before/After 对比、决策解释、调度结果展示、ROI/商业价值、阶段路线图，并改成更具体的实现位置、字段、验收标准和验证命令。
- 旧结构残留检查：`rg -n "未来应该怎么做|项目该如何优化|后续如何修改跟进|建议的决赛演示脚本|即时履约调度指挥舱|决赛演示版|产品原型版|产品演示职责" docs/deliverables/未来规划.md || true` 无输出。
- 关键章节检查：`rg -n "场景元数据|风险画像|Baseline vs AutoSolver|决策解释面板|调度结果视图|ROI|页面风格准则|分阶段实施路线图|开发验证清单|推荐演示流程" docs/deliverables/未来规划.md` 均命中。
- 误导性表达检查：`rg -n "官方成绩|本地分数|黑科技" web_agent_demo || true` 无输出；文档中这些词只出现在禁用/约束说明里，不会污染当前页面。
- 改动范围检查：`git diff --name-status` 只显示 `docs/deliverables/未来规划.md` 的 tracked 修改；`goal/` 是本 goal 流程新增记录目录。
- 格式检查：`git diff --check -- docs/deliverables/未来规划.md` 通过。
- 测试检查：`python` 命令不存在；改用 `python3 -m unittest tests.test_web_agent_demo`，7 个测试通过。
- 语法检查：`python3 -m py_compile web_agent_demo/server.py` 通过。
- 测试副作用处理：`python3 -m unittest tests.test_web_agent_demo` 会改写 `autosolver_agent/evolution_state/*` 和 `web_agent_demo/generated_cases/*`；已仅对这 11 个测试副作用文件反向应用其自身 diff，保留目标文档和 goal 文件。
- 清理后状态：`git status --short --branch` 只剩 `docs/deliverables/未来规划.md` 修改和 `goal/` 新增目录。
- 结论：未发现需要修复的问题；对 Task 1-2 当前实现有足够信心，可以进入 Task 4。

## Task 4: 专业化 Web demo 文案和信息架构

验证标准：Web demo 中未来规划或相关展示区域采用开发者工具语气，信息层级清楚，避免营销化和炫技表达。

完成记录：

- 已完成。
- 在 `web_agent_demo/sample_cases.py` 增加场景元数据字段：`scenario_type`、`risk_tags`，并把 case 名称从裸技术 ID 改为专业场景名，例如“官方大规模候选调度”“雨天低接单意愿”“骑手稀缺商圈”。
- 修改 `ensure_sample_cases()` 为缺失时才生成 synthetic case，避免 `list_cases()` 或测试运行反复改写已存在的生成样例文件。
- 在 `web_agent_demo/server.py::list_cases()` 返回 `scenario_name`、`scenario_type`、`risk_tags`、`operator_note`、`source_type`，仍保留稳定 `id`，且不暴露本地路径。
- 将首页文案从偏展示化的 “Live Agent Workbench / 启动 Agent 求解 / 测试用例” 改为更专业的 “Developer Workbench / 运行调度分析 / 调度场景”。
- 新增“场景摘要”区域：运行前展示 case ID、数据来源、风险标签、候选行数和 operator note；运行后补充后端识别的 regime、任务数和骑手数。
- 新增 “Baseline vs AutoSolver” 结果对比区域：运行后展示最快稳定基线与最终 best-so-far 的覆盖、未覆盖数、骑手占用、候选组、耗时和接受策略数；不展示内部排序数值。
- 调整策略候选表：主视图显示可读策略名，同时保留 `strategy_id` 便于开发人员定位代码； rejected/reference 候选展示明确原因。
- 在 `autosolver_agent/system.py` 的 perception 事件中补充 `regime` 字段，使前端能在运行中即时更新场景画像。
- 更新 `tests/test_web_agent_demo.py`，覆盖新页面结构、case 元数据字段和无路径暴露约束；同时 mock `EvolutionManager`，避免测试写入 Evolution Memory。
- 验证：`python3 -m unittest tests.test_web_agent_demo` 通过 7 个测试。
- 验证：`python3 -m py_compile web_agent_demo/server.py web_agent_demo/sample_cases.py autosolver_agent/system.py tests/test_web_agent_demo.py` 通过。
- 验证：`rg -n "Proxy score|local_cost|40/40|本地分数|本地评分|官方成绩" web_agent_demo/server.py || true` 无输出。
- 验证：直接调用 `render_index()`，确认 `AutoSolver Agent Workbench`、`scenario-name`、`scenario-risk-tags`、`Baseline vs AutoSolver`、`result-comparison`、`运行调度分析` 均存在。
- 验证：直接调用 `list_cases()` 返回 10 个场景，首个 case 为 `large_seed301`，`scenario_name` 为“官方大规模候选调度”，`source_type` 为 `official_case`，且无 `path` 字段。
- 自信度检查：当前实现对 Task 4 的文案和信息架构目标有充分信心；剩余视觉克制化属于 Task 5。

## Task 5: 专业化 Web demo 视觉风格

验证标准：样式更克制、专业、适合开发人员使用；避免过度装饰、夸张渐变、强烈动效和示例图式花哨布局。

完成记录：

- 已完成。
- 在 `web_agent_demo/server.py` 中收敛视觉系统：将配色改为中性 slate/blue 控制台风格，使用白底卡片、细边框和轻阴影。
- 移除花哨背景：删除多层 radial gradient、装饰网格背景和强烈彩色氛围，仅保留低饱和度纵向背景。
- 移除玻璃拟态和强动效：删除 `backdrop-filter: blur(...)`、pulse keyframes、状态点外发光、阶段/loop 的位移 transform。
- 降低视觉夸张度：面板圆角从 26px 收敛到 14px，内部卡片多处收敛到 12px；按钮从强渐变和大阴影改为实色/描边按钮。
- 提高开发者可读性：降低首页标题尺寸，减少字距夸张；事件卡片从 `min-height: 156px` 收敛到 `112px`，timeline 高度从 `620px` 收敛到 `560px`，整体信息密度更接近工作台。
- 调整状态语义色：accepted/pass 使用绿色，rejected/fail 使用红色，running 使用蓝色，warning 使用琥珀色，避免装饰性颜色。
- 更新 `tests/test_web_agent_demo.py`：断言新中性背景、紧凑高度、无 `radial-gradient`、无 `backdrop-filter`、无 `@keyframes pulse`、无 `transform: translate`。
- 验证：`python3 -m unittest tests.test_web_agent_demo` 通过 7 个测试。
- 验证：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py` 通过。
- 验证：直接调用 `render_index()`，确认 Workbench、场景摘要、结果对比仍存在，且 `radial-gradient`、`backdrop-filter`、`@keyframes pulse`、`transform: translate` 均不存在。
- 验证：`git diff --check -- web_agent_demo/server.py tests/test_web_agent_demo.py goal/goal-1/tasks.md` 通过。
- 自信度检查：当前实现满足 Task 5 的克制、专业、开发者工具视觉目标；后续 Task 6 继续做 UI/文案一致性和响应式风险检查。

## Task 6: 第二轮全面检查-debug循环

验证标准：检查任务 4-5 的 UI/文案一致性、可访问性、响应式风险和代码风险；发现问题立即修复。

完成记录：

## Task 7: 运行测试和最终 review

验证标准：运行相关自动化测试或静态检查；从用户视角、代码质量、安全性、可维护性角度做最终审查。

完成记录：

## Goal 完成归档

完成状态：

归档记录：
