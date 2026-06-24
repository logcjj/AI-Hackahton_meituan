# Goal 10 Tasks

## Task 1 - 策略展示与真实算法动态组合对齐

状态：已完成

验收：

- 页面不再把真实求解过程表达为固定 S1-S5。
- 可视策略分组对应真实算法族和动态补充阶段。
- 候选表最终选中方案使用真实最高策略分数，不再硬编码。
- 右侧指标标签根据对象语义变化。
- 展开全部按钮有实际展开效果。
- 相关单元测试更新并通过。

完成记录：

- 已将页面策略从旧的“合单/多派/修复/风险平衡”改成真实算法族分组：组合搜索/MCF、单任务多派、覆盖修复搜索、贪心基线/兜底、低意愿/自适应补充。
- 已补齐真实 Agent/solver 策略别名映射，包括 disjoint_gain、pair_matching、scarce_bundle_mcf、low_global_column、production_solver、evolution_replay 等。
- 已修复候选表最终行硬编码 0.89 的问题，最终 AutoSolver 分数来自当前样本 strategy_path 最高分。
- 已将右侧含混的“接单 / 覆盖概率”改成动态指标标签：商家覆盖率、接单概率、骑手接单意愿、策略评分。
- 已修复展开全部按钮状态，增加 aria-expanded，并确保展开后 br 和全文显示。
- 已更新 `tests/test_web_agent_demo.py` 相关断言，`python3 -m unittest tests.test_web_agent_demo` 通过。

## Task 2 - 大型全面检查/debug 循环

状态：已完成

验收：

- Python 编译通过。
- 前端内联 JS 语法检查通过。
- 单元测试通过。
- 至少一次浏览器级功能核查完成。
- 发现的问题已修复或明确记录。

完成记录：

- `python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py` 通过。
- 内联 JavaScript 抽取后 `node --check /tmp/autosolver-inline.js` 通过。
- `python3 -m unittest tests.test_web_agent_demo` 通过，13 个测试全部通过。
- `python3 -m unittest` 通过，59 个测试全部通过。
- 已用 Playwright 打开 `http://127.0.0.1:8769/`，执行刷新位置、运行派单推理、展开全部、点击策略详情。
- 浏览器程序化检查确认最终 AutoSolver 分数 `0.85 >= 0.85`，右侧指标为“策略评分”，展开按钮 `aria-expanded=true`，策略卡显示“组合/多派/修复/基线/自适应”。
- 验证截图已保存：`goal/goal-10/task2-browser-verified.png`。
