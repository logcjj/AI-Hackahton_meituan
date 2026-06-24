# Goal 10 Plan

## 需求

修复 AutoSolver 演示页中策略展示和真实算法不一致的问题，重点解决最终选中策略不是最高分、展开全部无效、右侧概率指标含义混乱、策略列表与真实算法不一致、以及页面看起来像固定跑 S1-S5 而非动态自适应求解的问题。

## 上下文

真实算法入口位于 `solver.py` 与 `autosolver_agent/system.py`。系统并不是只运行固定 S1-S5，而是根据场景 regime、覆盖率、历史最佳解和 fallback 动态组合多个求解器，包括 greedy baseline、single_task_multidispatch、disjoint/multidispatch、pair potential matching、sparse cover、low column search、scarce bundle MCF、production solver、evolution/trusted/generated strategies 等。

当前 `web_agent_demo/server.py` 已经部分改了策略名称，但前端 `strategyBranchCatalog`、候选表、右侧指标标签和测试仍保留旧的“合单优先/多派候选/局部修复/风险平衡/S1-S5”表达。

## 风险

1. 如果只改中文文案，用户会继续认为是形而上的假展示。
2. 如果最终 AutoSolver 评分仍硬编码，表格会出现“被选方案不是最好”的硬 bug。
3. 如果前端和后端策略映射不一致，点击策略、路线和右侧详情会错位。
4. 如果测试只检查旧字符串，无法防止策略展示再次退回固定 S1-S5。

## 执行方案

1. 对齐策略模型：把页面上的 5 个可视分组改成真实算法族/动态组合阶段，而不是伪装成固定求解器。
2. 修复候选表：最终 AutoSolver 行使用当前样本真实最高策略分数，不再硬编码 0.89，并保证选中项来源于动态策略路径。
3. 修复右侧指标：不同对象显示不同指标标签，例如商家覆盖率、接单概率、骑手接单意愿、策略评分，避免“53% 覆盖”语义错误。
4. 修复展开全部：让按钮真正展开 ReasonGraph 和策略说明，并通过测试覆盖。
5. 更新测试：用真实算法族名称、动态组合文案和分数一致性测试替代旧 S1-S5 文案测试。

## 验证方式

1. `python3 -m py_compile web_agent_demo/server.py tests/test_web_agent_demo.py`
2. 抽取内联 JavaScript 并执行 `node --check`
3. `python3 -m unittest tests.test_web_agent_demo`
4. `python3 -m unittest`
5. 如服务可启动，使用浏览器/Playwright 验证运行后最终方案分数不低于候选策略、展开全部可用、右侧指标标签随点击对象变化。

## 回滚方案

如改动引入页面不可运行或测试失败，优先回滚本 goal 中对策略展示、指标标签和候选表的局部改动，保留上一轮地图稳定性修复。
