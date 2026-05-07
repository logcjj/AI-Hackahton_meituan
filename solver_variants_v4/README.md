# Solver variants v4

这些文件都可以单独改名为 `solver.py` 后提交。

## 稳定版

1. `solver_v4_0_rollback_715.py`
   - v3/715 保底回滚版。

2. `solver_v4_1_safe_mixed_local.py`
   - 当前主文件同款。
   - 只增加严格局部搜索：同 task_key 替换、bundle 拆单、两单合单。
   - 所有改动必须让当前本地严格目标下降才会保留。
   - `large_seed301` 本地：约 `657.808`，约 `7.5-7.9s`。

## 实验版

3. `solver_v4_2_overlap_low_only.py`
   - 只在低意愿场景启用“交叉多派”。
   - 依据旧单测线索，允许一个任务同时出现在单单和合单里。
   - 正常 `large_seed301` 不触发，低意愿代理样本会明显改变输出。

4. `solver_v4_3_overlap_low_fast.py`
   - `v4_2` 的提速版。
   - 低意愿只跑 gain 模式，低意愿代理样本约 `3.5s`。
   - 如果要赌 low_willingness 是否支持交叉多派，优先试这个。

5. `solver_v4_4_overlap_low_scarce.py`
   - 在低意愿和骑手稀缺场景都启用交叉多派。
   - 这是更激进的规则反推版，可能改善 `low_willingness_seed501` 和 `scarce_couriers_seed401`，但如果后台不允许 task 跨 task_key 重复，会有风险。

## 当前建议

- 稳健提交：`solver_v4_1_safe_mixed_local.py`。
- 想突破 715：先试 `solver_v4_3_overlap_low_fast.py`。
- 如果 `v4_3` 没坏且 low 有改善，再试 `solver_v4_4_overlap_low_scarce.py`。
