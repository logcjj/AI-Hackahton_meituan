# Tasks

## Task 1: 建立场景样本数据模型

验证标准：后端或前端具备 5-6 类场景、每类 10 个 deterministic samples；每个 sample 至少 3 个商家/订单点、多个骑手点、意愿/价格/距离/ETA/风险字段齐全。

完成记录：
- 已在 `web_agent_demo/server.py` 建立仿真数据模型：`list_simulated_scenarios()`、`build_simulated_scenario_sample()`、`build_simulated_scenario_samples()`。
- 已定义 6 类 To B 调度场景：商圈十字路口高峰、中型并行派单、骑手稀缺修复、雨天低接单意愿、低峰分散订单、活动混合压力。
- 每类场景支持 10 个 deterministic sample，总计 60 个样本；每个样本包含 3-6 个商家/订单点、7-15 个骑手点、候选派单、assignment 草案、意愿、成本、距离、ETA、风险和策略路径。
- 地图模型已包含 `baidu_like_simulated` 匿名导航图层元数据：道路层级、路况状态、建筑块、商圈热区，且 `hide_road_names=True`、`road_name_labels=[]`。
- 已新增只读 API：`/api/simulation-scenarios` 和 `/api/simulation-sample?scenario=...&sample=...`，供后续刷新按钮和地图渲染接入。
- 已补单测覆盖 60 个样本、5 条策略覆盖、地图匿名层级字段、assignment 字段完整性。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py web_agent_demo/delivery_routes_clone.py web_agent_demo/reasongraph_clone.py`。
- 验证通过：内联前端脚本 `node --check`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`，共 12 个测试通过。

## Task 2: 修复刷新按钮为“刷新当前场景样本”

验证标准：点击刷新后当前场景 sample index 变化，地图只显示商家/订单和骑手，不显示最终派单线；右侧回到等待推理状态。

完成记录：
- 已将刷新按钮改为 `refreshSimulationSample()`，在当前仿真场景内按 1-10 deterministic sample 切换，而不是重新加载旧 case 列表。
- 刷新后进入 `pending-run sample-preview` 状态，只渲染商家/订单点和骑手点，清空派单线、箭头、assignment 高亮和最终方案详情。
- 已接入 6 个场景按钮和场景下拉选择；场景切换后会加载该场景的第 1 个 sample，刷新继续切换同场景样本。
- 已修复无 assignment preview 状态下的地图聚焦逻辑，避免初始/刷新状态误把候选点标记为已派单或 active。
- 浏览器验证产物：`goal/goal-6/task2-refresh-audit.json` 和 `goal/goal-6/task2-refresh-preview.png`。
- 浏览器审计通过：刷新前 pins/routes/labels 均为 0；第一次刷新生成 5 个商家/订单点、14 个骑手点、0 条路线；第二次刷新切换到 #02，生成 5 个商家/订单点、12 个骑手点、0 条路线。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py web_agent_demo/delivery_routes_clone.py web_agent_demo/reasongraph_clone.py`。
- 验证通过：内联前端脚本 `node --check`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`，共 12 个测试通过。

## Task 3: 重做 To B 仿真地图底图与 preview 点位

验证标准：地图呈现接近百度地图/导航商圈图层的道路、街区、建筑块、路口热区和路况层级，但不显示真实路名；商家/订单与骑手沿道路分布，不再像随机横排或粗糙线条。

完成记录：
- 已将地图底图从硬编码静态 SVG 替换为 sample 驱动的匿名导航图层：`renderSimulatedBaseMap()` 根据 `sample.map_layers` 实时渲染片区、建筑块、主路/次路/支路、路况色带、商圈热区和路口信号点。
- 后端 `map_layers` 已扩展为接近参考图的深色导航层级：12 个匿名片区、24 个建筑块、28 条道路、8 条路况色带、3 个商圈热区、最多 10 个路口信号点；仍保持 `hide_road_names=True` 和空路名标签。
- 刷新样本新增可复盘随机 seed：默认仍保留每场景 10 个 deterministic sample 供测试，前端刷新会附带 seed 生成更丰富的随机点位和地图变化。
- 已调整点位生成逻辑：骑手吸附在道路中心线/道路边，商家点偏移到道路边/建筑边，不再压在道路中心；商家默认只显示黄色点，不显示订单数量标签，避免挡住地图。
- 已补预览态实体点击：未运行前点击商家显示订单期望、候选骑手和接单概率；点击骑手显示接单意愿、容量、可接候选商家和风险。
- 已修复刷新样本与运行推理脱节问题：当前有刷新样本时，`运行派单推理` 会基于当前样本的 `strategy_path`、`assignments`、`map_layers` 生成策略结果和派单线，不再切回旧 case。
- 浏览器验证产物：`goal/goal-6/task3-refresh-map.png`、`goal/goal-6/task3-run-map.png`、`goal/goal-6/task3-final-no-errors.png`、`goal/goal-6/task3-browser-audit.json`。
- 浏览器审计通过：刷新后 5 个商家点、11-13 个骑手点、24 个建筑块、28 条道路、8 条路况色带、0 条派单线、0 个商家文字标签；点击商家可显示候选骑手与概率；运行后生成 5 条派单线、5 个箭头、1 条 active route、4 个 rejected 策略，且无新增前端错误。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py web_agent_demo/delivery_routes_clone.py web_agent_demo/reasongraph_clone.py`。
- 验证通过：内联前端脚本 `node --check`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`，共 12 个测试通过。

## Task 4: 第一轮大型全面检查-debug循环

验证标准：语法、单测、JS 检查、浏览器截图通过；抽查至少 3 个场景的 2 个 sample，确认刷新状态无派单线、点位不拥挤。

完成记录：
- 已完成第一轮大型检查-debug循环，并按严格评审 Agent 反馈补修 P2 问题。
- 已强化场景语义：商圈高峰 `density_profile=clustered` 下订单点明显聚集；雨天低接单意愿场景带 `weather=rain`、76 条雨线和雨天文案，平均接单意愿低于普通场景。
- 已修复最终态派单线：运行后默认进入 `assignment-overview`，每个商家/订单点都有可见派单线和箭头连接到对应骑手，不需要点击后才显示。
- 已升级路线生成：`roadFollowingRoute()` 通过道路吸附、同路链路和道路间换乘点生成折线，派单线不再是简单直穿线。
- 已修复按钮真实性：`depots` 会弱化/恢复点位图层；`fullscreen` 会进入/退出地图聚焦布局；`all/selected/fit/zoom` 均有可审计状态变化。
- 已修复多订单详情：多订单商家会展开为独立订单 chip，详情和 toast 使用真实 `orderCount`，不再把 `2单` 当成一个订单。
- 严格 verifier 结论：无 P0/P1；指出的两个 P2 已修复并复测通过。
- 浏览器验证产物：`goal/goal-6/task4-browser-audit.json`、`goal/goal-6/task4-browser-audit.png`、`goal/goal-6/task4-commerce-final.png`、`goal/goal-6/task4-rain-final.png`、`goal/goal-6/task4-control-audit.json`、`goal/goal-6/task4-p2-fix-audit.json`、`goal/goal-6/task4-p2-fix.png`、`goal/goal-6/task4-multi-order-audit.json`。
- 浏览器审计通过：抽查商圈十字路口高峰、中型并行派单、雨天低接单意愿；每个场景刷新 2 次均为 0 条路线/0 个箭头，运行后路线数与商家点数一致，默认 `assignment-overview=true` 且 `focusSelected=false`。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py web_agent_demo/delivery_routes_clone.py web_agent_demo/reasongraph_clone.py`。
- 验证通过：内联前端脚本 `node --check`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`，共 12 个测试通过。

## Task 5: 构建推理运行状态机

验证标准：点击开始推理后进入 reasoning 状态，左侧策略节点按样本特征依次 evaluating/rejected/selected；运行完成前地图不显示最终派单线。

完成记录：
- 已新增前端推理状态机：`currentReasoningState`、`reasoningOrderForSample()`、`buildReasoningState()`、`setReasoningState()`、`clearReasoningState()`。
- 点击 `运行派单推理` 后页面进入 `pending-run sample-preview reasoning`，保留当前样本 preview 地图和 0 条最终派单线。
- 策略卡片新增 `data-reasoning-status` 和 `data-reasoning-order`，运行中按当前样本评分顺序依次展示 `Evaluating`，已评估策略保留为 `Rejected`，最终样本策略展示为 `Selected`。
- 已调整运行链路：最终策略被选中后先停留在 reasoning 阶段，此时仍无 `.dispatch-link` 和 `.dispatch-arrow`；随后才调用 `simulationFinalMap()`/`render(report)` 渲染最终派单线。
- 浏览器验证产物：`goal/goal-6/task5-reasoning-timeline.json`、`goal/goal-6/task5-final.png`、`goal/goal-6/task5-console-errors.json`。
- 浏览器时间线审计通过：雨天低接单意愿样本运行中采样 18 次，`maxRoutesDuringReasoning=0`，捕获到 `Evaluating`、`Rejected`、`Selected`，且 selected 出现时路线/箭头仍为 0；最终退出 reasoning 后渲染 4 条派单线覆盖 4 个商家点。
- 浏览器 console 审计通过：页面错误数为 0。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py web_agent_demo/delivery_routes_clone.py web_agent_demo/reasongraph_clone.py`。
- 验证通过：内联前端脚本 `node --check`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`，共 12 个测试通过。

## Task 6: 实现多策略场景覆盖

验证标准：5 条策略在 10 个样本集合中都能出现为 selected 或主要 evaluating；不同场景不会总是同一条策略胜出。

完成记录：

## Task 7: 第二轮大型全面检查-debug循环

验证标准：跑全场景策略审计、浏览器点击运行、截图，确认策略路径真实变化且无 JS/单测回归。

完成记录：

## Task 8: 实现最终派单线与地图联动

验证标准：推理完成后每个商家/订单点都有 1-2 条派单线连接到骑手；线沿道路感折线或清晰直线，不乱、不遮挡；当前选中高亮，其它低噪可见。

完成记录：

## Task 9: 完善骑手/订单/线路详情面板

验证标准：点击骑手、订单、商家、线路都会切换右侧详情，显示位置、订单期望、派单对象、接单概率、成本、ETA、风险和策略理由。

完成记录：

## Task 10: 第三轮大型全面检查-debug循环

验证标准：全按钮点击审计、DOM 状态审计、截图检查、语法/单测/JS 全通过；修复地图联动和详情面板回归问题。

完成记录：

## Task 11: 修复所有按钮的真实可用性

验证标准：刷新、运行、场景切换、图层、候选/最终、定位、适配、缩放、全屏、策略卡片、表格行都有明确状态变化或详情输出。

完成记录：

## Task 12: 最终严格评审与归档

验证标准：以严格评审 Agent 视角从 To B 视觉、业务逻辑、算法可信度、交互完整性、测试覆盖、演示稳定性审查；修完问题后标记 goal 完成并归档。

完成记录：
