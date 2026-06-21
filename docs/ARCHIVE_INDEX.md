# 官方记录索引

最终复现目录只保留一份官方提交记录，用于证明正式结果来源。评审材料中的正式结果统一从该记录引用。

## 保留文件

| 文件 | 用途 |
|---|---|
| `archive/runs/official_submit_20260520_132026_70222083.json` | 官方提交记录。产品说明和项目文档如需引用正式结果，只引用该文件。 |

## 引用规则

- 对外说明 Agent 系统时，引用 `autosolver_agent/`、`web_agent_demo/`、`tests/test_agent_evolution.py`、`tests/test_web_agent_demo.py` 和页面截图。
- 对外说明正式求解器时，引用 `solver.py`、`_bench.py`、测试命令和官方提交 JSON。
- 本地 Critic cost、覆盖率、trace cost 和网页运行结果只用于解释 Agent 决策，不作为官方成绩。
- 生成交付包时由 `tools/make_submission.py` 复制该官方记录并写入 manifest。
