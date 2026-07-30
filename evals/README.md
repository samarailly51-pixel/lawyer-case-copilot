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
