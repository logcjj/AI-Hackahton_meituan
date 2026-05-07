# v5 反推记录

## 从 V4 反馈修正的判断

- `V4_1 = 714.42`：只在 `small/tiny/scarce` 有很小提升，说明主线模型仍然可用，但已接近局部上限。
- `V4_4 = 727.50`：跨 `task_key` 交叉多派不是正解。平台更可能要求一个订单只被一个 `task_id_list` 覆盖，多派只发生在同一个 `task_id_list` 的骑手列表中。

## 新审题点

样例 `large_seed301` 只有 1 单和 2 单合单：

```text
T0037,T0039
T0012
```

但题面说的是“多个订单合并”，没有保证 hidden 只存在二单合单。因此旧代码里这些限制是危险的：

- `_solve_pair_potential_matching` 只看 `len(task_ids) == 2`
- 局部搜索里的 bundle split / single merge 只支持二单

如果 `low_willingness_seed501` 或 `scarce_couriers_seed401` 包含三单以上合单，旧代码会系统性忽略这些候选。

## v5 修正

当前主文件和 `solver_variants_v5/solver_v5_6_multi_bundle.py` 做了四件事：

- 合单候选搜索改成 `len(task_ids) >= 2`，不设二单上限。
- 合单拆成多个单任务的局部搜索支持任意长度合单。
- 多个单任务合并为一个 bundle 的局部搜索支持任意长度合单。
- 已有小合单组合合并为更大 bundle 的局部搜索支持任意长度合单，例如 `(A,B)+(C,D) -> (A,B,C,D)`。

这个修改不会影响只有二单的样例，但 hidden 有三单/多单时会多一条合法搜索路径。

## 本地验证

- `large_seed301`：本地约 `657.808`，与 V4_1 一致。
- 合成 5 单样例：能输出 `('T1,T2,T3,T4,T5', ['C6', 'C7'])`。
- 合成小合单转大合单样例：能输出 `('T1,T2,T3,T4', ['C3', 'C4'])`。
