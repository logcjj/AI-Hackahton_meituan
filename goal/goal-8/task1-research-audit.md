# Task 1 Research And Audit

## 结论

本轮不应继续守着现版本只调颜色。正确方向是把地图系统重构为：

1. `预设地图路网`：固定一张业务可解释的匿名城市配送路网，不再每次生成完全不同的底图。
2. `锚点池`：提前定义商家可出现点、骑手可出现点、商圈热点、路口、拥堵段、雨天影响区。
3. `场景采样`：10 个中文场景从锚点池中按场景特征抽样，刷新只改变合理位置组合，不破坏场景语义。
4. `道路路径`：派单线必须使用路网 shortest path / roadFollowingRoute，而不是自由折线。
5. `To B 视觉层`：深色地图、低噪道路纹理、黄色商家、蓝绿骑手、橙/红风险、清晰按钮状态、细线加中段箭头。

## 外部参考

### deck.gl TripsLayer

来源：https://deck.gl/docs/api-reference/geo-layers/trips-layer

可借鉴点：

- TripsLayer 的核心数据是 `waypoints`，每个点包含坐标和时间戳。
- `getPath` 返回路径坐标数组，`getTimestamps` 返回每个路径点的时间。
- `currentTime` 和 `trailLength` 控制动态轨迹和尾迹。
- `capRounded`、`jointRounded`、`widthMinPixels` 用于让轨迹更像专业交通可视化。

落地到当前项目：

- 不立即引入 WebGL 依赖；先把派单线数据结构升级为 `{assignment_id, courier_id, merchant_id, waypoints, timestamps, risk, selected}`。
- 推理中可以用 `currentTime` 思路做“线路逐段出现”，最终态保留完整派单线。
- SVG 线路应模拟 TripsLayer 视觉：圆角端点、圆角折点、淡入、风险色尾迹、低噪长段。

### deck.gl PathLayer

来源：https://deck.gl/docs/api-reference/layers/path-layer

可借鉴点：

- PathLayer 用点列表渲染 polyline，并支持 `pickable` 交互。
- 路径数据和 tooltip/点击详情是同一个数据对象驱动。
- 线宽可按数据属性变化，最小像素宽度防止缩放后看不清。

落地到当前项目：

- 当前 `.dispatch-link`、`.dispatch-arrow`、`.dispatch-hit-area` 应统一从同一个 route object 生成。
- 每条线必须带完整 `data-assignment`、`data-merchant`、`data-courier`、`data-route-source`，避免点击错对象。
- 长距离低噪线不能消失，只降权显示。

### deck.gl + Mapbox / MapLibre 叠层方式

来源：https://deck.gl/docs/developer-guide/base-maps/using-with-mapbox

可借鉴点：

- 地图底图和 deck.gl 业务图层是分层关系。
- interleaved 模式可把业务层放在地图标签之下或之上；overlaid 模式可独立控制业务层。
- 对当前项目而言，“底图”和“业务派单层”必须分离，不要把道路、图标、线路混成一层。

落地到当前项目：

- 保留 `tile-map` / `map-bg` / `route-svg` / `map-entities` 的分层，但数据来源要统一。
- 地图按钮应只改业务层状态，不破坏底图。
- 后续若接 deck.gl，可复用 route/anchor 数据结构，不需要重写业务采样。

### Kepler.gl 数据导入思路

来源：https://docs.kepler.gl/docs/user-guides/b-kepler-gl-workflow/a-add-data-to-the-map

可借鉴点：

- Kepler.gl 强调 WGS84/GeoJSON/CSV 数据格式，点、线、面均由结构化数据驱动。
- GeoJSON 支持 Point、LineString、Polygon 等几何类型，属性列可用于颜色和过滤。

落地到当前项目：

- 当前归一化 0-100 坐标可以继续用于匿名演示，但应向 GeoJSON 思路靠拢：`merchantAnchors` 是 Point，`dispatchRoads` 是 LineString，`districts` 是 Polygon/Rect，`routes` 是 LineString。
- 审计 JSON 可以输出 scene、anchors、routes，方便验证 10 个场景。

### 开源物流/车队项目参考

来源：https://github.com/Snowflake-Labs/sfguide-create-a-route-optimisation-and-vehicle-route-plan-simulator/blob/main/docs/ARCHITECTURE.md

可借鉴点：

- 该类 To B demo 通常抽象共享组件：Region Switcher、Vehicle Type Switcher、MapView、DataTable、MetricCard。
- 当前项目已经有 KPI、地图、表格和场景选择，但地图和数据表还没有形成统一的“调度工作台组件语义”。

落地到当前项目：

- 场景选择应更像 Region Switcher。
- 线路模式、刷新位置、天气/路况应更像地图控制栏。
- 表格应维持策略对比，不回到候选流水账。

### 开源 routing 参考

来源：https://github.com/valhalla/valhalla

可借鉴点：

- Valhalla 是基于 OpenStreetMap 的开源 routing engine，包含距离/时间矩阵、地图匹配、tour optimization 等能力。
- 当前项目不需要接完整 routing engine，但应学习“map matching / road graph / shortest path”的结构，而不是随意折线。

落地到当前项目：

- 当前已有 `buildRoadGraph()` 和 `shortestRoadGraphPath()`，但最终线没有使用它。
- 后续 Task 4 应强制最终总览 route 使用 `roadFollowingRoute()`，并为每条 route 输出 `route_source=road-graph`。

### 美团配送业务语境

来源：https://apps.apple.com/us/app/%E7%BE%8E%E5%9B%A2%E9%AA%91%E6%89%8B-%E7%BE%8E%E5%9B%A2%E9%AA%91%E6%89%8B%E9%80%81%E9%A4%90%E5%B7%A5%E5%85%B7/id1499806327

来源：https://www.meituan.com/news/NN250825125002496

可借鉴点：

- 美团骑手产品强调接收配送订单、管理订单、统计数据、GPS 定位、接单/履约引导。
- 美团公开解释订单分配时强调骑手位置、已有订单量、预计配送时间、对现有订单是否超时、骑手时间宽裕程度和顺路程度。

落地到当前项目：

- 右侧详情应继续强调“时间宽裕、顺路程度、无人接单风险、当前负载、预计配送时间”。
- 地图点位应体现商家在建筑/商圈边界，骑手在道路/路边，不要商家骑手都落在随意点。
- 美团语境颜色可以用黄色商家、蓝绿骑手、橙色风险，但整体不能变消费端花哨。

## 当前代码差距

### 场景数量不足

当前 `_SIMULATED_SCENARIO_CONFIGS` 只有 6 个场景：

- 商圈十字路口高峰
- 中型并行派单
- 骑手稀缺修复
- 雨天低接单意愿
- 低峰分散订单
- 活动混合压力

用户明确要求提前弄 10 个场景。因此 Task 3 必须扩展到 10 个，并保证每个场景的策略路径、天气、密度、骑手供给、位置分布不同。

### 位置没有显式锚点池

当前 `build_simulated_scenario_sample()` 通过角度、半径和 hash 随机生成商家/骑手，再 `_snap_to_dispatch_road()`。

问题：

- 商家“看起来”虽然偏离道路，但没有明确商家可出现点列表。
- 骑手“看起来”在道路附近，但没有明确骑手 road-side anchor。
- 刷新是 hash variant，不是从预设锚点池抽样。
- 无法向用户证明“所有位置都提前描定且合理”。

Task 2 应新增：

- `MERCHANT_ANCHORS`
- `COURIER_ANCHORS`
- `SCENE_ANCHOR_PROFILES`
- 每个 anchor 带 `road_id`、`side`、`zone`、`allowed_scenes`、`capacity`、`risk_modifier`。

### 最终派单线没有使用道路图算法

当前前端同时存在：

- `roadFollowingRoute(start, end, mapLayers)`：基于道路 snap、graph、shortest path 的道路路径。
- `stableDispatchRoute(start, end)`：最多 4 点的稳定折线。
- `renderDispatchLinks()`：最终总览中实际使用 `stableDispatchRoute(courierPoints[0], pickupPoint)`。

这解释了用户说“骑手到商家的线还是没画好，现在都没连上”。Task 4 应把最终派单线切换到 `roadFollowingRoute()`，只在道路图失败时 fallback 到 `stableDispatchRoute()`，并在审计里统计 fallback 数量。

### 地图按钮缺少“刷新地图/位置”的明确入口

当前只有 `刷新场景`，它实际会刷新 sample，但用户希望“刷新地图增加一个按钮”。后续应：

- 保留 `刷新场景` 用于重新生成该场景输入。
- 新增 `刷新位置` 或 `刷新地图`，只重抽当前场景锚点，不切换场景。
- 运行后点击刷新位置必须清空最终结果和派单线，回到输入态。

### 视觉资源仍偏程序化

当前地图使用 Carto raster tile + SVG 程序化道路/纹理，但商家/骑手还是文字 `M/C` 小圆点，线路是简单 SVG path。

Task 5 应升级：

- 商家图标：黄色圆角小店/餐袋符号，不只是 `M`。
- 骑手图标：蓝绿定位点/头盔/电动车抽象符号，不只是 `C`。
- 线路：主线、低噪线、选中线、风险线统一 token；箭头位于道路中段。
- 按钮：图标+tooltip+active 状态，不只单字“点/线/适/定”。
- 地图纹理：建筑区、商圈热区、雨天层、拥堵段更精致但不遮挡业务点线。

## 后续实现优先级

1. Task 2 先做锚点池，因为这是位置合理性的基础。
2. Task 3 扩展 10 场景，让刷新基于场景 anchor profile。
3. Task 4 再把线路切到 road graph，否则点位锚定后仍会出现不贴路。
4. Task 5 最后统一视觉资源，避免在错误数据结构上继续美化。

## Task 1 验收

- 已完成外部调研：deck.gl TripsLayer、PathLayer、deck.gl + Mapbox 叠层、Kepler.gl 数据格式、Snowflake Fleet demo、Valhalla routing、美团骑手/订单分配语境。
- 已完成当前代码审计：确认场景数量不足、缺少锚点池、最终线没有使用 road graph、刷新地图入口不明确、视觉资源仍偏程序化。
- 本任务不修改业务代码，后续实现从 Task 2 开始。
