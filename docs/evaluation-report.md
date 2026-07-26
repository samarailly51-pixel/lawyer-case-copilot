# 完全虚构回归评测结果

> 只验证系统输出完整性、材料忠实性、可追溯性和人工复核边界，不评价法律结论、医疗判断或真实业务效果。

| 指标 | 结果 |
|---|---:|
| 回归场景 | 9 |
| 通过场景 | 9 |
| 通过率 | 100% |
| 平均事实来源覆盖 | 100% |

| 场景 | 数据路径 | 状态 | 事实来源覆盖 | 专业字段来源覆盖 | 失败原因 |
|---|---|---|---:|---:|---|
| `contract-demo-traceability` | `demo` | 通过 | 100% | 100% | — |
| `contract-demo-review-boundary` | `demo` | 通过 | 100% | 100% | — |
| `traffic-demo-specialist` | `demo` | 通过 | 100% | 100% | — |
| `traffic-demo-evidence-gap` | `demo` | 通过 | 100% | 100% | — |
| `traffic-demo-conflict` | `demo` | 通过 | 100% | 100% | — |
| `traffic-demo-safety-boundary` | `demo` | 通过 | 100% | 100% | — |
| `traffic-real-path-material-fidelity` | `non_demo_traffic` | 通过 | 100% | 100% | — |
| `traffic-real-path-no-demo-leakage` | `non_demo_traffic` | 通过 | 100% | 100% | — |
| `contract-real-path-generic-analysis` | `non_demo_contract` | 通过 | 100% | 100% | — |

本报告由 `python -m evaluation.run_suite` 基于仓库内完全虚构数据生成。
它不构成模型准确率、法律正确率或真实业务效果声明。
