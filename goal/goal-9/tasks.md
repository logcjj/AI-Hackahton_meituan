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
