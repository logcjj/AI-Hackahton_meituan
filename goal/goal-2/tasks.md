# Goal 2 Tasks

## Task 1: 定位真正的未来计划来源

验证标准：列出所有候选未来计划来源，确认哪一份是用户反馈所指的权威版本。

完成记录：

- 候选来源 1：`goal/goal-1/input.md`。这是上一轮用户原始输入，明确说“参考这个未来计划，帮我完善一下里面提到的内容，注意风格不要按实例图片来，太花哨了，弄的专业一点，适合开发人员使用”。它证明用户要求的是“参考既有未来计划”，不是让我重写一个新方向。
- 候选来源 2：当前 `docs/deliverables/未来规划.md`。该文件已被上一轮改写成“面向开发人员和技术评审的调度分析工作台”路线图，因此不能作为判断用户反馈的唯一权威来源，否则会用上一轮结果反向定义目标。
- 候选来源 3：`git show HEAD~4:docs/deliverables/未来规划.md`，也就是上一轮改写前的 `docs/deliverables/未来规划.md`。该版本包含用户所说“未来计划”的具体内容：业务场景选择、即时履约调度指挥舱、城市网格/订单点/骑手点/派单连线、Baseline vs AutoSolver、任务级决策解释、业务 KPI、ROI 模拟器、三阶段推进路线和决赛演示脚本。
- 候选来源 4：`docs/deliverables/项目文档.md`、`docs/deliverables/项目总结.md`、`docs/deliverables/产品说明文档.md`。这些文件包含 Agent 阶段、后续动作和产品说明，但不是“未来规划”的直接来源，只能作为实现语境参考。
- 全仓搜索结论：除 goal 记录和当前/历史 `docs/deliverables/未来规划.md` 外，没有发现其他独立的 `future`、`roadmap`、`未来计划` 权威文件。
- 候选来源 5：用户在本轮直接提供的完整《AutoSolver 未来计划》，已完整保存到 `goal/goal-2/input.md`。它包含更明确的四个方向：ReasonGraph 推理过程可视化、真实物流路径规划界面、候选方案对比与淘汰机制、商业价值量化，并重申“不要按实例图片太花哨，专业一点，适合开发人员使用”。
- 候选来源 6：用户补充的参考图片 `/Users/logcjj/Desktop/ae864de6-3c5c-4d85-9aae-2431a6d6737a.png`。参考重点是顶部 KPI、左侧 AI Reasoning Graph、中间 Live Delivery Map、右侧 Decision Explanation、底部 Candidate Strategy Comparison；风格仍需降噪，不能照搬深色炫酷大屏。
- 候选来源 7：用户要求参考的两个 GitHub 仓库。已只读克隆到 `/tmp/autosolver_refs`：`https://github.com/ZongqianLi/ReasonGraph` 和 `https://github.com/aws-samples/delivery-routes-optimization-for-logistics`。ReasonGraph 无明显 LICENSE 文件，因此只参考公开 README 和结构概念；AWS 示例为 MIT-0，可参考其域模型和地图信息架构。
- 权威版本判定：用户最新直接提供的《AutoSolver 未来计划》优先级最高。本轮必须以 `goal/goal-2/input.md` 为准；`HEAD~4:docs/deliverables/未来规划.md` 只能作为历史背景，不能覆盖最新计划。
- 自信度检查：Task 1 已通过当前文件搜索、历史文件读取和候选来源排除完成；我对“真正的未来计划来源”判断有事实证据支撑。

## Task 2: 建立未来计划逐项对照表

验证标准：把未来计划里的每个明确条目映射到当前实现证据、缺口和修正动作。

完成记录：

- 文档修正：重写 `docs/deliverables/未来规划.md`，恢复并扩展用户最新计划的四大方向：AI 可解释调度决策平台、ReasonGraph 推理过程可视化、真实物流路径规划工作台、候选方案对比与淘汰机制、商业价值量化。
- 参考图落地：页面新增三问摘要、ReasonGraph 推理链、真实物流路径规划工作台、Decision Explanation、候选方案对比与淘汰机制、商业价值量化区域；信息架构对应用户图片的顶部 KPI、左图、中图、右解释、底表，但视觉风格保持浅色专业工作台。
- ReasonGraph 仓库参考：借鉴 sequential/tree reasoning flow、节点/边/分支、通过路径和失败路径状态；实现为本项目自己的六节点 ReasonGraph，不复制仓库代码。
- AWS 路线优化仓库参考：借鉴 warehouse/vehicle/order/delivery job/route segment、车辆访问链、MapLibre 路线层、真实道路距离/时间矩阵的界面和域模型；当前项目因缺少经纬度，先实现抽象路径工作台并明确为示意布局。
- 页面动态更新：`render()` 运行后调用 `renderReasonGraph()`、`renderRouteWorkbench()`、`renderCandidateComparison()`、`renderBusinessValue()`，把 report 和 attempts 映射到推理链、路线解释、候选淘汰和商业价值。
- 测试修正：`tests/test_web_agent_demo.py` 增加对 AI Explainable Dispatch Platform、三问摘要、ReasonGraph、路径规划、Decision Explanation、候选淘汰、五类候选方案、五类淘汰原因和商业价值估算的静态断言。
- 用户澄清后修正：ReasonGraph 不展示低价值的策略开始、结果、接受/拒绝事件，也不逐个长出策略分支。左侧只保留初始骨架、运行中“ReasonGraph 正在构建中”、运行完成后的最终推理树；中间地图初始只展示商家/骑手/订单，运行完成后再显示具体线路。

- 条目 1：总体方向。原文要求从“调度结果展示系统”升级为“AI 可解释调度决策平台”，让评委/业务方看到识别场景、生成候选、评估风险、淘汰低质量方案、最终选择路径。当前页面已有 Agent 事件流、场景摘要、策略候选表，但还偏技术日志，缺少统一的“可解释调度决策平台”信息架构。修正动作：文档重写为该定位；页面首屏和新增区域使用“AI 可解释调度决策平台”口径。
- 条目 2：ReasonGraph 推理过程可视化。原文六步是输入订单与骑手状态、场景识别与风险判断、候选策略生成、路线可行性校验、成本与接单风险评估、最终派单方案输出。当前页面只有阶段列表和事件流，没有候选路径级 ReasonGraph。修正动作：新增专业克制的推理链路面板，并用运行事件/最终 report 更新通过、高亮、灰化和淘汰原因。
- 条目 3：真实物流路径规划界面。原文要求地图层展示商家位置、订单配送点、骑手当前位置、合单路径、候选履约路线、最终选中派单路线，并与推理图联动。当前页面没有地图或路径层。修正动作：在不引入花哨地图和虚假经纬度的前提下，增加抽象物流路径工作台，用网格/节点/路线摘要表达商家、订单、骑手、候选路线、最终路线。
- 条目 4：三单合单示例解释。原文要求展示路线、预计送达时间、合单收益、接单概率、被淘汰替代方案原因。当前候选表只展示策略、原因、耗时、是否 best-so-far。修正动作：新增路线详情和决策解释卡，用本地可推导指标展示 ETA、bundle benefit、accept probability proxy、淘汰原因。
- 条目 5：候选方案对比与淘汰机制。原文要求展示贪心基线、合单优先、多派候选、局部修复、最终 AutoSolver 方案，并从覆盖率、无人接单风险、预计成本、骑手占用、预计送达时间、稳定性对比。当前有 Baseline vs AutoSolver 和策略候选表，但维度不足，且没有固定五类方案映射。修正动作：扩展候选方案对比表，加入五类业务方案、淘汰原因、风险/ETA/稳定性估算。
- 条目 6：淘汰原因。原文列出骑手接单意愿不足、路线绕行过长、占用骑手过多、合单收益不明显、无人接单风险偏高。当前仅有“未优于 best-so-far/无效”等技术原因。修正动作：将技术结果映射为业务淘汰原因，并在失败路径和候选表中展示。
- 条目 7：商业价值量化。原文要求算法指标转业务指标：无人接单减少、骑手利用率提升、履约成本下降、高峰期稳定性提升、人工干预减少，并给出日均 10 万单、每单 0.5-1 元、每日 5-10 万、单城市月度 150-300 万的估算口径。当前页面没有完整 ROI 量化。修正动作：增加商业价值量化区域，明确为演示口径估算，不伪装成官方成绩。
- 条目 8：最终回答三个问题。原文要求页面能回答“AI 是如何思考的？调度方案如何落地执行？这个方案能为业务节约多少钱？”。当前页面不能直接对应这三个问题。修正动作：新增三问摘要区，分别链接到推理链、路径工作台、商业价值量化。
- 风格约束：用户要求不要按示例图太花哨，专业一点，适合开发人员使用。修正动作：保留克制白底/灰蓝工程风格，不做霓虹、强动效、玻璃拟态或炫酷大屏。
- 自信度检查：Task 2 已覆盖用户最新未来计划中每个明确章节和列举条目；后续 Task 3 需要检查是否仍有遗漏或误读。

## Task 3: 第一轮全面检查-debug循环

验证标准：检查 Task 1-2 是否漏掉来源、误读条目或用当前实现反向定义目标；发现问题立即修复。

完成记录：

- 按用户补充要求调整页面结构：参考图的信息架构，但使用浅色专业开发者风格；上方保留运行/场景/KPI，中间改为左 ReasonGraph、中央实时物流路径、右决策解释，底部保留候选方案对比。
- ReasonGraph 行为修正：不再把 `attempt_start`、`attempt_result`、accepted/rejected 等底层策略事件显示为树的中间过程；运行前显示初始骨架，运行中仅显示“ReasonGraph 正在构建中”，运行完成后一次性渲染最终推理树。
- 地图行为修正：选择场景后只显示商家位置、骑手当前位置和订单配送点；运行中显示高层“调度决策正在构建”；运行完成后显示候选履约路线、合单路径和最终选中的派单路线。
- 中文化修正：左侧 ReasonGraph、中央路径、右侧决策解释均使用中文说明；保留必要技术 ID 在表格和事件流中，避免主视图变成日志重复。
- 验证：`python3 -m unittest tests.test_web_agent_demo` 通过；`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py` 通过；浏览器初始态确认包含初始骨架、无策略分支构建文案。

- 全量复读 `goal/goal-2/input.md`、`goal/goal-2/plan.md`、`goal/goal-2/tasks.md` 后检查，确认权威来源已更新为用户本轮直接提供的《AutoSolver 未来计划》，不是上一轮改写后的文档或历史版本。
- 关键词覆盖检查：`rg -n "ReasonGraph|真实物流路径|候选方案对比|商业价值量化|AI 可解释调度决策平台|AI 是如何思考|调度方案如何落地执行|业务节约" goal/goal-2 docs/deliverables/未来规划.md web_agent_demo/server.py tests/test_web_agent_demo.py -S` 当前只在 goal 文件命中，证明实现仍未完成，不能提前判定目标达成。
- 漏项检查：已覆盖总体方向、ReasonGraph 六步、路径规划六类地图元素、三单合单解释、五类候选方案、六个对比维度、五类淘汰原因、商业价值指标和最终三个问题。
- 风格检查：已保留用户约束“不要按实例图片太花哨，专业一点，适合开发人员使用”，后续页面实现必须使用克制工程风格，不能做炫酷大屏。
- 自信度检查：Task 3 发现的主要问题不是 Task 1-2 漏项，而是当前文档/页面还没有落地；下一步 Task 4 必须修正 `docs/deliverables/未来规划.md` 和 `web_agent_demo/server.py`/测试。

## Task 4: 按未来计划修正文档和页面

验证标准：修正后的内容能逐项对应未来计划，而不是只泛化成开发者工作台。

完成记录：

## Task 5: 验证和最终 review

验证标准：测试、语法检查、静态检查通过；最终逐项证明已参考未来计划并满足专业风格要求。

完成记录：

- 单元测试：`python3 -m unittest tests.test_web_agent_demo` 通过。
- 语法检查：`python3 -m py_compile web_agent_demo/server.py web_agent_demo/sample_cases.py autosolver_agent/system.py tests/test_web_agent_demo.py` 通过。
- 静态禁词/风格检查：`rg -n -- "Proxy score|local_cost|40/40|本地分数|本地评分|官方成绩|黑科技|降本增效神器|radial-gradient|backdrop-filter|@keyframes pulse|transform: translate|候选分支构建中|Planner 输出策略后|策略开始|接受或拒绝日志" web_agent_demo/server.py web_agent_demo/sample_cases.py docs/deliverables/未来规划.md || true` 无输出。
- 浏览器验证：当前页面已刷新到 `http://127.0.0.1:8765/`，初始态包含 ReasonGraph 初始骨架、实时物流路径工作台和右侧决策解释；没有候选分支构建和策略事件重复展示。
- 需求逐项证明：文档和页面覆盖用户给出的未来计划、参考图、ReasonGraph、AWS 路线优化项目、左中右布局、中文表达、地图初始/完成状态、商业价值量化和专业克制风格。
- 副作用检查：运行验证产生的 Evolution Memory/registry 差异已清理；`git status --short --branch` 只剩本轮文档、页面、测试和 `goal/goal-2/` 记录改动。

## Goal 完成归档

完成状态：

归档记录：
