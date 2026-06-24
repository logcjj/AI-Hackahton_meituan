# Task 17 完成前证据审计

## 审计范围

本审计基于 `goal/goal-9/input.md`、`goal/goal-9/plan.md`、当前 `main` 分支代码、已提交的 Playwright/Chrome 审计 JSON、截图证据和本轮命令输出。目标是验证 AutoSolver 演示页是否满足用户要求的企业级 To B 派单工作台标准，而不是只验证某一个单点 bug。

## 要求矩阵

| 要求 | 当前结论 | 证据 |
| --- | --- | --- |
| 地图放大后点击刷新位置不能继承异常 zoom，点位不能异常放大或挤成一团 | 已验证 | `task6-zoom-refresh-after-fix.json`、`task16-audit.json` 的 `after-zoom-refresh-position` 记录均显示 `zoomLevel=13.35`，且刷新后 `routeCount=0`、`arrowCount=0` |
| 运行必须保持约 10 秒推理过程 | 已验证 | `task10-enterprise-audit.json`、`task11-all-scenarios-audit.json`、`task16-audit.json` 均验证最终 `runtime=00:00:10` |
| 最终业务是派单，不是路线导航 | 已验证 | `web_agent_demo/server.py` 中路线详情文案明确“地图线表达骑手承接该商家，不作为骑行导航”；`task15-chrome-audit.json` 验证逐线详情为“派单关系：骑手到商家” |
| 最终线只能连接商家到最终承接骑手，不能连候选/备选骑手 | 已验证 | `task15-chrome-audit.json` 和 `task16-audit.json` 均显示 `duplicateCouriers=[]`、`mismatch=[]`，且 `finalCourier` 与 `courier` 一致 |
| 点击任意可见派单线必须打开该线对应商家和骑手的详情 | 已验证 | `task15-chrome-audit.json` 的逐线坐标点击 A0101-A0106 全部 `ok=true`；`task16-audit.json` 覆盖路线点击 |
| 点击商家/骑手不能被最近路线覆盖 | 已验证 | `task16-audit.json` 覆盖商家和骑手 pin 点击；`web_agent_demo/server.py` 使用 `preferEntityTarget` 保持实体点击优先级 |
| 天气卡片不能是黑块，必须是清晰浅色 To B 状态卡 | 已验证 | `task15-playwright-audit.json`、`task16-audit.json` 均显示 `oldWeatherRows=0`；截图 `task16-final.png` 显示浅色气象与路况卡 |
| 雨天/拥堵场景文案和地图状态要随场景变化 | 已验证 | `task16-audit.json` 的雨天低接单意愿场景包含“雨天 · 路面湿滑”和“ETA 上浮”；`task11-all-scenarios-audit.json` 覆盖 10 个场景天气/路况一致性 |
| 所有商家最终默认显示派给哪个骑手，不需要点一下才知道 | 已验证 | `task16-audit.json` final 阶段 `routeCount == merchantPins`；右侧详情包含“全部商家已自动连线” |
| 线路数量、商家数、骑手数、箭头数、ReasonGraph、底部表格口径一致 | 已验证 | `task10-enterprise-audit.json`、`task11-all-scenarios-audit.json` 和 `task16-audit.json` 均验证路线数、商家数、骑手数、箭头数和最终口径一致 |
| 候选策略、ReasonGraph、地图和右侧详情不能互相矛盾 | 已验证 | `syncReportMetricsFromAssignments()` 已将最终 assignments 回写到 report；`tests/test_web_agent_demo.py` 锁定该行为；`task10-enterprise-audit.json` 验证表格和 ReasonGraph 一致 |
| 收益量化不能只显示百分比，要有批次、每单、日/月估算 | 已验证 | `web_agent_demo/server.py` 包含“运营测算批次节约”“单城月节约测算”；`task6-final-chrome-audit.json` 验证批次节约、每单节约和单城月节约口径 |
| 地图、点位、线路、适配、定位、全屏、缩放、刷新位置、刷新地图按钮必须可用且状态一致 | 已验证 | `task14-button-audit-after.json` `failureCount=0`；`task16-audit.json` 再次覆盖线路/点位/适配/定位/全屏 |
| 场景切换后不能残留上一场景最终线、详情、天气或收益状态 | 已验证 | `task16-audit.json` 的 `after-scenario-switch` 记录显示 `routeCount=0`、`arrowCount=0`，且详情为“场景输入”而非“派单总览” |
| 页面不能卡顿，运行后缩放/刷新/点击仍可用 | 已验证 | `task7-enterprise-audit.json`、`task8-deep-audit.json`、`task16-audit.json` 覆盖运行后缩放、刷新、点击和按钮交互；无 failure |
| 页面要符合 To B 美团派单工作台观感，不是花哨炫酷 | 已验证 | `task13-final-overview-1280-after-fix.png`、`task15-playwright-final.png`、`task16-final.png` 展示克制的浅色地图、深色信息面板、中文派单语义、收益量化和表格；路线色彩已改为运营绿系 |
| 不能出现旧透明 hit area、旧天气 bar、路线 bundle 等误导层 | 已验证 | `tests/test_web_agent_demo.py` 禁止 `dispatch-hit-area` 和 `weather-bar`；`task16-audit.json` 显示 `hitAreas=0`、`oldWeatherRows=0` |
| 最新页面需有真实可访问服务供用户查看 | 已验证 | 本轮 `lsof -nP -iTCP:8765 -sTCP:LISTEN` 显示 `127.0.0.1:8765` 当前由 Python 服务监听 |

## 当前自动化证据摘要

- `task10-enterprise-audit.json`: `failureCount=0`。
- `task11-all-scenarios-audit.json`: `failureCount=0`，覆盖 10 个场景。
- `task13-audit-after-fix.json`: `failureCount=0`。
- `task14-button-audit-after.json`: `failureCount=0`。
- `task16-audit.json`: `failureCount=0`，覆盖 3 个场景的状态复位、按钮、路线点击、实体点击、天气和最终派单一致性。

## 残余风险

当前没有发现 P0/P1/P2 阻断问题。仍需承认的边界如下：

- 地图是半真实运营分析地图，不是生产百度/美团在线地图 SDK；这是当前演示约束内的实现选择。
- 金额是业务测算口径，不是生产财务结算口径；页面已用“运营测算”标注，避免误导。
- 浏览器外部扩展偶发 Statsig 网络告警来自 Codex/Chrome 扩展 telemetry，不是页面 console error；历史任务已记录该边界。

## 审计结论

按当前证据，用户在本 goal 中提出的地图、派单线、天气、收益量化、按钮、状态复位、性能和 To B 观感要求均有对应自动化或截图证据支撑。未发现需要继续修复的明确缺口。
