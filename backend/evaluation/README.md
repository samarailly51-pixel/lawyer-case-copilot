# Backend evaluation

当前提供案件处理质量评测，指标包括材料解析率、文本质量、事实来源覆盖、事实复核完成度、强制风险复核完成度和知识引用状态。

```bash
python -m evaluation.run_case_eval <case_id>
```

这些指标衡量流程完整性和可追溯性，不代表事实正确率、法律意见质量或案件结果。当前仍不包含真实案件或未经律师确认的标准答案。

经授权、脱敏并完成双人复核的标注可在受控环境运行：

```bash
python -m evaluation.run_labeled_eval ../private-evals/approved-cases.jsonl \
  --output ../private-evals/latest-results.json
```

评测器计算事实、缺失材料、冲突、规则命中和强制复核项的 precision、recall、F1。真实标注与结果文件均不应进入公开仓库。
