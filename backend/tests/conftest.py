from __future__ import annotations

import atexit
import os
import shutil
import tempfile
from pathlib import Path


test_root = Path(tempfile.mkdtemp(prefix="lawyer-case-copilot-tests-"))
database_path = (test_root / "test.db").as_posix()

os.environ["DATABASE_URL"] = f"sqlite:///{database_path}"
os.environ["UPLOAD_DIR"] = str(test_root / "uploads")
os.environ["MODEL_PROVIDER"] = "mock"
os.environ["ALLOW_EXTERNAL_MODEL_FOR_CASE_FILES"] = "false"
os.environ["AUTH_MODE"] = "disabled"
os.environ["PUBLIC_DEMO_MODE"] = "false"
os.environ["PUBLIC_DEMO_READ_ONLY"] = "false"

atexit.register(shutil.rmtree, test_root, True)
