# Tasks

## Task 1: 审计并修复最终派单线怪异问题

验证标准：最终派单线不再出现跨屏粗硬直线、误导性虚线或残留候选层；每个商家默认有清晰派单关系线连到承接骑手；端点贴合；运行后缩放/拖拽不卡顿。

完成记录：

## Task 2: 浏览器全流程验收地图交互和业务详情

验证标准：刷新位置、刷新地图、运行派单推理、缩放、拖拽、适配、定位、点位/线路开关、图层模式、全屏、点击商家/骑手/线路/策略均可用且业务解释合理。

完成记录：

## Task 3: 大型全面检查-debug循环 1

验证标准：前三个阶段前的修复完成后，运行全量测试、JS 语法、浏览器截图审计；若仍有 P0/P1/P2 视觉或交互问题，必须继续修。

完成记录：

## Task 4: 最终企业级验收与归档

验证标准：生成最终截图、审计 JSON 和验收说明；全量测试通过；goal 标记完成。

完成记录：

## Task 5: 修复 Chrome 实际页面派单线/详情不一致和天气卡片

验证标准：在用户 Google Chrome 页面实测，任意可见派单线点击后的右侧详情必须与该线的骑手和商家一致；最终答案没有派给某骑手时，不能有业务派单线连到该骑手；天气卡片不再是一坨黑，必须用浅色 To B 气象状态卡表达天气、拥堵和影响。

完成记录：
- 已在用户 Google Chrome 的 `http://127.0.0.1:8768/` 当前标签实测定位问题：旧逻辑允许骑手足够时仍复用同一骑手，导致 `R0103`、`R0110` 各出现两条最终派单线；透明 hit-area 还会抢点击，造成“点一条线但右侧详情停留在另一条线/总览”的错觉。
- 已修复最终派单重配：`reconcileDispatchPairsToVisibleMap()` 在骑手数不少于商家数时使用强唯一约束，默认一商家一骑手；只有骑手不足时才允许复用。
- 已修复派单线点击：透明 `.dispatch-hit-area` 不再参与 pointer events；可见 `.dispatch-link` 使用 `pointer-events: bounding-box`，每条线点击都能进入该线的“派单关系：骑手到商家”详情。
- 已重做天气卡片：移除旧 `.row/.bar` 继承，改为独立浅色 To B 气象状态卡，显示“气象与路况 / 天气 / 履约影响”，避免黑块和全局白字污染。
- 已补回归测试：防止回退到 `load * 4.5` 的骑手复用、旧天气 `.row/.bar` 查询、透明 hit-area 抢点击。
- Chrome 最终审计通过：`routeCount=5`、`arrowCount=5`、`merchantPins=5`、`courierPins=5`、`duplicateCouriers=[]`、`hitAreaPointer=none`、每条线 `pointerEvents=bounding-box`、`oldWeatherRows=0`、`errorLogs=0`。
- Chrome 逐线点击审计通过：A0101-A0105 每条派单线点击后均进入“派单关系：骑手到商家”，右侧详情均包含对应 `merchant` 和 `courier`，全部 `ok=true`。
- 已保存审计与截图：`goal/goal-9/task5-chrome-final-v3-audit.json`、`goal/goal-9/task5-chrome-final-v3.png`。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- 验证通过：提取内联脚本后 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`，13 个测试通过。
- 验证通过：`python3 -m unittest`，全仓 59 个测试通过。

## Task 6: 企业级验收循环 1：缩放后刷新位置、卡顿和收益量化

验证标准：在 Chrome 实测“放大地图后刷新位置”不会继承异常 zoom/点位比例；刷新后初始态无最终线且点位大小正常；后续运行推理、点击线/点、适配、缩放仍可用；新增收益量化模块能说明单次节约、每单节约、日/月估算，并与成本数据一致；无 console error 和明显卡顿。

完成记录：
- 已在用户 Google Chrome 当前 `http://127.0.0.1:8768/` 标签复现用户点名 bug：连续放大后点击 `刷新位置`，旧逻辑继承高 zoom，`frameZoomLevel=17.60`，商家/骑手聚集在局部放大地图上，后续运行后出现重复骑手 `R0109` 承接两条线。
- 已修复 `刷新位置` 视口继承问题：新增 `resetSemiRealMapViewportForScenario("refresh-position-reset")`，刷新位置前强制回到当前配送区域默认 center/zoom/pitch/bearing，再重新采样点位。
- 已强化最终重配唯一骑手约束：新增 `unusedCourierIds` 集合，在骑手数量不少于商家数量时只从未使用骑手中选择，避免仅靠惩罚分仍可能重复。
- 已新增收益量化展示：右侧“相对贪心基线”新增 `批次节约` 和 `单城月节约估算`；详情原因中显示每单节约、批次节约和按日均 10 万单估算的月节约。
- 已将收益估算改为保守业务口径：内部成本分先映射为每单约 `0.5-1.0 元` 履约损耗节约，再推导日/月节约，避免直接把成本分当人民币导致金额夸张。
- Chrome 最终复测通过：放大 5 次后点击 `刷新位置`，`frameZoomLevel=13.35`，刷新后 `routes=0`、`arrows=0`，点位分布宽高 `34.7 x 47.7`，不再挤成一小团。
- Chrome 最终运行复测通过：`runtime=00:00:10`、`routeCount=6`、`arrowCount=6`、`merchantPins=6`、`courierPins=6`、`duplicateCouriers=[]`、全部路线 `long=false` 且 `pointer=bounding-box`。
- 收益量化复测通过：右侧显示 `批次节约 ￥5.95`、`单城月节约估算 ￥2,974,133`，详情显示 `每单约节约 ￥0.99`，与当前批次和 10 万单/日口径一致。
- Chrome 页面错误日志为 0；浏览器控制层出现的 Statsig 网络告警来自 Codex/Chrome 扩展 telemetry，不是页面 console error。
- 已保存复现前证据：`goal/goal-9/task6-zoom-refresh-before-fix.json`、`goal/goal-9/task6-zoom-refresh-before-fix.png`。
- 已保存修复后证据：`goal/goal-9/task6-zoom-refresh-after-fix.json`、`goal/goal-9/task6-zoom-refresh-after-fix.png`、`goal/goal-9/task6-final-chrome-audit.json`、`goal/goal-9/task6-final-chrome.png`。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- 验证通过：提取内联脚本后 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`，13 个测试通过。
- 验证通过：`python3 -m unittest`，全仓 59 个测试通过。

## Task 7: 企业级验收循环 2：全按钮、响应式和详情一致性巡检

验证标准：继续在 Chrome 做宽/窄视口、多场景、多按钮巡检；验证刷新地图、刷新位置、点位、线路、图层模式、适配、定位、全屏、拖拽、缩放、点击路线/商家/骑手/策略/表格均与业务状态一致；右侧面板和底部表格在常见窗口宽度下不裁切关键内容。

完成记录：
- 已复现并修复 Task 7 初始巡检失败：A0201-A0203 路线点击会被其他路线包围盒或端点图标抢走，导致“点击某条黄线但右侧详情不是该商家/骑手”的错配。
- 已拆分路线层：`.dispatch-visual` 只负责显示最终派单线；`.dispatch-link.route-click-target` 是每条最终派单线唯一的透明中段点击锚点，携带同一条 assignment 的 `merchant/courier` 数据，避免 SVG 包围盒重叠抢点击。
- 已保留点位可用性：路线点击层只在中段命中，商家/骑手图标仍能打开各自详情；端点附近点击使用 7px 保护半径优先识别真实点位。
- 已重写路线详情文案：明确显示“最终派单 Mxxxx → Rxxxx”，并说明地图线只表达骑手承接商家，不作为骑行导航，避免把派单演示误解为路线规划。
- 已优化天气卡片：改为浅色 To B 状态卡，隔离全局样式污染，使用天气、拥堵、履约影响三段信息，不再显示黑块。
- 已补防回退测试：禁止 `pointer-events: bounding-box`，锁定 `dispatch-visual`、`routeClickMidpoint()`、`dispatchRouteClickTargetFor()`、7px 端点保护、最终派单路线文案和天气浅色样式。
- 浏览器聚焦复测通过：`routeCount=5`、`merchantPins=5`、`courierPins=5`、`duplicateCouriers=[]`，逐线点击全部 `isRoute=true` 且包含对应商家/骑手，商家点位点击全部可用，天气 `oldRows=0`。
- 完整 Task 7 多视口巡检通过：`failures=[]`；覆盖 `1280x720`、`1440x900`、`1024x720`，流程包含初始态、刷新位置、缩放后刷新位置、刷新地图、10 秒推理、图层模式、点位/线路开关、适配、定位、全屏、路线/商家/骑手/策略/表格点击。
- 已保存证据：`goal/goal-9/task7-enterprise-audit.json`、`goal/goal-9/task7-viewport-1280x720.png`、`goal/goal-9/task7-viewport-1440x900.png`、`goal/goal-9/task7-viewport-1024x720.png`、`goal/goal-9/task7-fix-probe.json`、`goal/goal-9/task7-fix-probe.png`。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- 验证通过：提取内联脚本后 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`，13 个测试通过。
- 验证通过：`python3 -m unittest`，全仓 59 个测试通过。

## Task 8: 企业级验收循环 3：视觉密度、拖拽性能和业务一致性复核

验证标准：以严格评审视角继续检查当前 UI 是否达到 To B 演示质量；覆盖真实拖拽、连续缩放、刷新位置、刷新地图、10 秒推理后性能、路线点击层、全屏/窄屏视觉、天气/收益/策略解释一致性；若截图或 JSON 证据显示视觉拥挤、按钮无效、数据错配、明显卡顿或业务表达不合理，必须继续修复。

完成记录：
- 已按严格评审反馈修正业务口径：顶部 KPI 改为 `商家覆盖率` / `未派商家`，避免把商家覆盖误写成订单统计。
- 已修正收益量化口径：使用 assignments 的订单数推导保守每单履约损耗节约，并显示 `运营测算批次节约` 与 `单城月节约测算`，避免直接把算法成本分解释成人民币。
- 已修复 `定位` 按钮：会基于当前选中商家和骑手中点执行 `map.easeTo({center: lngLat, ...})`，并标记 `locate-assignment-control`。
- 已修复右侧证据卡片复用问题：新增 `setEvidenceRows(items)`，不同详情类型使用不同中文标签和值，避免路线、商家、骑手和总览混用同一组证据文案。
- 已强化天气卡片点击与视觉隔离：天气层 `pointer-events: none`，不再挡住地图路线点击。
- 已强化骑手点位密度控制：最终重配增加近距离重叠惩罚，减少骑手挤到一起。
- 已修复路线层级：`.route-svg` 提升到 `z-index: 7`，可见路线和透明点击层分离。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- 验证通过：提取内联脚本后 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`，13 个测试通过。
- 验证通过：`python3 -m unittest`，全仓 59 个测试通过。
- 深度审计通过：`goal/goal-9/task8-deep-audit.json` 中 `failures=[]`，覆盖 3 个场景的拖拽、缩放、刷新、路线数量、点击层和天气/收益标签。
- 业务一致性复核通过：路线定位后点击可进入对应“派单关系：骑手到商家”，详情包含正确商家和骑手。

## Task 9: Chrome 实测修复最终派单线与天气卡片二次问题

验证标准：在用户 Chrome 当前页面复现并修复“最终答案没有派给某骑手，但地图有两根黄线连到该骑手”的问题；最终黄线只能表达商家到最终承接骑手，候选/备选骑手不能以最终派单线展示；点击任意黄线后右侧详情必须与该线商家和最终承接骑手一致；天气卡片改为清晰浅色 To B 状态条，不再出现黑块或一坨信息；补充自动化审计与单元测试。

完成记录：
- 已在 Chrome 当前 `http://127.0.0.1:8768/` 复现运行后重复骑手问题：同一场景曾出现 6 个商家中 2 条最终线连到 `R0103`，说明最终 payload 进入渲染前没有强制唯一重配。
- 已修复最终派单线源头：新增 `finalCourierTokensForAssignment()` / `finalCourierForAssignment()`，最终黄线、活跃骑手过滤、路线详情、定位按钮和收益统计都只使用最终承接骑手。
- 已修复后端预览/最终构图：`build_dispatch_assignment_map()` 不再把 `courier` 写成 `R1 + R2`，`map_couriers` 只包含最终骑手，其他候选保留为 `backup_couriers`，不进入最终黄线。
- 已修复最终 payload 渲染时机：`applyDispatchAssignmentMap()` 在 `simulation_final/final` 阶段先执行 `reconcileDispatchPairsToVisibleMap(profile)`，再渲染地图，确保骑手充足时默认一商家一骑手。
- 已修复路线点击误判：`.route-click-target` 优先进入路线详情，不再被 7px 端点保护改判成附近商家/骑手点位；真实点击 pin 仍打开点位详情。
- 已重做天气卡片为浅色 To B 状态条：两列显示天气/履约影响，底部动态显示调度建议；旧 `.row/.bar` 天气结构为 0。
- Chrome 最终审计通过：`runtime=00:00:10`、`routeCount=5`、`visualCount=5`、`arrowCount=5`、`merchantPins=5`、`courierPins=5`、`duplicateCouriers=[]`、`routeCourierMismatch=[]`、天气 `oldRows=0`、页面 error log 为 0。
- Chrome 逐线点击审计通过：5/5 条路线点击后标题均为 `派单关系：骑手到商家`，详情均包含该线的 `merchant` 和最终 `courier`，全部 `ok=true`。
- 已保存审计证据：`goal/goal-9/task9-final-chrome-audit.json`。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- 验证通过：提取内联脚本后 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`，13 个测试通过。
- 验证通过：`python3 -m unittest`，全仓 59 个测试通过。

## Task 10: 企业级验收循环 4：性能、响应式、按钮语义和业务一致性终检

验证标准：在最新提交基础上重新跑一轮不依赖旧证据的浏览器验收；覆盖桌面与窄屏视口、刷新位置、刷新地图、缩放、拖拽、运行 10 秒推理、线路/点位/定位/适配/全屏/图层模式按钮、路线/商家/骑手/策略/表格点击；运行完成后不能有重复骑手、错误黄线、JS error、明显卡顿、按钮状态与实际图层不一致、右侧详情和表格业务口径不一致、收益量化缺失或天气卡片遮挡/黑块。

完成记录：
- 初始 Task 10 审计发现真实业务一致性问题：地图最终重配后使用唯一骑手，但 ReasonGraph 最终节点和底部最终方案行仍沿用重配前的 `used_couriers`，导致截图中出现地图 5/6 个骑手、表格却显示 3/4 个骑手的矛盾。
- 已修复 report 指标同步：新增 `assignmentStatsForProfile(profile)` 与 `syncReportMetricsFromAssignments(report, profile)`，在 `simulation_final/final` 地图 payload 应用并完成 `reconcileDispatchPairsToVisibleMap(profile)` 后，把 `groups`、`used_couriers`、`covered_tasks`、`total_tasks`、`order_tasks` 和 `features` 回写为最终 assignments 的真实数据。
- 已补回归测试：锁定 `report.best.used_couriers = stats.courierCount`、`report.best.groups = stats.merchantCount`、`report.best.order_tasks = stats.orderCount`，防止地图、ReasonGraph 和表格再次口径分裂。
- 已用 Playwright CLI 重新跑企业审计，覆盖 `1280x720`、`1024x720` 和 `雨天低接单意愿` 场景；流程包含初始态、缩放后刷新位置、10 秒推理、逐线点击、线路/点位/图层/定位/适配/全屏、拖拽和雨天业务文案。
- 审计通过：`goal/goal-9/task10-enterprise-audit.json` 中 `failureCount=0`、`failures=[]`。
- 审计证明：三个最终场景的 `routeCount`、`courierPins`、最终表格 `finalStrategyRiders` 和 ReasonGraph `派出 N 个骑手` 完全一致；无重复最终骑手、无路线骑手错配、无可见点位泄漏到地图容器外。
- 已保存视觉证据：`goal/goal-9/task10-1280x720.png`、`goal/goal-9/task10-1024x720.png`、`goal/goal-9/task10-rain-scenario.png`。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- 验证通过：提取内联脚本后 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`，13 个测试通过。
- 验证通过：`python3 -m unittest`，全仓 59 个测试通过。

## Task 11: 企业级验收循环 5：全场景逐一运行一致性审计

验证标准：页面下拉中的全部调度场景逐个运行 10 秒推理；每个场景都必须满足最终路线数、商家数、骑手数、箭头数、最终表格骑手数、ReasonGraph 派出骑手数一致；无重复最终骑手、无路线骑手错配、无最终线提前出现、收益量化完整、天气/路况文案与场景一致、页面无横纵滚动溢出、运行后无 console error。

完成记录：
- 已完成全场景逐一运行审计：页面下拉 10 个场景全部执行完整 10 秒派单推理，`failureCount=0`、`scenarioCount=10`。
- 审计覆盖：最终路线数、可见路线数、商家点、骑手点、箭头数、底部最终方案骑手数、ReasonGraph “派出 N 个骑手”一致；无重复最终骑手、无路线骑手错配、无最终线提前出现、收益量化完整、天气/路况文案匹配场景。
- 已保存证据：`goal/goal-9/task11-all-scenarios-audit.json`、`goal/goal-9/task11-all-scenarios-final.png`。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- 验证通过：提取内联脚本后 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`，13 个测试通过。
- 验证通过：`python3 -m unittest`，全仓 59 个测试通过。

## Task 12: Chrome 实测修复重复黄线误导和天气卡片观感

验证标准：在用户 Google Chrome 当前页面实测，最终派单业务线只能有一条可见线对应一个商家到最终承接骑手；透明点击层和箭头不得被当成额外黄线或错误派单关系；点击任意可见线/箭头/商家/骑手时右侧详情必须与最终答案一致；天气卡片在正常和窄视口下都必须是清晰浅色 To B 状态条，不能出现黑块、堆叠或遮挡地图主信息；补充自动化验证。

完成记录：
- 已在用户 Chrome 当前页面读取运行后 DOM：业务点击层的最终骑手没有重复，但页面仍存在 `dispatch-visual + route-click-target + dispatch-hit-area + dispatch-arrow` 多层同业务数据，容易被看成一个骑手被多条黄线连接。
- 已移除冗余 `.dispatch-hit-area`：最终派单现在只生成一条可见业务线、一条中段点击目标和一个箭头；旧透明全路径命中层、样式、点击选择器和调试计数均清理。
- 已调整路线点击入口：地图点击只识别 `.map-label`、`.pin`、`.dispatch-link`、`.dispatch-arrow`，避免旧透明 hit-area 参与任何详情判断。
- 已优化天气卡片：移除拥挤的 `.weather-bar` 色条，改为更克制的浅色 To B 状态卡宽度、间距、阴影和行高，避免“黑块/一坨信息”的观感。
- 已补回归测试：禁止 `dispatch-hit-area`、`dispatchHitAreaFor`、旧 hit-area 点击选择器和 `weather-bar` 回到页面。
- Chrome 扩展在重启服务后拒绝执行 `127.0.0.1` reload，原因是浏览器 URL 策略拦截；未绕过该策略。已改用同端口实时服务 HTML 验证，证明手动刷新 Chrome 后会加载新页面。
- 服务级审计通过：`goal/goal-9/task12-service-html-audit.json` 中 `failureCount=0`，确认 `dispatch-hit-area_present=false`、`dispatchHitAreaFor_present=false`、`weather-bar_present=false`、`route-click-target_present=true`、天气卡存在且点击选择器已清理。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- 验证通过：提取内联脚本后 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`，13 个测试通过。
- 验证通过：`python3 -m unittest`，全仓 59 个测试通过。

## Task 13: 企业级验收循环 6：最新页面视觉、性能和交互复核

验证标准：在最新提交基础上重新打开页面，不依赖旧截图；覆盖 1280x720、1024x720、窄屏等视口，运行完整 10 秒推理，检查地图线、点位密度、天气卡片、右侧详情、收益量化、ReasonGraph、底部表格、刷新位置、刷新地图、缩放、拖拽、图层模式、线路/点位/定位/适配/全屏按钮。若发现视觉拥挤、按钮失效、卡顿、路线错配、天气遮挡或业务解释不合理，必须继续修复。

完成记录：
- 已用 Playwright CLI 重新打开 `http://127.0.0.1:8768/`，不复用旧截图；覆盖预览态、缩放后刷新位置、完整 10 秒推理、线路/点位/图层/适配/定位、路线点击详情、1024 视口和窄屏视口。
- 初始审计 `goal/goal-9/task13-audit.json` 中 `failureCount=0`，但人工目视 `goal/goal-9/task13-final-overview-1280.png` 发现总览态普通派单线偏细偏淡，容易和底图道路/虚线混淆。
- 已优化总览派单线：统一为美团运营绿系，不再使用蓝/黄等多色路线；总览普通线提升到 `stroke-width: 1.75`、`opacity: .72`，选中线提升到 `2.05`、`.84`，保持专业克制但更清楚。
- 已补回归测试：锁定绿色 route palette，禁止回退到旧蓝/黄多色路线，并锁定总览线条强度。
- 修复后审计通过：`goal/goal-9/task13-audit-after-fix.json` 中 `failureCount=0`，路线/视觉/箭头均为 6，商家/骑手均为 6，`hitAreas=0`，无重复骑手、无 route mismatch、收益量化完整。
- 响应式复测通过：`goal/goal-9/task13-responsive-audit-after-fix.json` 中 1024 与窄屏均无滚动溢出，路线/商家/骑手/箭头数量一致，天气卡片不拦截点击，旧 hit-area 为 0。
- 已保存视觉证据：`goal/goal-9/task13-final-overview-1280-after-fix.png`、`goal/goal-9/task13-final-1024-after-fix.png`。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- 验证通过：提取内联脚本后 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`，13 个测试通过。
- 验证通过：`python3 -m unittest`，全仓 59 个测试通过。

## Task 14: 企业级验收循环 7：地图控制按钮语义和状态一致性

验证标准：地图控制按钮必须符合业务语义；`线路` 和 `点位` 作为开关可以保持 active，`全屏` 作为模式开关可以保持 active 并切换文案；`适配`、`定位`、`刷新位置`、`刷新地图`、缩放等一次性动作不应留下误导性 active 状态。连续点击后，按钮状态、`map-frame.dataset`、实际图层显示和右侧详情必须一致，不得出现“按钮看起来关闭但地图仍处于定位态”或“适配按钮常亮”的问题。

完成记录：
- 已复现按钮状态问题并保存证据：`goal/goal-9/task14-button-audit-before.json`。复现结果显示 `定位` 第二次点击后按钮 `active=false` 但 `frame.dataset.locating=true`，`适配` 第一次点击后按钮会常亮，属于一次性动作和持久开关语义混用。
- 已修复地图控制语义：新增 `isPersistentMapAction()`，只有 `点位`、`线路`、`全屏` 会保留 active；`适配`、`定位`、缩放、回中心都作为一次性动作处理。
- 已修复定位态残留：新增 `clearLocatingStateSoon()`，`定位` 和回中心只短暂高亮路线，动画结束后自动清除 `.locating` 和 `dataset.locating=false`，按钮不再留下误导状态。
- 已强化 `resetMapControlState()`：统一清理 `locating/routesHidden/entitiesMuted` dataset，并清理 `fit/locate/zoom/recenter` 的临时 active 状态。
- 已补回归测试：锁定持久开关白名单、临时按钮清理函数、定位态自动清理，以及 reset 状态字段。
- 修复后按钮审计通过：`goal/goal-9/task14-button-audit-after.json` 中 `failureCount=0`；连续点击 `定位`、`适配`、缩放、回中心、线路、点位、全屏后，按钮 active 状态与 `map-frame.dataset` 全部一致。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- 验证通过：提取内联脚本后 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`，13 个测试通过。
- 验证通过：`python3 -m unittest`，全仓 59 个测试通过。

## Task 15: Chrome 实页复核重复连线和天气卡片

验证标准：在用户 Google Chrome 当前页面复现并修复“一个骑手被两条最终黄线连接，但最终答案没有派给该骑手”的口径错误；最终地图只显示商家到最终承接骑手的派单线，候选/备选骑手不得作为最终线展示；点击任意线、箭头、骑手、商家后的右侧详情必须与最终答案一致；天气模块必须改为清晰、浅色、To B 状态卡，不能再出现黑底或一坨信息；修复后必须保存 Chrome 实测截图/JSON，跑 JS、Python 和单元测试，并提交代码。

完成记录：
- 已在用户 Google Chrome 当前标签发现实际打开的是 `http://127.0.0.1:8765/` 的旧残留页面，不是当前 `8768` 服务；旧页面复现了 `M0101 → R0113` 与 `M0102 → R0113` 两条最终黄线连到同一骑手，右侧总览显示 4 个骑手，天气卡片仍为黑色旧结构且存在 `.row/.bar`。
- 已在 `8765` 和 `8768` 均启动当前代码服务，刷新 Chrome 后确认页面标题为“美团即时配送派单决策工作台”，天气旧结构数为 0。
- 最新 Chrome 运行 10 秒推理后数据审计通过：`routeCount=6`、`linkCount=6`、`arrowCount=6`、`merchantPins=6`、`courierPins=6`、`dupCouriers=[]`、`routeCourierMismatch=[]`、`hitAreas=0`、`oldWeatherRows=0`。
- 已发现并修复新交互 bug：MapLibre canvas 会盖住 SVG 派单线，用户点击可见黄线时可能命中 canvas 或下方表格，导致右侧详情停在策略详情/总览，造成“线和最终答案不一致”的观感。
- 已新增 `distanceToRouteAtClientPoint()` 与 `dispatchRouteAtClientPoint()`，地图点击时会根据点击坐标识别最近的最终派单线；即使事件目标是 MapLibre canvas，也能打开该线对应的“派单关系：骑手到商家”详情。
- 已补实体点击优先级：真实点击商家/骑手 pin 或 label 时不走最近路线覆盖，避免端点附近点击被误判成派单线，保证商家、骑手和线路三类交互都可用。
- Chrome 逐线坐标点击复测通过：A0101-A0106 每条线均进入“派单关系：骑手到商家”，详情均包含对应 `merchant` 与最终 `courier`，全部 `ok=true`。
- Playwright 独立验收通过：`routeCount=6`、`linkCount=6`、`arrowCount=6`、`merchantPins=6`、`courierPins=6`、`duplicateCouriers=[]`、`mismatch=[]`、`hitAreas=0`、`oldWeatherRows=0`。
- 已保存证据：`goal/goal-9/task15-chrome-audit.json`、`goal/goal-9/task15-playwright-audit.json`、`goal/goal-9/task15-playwright-final.png`。Chrome 扩展截图接口一度断开，已用 Playwright 截图补足可视证据。
- 已补回归测试：锁定 `dispatchRouteAtClientPoint(event, threshold = 14)`、最近最终派单线识别、`.dispatch-visual.pickup-leg` 检索和 `routeByPoint || domTarget` 点击入口，防止 MapLibre canvas 再次抢线点击。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- 验证通过：提取内联脚本后 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`，13 个测试通过。
- 验证通过：`python3 -m unittest`，全仓 59 个测试通过。
