# 企业部署

## 推荐拓扑

```text
TLS Reverse Proxy
  ├─ React/Nginx
  └─ FastAPI
       ├─ PostgreSQL
       ├─ S3/MinIO
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

## 初始化

```bash
docker compose -f docker-compose.production.yml up --build
```

后端会先运行 `alembic upgrade head`。基线迁移采用非破坏方式接管既有 SQLite Demo 数据；后续 Schema 变化应创建独立 Alembic revision。

## 权限与租户

用户通过 `WorkspaceMembership` 加入律所工作空间。案件和知识资料使用独立关联表绑定工作空间。所有案件、材料、运行、复核、质量和报告接口都会验证当前工作空间；工作空间 ID 不能绕过成员身份。

## 存储

- 本地模式可以使用 AES-GCM 加密，密钥不得和数据保存在同一卷；
- S3 模式支持服务端 AES256 加密标志；
- 对象 Key 按案件隔离并使用文件哈希；
- 数据库保留 SHA-256、对象 URI 和解析元数据。

## 后台任务

项目支持三种执行模式：`inline` 用于测试和本地 Demo，`background` 使用 FastAPI BackgroundTasks，`queue` 将 `AgentRun` 保存在数据库并由独立 `python -m services.worker` 进程领取。生产 Compose 默认使用数据库队列；Worker 异常退出后，超过恢复窗口的 claimed 任务会重新进入领取范围。

高吞吐集群仍可将相同任务边界替换为 Redis、RabbitMQ 或云队列，但不影响现有 API 和运行回放模型。
