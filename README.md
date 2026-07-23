# Lawyer Case Copilot｜律师案件智能助理

面向案件负责律师的可追溯案件工作空间。项目以通用律师办案工作台为基础，并通过可插拔领域模块提供交通事故人伤案件的专业材料整理、证据检查和风险提示。

> 系统只提供办案辅助，不构成正式法律意见，不替代案件负责律师作出责任、因果关系、证据效力、鉴定或法律适用判断。

## MVP 能力

- 案件创建、类型路由、负责人及阶段管理；
- PDF、DOCX、图片、TXT/Markdown 材料上传、解析和自动分类；
- 带文件、页码和原文片段的事实提取；
- 时间线、证据矩阵、信息冲突及缺失材料提示；
- 交通事故基本信息、伤情治疗、医疗费用、保险信息整理；
- 13 类赔偿项目证据矩阵和 YAML 规则检查；
- Agent 节点状态、输入输出摘要、警告、重跑和历史运行；
- AI 结果接受、修改/驳回接口及审计日志；
- 通用案件和交通事故辅助分析报告；
- 无 API Key 可运行的确定性 Mock Provider；
- 两个完全虚构、自动加载的 Demo 案例。

第二阶段强化能力：

- PDF 页级切片和可选本地 Tesseract OCR；
- 文本质量、低 OCR 置信度和 Prompt Injection 检测；
- 外部模型案件材料发送的显式授权开关；
- 模型结构化事实抽取及原文引用逐条校验；
- 带来源、时间、地区、适用范围和核验人的知识导入 API；
- 案件质量评分、来源覆盖率和强制复核完成度。

企业化阶段能力：

- JWT 登录、scrypt 密码哈希和管理员初始化；
- 律所工作空间、多租户案件/知识隔离；
- `viewer / assistant / lawyer / admin` 四级权限；
- 本地 AES-GCM 可选加密与 S3/MinIO 兼容对象存储；
- 发往外部模型前的身份证、手机号、邮箱和银行卡号脱敏；
- 同步演示、进程内后台任务和数据库持久队列 Worker；
- DOCX、Markdown 报告导出；
- Alembic 基线迁移、PostgreSQL/MinIO 生产编排和 GitHub Actions CI。

可追溯复核增强：

- 材料文本预览、页码跳转、引用原文高亮和原始文件安全打开；
- 区分逐字匹配与近似定位，近似定位强制提示人工核对；
- 批量接受/驳回、可视化修改对比、复核历史和版本号；
- 报告材料引用目录，并同步导出到 DOCX/Markdown；
- 主体关系页、办案任务看板和任务状态更新；
- 交通事故赔偿参数情景测算，仅做输入参数的算术汇总；
- 律所成员与四级角色管理页面；
- 完全虚构的合同/交通事故结构化回归评测集。

## 技术架构

```text
React + Vite + TypeScript
           ↓
       FastAPI API
           ↓
Workflow Orchestrator → General / Traffic Injury Plugin
           ↓                    ↓
 SQLAlchemy + SQLite        YAML Rules
           ↓
SourceReference + HumanReview + AuditLog
```

MVP 采用模块化单体。节点是同一编排工作流中的结构化功能节点，并非互相对话的多个 Agent。SQLite 可通过 `DATABASE_URL` 换为 PostgreSQL。

## 本地运行

要求：Python 3.11+、Node.js 20+。

### 1. 启动后端

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

首次启动会创建 `lawyer_case_copilot.db`，并加载两个完全虚构的 Demo 案例。API 文档位于 `http://localhost:8000/docs`。

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

打开 `http://localhost:5173`。

## 简历公开 Demo

仓库包含 Render 免费公开 Demo 配置：

- `Dockerfile.render`：将 React 与 FastAPI 合并为一个同域服务；
- `render.yaml`：使用 Free 实例和 `/health` 健康检查；空闲 15 分钟后会休眠；
- `PUBLIC_DEMO_READ_ONLY=true`：服务端强制只读；
- `MODEL_PROVIDER=mock`：不调用外部模型；
- 完全虚构 Demo 数据，重新部署自动恢复。

部署方法和自定义域名步骤见 [Render 部署指南](docs/render-deployment.md)。

### 启用登录与权限

默认 `AUTH_MODE=disabled`，用于本地作品集 Demo。启用认证时设置：

```dotenv
AUTH_MODE=enabled
JWT_SECRET=请使用至少32字符的随机密钥
BOOTSTRAP_ADMIN_EMAIL=admin@your-lawfirm.com
BOOTSTRAP_ADMIN_PASSWORD=至少10位的初始密码
```

也可通过命令创建或重置管理员：

```bash
cd backend
python -m core.bootstrap_admin --email admin@your-lawfirm.com --password "your-secure-password"
```

| 角色 | 能力 |
|---|---|
| `viewer` | 查看当前工作空间案件、材料和报告 |
| `assistant` | 上传/分类材料、运行和重跑节点 |
| `lawyer` | 创建/修改案件、复核 AI 结果、维护知识资料 |
| `admin` | 律师权限以及工作空间、成员和角色管理 |

### Docker Compose

```bash
docker compose up --build
```

生产化参考编排：

```bash
docker compose -f docker-compose.production.yml up --build
```

该编排启用 PostgreSQL、MinIO、JWT 认证、S3 存储和后台工作流模式。部署前必须配置密码与密钥。

数据库迁移：

```bash
cd backend
alembic -c alembic.ini upgrade head
```

## 模型配置

默认值 `MODEL_PROVIDER=mock` 不调用外部模型。使用 OpenAI-compatible API 时，在本地 `.env` 或进程环境中设置：

```dotenv
MODEL_PROVIDER=openai-compatible
MODEL_BASE_URL=https://example.com/v1
MODEL_API_KEY=your-secret
MODEL_NAME=your-model
ALLOW_EXTERNAL_MODEL_FOR_CASE_FILES=true
```

仓库不会读取或保存密钥到数据库。模型输出必须通过结构化 Schema，且关键结果仍需人工复核。默认 `ALLOW_EXTERNAL_MODEL_FOR_CASE_FILES=false`；仅配置模型密钥不会发送案件材料，必须由部署者显式授权。

本地图片 OCR 可选启用：

```dotenv
OCR_PROVIDER=tesseract
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

运行环境还需安装 Tesseract 及中文语言包；扫描 PDF 会尝试用 `pypdfium2` 逐页渲染后进行本地 OCR。未启用或执行失败时，材料进入人工处理状态。

存储配置：

```dotenv
STORAGE_BACKEND=local
ENCRYPT_UPLOADS=true
# URL-safe Base64 编码的 32 字节密钥
STORAGE_ENCRYPTION_KEY=
```

生产环境可设置 `STORAGE_BACKEND=s3`，并配置 `S3_ENDPOINT_URL`、`S3_BUCKET` 和访问凭证。支持 AWS S3、MinIO 及其他兼容实现。

## Demo 路径

1. 打开合同纠纷案例，查看事实、时间线和证据矩阵；
2. 打开交通事故案例，查看事故责任材料原文、治疗时间线和医疗费用关联；
3. 查看住院日期与票据日期提示、缺失护理证明和因果关系人工判断项；
4. 在“Agent 执行”中查看或重跑节点；
5. 点击任一材料引用，验证页码定位和原文高亮；
6. 在“律师复核”中批量处理、修改内容并查看版本历史；
7. 在“办案任务”中更新任务状态，在“主体关系”查看关系图；
8. 在“报告中心”查看引用目录并导出带来源的辅助报告。

详见 [Demo 指南](docs/demo-guide.md)。

## 测试

```bash
cd backend
pytest -q
python -m evaluation.run_suite

cd ../frontend
npm run build
```

## 当前限制

- 默认配置仍是免登录本地 Demo；认证、多租户和 S3 需通过环境变量启用；
- 图片默认不启用 OCR，可选择本地 Tesseract，不向外部 OCR 服务发送；
- 不内置未经核实的法律法规或赔偿计算参数；
- 已有完全虚构的回归评测集，但尚无律师标注的真实脱敏领域准确率评测集；
- 不生成正式法律意见、诉状或可直接提交法院的最终文书；
- Demo 数据、机构、姓名、编号和事实均为虚构。

生产上线前仍需完成组织自身的等保/隐私合规评估、供应商数据处理协议、灾备演练、恶意文件扫描和经律师标注的领域评测。这些不能由代码仓库自行替代。

## 个人经验预留

- `backend/rules/traffic_injury/personal_experience_rules.yaml`
- `docs/traffic-injury-business-insights.md`
- `knowledge_base/traffic_injury/personal_experience/`

这些位置只包含结构说明，不包含擅自虚构的实际办案规则。

## 文档

- [产品定位](docs/product-positioning.md)
- [系统架构](docs/architecture.md)
- [通用办案工作流](docs/general-workflow.md)
- [交通事故人伤工作流](docs/traffic-injury-workflow.md)
- [人工复核](docs/human-review.md)
- [安全边界](docs/safety-boundaries.md)
- [Demo 指南](docs/demo-guide.md)
- [企业部署](docs/enterprise-deployment.md)
- [安全运维](docs/security-operations.md)
- [Render 免费公开 Demo](docs/render-deployment.md)
