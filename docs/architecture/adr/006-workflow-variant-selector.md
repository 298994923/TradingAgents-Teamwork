# 006-workflow-variant-selector.md

**ADR-006 · main 候选 · 待采纳，不授权修改源代码**

目标基线：`main@ab30058506b62fc14d403395b7cbb36122c0d343`。本候选承接 C-v1-workflow-variant-adr-addendum.md（v0.1）。D-to-C-integration-governance-replies.md 批准了原决策文本，并指定 ADR-006；本次只更新交付目标与验收边界。C-v1-fixed-pruning-plan-v0.2.md 中的 `ADR-001` 是历史草案定位，不回改原记录。目标提交仅有 `005-deterministic-guard.md`，本 ADR 尚未采纳。

## 决策

固定剪枝实验在同一提交、其余设置相同的条件下对比两组与一组 Bull/Bear，不改变全局默认值。`TradingAgentsGraph` 增加仅关键字参数 `workflow_variant: str | None = None`。基础配置仍按 `config or DEFAULT_CONFIG` 选择：非空调用方配置优先；省略或空配置使用 `DEFAULT_CONFIG`；不增加配置合并逻辑。

| 选择 | 生效的研究辩论深度 | 配置与行为 |
| --- | --- | --- |
| 省略或 `None` | 沿用配置；内置默认一组 | 保留旧路径、运行设置的键结构及原检查点签名。 |
| `workflow_variant="v0"` | 两组，每组一对 Bull/Bear | 浅复制基础配置，只覆盖 `max_debate_rounds`。 |
| `workflow_variant="v1"` | 一组，一对 Bull/Bear | 同上，只覆盖 `max_debate_rounds`。 |

显式预设优先于配置中的研究深度，不修改调用方配置、`DEFAULT_CONFIG` 或 `max_risk_discuss_rounds`。沿用既有路由、Aggressive → Conservative → Neutral 三角色风险流程及 Portfolio Manager。`"v2"` 以 `ValueError` 拒绝为尚不可用，其余非法值（包括 `"v3"`、`"V1"`、空字符串和整数）以 `ValueError` 拒绝为无效选择器。校验先于全局 `set_config`、目录及产物创建、客户端构造和模型调用。

- `run_settings()` 提供生效的 `max_debate_rounds` 和 `max_risk_discuss_rounds`，只有显式预设增加 `workflow_variant`。现有 `full_states_log_<trade_date>.json` 在 `run_settings` 下保存同样的值。报告沿用现有入口。
- `_run_signature()` 使用生效配置。省略或 `None` 保留原签名；显式预设追加 `workflow_variant=v0` 或 `workflow_variant=v1`，使相同标的、日期和深度的旧调用与显式预设仍可区分。相同生效输入的显式签名稳定。不修改 SQLite 存储或恢复流程。
- **实验口径。** 显式 `v0` 是与显式 `v1` 在同一提交上运行的两轮实验对照。`baseline-v0` 是用于回归的冻结 Git 标签（指向 `b5d2f6714e98724506262cca7d38d62f4613d91b`），既不是该预设，也不是省略选择器的别名。

本决策只覆盖程序化选择器和相应离线验证，不改变 CLI、manifest、Guard、V2 路由、检查点存储或报告写入器。CLI 标签不是实际执行深度的证据。

## 历史证据与目标基线核对

1. **先红测。** C-v1-fixed-pruning-delivery-review.md 附录记录 `f4957b20fadef9809bc314be0be1a8fc0782ad08` 上的独立运行：`2 passed / 9 failed`，九项失败均因构造函数没有 `workflow_variant`。
2. **本地原型与复跑。** 定向 `11 passed`；离线回归 `1,513 passed, 1 skipped`（缺 `langchain_aws`）、`1 deselected`、`100 subtests passed`。`git diff --check` 通过。之后仅为 Ruff 对调一个等式的两侧，断言不变；Ruff 与复跑的 11 项均通过。
3. **随后独立技术审核。** D-to-C-alignment-and-v1-review.md（2026-11-22，Part B）对已有原型给出技术 `APPROVE`、交付 `APPROVE WITH EVIDENCE`。D 未运行候选；该审核不是原型实施前的批准，也不替代正式交付记录。
4. **集成复验。** C-v1-integration-verification.md 记录 `integration@0531db16a75f936c836255a5ce44986119334701` 上原候选的定向 `11 passed`；离线回归 `1,713 passed, 1 skipped`（缺 `langchain_aws`）、`1 deselected`、`100 subtests passed`、24 条警告。候选文件 Ruff 通过，全库原有 69 项诊断未变。后续 receipt 评审针对不同的集成基线和适配补丁，不是 main 的验收结果。
5. **本次 main 核对。** 原附录源补丁在目标 `main` 上通过 `git apply --check --index --whitespace=error-all`，未应用。目标 `trading_graph.py` 已包含独立的 Guard 改动，该改动不在源补丁范围内。原审核源文件哈希标识历史版本，不是目标叠加后的文件哈希。本次未运行测试。

| 固定材料 | SHA-256 |
| --- | --- |
| C-v1-fixed-pruning-delivery-review.md 附录中的原源补丁 | `951aa235a7d655595a515da0c26fc23b880f588a4b2f191fa9237bf5529979e9` |
| 原审核 `trading_graph.py`（历史候选） | `fefce348c01c29f72e70b0be4e6645e8e9e77496148b718e36f40c76b43a0274` |
| `test_v1_fixed_pruning.py`（11 项） | `6b8b412a29f7af2fc03f1b5b531b75171b39c97b03e29c0acec2fe723b4e5099` |
| `test_v1_prompt_receipts.py`（3 项） | `072581696ab832d2ace3825481fd69e83870a4e35b02734e763a2412f00e6126` |

## 分开验收

- **独立 V1。** 原 11 项不依赖 B。获授权后，在实际交付基线先复现红测，再用同一候选复跑原 11 项、旧检查点回归、全量离线套件、Ruff 与 `git diff --check`。覆盖省略和 `None`、显式 2/1 组辩论、三角色风险流程、报告及状态日志、签名和无副作用拒绝。
- **B 的 prompt receipts。** 目标 `main` 没有 `on_prompt` 构造参数或向 `GraphSetup` 的转发。原 `test_v1_prompt_receipts.py` 的省略、`v0` 和 `v1` 三项均依赖真实接线；不要替换、跳过后计为通过，或用 shim 模拟。B 接线到达后，在同一候选运行两份固定 V1 测试和已有 receipt 对照，核对真实输入的有序角色及摘要。D 的原集成裁定要求同一候选完成全部 14 项；仅通过 11 项不满足该裁定。

## 采纳与受保护源文件

这次只准备 ADR 文档，不是采纳或实施。ADR-006 需先经团队知悉并在独立文档 PR 合入 main。D（60894001）仍需针对实际 main 实施基线，明确确认原补丁和固定 11 项测试对应的计划、测试版本与修改范围，明确授权受保护的 `src/tradingagents/graph/trading_graph.py`，并明确是否允许把三项 receipt 验收到 B 接线后再做。若不确认分开验收，则沿用集成裁定的同候选门槛。D 对集成适配补丁的条件授权不自动覆盖 main 上的原补丁。正式记录由人维护，保留真实日期、范围与历史顺序；其他交付约束不因文档采纳而消失。
