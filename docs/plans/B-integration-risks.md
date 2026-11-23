# B 联调风险与验收记录

日期为 2026-11-22。本批应 B 的明确要求进入团队 `integration` 供联调。代码候选为 `6817a5a`，基于 `16f8670`。以下事项仍需核实并留证。

| 风险 | 影响及联调验收 |
|---|---|
| 独立批准仍缺 | 审批脚本对 `agents/schemas.py`、`agents/managers/research_manager.py`、`agents/researchers/bear_researcher.py`、`agents/researchers/bull_researcher.py`、`b_interfaces.py`、`context_builder.py` 和 `review.py` 返回 BLOCKED，路径均相对 `src/tradingagents/`。联调推送由 B 授权，独立审核人仍需记录对应的计划、测试版本与修改范围，再复跑审批检查。 |
| 共享 schema 和主图接口仍待联调 | 共享 schema 新增评审、上下文和经理决策类型。C 需验证旧状态读入、检查点恢复、经理引用向最终输出传播，以及未决分歧保留。 |
| Prompt 回执和跨变体比较 | 2026-11-23 修订已在 v0 CLI 的离线整图验证三角色回执；经理结构化成功记录 3 次，回退记录 4 次。manifest 写入实际角色模板哈希，逐次输入摘要存入同目录 prompt_receipts.json。独立调用总数仍未知。真实供应商及跨变体 guard 仍待联调验证。 |
| 历史证据策略与真实结果待确认 | 严格模式的未知时间会在适配器返回 `UNKNOWN_TIME`。B/C/D 仍需确认整图处置并留证。真实 V0/V1/V2 manifest、完整比较结果及旧版与当前 legacy 逐字等价证据待补。 |
| 回归覆盖边界 | 原试合并 `0e05063` 默认套件 1704 通过、1 跳过、1 未选中。新的代码候选复跑 B 三个离线测试文件，33 项通过。默认套件排除了 integration 标记，并因缺少 `langchain_aws` 跳过一项。合并后的整图和真实三变体运行是本轮联调验收项。 |
