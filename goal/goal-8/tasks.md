# Tasks

## Task 1: 外部调研与当前地图差距审计

验证标准：完成 deck.gl / GitHub / To B 地图参考调研；形成可落地的地图、线路、按钮、图标、锚点体系设计清单；不修改业务代码，只产出审计和设计依据。

完成记录：
- 已完成外部调研，覆盖 deck.gl TripsLayer、PathLayer、deck.gl + Mapbox 叠层、Kepler.gl 数据格式、Snowflake Fleet demo、Valhalla routing、美团骑手/订单分配语境。
- 已写入调研与差距审计文档：`goal/goal-8/task1-research-audit.md`。
- 已确认当前代码关键差距：只有 6 个场景、没有显式商家/骑手锚点池、最终总览线仍使用 `stableDispatchRoute()` 而不是 `roadFollowingRoute()`、缺少独立“刷新地图/刷新位置”入口、图标/按钮/线路纹理仍偏程序化。
- 已确定后续实现优先级：先锚点池，再 10 场景，再道路图线路，最后 To B 视觉资源。
- 本任务未修改业务代码。

## Task 2: 设计并接入地图锚点池

验证标准：代码中存在明确的商家锚点、骑手锚点、道路节点和场景锚点选择规则；刷新同一场景时点位变化但仍落在合理锚点/路边；商家不在道路中间，骑手在道路或路边。

完成记录：
- 已在 `web_agent_demo/server.py` 新增显式锚点体系：`_MERCHANT_ANCHOR_BLUEPRINTS`、`_COURIER_ANCHOR_BLUEPRINTS`、`_MERCHANT_ANCHORS`、`_COURIER_ANCHORS`、`_select_scene_anchors()`。
- 已把 `build_simulated_scenario_sample()` 从角度/半径自由散点改为按场景标签从预设锚点池抽样；同一场景不同 seed 会重抽锚点组合，但仍保留场景特征。
- 已给每个商家、配送入口和骑手写入 `anchor_id`、`anchor_zone`、`anchor_road_id`、`anchor_role`、`curb_distance`；`map_layers.anchor_pools` 记录本次选中的锚点。
- 已加入商家锚点安全距离后处理，防止商家点落在道路中线或交叉路中心；当前全局商家最小离路距离 `1.41`，骑手最大离路距离 `0.14`。
- 已生成审计文件：`goal/goal-8/task2-anchor-audit.json`，覆盖当前 6 个场景各 10 个样本，`violations=[]`。
- 已补回归测试：锚点池规模、商家/骑手 anchor 元数据、商家不在路中、骑手贴路、刷新 variant 改变锚点组合。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- 验证通过：提取内联脚本后 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`，13 个测试通过。
- 验证通过：`python3 -m unittest`，全仓 59 个测试通过。
- 验证通过：`python3 -m unittest`，全仓 59 个测试通过。

## Task 3: 扩展为 10 个场景并绑定场景特征

验证标准：前端场景选择提供 10 个中文场景；每个场景有不同天气、密度、骑手供给、价格/意愿/风险特征；刷新不显示样本编号/总数。

完成记录：
- 已在 `web_agent_demo/server.py` 将仿真场景从 6 个扩展为 10 个：新增夜间商圈宵夜、校园午高峰、医院写字楼午峰、拥堵异常补单。
- 已给新增场景绑定不同 `scene_type`、天气、密度、骑手供给、商家数量、意愿基线、交通压力和策略周期，避免所有场景走同一条推理链路。
- 已扩展商家/骑手锚点标签，使 10 个场景都能从预设锚点池中抽样，继续保持商家不在道路中线、骑手贴近道路/路边。
- 已强化 `tests/test_web_agent_demo.py`：精确断言 10 个中文场景、10 个唯一 case_id、100 个样本、天气/密度覆盖、每个场景至少 2 种策略分布、前端不显示样本总数/样本编号、场景按钮入口不存在。
- 已生成审计文件：`goal/goal-8/task3-scenario-audit.json`，`violations=[]`。
- 浏览器检查通过：当前代码在 `http://127.0.0.1:8766/` 动态加载 10 个中文场景，`.scene-button/.scene-strip` 数量为 0，没有 `10 samples`、`samples ·` 或当前样本文案。注意 `http://127.0.0.1:8765/` 当时有旧进程占用，仍显示旧版本，需要重启旧进程才能看到本任务改动。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- 验证通过：提取内联脚本后 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`，13 个测试通过。
- 验证通过：`python3 -m unittest`，全仓 59 个测试通过。

## 大型全面检查-debug循环 1

验证标准：前三个 task 完成后，必须运行单测、JS 语法、浏览器 10 场景刷新审计；发现位置不合理、按钮无效、结果提前显示或视觉明显差的问题必须修复。

完成记录：
- 已根据用户更新目标补充计划约束：`刷新骑手和商家位置` 与 `刷新地图` 是两码事，后续 Task 6 必须拆分按钮和语义。
- 已生成审计文件：`goal/goal-8/task3-debug-cycle-1-audit.json`。
- 静态验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- JS 语法验证通过：提取内联脚本后 `node --check /tmp/autosolver-inline.js`。
- 专项单测通过：`python3 -m unittest tests.test_web_agent_demo`，13 个测试通过。
- 全仓单测通过：`python3 -m unittest`，59 个测试通过。
- 浏览器初始态检查通过：当前代码临时服务 `http://127.0.0.1:8766/` 加载 10 个唯一中文场景，`.scene-button/.scene-strip` 数量为 0，没有 `10 samples`、`samples ·`、当前样本/样本编号文案，初始无点位、无派单线、详情为“等待运行派单推理”。
- 浏览器刷新检查通过：同一场景连续刷新后点位变化，仍保留当前场景，预览态只显示商家/骑手点位，不提前显示派单线、ReasonGraph selected/rejected 结果或样本编号。
- 浏览器 10 场景巡检通过：10 个场景逐个选择并刷新，商家数 4-6、骑手数 8-14，均进入预览态且没有样本文案泄露、没有提前派单线。
- 地图按钮基础功能检查通过：`点`、`线`、`适`、`定`、`↗`、`+`、`−` 均可点击并改变对应 DOM 状态或不产生 JS 错误。
- 完整 10 秒推理检查通过：运行后 `runtime=00:00:10`、完成率 `100%`、ReasonGraph 1 个 selected / 4 个 rejected、5 个商家生成 5 条派单线和 5 个箭头、详情为“派单总览：全部商家已自动连线”，页面日志无本地 JS error。
- 本轮没有发现 Task 1-3 范围内的 P0/P1/P2 问题；仍保留后续风险：Task 4 需要继续提升沿路派单线质量，Task 5 需要继续 To B 地图/图标/按钮视觉升级，Task 6 必须拆分“刷新位置”和“刷新地图”。

## Task 4: 替换地图路网基础并重构沿路派单线

验证标准：地图不能继续守着旧路网视觉，必须替换为更接近参考项目/美团配送语境的专业地图结构；固定使用运营分析浅色底图；道路/街道结构可见但道路名、地名、POI 文本不显示；刷新地图切换所在配送区域位置而不是切换风格；最终派单线默认全部显示，数量等于商家数；线路基于新道路节点连接，箭头位于道路段中部；没有明显跨楼宇/跨地图直线；点击线进入“派单关系”详情。

完成记录：
- 已替换为 MapLibre + OpenFreeMap 半真实地图层，固定使用 `https://tiles.openfreemap.org/styles/positron` 运营分析浅色底图；代码中不再包含 `bright` / `liberty` 风格切换。
- 已新增 4 个“运营分析浅色区域”配置；`刷新地图` 现在切换配送区域位置，不再切换地图风格，浏览器验证从区域 A 切到区域 B 后仍保持 `positron`。
- 已隐藏 MapLibre 全部文字图层；浏览器审计显示 `textLayers.total=19`、`visible=0`、`hidden=19`，道路名、地名和 POI 名称不显示，只保留道路/街区结构。
- 已把商家/骑手点位绑定到 MapLibre 渲染要素：商家来自 `maplibre-building-or-landuse`，骑手来自 `maplibre-road`；最终 `roadGraph=maplibre_rendered_road_graph`，本轮审计路网数量 `90`。
- 已修正商家锚点选择逻辑：商家落在建筑/用地内但靠近道路边界，不再选离道路最远的块中心；最终每个商家都有端点连接线。
- 已重构最终 SVG 派单线：从旧 `stableDispatchRoute()` 切换到 `roadFollowingRoute(courierPoints[0], pickupPoint, mapLayers)`，并删除旧 `stableDispatchRoute()` / `stable-local` 路线源。
- 已增强线路质量：增加 `densifyRoutePoints()` 分段插值、扩大端点连接覆盖距离、提高长距离低噪阈值；最终审计 `endpointConnectorTotal=5`、`longLegCount=0`、`minRoutePoints=3`。
- 已修复路线点击优先级：路线 SVG 交互层高于点位层，点击箭头进入“派单关系：骑手到商家”，不会被骑手/商家 pin 抢事件。
- 已保存浏览器审计与截图：`goal/goal-8/task4-final-region-map-audit.json`、`goal/goal-8/task4-final-region-map.png`、`goal/goal-8/task4-final-overview-map.png`、`goal/goal-8/task4-control-audit.json`、`goal/goal-8/task4-route-arrow-audit.json`。
- 浏览器验证通过：运行 10 秒后 UI 显示 `00:00:10`，5 个商家生成 5 条派单线和 5 个箭头，路线源全部为 `delivery-routes-road-graph-v3`，商家数、派单数、路线数一致。
- 浏览器控件验证通过：图层模式、点、线、适、定、全屏、放大、缩小、回中、点击商家、点击路线入口均可触发状态或详情变化。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- 验证通过：提取内联脚本后 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`，13 个测试通过。
- 验证通过：`python3 -m unittest`，全仓 59 个测试通过。

## Task 5: To B 地图纹理、图标、按钮和线路视觉升级

验证标准：地图底图、商家/骑手图标、线路纹理、箭头、工具按钮统一为专业 To B 风格；视觉参考调研清单但不直接复制外部版权图；截图中无明显廉价感、花哨感或遮挡。

完成记录：
- 已将地图工具栏从旧的单字按钮 `点/线/适/定/↗` 改为可读中文运营按钮：`点位`、`线路`、`适配`、`定位`、`全屏/退出`。
- 已把地图工具栏、地图头部按钮、缩放控件、图例和天气卡片统一为浅色 To B 浮层样式，降低旧版深色玻璃/霓虹感。
- 已把商家/骑手标记从 `M/C` 字母改为中文 `商/骑` 图标；商家使用美团语境黄色，骑手使用青绿色，尺寸从 14px 增强到 18px，降低地图上识别成本。
- 已把派单线从高饱和青色系改为更克制的绿色/青绿色线路调色板，箭头和聚焦线改成低饱和业务色；保留路线点击、端点连接和派单关系详情逻辑。
- 已修复地图头部控件换行问题，浏览器审计显示 `刷新位置`、`刷新地图`、`运行派单推理` 高度均为 30px，`headerWrapRisk=false`。
- 已补回归测试：工具按钮不能退回单字，图例/点位不能退回 `M/C`，路线调色板不能退回旧霓虹色。
- 已保存浏览器审计与截图：`goal/goal-8/task5-visual-audit.json`、`goal/goal-8/task5-visual-map.png`。
- 浏览器审计通过：`hasOldSingleCharTools=false`、`hasOldMCMarks=false`、`routeLinks=6`、`routeArrows=6`、`runtimeText=00:00:10`、MapLibre 文本图层继续 `visible=0`。
- 浏览器错误日志为空。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- 验证通过：提取内联脚本后 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`，13 个测试通过。
- 验证通过：`python3 -m unittest`，全仓 59 个测试通过。

## Task 6: 刷新地图/刷新位置交互完善

验证标准：页面提供清晰分离的“刷新位置”和“刷新地图”能力；刷新位置改变当前场景骑手/商家点位和候选关系，保留当前场景特征；刷新地图切换当前配送区域位置，固定使用运营分析浅色底图且不切换地图风格；运行后任一刷新会清空最终线和结果，回到输入态。

完成记录：
- 用户指出 Task 5 后整体样式仍然明显不合格，本轮先作为 Task 6 前置视觉回归缺陷处理，避免在错误视觉基础上继续做交互。
- 已用浏览器真实运行 10 秒推理并保存问题截图，确认旧版问题：地图只有约 658x412，右侧卡片和底部表格裁切，图例/工具条遮挡地图，商家/骑手点位集中，视觉不像专业 To B 工作台。
- 已重排工作台比例：压缩顶部 KPI、侧栏和浮层，地图主区域提升为约 724x398，底部策略表提升到 204px，1280x720 下 6 行策略结果全部完整显示。
- 已将图例、工具条、天气卡和 toast 改为低遮挡浅色运营浮层，降低地图遮盖和深色霓虹感。
- 已新增 MapLibre 渲染锚点的安全区与最小距离分散采样，商家不再集中贴边，骑手不再大量堆在一条中轴线上。
- 已将右侧派单解释压缩为摘要看板：订单 chip、决策依据和证据行按关键项展示，避免长文在固定高度内裁切。
- 已对长距离派单线做降噪处理，避免一条长斜线在总览态过度主导视觉。
- 已保存最终浏览器截图与审计：`goal/goal-8/task6-style-regression-final2.png`、`goal/goal-8/task6-style-regression-final2-audit.json`。
- 最终浏览器审计通过：运行时间 `00:00:10`，最终状态 `当前场景派单完成`，最终派单线 5 条，箭头 5 个，底部策略表 6 行全部在视口内。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- 验证通过：提取内联脚本后 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`，13 个测试通过。
- 用户追加指出骑手压到按钮、线路七扭八歪、拖拽/缩放/刷新地图仍不合理，本轮继续作为 Task 6 企业级阻断项修复。
- 已将页面外层改为固定 `1280x720` 企业看板并按实际视口等比缩放，避免窄窗口把中间地图压成 2px、按钮漂到左侧面板上。
- 已修复最终派单线：主线包含骑手端点和商家端点，不再只靠端点辅助线补断点；最终渲染前按当前可见商家重建派单覆盖，保证每个商家都有明确承接骑手。
- 已把派单补全限制在最终态，刷新地图/刷新位置后不再提前生成旧派单线，页面回到输入态。
- 已修复骑手聚集：最终态只显示实际承接派单的骑手，并增加 `enforceCourierSeparation()` 防碰撞兜底；区域 B 复测后骑手最小间距 `4.55`，无近距离碰撞。
- 已修复地图控件遮挡：商家/骑手锚点安全区排除图例、工具条、缩放按钮和天气卡；最终审计无点位压控件。
- 已修复真实地图交互：缩放驱动 MapLibre `easeTo`，拖拽支持 mouse/pointer/touch/drag fallback，空白地图区域拖动后中心从 `121.462,31.229` 变为 `121.494061,31.240006`。
- 已修复刷新地图语义：刷新地图切换配送区域/MapLibre center，并重新绑定新区域路网和点位；刷新后路线/箭头为 0，状态为等待推理。
- 已保存最终浏览器审计与截图：`goal/goal-8/task6-enterprise-map-audit-final.json`、`goal/goal-8/task6-enterprise-map-final.png`。
- 最终浏览器审计通过：区域 A `6/6` 商家连线、区域 B `6/6` 商家连线；刷新地图清空路线；端点距离均 `<0.2`；MapLibre 文字图层 `19/19` 隐藏；浏览器页面 error 日志为空。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- 验证通过：提取内联脚本后 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`，13 个测试通过。
- 验证通过：`python3 -m unittest`，全仓 59 个测试通过。

## 大型全面检查-debug循环 2

验证标准：Task 4-6 后进行浏览器全流程检查：10 个场景、刷新、运行 10 秒、按钮、点线表详情、截图；无 P0/P1/P2 问题。

完成记录：
- 已完成 Task 4-6 后的大型全面检查-debug 循环，使用当前代码在 `http://127.0.0.1:8772/` 做浏览器验收，避免旧端口进程干扰。
- 静态验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- JS 语法验证通过：提取内联脚本后 `node --check /tmp/autosolver-inline.js`。
- 全仓单测通过：`python3 -m unittest`，59 个测试通过。
- 10 场景浏览器巡检通过：10 个中文调度场景逐个选择、刷新位置、运行 10 秒；每个场景预览态无派单线，最终态均 `runtime=00:00:10` 且状态为 `当前场景派单完成`。
- 10 场景最终派单检查通过：每个场景均满足 `商家数 = 主派单线数 = 箭头数`，路线端点贴合骑手/商家，MapLibre 文字图层隐藏，表格行和 5 个策略卡均正常渲染。
- 10 场景点位检查通过：最终态无骑手堆叠、无图例/工具条/缩放按钮/天气卡遮挡；预览态只显示输入点位，不提前泄露最终派单线。
- 地图控件检查通过：放大、缩小、点位弱化、线路隐藏/恢复、图层模式 `全部/聚焦/增强`、适配、全屏、拖拽均可用并改变对应状态或地图视口。
- 详情交互检查通过：点击商家、骑手、派单线/箭头、策略卡、策略表行均能更新右侧详情，不是空点击或无效装饰。
- 刷新语义检查沿用 Task 6 最终审计：刷新地图切换配送区域并清空最终线；刷新位置重抽当前场景点位并清空最终线。
- 已保存审计文件和截图：`goal/goal-8/task6-debug-cycle-2-audit.json`、`goal/goal-8/task6-debug-cycle-2-final.png`。
- 浏览器页面 `error` 日志为空；没有发现 P0/P1/P2 问题，本轮无需修改业务代码。

## Task 7: MapLibre 地图交互与点线投影 P0 回归修复

验证标准：放大缩小必须真实驱动 MapLibre 连续 zoom，连续点击累计变化明显；鼠标按压拖动地图必须改变中心点；骑手、商家和派单线必须使用同一 MapLibre 投影重绘，拖拽/缩放后不浮在旧位置；可见骑手/商家不得压到图例、工具条、缩放按钮、天气卡；最终每个商家默认都有贴合骑手和商家的派单线，不能七扭八歪或端点断开。

完成记录：
- 已把地图覆盖层从“旧 0-100 固定屏幕坐标”改为“MapLibre 经纬度锚点 + 当前视口投影”：商家/骑手首次锚定时保存 `rendered_lnglat`，拖拽和缩放时用 `map.project()` 重新计算点位和派单线。
- 已启用 MapLibre 原生交互：`dragPan`、`scrollZoom`、`doubleClickZoom`、`touchZoomRotate` 开启；有 MapLibre 时不再绑定会 `preventDefault` 的旧拖拽兜底，`dragPan=native`。
- 已增加 `move` 实时同步和 `moveend` 终态同步；缩放/拖动时只重投影覆盖层，不再重抽点位，避免“第一秒和第二秒路径不同”。
- 已把图例、工具条、缩放按钮、天气卡的层级提升到点线之上，并新增安全区投影钳制，避免骑手/商家浮在按钮上。
- 已把最终派单重配限制为每个地图区域首次最终态执行一次；后续缩放/拖动不再反复换骑手。
- 已降低最终派单补全中的骑手负载惩罚，减少为了均衡负载而跨很远派给不合理骑手的长线。
- 已更新回归测试，防止退回旧缩放步长、旧拖拽拦截和无经纬度投影的覆盖层。
- 浏览器审计通过：运行 `00:00:10` 后 5 个商家、5 条主派单线、5 个箭头、5 个承接骑手；点位压控件 `overlaps=[]`；路线端点最大误差 `0.52`；MapLibre 文字图层 `19/19` 隐藏；连续缩放后 zoom 到 `14.20`；拖拽后中心变为 `121.467230,31.231236`；浏览器 error 日志为空。
- 已保存审计与截图：`goal/goal-8/task7-map-interaction-audit.json`、`goal/goal-8/task7-map-interaction-final.png`。
- 验证通过：`python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`。
- 验证通过：提取内联脚本后 `node --check /tmp/autosolver-inline.js`。
- 验证通过：`python3 -m unittest tests.test_web_agent_demo`，13 个测试通过。
- 验证通过：`python3 -m unittest`，全仓 59 个测试通过。

## Task 8: 完整业务语义与美团即时配送表达收敛

验证标准：所有文案、详情、图例、toast 和表格都围绕“商家派给骑手”而不是路线导航；商家、骑手、雨天、拥堵、合单、多派、无人接单风险等表达符合美团外卖/配送语境。

完成记录：

## Task 9: 最终验收、截图、审计与归档

验证标准：完成最终最大 review，从 UI、代码、测试、安全、业务逻辑、交互可用性角度审计；保存最终截图和审计 JSON；全量测试通过；goal 标记完成。

完成记录：
