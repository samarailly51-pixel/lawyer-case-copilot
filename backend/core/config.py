from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    app_name: str = "Lawyer Case Copilot"
    app_env: str = os.getenv("APP_ENV", "development")
    public_demo_mode: bool = os.getenv("PUBLIC_DEMO_MODE", "false").lower() == "true"
    public_demo_read_only: bool = os.getenv("PUBLIC_DEMO_READ_ONLY", "false").lower() == "true"
    seed_demo_data: bool = os.getenv(
        "SEED_DEMO_DATA",
        "false" if os.getenv("APP_ENV", "development") == "production" else "true",
    ).lower() == "true"
    serve_frontend: bool = os.getenv("SERVE_FRONTEND", "false").lower() == "true"
    frontend_dist_dir: Path = Path(os.getenv("FRONTEND_DIST_DIR", "../frontend/dist"))
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./lawyer_case_copilot.db")
    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", "./storage/uploads"))
    model_provider: str = os.getenv("MODEL_PROVIDER", "mock")
    model_base_url: str = os.getenv("MODEL_BASE_URL", "https://api.openai.com/v1")
    model_api_key: str = os.getenv("MODEL_API_KEY", "")
    model_name: str = os.getenv("MODEL_NAME", "")
    model_temperature: float = float(os.getenv("MODEL_TEMPERATURE", "0.1"))
    model_timeout_seconds: int = int(os.getenv("MODEL_TIMEOUT_SECONDS", "60"))
    allow_external_model_for_case_files: bool = os.getenv("ALLOW_EXTERNAL_MODEL_FOR_CASE_FILES", "false").lower() == "true"
    ocr_provider: str = os.getenv("OCR_PROVIDER", "disabled")
    tesseract_cmd: str = os.getenv("TESSERACT_CMD", "")
    auth_mode: str = os.getenv("AUTH_MODE", "disabled")
    jwt_secret: str = os.getenv("JWT_SECRET", "development-only-secret-change-me")
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
    bootstrap_admin_email: str = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "admin@example.com")
    bootstrap_admin_password: str = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
    bootstrap_workspace_name: str = os.getenv("BOOTSTRAP_WORKSPACE_NAME", "演示律师事务所")
    storage_backend: str = os.getenv("STORAGE_BACKEND", "local")
    encrypt_uploads: bool = os.getenv("ENCRYPT_UPLOADS", "false").lower() == "true"
    storage_encryption_key: str = os.getenv("STORAGE_ENCRYPTION_KEY", "")
    s3_endpoint_url: str = os.getenv("S3_ENDPOINT_URL", "")
    s3_bucket: str = os.getenv("S3_BUCKET", "")
    s3_region: str = os.getenv("S3_REGION", "auto")
    s3_access_key_id: str = os.getenv("S3_ACCESS_KEY_ID", "")
    s3_secret_access_key: str = os.getenv("S3_SECRET_ACCESS_KEY", "")
    workflow_execution_mode: str = os.getenv("WORKFLOW_EXECUTION_MODE", "inline")
    redact_before_external_model: bool = os.getenv("REDACT_BEFORE_EXTERNAL_MODEL", "true").lower() == "true"
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "20"))
    malware_scan_provider: str = os.getenv("MALWARE_SCAN_PROVIDER", "disabled")
    malware_scan_required: bool = os.getenv("MALWARE_SCAN_REQUIRED", "false").lower() == "true"
    clamav_host: str = os.getenv("CLAMAV_HOST", "localhost")
    clamav_port: int = int(os.getenv("CLAMAV_PORT", "3310"))
    enforce_production_readiness: bool = os.getenv("ENFORCE_PRODUCTION_READINESS", "false").lower() == "true"
    require_personal_experience_rules: bool = os.getenv("REQUIRE_PERSONAL_EXPERIENCE_RULES", "false").lower() == "true"
    data_retention_days: int = int(os.getenv("DATA_RETENTION_DAYS", "0"))


settings = Settings()
