# Tasks

## Task 1: 视觉审计并修复核心路线问题

验证标准：运行完成后不再出现巨大青色斜线横穿地图；长距离骑手取餐段低噪显示；所有商家派单关系仍自动可见。

完成记录：
- 已对比参考图 `/Users/logcjj/Desktop/ae864de6-3c5c-4d85-9aae-2431a6d6737a.png` 和用户打回截图 `/var/folders/96/7y9tr62n4rzfg3flff0_pk780000gn/T/codex-clipboard-0cdd8a75-01fa-4ff6-9dc0-5e687430a152.png`，确认核心问题是默认高亮路线把长取餐/长配送段渲染成跨屏青色主线。
- 已修改 `renderDispatchLinks()`：总览态 `focusMode=false` 时不再给任何单条 assignment 加 `primary/active-assignment`，只有点击聚焦或选择“最终派单”时才高亮。
- 已新增 `routePolylineLength()`、`routeSpan()`、`longRouteClass()`，并给长距离取餐段和配送段添加 `long-pickup` / `long-delivery` 类，强制灰色虚线低噪展示。
- 已修改 `applyMapFocus()`：只有 `focused=true` 时才给 pin、label、route 添加 active 状态，避免运行完成默认总览出现刺眼主路线。
- 已补测试断言，防止恢复到旧的默认高亮逻辑。
- 浏览器真实点击通过：刷新后 5 个商家、14 个骑手、0 条路线；运行后显示 `00:00:10`，生成 12 条线路、5 条取餐段、7 条配送段，默认 `activeRoutes=0`、`primaryRoutes=0`、`longPickup=4`、`longDelivery=3`。
- 截图产物：`goal/goal-7/task1-final-map.png`。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py web_agent_demo/delivery_routes_clone.py web_agent_demo/reasongraph_clone.py`。
- 验证通过：内联脚本 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`。

## Task 2: 贴近参考图重做地图视觉层级

验证标准：中央地图在暗色道路、建筑片区、商圈点位、图例和路线层级上明显接近参考图，而不是普通抽象 SVG。

完成记录：
- 已把场景按钮区从两行大卡片压缩成单行 6 个紧凑场景按钮，地图高度从上一版约 440px 提升到约 509px，更接近参考图的中央地图占比，同时保留用户要求的场景选择功能。
- 已提高匿名导航底图的路网和建筑层级：增强 fine-street-mesh、道路 core/casing、建筑片区、路况色带和水域/街区块对比度，使地图不再像黑底上的几条粗线。
- 已强化总览态商家 → 骑手派单关系线：短取餐段用克制青色实线，长段仍由 `long-pickup` 灰色虚线覆盖降噪。
- 已新增 `selected-overview`：默认推荐 assignment 的短履约段显示为参考图式选中路线束，但不使用 `active-assignment/primary`，不会触发跨屏高亮；长取餐/长配送不会被选中高亮。
- 浏览器真实点击通过：刷新 → 运行派单推理耗时约 10.2 秒，显示 `00:00:10`；最终态生成 12 条线路、5 个商家、13 个骑手、7 个配送点，`activeRoutes=0`、`primaryRoutes=0`、`selectedOverview=3`、`selectedOverviewLong=0`。
- 截图产物：`goal/goal-7/task2-final-map.png`、`goal/goal-7/task2-selected-overview-map.png`。
- 严格视觉评审记录：`goal/goal-7/task2-visual-verdict.json`，当前分数 82/100，结论为核心错误已修复但仍需 Task 3 做全按钮回归和最终视觉复核。
- 验证通过：内联脚本 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`。

## Task 3: 浏览器严格功能与视觉回归检查

验证标准：刷新、运行、场景切换、图层、路线点击、实体点击均可用；浏览器截图和 DOM 审计证明视觉和逻辑都达标。

完成记录：
- 已使用 in-app browser 真实执行最终页面流程：刷新样本、运行派单推理、等待约 10 秒、验证最终派单地图。
- 已验证最终态：`runtime=00:00:10`，`routeCount=12`，`merchantPins=5`，`courierPins=14`，`orderPins=7`，`selectedOverview=3`，`selectedOverviewLong=0`，`activeRoutes=0`，`primaryRoutes=0`。
- 已验证 preview 态：切换到雨天低接单意愿后 `routeCount=0`，`rainStreaks=76`，`detailType=sample-preview`，不会残留上一次表格/路线详情状态。
- 已修复审计发现的状态清理问题：`resetDecisionPanelForSimulationPreview()` 和 `clearDispatchResult()` 会重置 `setDetailContext()`，避免右侧 detailType 残留。
- 已修复推荐路线束消失问题：新增 `overviewAssignmentIdForRoutes()`，总览态基于真实道路路径和 `longRouteClass()` 选择至少有短履约段的 assignment 做 `selected-overview`，不会高亮长取餐/长配送段。
- 已完成全按钮审计：场景切换、刷新、运行、图层 selected/all、点位弱化、配送线隐藏/恢复、定位、适配、放大、缩小、全屏、路线点击、策略卡点击、表格行点击均有可验证状态变化。
- 浏览器审计产物：`goal/goal-7/task3-browser-audit.json`，`violations=[]`，页面 console error 数为 0。
- 截图产物：`goal/goal-7/task3-final-map.png`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`。
- 验证通过：内联脚本 `node --check /tmp/autosolver-inline.js`。

## 大型全面检查-debug循环

验证标准：前三个 task 完成后，必须进行一次完整 debug 循环，包括单测、JS 语法、浏览器真实点击、截图/视觉评审；发现问题继续修复，直到没有 P0/P1/P2 问题。

完成记录：
- 已完成大型全面检查-debug循环。
- 视觉侧：最终截图 `goal/goal-7/task3-final-map.png` 相比用户打回截图已移除跨屏大青线，保留短推荐路线束，长路线低噪灰化，地图高度和底图层级更接近参考图。
- 功能侧：浏览器 18 步真实点击审计通过，`violations=[]`。
- 代码侧：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py web_agent_demo/delivery_routes_clone.py web_agent_demo/reasongraph_clone.py` 通过。
- JS 侧：提取内联脚本后 `node --check /tmp/autosolver-inline.js` 通过。
- 测试侧：`python3 -m unittest` 全仓 58 个测试通过。
- 剩余风险：当前仍是匿名模拟地图，不是接入真实地图瓦片；但符合“不显示真实路名/地址、模拟百度地图式层级”的约束。

## Task 4: 合并商家与配送点，只展示派单关系

验证标准：最终态地图不再显示独立配送点/订单端点，不显示绿色 O 或 D01/D02 类标签；每个商家点同时代表商家和订单点，运行完成后自动沿道路展示骑手到商家的派单关系线，并且点击商家、骑手、线路仍能打开中文业务详情。

完成记录：
- 已把官方回退地图和模拟最终地图统一为“商家 + 骑手”实体模型：`map_orders` 不再驱动地图实体，最终地图不再生成 `order` 点。
- 已把模拟样本商家 ID 从 `O****` 改为 `M****`，商家点自身代表该商家的全部订单；内部 `delivery_points` 仅保留一个与商家同坐标的逻辑点。
- 已删除商家到订单端点的线路渲染，`renderDispatchLinks()` 只生成 `courier-to-merchant` 派单线；`merchant-to-order`、`route-stop-label`、`long-delivery`、D01/D02 标签均已移除。
- 已把右侧详情、总览、图例、toast 和按钮文案改成“商家派给骑手”的派单关系，不再展示配送点/订单端点/配送链路。
- 已修复路线按钮：现在会隐藏/恢复全部派单关系线，而不是只处理旧配送端点线。
- 浏览器真实验证通过：刷新态 `merchantPins=5`、`courierPins=13`、`orderPins=0`、`routeCount=0`；最终态 `runtime=00:00:10`、`routeCount=5`、`pickupRoutes=5`、`merchantToOrderRoutes=0`、`stopLabels=0`、`orderPins=0`；路线按钮 `hide-dispatch-routes=true`；点击线路打开“线路详情：骑手到商家”。
- 截图与审计产物：`goal/goal-7/task4-final-map.png`、`goal/goal-7/task4-browser-audit.json`。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- 验证通过：内联脚本 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest` 全仓 58 个测试通过。

## Task 5: 移除地图临时 ETA 浮框，修正未推理置信度

验证标准：地图点击/聚焦后不再出现单独的骑手 ETA 浮框；ReasonGraph 初始和刷新后不显示写死置信度，只有推理中/完成后才逐步显示可信度、候选数量、通过数、最佳分和最终置信度。

完成记录：
- 已把 ReasonGraph 静态 HTML 中写死的 `1.00 / 0.96 / 0.89` 改为 `待输入 / --`，未运行前不再显示置信度。
- 已新增 `updateReasonMetrics()` 和 `setNodeMetric()`，刷新后只显示“已刷新”，推理中显示“计算中 / 生成中 / 校验中”，运行完成后才写入可信度、候选数、通过数、最佳分和最终置信度。
- 已关闭地图选中实体临时标签：`showSelectedLabel=false`，删除 `selectedLabelHtml`，不再出现截图里的单独骑手 `R0405 ETA 23 min` 浮框。
- 已补单测防回归：禁止初始写死置信度、禁止 `<small>ETA` 地图浮框模板、要求动态指标更新函数存在。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- 验证通过：内联脚本 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest` 全仓 58 个测试通过。
- 浏览器复核说明：本轮尝试连接 in-app browser 时被 Browser Use URL policy 阻断，未继续绕过；已用 render_index 结构检查和全量测试覆盖本轮逻辑。

## Task 6: 专业化地图与调度工作台视觉返工

验证标准：页面不再显得粗糙或拥挤；地图更像 To B 调度工作台的匿名导航底图，商家点、骑手点、派单线、候选线、图例、右侧详情都有清晰层级；运行前不展示结果，运行后自动展示每个商家派给骑手且不遮挡地图主体；所有按钮和点击交互继续可用。

完成记录：
- 已重启本地 `127.0.0.1:8765` 服务，确认 Chrome 初始页加载的是当前代码而不是旧进程；初始状态不再显示旧置信度、旧 ETA 浮框、旧仓库/配送点图例和最终派单线。
- 已降低匿名地图底图噪声：压低网格、建筑块、商圈热区、道路和路况色带的亮度与饱和度，减少发光感，使地图更接近 To B 调度后台。
- 已压低派单线视觉权重：总览态只展示真实 assignment 派单线，不再额外叠加路线束 overlay；聚焦态才显示参考路线束，避免运行完成后一堆重复线条显乱。
- 已把商家点改成更明确的 `M`，骑手点保留 `C`；图例改为“商家订单 / 骑手位置 / 派单关系 / 长距离低噪”，并移除“仓库、配送点、订单组、选中路线、候选路线”等不符合当前派单语义的旧文案。
- 已删除残留的 `route-bundle-label` / `routeBundleLabel` 逻辑，防止地图再出现“商家 Mxxxx / 派给 Rxxxx · ETA”类浮框。
- 已补测试断言：未推理阶段不出现 `可信度 --` / `置信度 --`，页面不出现仓库、配送点、订单组和 ETA 浮框，且总览 route bundle 只在 focusMode 下启用。
- 已完成接口级验证：雨天低接单意愿样本生成 `weather=rain`、76 条雨层、策略 `S5`；商圈高峰生成集中商家和策略 `S1`；骑手稀缺生成分散商家和策略 `S3`；所有商家订单点与商家同坐标，所有 assignment 都有 route。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- 验证通过：提取内联脚本后 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest` 全仓 58 个测试通过。
- 浏览器自动点击限制说明：in-app browser 控制接口持续引用旧 tab，Chrome 的 AppleScript 执行 JS 被安全设置禁用，Computer Use 坐标点击不稳定；本轮已用 Chrome 可视初始状态、后端接口、HTML/JS 结构和全量测试完成可验证覆盖。

## Task 7: 修复策略分数提前泄露与派单线贴路问题

验证标准：候选策略未被评估前不显示最终分数、证据或置信度；当前评估策略只显示计算中；已评估策略才逐步显示分数与状态。派单线主路径必须沿模拟道路走，骑手/商家到道路的短连接不能作为刺眼主路线穿过道路或楼宇。

完成记录：
- 已修复候选策略卡片分数提前泄露：初始、刷新、推理中未评估策略均只显示 `--`，当前评估策略显示 `-- 计算中`，不会提前显示最终分数、rank 或证据。
- 已调整最终态策略卡片：卡面只突出最终选中的策略分值与核心证据，未采用策略显示 `-- 未采用`，完整证据仍保留在点击策略卡后的右侧详情里，避免最终页面像调试评分面板。
- 已重构派单路线端点处理：`roadTerminalRoute()` 主路径只保留道路吸附点和道路图路径；骑手/商家到路边的短连接由 `endpoint-connector` 低透明虚线单独渲染，避免端点直线成为刺眼主路线。
- 已降低地图总览态路线噪声：所有商家派给骑手的关系仍自动渲染，但默认只突出推荐/短距离关系，其他派单线低噪展示，点击后仍可查看完整线路详情。
- 浏览器中途审计通过：推理约 3.6 秒时只有当前策略显示 `-- 计算中`，`revealed=[]`，`routeCount=0`，没有提前出现最终路线。
- 浏览器最终审计通过：`scoreCards=["S1"]`，未采用策略卡面无分值；`routeCount=6`、`selectedOverview=1`、`mutedOverview=11`、`endpointConnectors=4`、`activeRoutes=0`、`primaryRoutes=0`。
- 严格视觉评审反馈已纳入本轮二次修复：减少全量评分暴露和满屏青色派单线，最终截图更新为 `goal/goal-7/task7-final-browser-v2.png`，审计文件为 `goal/goal-7/task7-browser-audit-v2.json`。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- 验证通过：提取内联脚本后 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest` 全仓 58 个测试通过。

## Task 8: 复刻参考图地图底图层级

验证标准：中央地图不再像随机 SVG 线稿，而是接近参考模板的深色真实地图截片效果；底图有密集细路网、主路灰色层级、暗色建筑/区域纹理，业务点位和派单线叠加在其上仍可点击；不接入不稳定外部瓦片，默认使用本地生成的模板化地图底图。

完成记录：
- 已从用户提供的参考图 `/Users/logcjj/Desktop/ae864de6-3c5c-4d85-9aae-2431a6d6737a.png` 截取中央地图区域，生成本地深色匿名地图资产 `web_agent_demo/static/reference-dark-map.png`，不依赖外部瓦片和网络。
- 已新增 `/assets/reference-dark-map.png` 静态服务路由，并限制只允许访问这一张本地地图资产，避免开放任意静态文件读取。
- 已把地图容器底层切换为模板化地图截片：`.map-frame.topology::before` 加载本地地图背景，原 SVG 区域/道路层降为辅助透明层，不再是主视觉。
- 已把 `_DISPATCH_ROADS` 改成参考地图坐标系的道路骨架，包含模板里的选中环线、横向主干、斜向快速路和右侧候选走廊，让商家、骑手和派单线吸附到这张模板底图的道路上。
- 已补测试断言：页面必须引用 `/assets/reference-dark-map.png`，且本地地图资产必须存在。
- 浏览器验证通过：刷新样本后 `hasMapBefore=true`、`frameClass="map-frame topology"`、`mapStyle="baidu_like_simulated"`，说明本地模板底图已加载。
- 浏览器最终态验证通过：`runtime=00:00:10`、`routeCount=5`、`selectedOverview=1`、`pinCount=16`、`scoreCards=["S2"]`，最终截图为 `goal/goal-7/task8-template-road-final.png`，审计文件为 `goal/goal-7/task8-template-road-audit.json`。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- 验证通过：提取内联脚本后 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest` 全仓 58 个测试通过。
