# Evaluation

MVP 评测关注：字段准确性、来源引用完整率、材料冲突召回、无依据确定结论率、强制复核覆盖率和节点可重放性。后续应基于脱敏且经律师标注的案例建立评测集。

`synthetic_cases.jsonl` 是完全虚构的结构化回归集，只检查材料处理、来源覆盖、规则触发和人工复核边界，不把模型输出当作法律结论。

评测集包含 2 个完全虚构案例上的 6 个结构化回归场景。它验证材料引用、缺失材料、冲突识别、赔偿项目矩阵和人工复核边界，不用于宣称真实案件准确率或法律正确率。

运行并生成作品集报告：

```bash
cd backend
python -m evaluation.run_suite \
  --json-output ../evals/latest-results.json \
  --markdown-output ../docs/evaluation-report.md
```

新增个人经验规则后，应先为规则增加脱敏样例，再纳入该回归集。
