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

## 大型全面检查-debug循环 2

验证标准：Task 4-6 后进行浏览器全流程检查：10 个场景、刷新、运行 10 秒、按钮、点线表详情、截图；无 P0/P1/P2 问题。

完成记录：

## Task 7: 完整业务语义与美团即时配送表达收敛

验证标准：所有文案、详情、图例、toast 和表格都围绕“商家派给骑手”而不是路线导航；商家、骑手、雨天、拥堵、合单、多派、无人接单风险等表达符合美团外卖/配送语境。

完成记录：

## Task 8: 最终验收、截图、审计与归档

验证标准：完成最终最大 review，从 UI、代码、测试、安全、业务逻辑、交互可用性角度审计；保存最终截图和审计 JSON；全量测试通过；goal 标记完成。

完成记录：
