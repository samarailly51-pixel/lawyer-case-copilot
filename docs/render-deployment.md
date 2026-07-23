# Render 常驻公开 Demo 部署

本方案用于简历展示：单个 Render Web Service 同时提供 React 页面和 FastAPI API，使用完全虚构的初始化案例、Mock Provider 和服务端强制只读模式。

## 部署结构

```text
GitHub main
   ↓ checksPass
Render Starter Web Service
   ├── /            React SPA
   ├── /api/*       FastAPI
   ├── /health      健康检查
   └── /docs        API 文档
```

`render.yaml` 明确选择 `starter` 实例，避免免费实例闲置休眠。`Dockerfile.render` 在构建阶段编译前端，并在运行镜像中由 FastAPI 同域提供页面和 API。

## 公开 Demo 安全边界

- `PUBLIC_DEMO_READ_ONLY=true`：服务端拒绝创建案件、上传、分类、运行节点、复核、任务修改、知识导入和成员管理。
- 仅允许 GET/HEAD/OPTIONS，以及无持久化的知识搜索和赔偿参数情景测算。
- `MODEL_PROVIDER=mock`：不调用外部模型，不产生模型费用。
- `ALLOW_EXTERNAL_MODEL_FOR_CASE_FILES=false`：禁止发送案件材料。
- 数据库位于临时目录；由于公开服务不可写，重新部署只会恢复标准虚构 Demo。
- 不得上传或写入任何真实客户信息。

## Render 操作

1. 将仓库推送到 GitHub。
2. 登录 Render，选择 **New → Blueprint**。
3. 连接该 GitHub 仓库，Render 会读取根目录的 `render.yaml`。
4. 确认实例类型为 **Starter**，创建服务。
5. 部署完成后检查：
   - `/health` 返回 `{"status":"ok"}`；
   - `/api/cases` 返回两个虚构案例；
   - 页面顶部显示“公开只读 Demo”；
   - POST `/api/cases` 返回 `403` 和 `PUBLIC_DEMO_READ_ONLY`。

## 自定义域名

部署完成后，在 Render 服务的 **Settings → Custom Domains** 中添加：

```text
casecopilot.example.com
```

然后到域名 DNS 服务商添加 Render 提供的 CNAME/ANAME 记录并完成验证。证书由 Render 自动签发。正式写入 `render.yaml` 的 `domains` 字段前，应先确定并持有域名。

## 简历展示文案

```text
Lawyer Case Copilot｜律师案件智能助理
在线 Demo：https://casecopilot.example.com
技术栈：React、TypeScript、FastAPI、SQLAlchemy、RAG、可配置规则、Human Review
说明：完全虚构数据；公开环境只读；不构成法律意见。
```
