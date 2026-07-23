import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_lawyer_case_copilot.db")
os.environ.setdefault("UPLOAD_DIR", "./storage/test_uploads")
os.environ.setdefault("MODEL_PROVIDER", "mock")

