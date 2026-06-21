# 项目目录结构

本文说明 `/Users/比赛/FOR_AutoSolver_706.20_提交版` 的最终复现目录，帮助评委快速定位正式求解器、网页 Agent、验证命令和文档资产。

## 核心提交线

| 路径 | 当前定位 | 备注 |
|---|---|---|
| `solver.py` | 正式比赛唯一提交文件 | 与网页展示解耦；所有官方热路径约束都集中在这里。 |
| `solution.py` | 兼容导出入口 | 主要用于兼容不同评测或导入方式。 |
| `example_solver.py` | 最小调用示例 | 可用于说明 `solve(input_text)` 的调用方式。 |

## Agent 展示线

| 路径 | 当前定位 | 备注 |
|---|---|---|
| `autosolver_agent/system.py` | 网页 Agent 后端控制器 | 负责 Perception、Planner、Trial、Critic、Controller、Memory、SSE 事件。 |
| `autosolver_agent/evolution.py` | Self-Evolving Code Loop 实验轨道 | 负责生成实验 strategy、安全门、试跑、回退、晋升和记忆写入。 |
| `autosolver_agent/evolution_state/` | 运行态 Evolution Memory | 网页 Agent 运行时自动创建；不作为正式提交热路径，也不需要预置历史策略文件。 |
| `web_agent_demo/server.py` | 前端页面和本地 HTTP 服务 | 浏览器入口，当前用于最终展示 AutoSolver Agent。 |
| `web_agent_demo/generated_cases/` | 网页演示测试样例 | 用于切换不同 case 展示动态 Agent 行为。 |
| `web_agent_demo/sample_cases.py` | 样例列表与加载逻辑 | 页面选择样例时使用。 |
| `data/official_cases/` | 脱敏样例数据 | 由原来的长中文目录收纳而来，供 bench、trace 和网页 large case 使用。 |

## 支持模块与验证工具

| 路径 | 当前定位 | 备注 |
|---|---|---|
| `autosolver/` | 算法模块与本地验证工具 | 用于解释算法结构和支撑测试；正式提交以 `solver.py` 为准。 |
| `tools/agent_trace_demo.py` | Trace 生成工具 | 用于生成 Agent 调用证据和技术审阅材料。 |
| `tools/render_lineage.py` | Trace 图渲染工具 | 将 trace JSON 渲染为 Graphviz DOT。 |
| `tools/make_submission.py` | 交付包生成工具 | 将核心文件复制到 `submission_final/` 并生成 manifest。 |
| `tests/` | 单元测试与展示系统测试 | 包含 `tests/agent_capabilities/`、`test_web_agent_demo.py`、`test_agent_evolution.py` 等。 |
| `_bench.py` | 本地基准脚本 | 用于快速检查 `solver.py` 在样例上的运行时间与输出。 |

## 交付与文档

| 路径 | 当前定位 | 备注 |
|---|---|---|
| `README.md` | 根目录快速入口 | 应保持简洁，只提供项目定位、启动、验证和文档导航。 |
| `docs/` | 当前权威文档中心 | 包含最终说明文档、架构图、运行截图和官方记录索引。 |
| `docs/deliverables/` | 交付文档区 | 包含产品说明文档、项目文档和作品简介。 |
| `submission_final/` | 按需生成的交付包副本 | 由 `tools/make_submission.py` 创建，不作为源代码编辑入口。 |
| `submission_final/MANIFEST.txt` | 交付包清单 | 生成后记录复制文件和验证摘要。 |

## 官方记录

| 路径 | 当前定位 | 备注 |
|---|---|---|
| `archive/runs/official_submit_20260520_132026_70222083.json` | 官方提交记录 | 文档中如需引用正式结果，只引用该官方记录，不引用本地页面分数。 |

## 运行态文件

以下内容由运行过程自动生成，不需要随最终源码预置：

- `autosolver_agent/evolution_state/generated_strategies/`
- `autosolver_agent/evolution_state/evolution_memory.jsonl`
- `autosolver_agent/evolution_state/strategy_registry.json`
- `__pycache__/`
- `*.pyc`

如果重新启动网页 Agent，上述 Evolution Memory 文件会按需重新创建。
