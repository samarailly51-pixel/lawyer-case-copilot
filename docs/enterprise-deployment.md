# 企业部署

## 推荐拓扑

```text
TLS Reverse Proxy
  ├─ React/Nginx
  └─ FastAPI
       ├─ PostgreSQL
       ├─ S3/MinIO
       ├─ ClamAV
       ├─ OpenAI-compatible Model（可选、显式授权）
       └─ 本地 Tesseract OCR（可选）
```

`docker-compose.production.yml` 是可演示的单机生产参考，不等同于高可用集群。正式环境应使用托管 PostgreSQL、具备版本和生命周期策略的对象存储、集中密钥管理、TLS 和独立备份。

## 必需密钥

- `POSTGRES_PASSWORD`；
- `JWT_SECRET`：至少 32 字符；
- `BOOTSTRAP_ADMIN_PASSWORD`：至少 10 位，首次登录后应轮换；
- `MINIO_ROOT_USER / MINIO_ROOT_PASSWORD`；
- 模型密钥仅在确定供应商授权后配置。
- `DATA_RETENTION_DAYS`：由律所的数据分类和保留制度确定；
- 生产镜像应固定到经过验证的版本或 digest，不应长期依赖 `latest`。

## 初始化

```bash
docker compose -f docker-compose.production.yml up --build
```

后端会先运行 `alembic upgrade head`。生产准入门禁随后检查认证、JWT、PostgreSQL、对象存储、ClamAV、队列、模型边界、规则和保留周期。任一必需项失败时，后端拒绝启动。

真实案件环境必须设置 `SEED_DEMO_DATA=false`。只有与真实数据完全隔离的公开只读作品集环境可以同时设置 `PUBLIC_DEMO_MODE=true`、`PUBLIC_DEMO_READ_ONLY=true` 和 `SEED_DEMO_DATA=true`。

当前仓库的个人经验规则为空，因此默认生产 Compose **会有意拒绝启动**。项目所有者需在脱敏、核验、填写来源及适用范围后补充规则；也可在仅验证基础设施的临时环境中显式设置 `REQUIRE_PERSONAL_EXPERIENCE_RULES=false`，但不得据此宣称业务规则已就绪。

## 权限与租户

用户通过 `WorkspaceMembership` 加入律所工作空间。案件和知识资料使用独立关联表绑定工作空间。所有案件、材料、运行、复核、质量和报告接口都会验证当前工作空间；工作空间 ID 不能绕过成员身份。

## 存储

- 本地模式可以使用 AES-GCM 加密，密钥不得和数据保存在同一卷；
- S3 模式支持服务端 AES256 加密标志；
- 对象 Key 按案件隔离并使用文件哈希；
- 数据库保留 SHA-256、对象 URI 和解析元数据。

## 恶意文件扫描

上传在写入对象存储和解析之前使用 ClamAV `INSTREAM` 协议扫描。生产配置采用 fail-closed：扫描服务不可达、返回未知结果或命中病毒时均拒绝上传。扫描服务和病毒库更新状态应纳入监控。

## 后台任务

项目支持三种执行模式：`inline` 用于测试和本地 Demo，`background` 使用 FastAPI BackgroundTasks，`queue` 将 `AgentRun` 保存在数据库并由独立 `python -m services.worker` 进程领取。生产 Compose 默认使用数据库队列；Worker 异常退出后，超过恢复窗口的 claimed 任务会重新进入领取范围。

高吞吐集群仍可将相同任务边界替换为 Redis、RabbitMQ 或云队列，但不影响现有 API 和运行回放模型。

## 数据保留

清理工具只处理超过保留期、状态为 `closed/archived`、且非 Demo 的案件。它先删除对象存储文件；任一对象删除失败时保留该案件数据库记录，避免产生不可解释的半删除状态。命令默认 dry-run，执行需要双重确认参数。
