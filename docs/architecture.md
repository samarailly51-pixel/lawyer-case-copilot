# 系统架构

## 架构决策

MVP 使用模块化单体。React SPA 调用 FastAPI；SQLAlchemy 管理 SQLite，数据库 URL 可替换为 PostgreSQL。原始文件写入本地存储目录，生产阶段再替换为对象存储。

工作流编排器按固定顺序执行节点。每个节点接受 `case_id`、`run_id` 和配置快照，输出生成记录数、警告、指标和复核要求。`AgentRun` 保存整次执行，`NodeRun` 保存单节点状态。

领域插件提供材料分类、节点和规则文件声明。MVP 包含 `general` 与 `traffic_injury`。

## 数据追溯

`SourceReference` 通过 `target_type + target_id` 连接结构化结果和材料，保存文件、页码、引用片段及偏移。系统展示五类信息：材料原文、AI 提取、AI 建议、知识检索结果、律师确认内容。

## 模型和知识库

`ModelProvider` 支持确定性 Mock 与 OpenAI-compatible API。`Retriever` 定义统一检索接口；项目不附带未经核验的法律结论。知识条目必须包含名称、时间、地区、适用范围和过期风险。

案件材料默认禁止发送至外部模型。部署者必须显式设置授权开关；模型输出中的 `document_id + quote` 会回查原始材料，不存在的引用不会落库。

文档处理为 PDF 保留页码；图片可选择本地 Tesseract OCR。`DocumentPage` 保存每页文本来源、OCR 平均置信度、识别区域坐标和图像尺寸，`DocumentQualityAssessment` 保存文档级文本质量、疑似 Prompt Injection 和人工复核要求。

工作流既支持单节点重跑，也支持从指定节点向下游恢复。每次执行都会生成新的 `NodeRun` 并记录替代关系、执行原因和尝试序号；律师已经接受或修改的结构化记录不会被自动标记为过期，新生成结果仍须重新复核。

`GET /api/cases/{case_id}/quality` 汇总材料解析率、文本质量、事实来源覆盖、事实复核、强制风险复核和知识引用状态。该评分只反映系统处理质量，不反映案件结果。

## 后续扩展

- PostgreSQL、pgvector 与生产对象存储；
- 异步任务队列和长任务取消；
- 律所多租户、RBAC、数据保留策略；
- 受控 OCR、病毒扫描和材料脱敏；
- 更多经过律师验证的领域插件。

真实案件评测采用本地离线流程。评测器仅接受已确认授权、完成脱敏、由不同人员标注和复核且状态为 `approved` 的记录，不提供公开上传接口。

## 企业化实现

认证使用 JWT，密码使用标准库 scrypt。`LawFirmWorkspace`、`WorkspaceMembership`、`CaseWorkspaceLink` 和 `KnowledgeWorkspaceLink` 提供租户与权限边界。

存储通过 `StorageBackend` 解耦本地和 S3；本地可选 AES-GCM，S3 可使用服务端 AES256。工作流支持 inline 与 background 模式，前端会轮询运行状态。报告可导出 DOCX 和 Markdown。
