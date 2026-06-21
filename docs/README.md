# AutoSolver 文档中心

本目录是当前项目的文档入口，用于评委复现、技术审阅和答辩展示。

## 当前权威入口

| 文档 | 用途 |
|---|---|
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | 说明当前目录结构，区分正式求解器、Agent 展示、测试工具和文档资产。 |
| [ARCHIVE_INDEX.md](ARCHIVE_INDEX.md) | 说明保留的官方提交记录及其引用边界。 |
| [deliverables/产品说明文档.md](deliverables/产品说明文档.md) | 面向评委，说明产品定位、Agent 能力和展示方式。 |
| [deliverables/项目文档.md](deliverables/项目文档.md) | 面向技术审阅，解释架构、Agent 闭环、验证方式和交付边界。 |
| [deliverables/作品简介.md](deliverables/作品简介.md) | 用于报名页、展示页或答辩开场的作品简介。 |

## 当前项目口径

AutoSolver 当前包含两条线：

| 线 | 位置 | 定位 |
|---|---|---|
| 正式比赛求解器 | `solver.py` | 唯一官方提交热路径，必须满足单文件、无第三方依赖、10 秒内返回。 |
| 网页端 Agent 系统 | `autosolver_agent/` + `web_agent_demo/` | 用于最终展示和答辩，呈现 Perception、Planner、Strategy Trials、Critic、Self-Evolving Code Loop、Memory、Rollback 的动态闭环。 |

重要边界：

- 网页 Agent 可以生成实验 Python strategy、执行 Safety Gate、Sandbox、Rollback 和 Memory 记录。
- 正式比赛 `solver.py` 不在运行期读取 Evolution Memory，也不动态加载生成策略。
- 本地 Critic cost 只用于候选相对筛选和展示解释，不等同于官方成绩。
- 官方分数如需引用，必须指向 `archive/runs/official_submit_20260520_132026_70222083.json` 等官方提交记录，不使用页面展示值替代。

## 常用命令

启动网页 Agent 展示：

```bash
cd /Users/比赛/FOR_AutoSolver_706.20_提交版
python3 web_agent_demo/server.py --host 127.0.0.1 --port 8765
```

基础验证：

```bash
python3 -m py_compile autosolver_agent/*.py web_agent_demo/server.py tools/make_submission.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 _bench.py solver.py 1
```

生成交付包：

```bash
python3 tools/make_submission.py --output submission_final
```

## 交付边界

- 正式求解入口是 `solver.py`。
- 网页展示入口是 `web_agent_demo/server.py`。
- 自进化运行态文件由网页 Agent 运行时自动生成，不作为正式评测热路径。
- 官方结果只引用 `archive/runs/official_submit_20260520_132026_70222083.json`。
