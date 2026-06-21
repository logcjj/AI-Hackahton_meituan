# FOR_AutoSolver

美团 AI Hackathon 命题四 `AutoSolver` 提交版项目。目录包含正式比赛求解器、网页端 Agent 展示系统、复现测试和最终说明文档。

## 项目组成

| 部分 | 路径 | 说明 |
|---|---|---|
| 正式求解器 | `solver.py` | 官方评测热路径，保留 `solve(input_text: str) -> list`，无第三方运行时依赖。 |
| Agent 后端 | `autosolver_agent/` | 负责感知、规划、策略试跑、自动评估、自进化实验、回退和报告。 |
| Web 展示 | `web_agent_demo/` | 本地网页入口，通过 SSE 展示 Agent 求解过程。 |
| 样例数据 | `data/official_cases/`、`web_agent_demo/generated_cases/` | 复现和演示使用的样例输入。 |
| 测试与工具 | `tests/`、`tools/`、`_bench.py` | 单元测试、页面测试、打包脚本和基准检查。 |
| 文档 | `docs/` | 产品说明、项目文档、作品简介、架构图和截图证据。 |
| 官方记录 | `archive/runs/official_submit_20260520_132026_70222083.json` | 保留的官方提交记录。 |

更完整的目录说明见 [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)。

## 运行展示

```bash
cd /Users/比赛/FOR_AutoSolver_706.20_提交版
python3 web_agent_demo/server.py --host 127.0.0.1 --port 8765
```

浏览器打开：

```text
http://127.0.0.1:8765
```

页面中选择样例后点击 `启动 Agent 求解`，即可查看 Perception、Planner、Strategy Trials、Critic、Controller、Memory 和 Self-Evolving Code Loop 的实时事件。

## 验证命令

```bash
python3 -m py_compile solver.py autosolver/*.py autosolver_agent/*.py web_agent_demo/server.py tools/*.py _bench.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 _bench.py solver.py 1
```

生成交付包：

```bash
python3 tools/make_submission.py --output submission_final
```

## 文档入口

- [文档中心](docs/README.md)
- [产品说明文档](docs/deliverables/产品说明文档.md)
- [项目文档](docs/deliverables/项目文档.md)

正式成绩只引用官方提交记录；网页端本地评估值只用于解释 Agent 决策过程，不作为官方成绩。
