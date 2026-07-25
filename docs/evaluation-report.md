# 完全虚构回归评测结果

> 只验证系统输出完整性、可追溯性和人工复核边界，不评价法律结论。

| 指标 | 结果 |
|---|---:|
| 回归场景 | 6 |
| 通过场景 | 6 |
| 通过率 | 100% |
| 平均事实来源覆盖 | 100% |

| 场景 | 状态 | 来源覆盖 | 失败原因 |
|---|---|---:|---|
| `contract-demo-traceability` | 通过 | 100% | — |
| `contract-demo-review-boundary` | 通过 | 100% | — |
| `traffic-demo-specialist` | 通过 | 100% | — |
| `traffic-demo-evidence-gap` | 通过 | 100% | — |
| `traffic-demo-conflict` | 通过 | 100% | — |
| `traffic-demo-safety-boundary` | 通过 | 100% | — |

本报告由 `python -m evaluation.run_suite` 基于仓库内完全虚构 Demo 数据生成。它不构成模型准确率、法律正确率或真实业务效果声明。
