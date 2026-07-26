from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from core.config import settings
from services.rules import validate_rule_file


@dataclass(frozen=True)
class ReadinessCheck:
    id: str
    status: str
    message: str


def production_readiness() -> dict:
    checks: list[ReadinessCheck] = []

    def add(check_id: str, passed: bool, message: str, *, warning: bool = False) -> None:
        checks.append(ReadinessCheck(check_id, "pass" if passed else ("warn" if warning else "fail"), message))

    add("auth", settings.auth_mode == "enabled", "生产环境必须启用登录认证。")
    add(
        "demo_data",
        not settings.seed_demo_data or settings.public_demo_mode,
        "真实案件环境不得自动写入展示案例；只有公开只读 Demo 可启用 SEED_DEMO_DATA。",
    )
    add(
        "jwt_secret",
        len(settings.jwt_secret) >= 32 and settings.jwt_secret != "development-only-secret-change-me",
        "JWT_SECRET 必须是至少 32 字符的独立随机密钥。",
    )
    add("database", settings.database_url.startswith("postgresql"), "生产环境必须使用 PostgreSQL。")
    add("object_storage", settings.storage_backend == "s3" and bool(settings.s3_bucket), "生产环境必须配置受控 S3/MinIO。")
    add("storage_encryption", settings.encrypt_uploads, "生产环境必须启用对象存储服务端加密标志。")
    add(
        "malware_scan",
        settings.malware_scan_required and settings.malware_scan_provider == "clamav",
        "上传入口必须强制启用 ClamAV 扫描。",
    )
    add("queue", settings.workflow_execution_mode == "queue", "生产环境应使用独立持久队列 Worker。")
    add(
        "external_model_boundary",
        (
            not settings.allow_external_model_for_case_files
            or (
                bool(settings.model_api_key)
                and bool(settings.model_name)
                and settings.redact_before_external_model
            )
        ),
        "如允许外部模型读取案件材料，必须配置模型、脱敏与供应商授权。",
    )
    add(
        "retention",
        settings.data_retention_days > 0,
        "尚未配置 DATA_RETENTION_DAYS；应由律所确定并演练删除策略。",
        warning=True,
    )
    root = Path(__file__).resolve().parents[1] / "rules" / "traffic_injury"
    personal = validate_rule_file(root / "personal_experience_rules.yaml")
    add("personal_rule_schema", personal.valid, "个人经验规则文件必须通过结构和来源校验。")
    if settings.require_personal_experience_rules:
        add(
            "personal_rules",
            personal.enabled_rule_count > 0,
            "生产配置已要求个人经验规则；当前必须至少有一条经律师核验并启用的规则。",
        )
    else:
        add(
            "personal_rules",
            personal.enabled_rule_count > 0,
            "当前环境未强制个人经验规则；进入律师内测前应补充并启用经核验规则。",
            warning=True,
        )
    failures = [check for check in checks if check.status == "fail"]
    return {
        "ready": not failures,
        "environment": settings.app_env,
        "checks": [asdict(check) for check in checks],
        "failure_count": len(failures),
        "warning_count": sum(check.status == "warn" for check in checks),
        "disclaimer": "该检查仅验证仓库可自动确认的配置，不替代等保、隐私、供应商合同、备份恢复和人工安全评审。",
    }


def enforce_production_readiness() -> None:
    if settings.app_env != "production" or not settings.enforce_production_readiness:
        return
    report = production_readiness()
    if not report["ready"]:
        messages = [check["message"] for check in report["checks"] if check["status"] == "fail"]
        raise RuntimeError("生产准入检查失败：" + "；".join(messages))
