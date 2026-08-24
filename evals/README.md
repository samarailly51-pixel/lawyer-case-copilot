# 评测数据说明

本目录只保存完全虚构的回归数据和自动生成的评测快照，不包含真实客户或案件信息。

## 当前文件

- `synthetic_cases.jsonl`：九个 Demo / 非 Demo 结构化回归场景；
- `latest-results.json`：最近一次自动评测的机器可读快照；
- `real_case_annotation_template.jsonl`：真实脱敏评测的空白标注模板，不包含示例事实；
- `annotation-guideline.md`：未来由项目所有者与试点律师共同确认的标注流程。

## 运行

```bash
cd backend
python -m evaluation.run_suite \
  --json-output ../evals/latest-results.json \
  --markdown-output ../docs/evaluation-report.md
```

合成评测只验证输出完整性、材料忠实性、可追溯性和人工复核边界，不代表真实案件准确率、法律正确率或业务效果。

## 真实脱敏案例离线评测

真实标注文件只应保存在受控环境，不得提交到 Git。模板通过授权、脱敏、双人复核和 `approved` 状态校验后，才会进入指标计算：

```bash
cd backend
python -m evaluation.run_labeled_eval ../private-evals/approved-cases.jsonl \
  --output ../private-evals/latest-results.json
```

输出 facts、缺失材料、冲突、规则命中和强制人工复核项的 precision、recall、F1 及宏平均 F1。指标必须连同样本量、案件分布和标注流程披露。
